"""
Progress Agent Implementation
Agent specialized in progress monitoring and predictions
Following SOLID principles
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from uuid import UUID
import numpy as np
from sklearn.linear_model import LinearRegression

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.interfaces.agent_interface import IProgressAgent, AgentContext, AgentResult
from domain.entities.project import Project
from domain.entities.location import Location
from domain.value_objects.progress import Progress
from domain.exceptions.domain_exceptions import DomainException
from infrastructure.config.prompt_manager import get_prompt_manager
from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class ProgressAgent(IProgressAgent):
    """
    Progress Agent - Progress Monitoring Specialist
    Responsible for tracking, analyzing, and predicting project progress
    """

    def __init__(self, config: Dict[str, Any], project_repository=None):
        """Initialize progress agent with configuration"""
        self.config = config
        self.project_repository = project_repository  # Injected dependency
        settings = get_settings()
        self.model = config.get('llm')
        if self.model is None:
            self.model = ChatOpenAI(
                model=config.get('model', settings.chat_model),
                temperature=config.get('temperature', 0.2),
                max_tokens=config.get('max_tokens', 2048)
            )
        self.prediction_model = LinearRegression()  # Simple ML model for predictions
        self.thresholds = self._load_thresholds()

        # Load prompts from centralized YAML
        self.prompt_manager = get_prompt_manager()

    def get_name(self) -> str:
        return "ProgressAgent"

    def get_description(self) -> str:
        return "Specialized agent for progress monitoring, delay detection, and completion predictions"

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input has required project data"""
        if 'project_id' not in input_data:
            return False
        
        try:
            UUID(str(input_data['project_id']))
            return True
        except ValueError:
            return False

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> AgentResult:
        """Main processing method for progress analysis"""
        try:
            if not self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    data=None,
                    message="Invalid input: valid project_id required",
                    errors=["Missing or invalid project_id"]
                )

            project_id = UUID(str(input_data['project_id']))
            task = input_data.get('task', 'calculate_progress')
            
            if task == 'calculate_progress':
                return await self.calculate_overall_progress(project_id, context)
            elif task == 'detect_delays':
                return await self.detect_delays(project_id, context)
            elif task == 'generate_predictions':
                return await self.generate_predictions(project_id, context)
            elif task == 'analyze_trends':
                return await self.analyze_trends(project_id, context)
            else:
                return AgentResult(
                    success=False,
                    data=None,
                    message=f"Unknown task: {task}",
                    errors=[f"Task {task} not supported"]
                )

        except Exception as e:
            logger.error(f"Progress agent processing error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Processing failed",
                errors=[str(e)]
            )

    async def calculate_overall_progress(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Calculate overall project progress"""
        try:
            # Get project from MongoDB directly (not using DDD model)
            from infrastructure.database.project_models import ConstructionProjectModel

            doc = await ConstructionProjectModel.find_one(
                ConstructionProjectModel.project_id == str(project_id)
            )

            if not doc:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )

            # Get overall_progress directly from database (real aggregated progress)
            overall_progress = doc.overall_progress or 0.0

            cronograma_summary = {}
            activity_details = []

            if doc.metadata and doc.metadata.get('cronograma'):
                cronograma = doc.metadata['cronograma']
                cronograma_summary = cronograma.get('summary', {})

                # Extract activity details for better insights
                activities = cronograma.get('activities', {})
                for activity_name, activity_data in activities.items():
                    if isinstance(activity_data, dict):
                        expected_today = activity_data.get('expected_progress', 0)
                        actual_today = activity_data.get('actual_progress', 0)
                        history = activity_data.get('history', [])
                        activity_details.append({
                            'activity': activity_name,
                            'expected_progress_today': expected_today,
                            'actual_progress': actual_today,
                            'variance': round(actual_today - expected_today, 2),
                            'status': activity_data.get('status', 'unknown'),
                            'weight': activity_data.get('percentage', 0),
                            'has_started': activity_data.get('has_started'),
                            'is_overdue': activity_data.get('is_overdue'),
                            'last_detected': activity_data.get('last_detected'),
                            'history': history[-5:] if history else []
                        })

            expected_progress = cronograma_summary.get('expected_progress_until_today', 0)
            actual_progress = cronograma_summary.get('actual_progress', overall_progress)
            variance = cronograma_summary.get('variance', actual_progress - expected_progress)

            metrics = {
                'total_progress': actual_progress,
                'schedule_variance': variance,
                'expected_progress_until_today': expected_progress,
                'actual_progress': actual_progress,
                'activities_completed': cronograma_summary.get('total_weight_completed', 0),
                'activities_in_progress': cronograma_summary.get('total_weight_in_progress', 0),
                'activities_remaining': cronograma_summary.get('total_weight_remaining', 0),
                'reference_date': cronograma_summary.get('reference_date')
            }

            recommendations = self._generate_simple_recommendations(actual_progress, metrics, activity_details)

            return AgentResult(
                success=True,
                data={
                    'overall_progress': round(actual_progress, 2),
                    'cronograma_summary': cronograma_summary,
                    'activity_details': activity_details[:10],  # Limit to 10 for brevity
                    'metrics': metrics,
                    'variance': variance,
                    'is_on_track': metrics['schedule_variance'] >= -5,
                    'recommendations': recommendations
                },
                message=f"Overall progress: {actual_progress:.1f}% (variance {variance:+.1f}%)",
                confidence=0.90,
                metadata={'project_id': str(project_id)}
            )

        except Exception as e:
            logger.error(f"Progress calculation error: {str(e)}", exc_info=True)
            return AgentResult(
                success=False,
                data=None,
                message="Progress calculation failed",
                errors=[str(e)]
            )

    async def detect_delays(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Detect project delays and bottlenecks"""
        try:
            project = await self._get_project(project_id)
            if not project:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )
            
            delays = []
            bottlenecks = []
            
            # Check if project is delayed
            if project.is_delayed():
                if project.info and project.info.start_date and project.info.expected_completion:
                    days_elapsed = (datetime.utcnow().date() - project.info.start_date).days
                    total_days = (project.info.expected_completion - project.info.start_date).days
                    expected_progress = (days_elapsed / total_days * 100) if total_days > 0 else 0
                    
                    delays.append({
                        'type': 'project_delay',
                        'severity': 'high' if project.overall_progress.percentage < expected_progress * 0.8 else 'medium',
                        'expected_progress': expected_progress,
                        'actual_progress': project.overall_progress.percentage,
                        'delay_percentage': expected_progress - project.overall_progress.percentage,
                        'estimated_delay_days': self._estimate_delay_days(project, expected_progress)
                    })
            
            # Check location-specific delays
            for location in project.locations:
                if location.progress.percentage < 30 and location.current_phase.name not in ['planning', 'foundation']:
                    bottlenecks.append({
                        'location_id': str(location.id),
                        'location_name': location.name,
                        'issue': 'slow_progress',
                        'current_progress': location.progress.percentage,
                        'current_phase': location.current_phase.name if location.current_phase else 'unknown',
                        'recommendation': f"Accelerate work on {location.name}"
                    })
                
                # Check for quality issues
                if location.quality_score and location.quality_score < 70:
                    bottlenecks.append({
                        'location_id': str(location.id),
                        'location_name': location.name,
                        'issue': 'quality_concern',
                        'quality_score': location.quality_score,
                        'recommendation': "Review and improve quality standards"
                    })
            
            # Use AI to analyze delay patterns
            delay_analysis = await self._analyze_delay_patterns(project, delays, bottlenecks)
            
            return AgentResult(
                success=True,
                data={
                    'is_delayed': len(delays) > 0,
                    'delays': delays,
                    'bottlenecks': bottlenecks,
                    'analysis': delay_analysis,
                    'critical_path_impact': self._assess_critical_path_impact(project, bottlenecks),
                    'recovery_plan': self._generate_recovery_plan(project, delays, bottlenecks)
                },
                message=f"Detected {len(delays)} delays and {len(bottlenecks)} bottlenecks",
                confidence=0.85,
                metadata={'project_id': str(project_id)}
            )
            
        except Exception as e:
            logger.error(f"Delay detection error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Delay detection failed",
                errors=[str(e)]
            )

    async def generate_predictions(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate completion predictions using ML"""
        try:
            project = await self._get_project(project_id)
            if not project:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )
            
            # Collect historical progress data
            progress_history = self._get_progress_history(project)
            
            # Simple linear prediction
            if len(progress_history) > 2:
                X = np.array(range(len(progress_history))).reshape(-1, 1)
                y = np.array([p['progress'] for p in progress_history])
                
                self.prediction_model.fit(X, y)
                
                # Predict future progress
                future_days = 30
                future_X = np.array(range(len(progress_history), len(progress_history) + future_days)).reshape(-1, 1)
                predictions = self.prediction_model.predict(future_X)
                
                # Find completion date
                completion_index = np.where(predictions >= 100)[0]
                if len(completion_index) > 0:
                    days_to_completion = completion_index[0] + len(progress_history)
                    predicted_completion = datetime.utcnow().date() + timedelta(days=days_to_completion)
                else:
                    # Extrapolate if not reaching 100% in prediction window
                    slope = self.prediction_model.coef_[0]
                    if slope > 0:
                        days_to_completion = int((100 - project.overall_progress.percentage) / slope)
                        predicted_completion = datetime.utcnow().date() + timedelta(days=days_to_completion)
                    else:
                        predicted_completion = None
            else:
                # Fallback to simple estimation
                if project.overall_progress.percentage > 0:
                    days_elapsed = (datetime.utcnow().date() - project.info.start_date).days if project.info and project.info.start_date else 30
                    rate = project.overall_progress.percentage / days_elapsed if days_elapsed > 0 else 1
                    days_remaining = (100 - project.overall_progress.percentage) / rate if rate > 0 else 365
                    predicted_completion = datetime.utcnow().date() + timedelta(days=int(days_remaining))
                else:
                    predicted_completion = None
            
            # Generate confidence based on data quality
            confidence = self._calculate_prediction_confidence(progress_history, project)
            
            # AI-enhanced insights
            insights = await self._generate_prediction_insights(project, predicted_completion)
            
            return AgentResult(
                success=True,
                data={
                    'predicted_completion': predicted_completion.isoformat() if predicted_completion else None,
                    'original_deadline': project.info.expected_completion.isoformat() if project.info and project.info.expected_completion else None,
                    'variance_days': (predicted_completion - project.info.expected_completion).days if predicted_completion and project.info and project.info.expected_completion else None,
                    'confidence': confidence,
                    'insights': insights,
                    'risk_factors': self._identify_risk_factors(project),
                    'scenarios': self._generate_scenarios(project, predicted_completion)
                },
                message=f"Predicted completion: {predicted_completion}" if predicted_completion else "Unable to predict completion",
                confidence=confidence,
                metadata={'project_id': str(project_id)}
            )
            
        except Exception as e:
            logger.error(f"Prediction generation error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Prediction generation failed",
                errors=[str(e)]
            )

    async def analyze_trends(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Analyze progress trends and patterns"""
        try:
            project = await self._get_project(project_id)
            if not project:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )
            
            # Analyze timeline events
            trends = {
                'progress_trend': 'stable',
                'quality_trend': 'stable',
                'phase_transitions': [],
                'productivity_analysis': {},
                'seasonal_factors': []
            }
            
            # Analyze progress trend
            if project.timeline:
                progress_events = project.timeline.get_events_by_type('progress_update')
                if len(progress_events) > 1:
                    recent_progress = [e.metadata.get('new_progress', 0) for e in progress_events[-5:]]
                    if len(recent_progress) > 1:
                        if all(recent_progress[i] >= recent_progress[i-1] for i in range(1, len(recent_progress))):
                            trends['progress_trend'] = 'improving'
                        elif all(recent_progress[i] <= recent_progress[i-1] for i in range(1, len(recent_progress))):
                            trends['progress_trend'] = 'declining'
            
            # Analyze phase transitions
            for location in project.locations:
                if location.timeline:
                    phase_events = location.timeline.get_events_by_type('phase_change')
                    for event in phase_events:
                        trends['phase_transitions'].append({
                            'location': location.name,
                            'from_phase': event.metadata.get('old_phase'),
                            'to_phase': event.metadata.get('new_phase'),
                            'date': event.timestamp.isoformat()
                        })
            
            # Calculate productivity
            productivity = self._calculate_productivity(project)
            trends['productivity_analysis'] = productivity
            
            return AgentResult(
                success=True,
                data=trends,
                message="Trend analysis completed",
                confidence=0.80,
                metadata={'project_id': str(project_id)}
            )
            
        except Exception as e:
            logger.error(f"Trend analysis error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Trend analysis failed",
                errors=[str(e)]
            )

    async def _get_project(self, project_id: UUID) -> Optional[Project]:
        """Get project from repository"""
        if self.project_repository:
            return await self.project_repository.get_project(str(project_id))
        return None

    def _get_location_weights(self, project: Project) -> Dict[UUID, float]:
        """Get location weights for progress calculation"""
        weights = {}
        num_locations = len(project.locations)
        
        if num_locations == 0:
            return weights
        elif num_locations == 1:
            weights[project.locations[0].id] = 1.0
        elif num_locations == 2:
            weights[project.locations[0].id] = 0.6  # External
            weights[project.locations[1].id] = 0.4  # Internal
        else:
            # Standard 3-location weights
            weights[project.locations[0].id] = 0.4  # External
            weights[project.locations[1].id] = 0.3  # Internal
            weights[project.locations[2].id] = 0.3  # Technical
        
        return weights

    def _calculate_progress_metrics(self, project: Project, total_progress: float) -> Dict[str, Any]:
        """Calculate additional progress metrics"""
        metrics = {
            'total_progress': total_progress,
            'schedule_variance': 0,
            'cost_variance': 0,
            'quality_index': 0,
            'productivity_rate': 0
        }
        
        if project.info and project.info.start_date and project.info.expected_completion:
            days_elapsed = (datetime.utcnow().date() - project.info.start_date).days
            total_days = (project.info.expected_completion - project.info.start_date).days
            
            if total_days > 0:
                expected_progress = (days_elapsed / total_days) * 100
                metrics['schedule_variance'] = total_progress - expected_progress
                metrics['productivity_rate'] = total_progress / days_elapsed if days_elapsed > 0 else 0
        
        # Calculate quality index
        quality_scores = [loc.quality_score for loc in project.locations if loc.quality_score]
        if quality_scores:
            metrics['quality_index'] = sum(quality_scores) / len(quality_scores)
        
        return metrics

    def _generate_simple_recommendations(self, overall_progress: float, metrics: Dict[str, Any], activity_details: List[Dict]) -> List[str]:
        """Generate recommendations based on cronograma-based progress metrics"""
        recommendations = []

        # Check schedule variance
        schedule_variance = metrics.get('schedule_variance', 0)
        if schedule_variance < -10:
            recommendations.append("Obra significativamente atrasada em relação ao cronograma. Considere realocar recursos.")
        elif schedule_variance < -5:
            recommendations.append("Obra levemente atrasada. Monitore de perto e ajuste se necessário.")
        elif schedule_variance > 5:
            recommendations.append("Obra adiantada em relação ao cronograma. Mantenha o ritmo.")

        # Check activities that should be completed but aren't
        activities_behind = [
            a for a in activity_details
            if a.get('status') == 'deveria_estar_concluída' and a.get('actual_progress', 0) < 100
        ]
        if activities_behind:
            delayed_activities = ', '.join([a['activity'] for a in activities_behind[:3]])
            recommendations.append(f"Atividades atrasadas: {delayed_activities}. Priorize a conclusão destas etapas.")

        # Check activities in progress with low completion
        in_progress_low = [
            a for a in activity_details
            if a.get('status') == 'em_andamento'
            and a.get('actual_progress', 0) < a.get('expected_progress_today', 0) * 0.5
        ]
        if in_progress_low:
            slow_activities = ', '.join([a['activity'] for a in in_progress_low[:3]])
            recommendations.append(f"Atividades com progresso lento: {slow_activities}. Analise gargalos no fluxo de trabalho.")

        # Highlight activities already overdue even after updates
        overdue_activities = [
            a for a in activity_details if a.get('is_overdue') and a.get('actual_progress', 0) < 100
        ]
        if overdue_activities:
            overdue_list = ', '.join([a['activity'] for a in overdue_activities[:3]])
            recommendations.append(
                f"Atividades fora do prazo: {overdue_list}. Necessário plano de recuperação imediato."
            )

        # General progress check
        if overall_progress < 10 and metrics.get('expected_progress_until_today', 0) > 30:
            recommendations.append("Foco em acelerar as fases iniciais do projeto.")

        return recommendations if recommendations else ["Projeto progredindo conforme o planejado. Mantenha o ritmo atual."]

    def _generate_progress_recommendations(self, project: Project, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on progress metrics"""
        recommendations = []

        if metrics['schedule_variance'] < -10:
            recommendations.append("Project is significantly behind schedule. Consider resource reallocation.")
        elif metrics['schedule_variance'] < -5:
            recommendations.append("Project is slightly behind. Monitor closely and adjust if needed.")

        if metrics['quality_index'] < 70:
            recommendations.append("Quality concerns detected. Review quality control processes.")

        if metrics['productivity_rate'] < 0.5:
            recommendations.append("Low productivity detected. Analyze workflow bottlenecks.")

        return recommendations if recommendations else ["Project is progressing well. Maintain current pace."]

    def _estimate_delay_days(self, project: Project, expected_progress: float) -> int:
        """Estimate delay in days"""
        if project.overall_progress.percentage >= expected_progress:
            return 0
        
        progress_gap = expected_progress - project.overall_progress.percentage
        daily_rate = 1.0  # Assume 1% progress per day as baseline
        
        # Adjust rate based on historical data if available
        if project.timeline:
            recent_events = project.timeline.get_events_by_type('progress_update')[-10:]
            if len(recent_events) > 1:
                days_span = (recent_events[-1].timestamp - recent_events[0].timestamp).days
                progress_span = recent_events[-1].metadata.get('new_progress', 0) - recent_events[0].metadata.get('old_progress', 0)
                if days_span > 0 and progress_span > 0:
                    daily_rate = progress_span / days_span
        
        return int(progress_gap / daily_rate) if daily_rate > 0 else 30

    async def _analyze_delay_patterns(self, project: Project, delays: List, bottlenecks: List) -> Dict[str, Any]:
        """Use AI to analyze delay patterns"""

        # Get prompts from centralized YAML
        system_msg = self.prompt_manager.get_prompt('progress', 'delay_analysis_system')
        user_prompt = self.prompt_manager.get_prompt(
            'progress',
            'delay_analysis_prompt',
            delays=json.dumps(delays),
            bottlenecks=json.dumps(bottlenecks)
        )

        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.model.ainvoke(messages)
        
        return {
            'analysis': response.content,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _assess_critical_path_impact(self, project: Project, bottlenecks: List) -> str:
        """Assess impact on critical path"""
        if not bottlenecks:
            return "low"
        
        critical_locations = [b for b in bottlenecks if b.get('current_progress', 100) < 30]
        if len(critical_locations) > 1:
            return "high"
        elif len(critical_locations) == 1:
            return "medium"
        return "low"

    def _generate_recovery_plan(self, project: Project, delays: List, bottlenecks: List) -> List[Dict[str, Any]]:
        """Generate recovery plan for delays"""
        plan = []
        
        for delay in delays:
            plan.append({
                'action': 'accelerate_progress',
                'target': 'overall_project',
                'priority': 'high',
                'description': f"Increase resources to recover {delay['delay_percentage']:.1f}% progress gap"
            })
        
        for bottleneck in bottlenecks:
            plan.append({
                'action': 'resolve_bottleneck',
                'target': bottleneck.get('location_name', 'unknown'),
                'priority': 'medium' if bottleneck['issue'] == 'quality_concern' else 'high',
                'description': bottleneck.get('recommendation', 'Address bottleneck')
            })
        
        return plan

    def _get_progress_history(self, project: Project) -> List[Dict[str, Any]]:
        """Get historical progress data"""
        history = []
        
        if project.timeline:
            events = project.timeline.get_events_by_type('progress_update')
            for event in events:
                history.append({
                    'date': event.timestamp,
                    'progress': event.metadata.get('new_progress', 0)
                })
        
        # Add current state
        history.append({
            'date': datetime.utcnow(),
            'progress': project.overall_progress.percentage
        })
        
        return history

    def _calculate_prediction_confidence(self, history: List, project: Project) -> float:
        """Calculate prediction confidence based on data quality"""
        confidence = 0.5  # Base confidence
        
        # More data points increase confidence
        if len(history) > 10:
            confidence += 0.2
        elif len(history) > 5:
            confidence += 0.1
        
        # Regular updates increase confidence
        if len(history) > 1:
            days_between = [(history[i]['date'] - history[i-1]['date']).days for i in range(1, len(history))]
            avg_days = sum(days_between) / len(days_between) if days_between else 30
            if avg_days < 7:  # Weekly updates
                confidence += 0.15
            elif avg_days < 14:  # Bi-weekly updates
                confidence += 0.1
        
        # Quality data increases confidence
        if all(loc.quality_score and loc.quality_score > 70 for loc in project.locations):
            confidence += 0.1
        
        return min(confidence, 0.95)  # Cap at 95%

    async def _generate_prediction_insights(self, project: Project, predicted_completion) -> str:
        """Generate AI insights about prediction"""

        # Get prompts from centralized YAML
        system_msg = self.prompt_manager.get_prompt('progress', 'prediction_insights_system')
        user_prompt = self.prompt_manager.get_prompt(
            'progress',
            'prediction_insights_prompt',
            progress_percentage=project.overall_progress.percentage,
            predicted_completion=str(predicted_completion),
            original_deadline=str(project.info.expected_completion) if project.info else 'unknown'
        )

        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.model.ainvoke(messages)
        return response.content

    def _identify_risk_factors(self, project: Project) -> List[Dict[str, Any]]:
        """Identify risk factors for project completion"""
        risks = []
        
        # Check for slow locations
        for location in project.locations:
            if location.progress.percentage < 20:
                risks.append({
                    'type': 'slow_progress',
                    'location': location.name,
                    'severity': 'high',
                    'impact': 'Potential major delay'
                })
            elif location.quality_score and location.quality_score < 60:
                risks.append({
                    'type': 'quality_issue',
                    'location': location.name,
                    'severity': 'medium',
                    'impact': 'May require rework'
                })
        
        # Check for lack of recent updates
        if project.timeline:
            last_event = project.timeline.get_latest_event()
            if last_event and (datetime.utcnow() - last_event.timestamp).days > 14:
                risks.append({
                    'type': 'stale_data',
                    'severity': 'medium',
                    'impact': 'Predictions may be outdated'
                })
        
        return risks

    def _generate_scenarios(self, project: Project, predicted_completion) -> Dict[str, Any]:
        """Generate best/worst case scenarios"""
        scenarios = {
            'best_case': {},
            'realistic': {},
            'worst_case': {}
        }
        
        if predicted_completion:
            # Best case: 20% faster
            best_days = int((predicted_completion - datetime.utcnow().date()).days * 0.8)
            scenarios['best_case'] = {
                'completion_date': (datetime.utcnow().date() + timedelta(days=best_days)).isoformat(),
                'conditions': 'All bottlenecks resolved, resources optimized'
            }
            
            # Realistic
            scenarios['realistic'] = {
                'completion_date': predicted_completion.isoformat(),
                'conditions': 'Current pace maintained'
            }
            
            # Worst case: 50% slower
            worst_days = int((predicted_completion - datetime.utcnow().date()).days * 1.5)
            scenarios['worst_case'] = {
                'completion_date': (datetime.utcnow().date() + timedelta(days=worst_days)).isoformat(),
                'conditions': 'Additional delays, resource constraints'
            }
        
        return scenarios

    def _calculate_productivity(self, project: Project) -> Dict[str, Any]:
        """Calculate productivity metrics"""
        productivity = {
            'overall_rate': 0,
            'phase_rates': {},
            'location_rates': {}
        }
        
        if project.info and project.info.start_date:
            days_elapsed = (datetime.utcnow().date() - project.info.start_date).days
            if days_elapsed > 0:
                productivity['overall_rate'] = project.overall_progress.percentage / days_elapsed
        
        for location in project.locations:
            if location.timeline:
                duration = location.timeline.calculate_duration()
                if duration and duration > 0:
                    productivity['location_rates'][location.name] = location.progress.percentage / duration
        
        return productivity

    def _load_thresholds(self) -> Dict[str, Any]:
        """Load configuration thresholds"""
        return {
            'delay_tolerance': 0.1,  # 10% schedule variance
            'quality_minimum': 70,  # Minimum quality score
            'productivity_minimum': 0.5,  # Minimum daily progress rate
            'confidence_threshold': 0.7  # Minimum confidence for predictions
        }
