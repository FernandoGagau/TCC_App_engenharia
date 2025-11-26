"""
Report Agent Implementation
Agent specialized in report generation and business intelligence
Following SOLID principles
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from uuid import UUID
from pathlib import Path

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from jinja2 import Template, Environment, FileSystemLoader

# Optional dependencies for report generation
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    PLOTTING_AVAILABLE = True
except ImportError:
    plt = None
    sns = None
    pd = None
    PLOTTING_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from agents.interfaces.agent_interface import IReportAgent, AgentContext, AgentResult
from domain.entities.project import Project
from domain.exceptions.domain_exceptions import DomainException
from infrastructure.config.prompt_manager import get_prompt_manager
from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class ReportAgent(IReportAgent):
    """
    Report Agent - Business Intelligence and Reporting Specialist
    Responsible for generating reports, dashboards, and insights
    """

    def __init__(self, config: Dict[str, Any], project_repository=None):
        """Initialize report agent with configuration"""
        self.config = config
        self.project_repository = project_repository
        settings = get_settings()
        self.model = config.get('llm')
        if self.model is None:
            self.model = ChatOpenAI(
                model=config.get('model', settings.chat_model),
                temperature=config.get('temperature', 0.3),
                max_tokens=config.get('max_tokens', 4096)
            )
        self.template_path = config.get('template_path', 'templates/')
        self.output_path = config.get('output_path', 'reports/')
        self.styles = self._initialize_styles()

        # Load prompts from centralized YAML
        self.prompt_manager = get_prompt_manager()

        # Set visualization style (only if dependencies are available)
        if PLOTTING_AVAILABLE:
            sns.set_theme(style="whitegrid")
            plt.rcParams['figure.figsize'] = (10, 6)

    def get_name(self) -> str:
        return "ReportAgent"

    def get_description(self) -> str:
        return "Specialized agent for report generation, dashboards, and business intelligence"

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
        """Main processing method for report generation"""
        try:
            if not self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    data=None,
                    message="Invalid input: valid project_id required",
                    errors=["Missing or invalid project_id"]
                )

            project_id = UUID(str(input_data['project_id']))
            task = input_data.get('task', 'progress_report')
            format_type = input_data.get('format', 'json')
            
            if task == 'progress_report':
                return await self.generate_progress_report(project_id, context)
            elif task == 'executive_summary':
                return await self.generate_executive_summary(project_id, context)
            elif task == 'recommendations':
                return await self.generate_recommendations(project_id, context)
            elif task == 'dashboard':
                return await self.generate_dashboard(project_id, context)
            elif task == 'custom_report':
                return await self.generate_custom_report(
                    project_id,
                    input_data.get('template', 'default'),
                    context
                )
            else:
                return AgentResult(
                    success=False,
                    data=None,
                    message=f"Unknown task: {task}",
                    errors=[f"Task {task} not supported"]
                )

        except Exception as e:
            logger.error(f"Report agent processing error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Processing failed",
                errors=[str(e)]
            )

    async def generate_progress_report(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate comprehensive progress report"""
        try:
            project = await self._get_project(project_id)
            if not project:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )
            
            # Collect report data
            report_data = {
                'project_info': self._get_project_summary(project),
                'progress_overview': self._get_progress_overview(project),
                'location_details': self._get_location_details(project),
                'timeline_summary': self._get_timeline_summary(project),
                'quality_metrics': self._get_quality_metrics(project),
                'recommendations': project.get_recommendations(),
                'generated_at': datetime.utcnow().isoformat(),
                'report_type': 'progress_report'
            }
            
            # Generate visualizations
            charts = await self._generate_progress_charts(project)
            report_data['charts'] = charts
            
            # Generate narrative using AI
            narrative = await self._generate_narrative(report_data, 'progress')
            report_data['narrative'] = narrative
            
            # Generate PDF if requested
            pdf_path = None
            if context.metadata.get('generate_pdf', False):
                pdf_path = await self._generate_pdf_report(report_data, project_id)
                report_data['pdf_path'] = pdf_path
            
            return AgentResult(
                success=True,
                data=report_data,
                message="Progress report generated successfully",
                confidence=0.95,
                metadata={
                    'project_id': str(project_id),
                    'report_id': str(UUID()),
                    'pdf_path': pdf_path
                }
            )
            
        except Exception as e:
            logger.error(f"Progress report generation error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Progress report generation failed",
                errors=[str(e)]
            )

    async def generate_executive_summary(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate executive summary for stakeholders"""
        try:
            project = await self._get_project(project_id)
            if not project:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )
            
            # Prepare executive data
            executive_data = {
                'project_name': project.info.project_name if project.info else 'Unknown Project',
                'overall_status': self._determine_overall_status(project),
                'progress_percentage': project.overall_progress.percentage,
                'key_metrics': self._get_key_metrics(project),
                'critical_issues': self._identify_critical_issues(project),
                'upcoming_milestones': self._get_upcoming_milestones(project),
                'budget_status': self._get_budget_status(project),
                'timeline_status': self._get_timeline_status(project),
                'action_items': self._get_action_items(project)
            }
            
            # Get prompts from centralized YAML
            system_msg = self.prompt_manager.get_prompt('report', 'executive_summary_system')
            user_prompt = self.prompt_manager.get_prompt(
                'report',
                'executive_summary_prompt',
                executive_data=json.dumps(executive_data, indent=2)
            )

            messages = [
                SystemMessage(content=system_msg),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.model.ainvoke(messages)
            executive_summary = response.content
            
            # Create final summary
            summary = {
                'executive_summary': executive_summary,
                'data': executive_data,
                'generated_at': datetime.utcnow().isoformat(),
                'next_review_date': (datetime.utcnow() + timedelta(days=7)).isoformat(),
                'distribution_list': ['CEO', 'CFO', 'Project Director', 'Board']
            }
            
            return AgentResult(
                success=True,
                data=summary,
                message="Executive summary generated successfully",
                confidence=0.90,
                metadata={'project_id': str(project_id)}
            )
            
        except Exception as e:
            logger.error(f"Executive summary generation error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Executive summary generation failed",
                errors=[str(e)]
            )

    async def generate_recommendations(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate actionable recommendations"""
        try:
            project = await self._get_project(project_id)
            if not project:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )
            
            # Collect all relevant data for recommendations
            analysis_data = {
                'project_progress': project.overall_progress.percentage,
                'is_delayed': project.is_delayed(),
                'location_statuses': [
                    {
                        'name': loc.name,
                        'progress': loc.progress.percentage,
                        'phase': loc.current_phase.name if loc.current_phase else 'unknown',
                        'quality': loc.quality_score
                    }
                    for loc in project.locations
                ],
                'quality_metrics': self._get_quality_metrics(project),
                'timeline_status': self._get_timeline_status(project)
            }
            
            # Get prompts from centralized YAML
            system_msg = self.prompt_manager.get_prompt('report', 'recommendations_system')
            user_prompt = self.prompt_manager.get_prompt(
                'report',
                'recommendations_prompt',
                analysis_data=json.dumps(analysis_data, indent=2)
            )

            messages = [
                SystemMessage(content=system_msg),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.model.ainvoke(messages)
            ai_recommendations = json.loads(response.content)
            
            # Combine with rule-based recommendations
            rule_recommendations = project.get_recommendations()
            
            recommendations = {
                'ai_recommendations': ai_recommendations,
                'rule_based_recommendations': rule_recommendations,
                'priority_matrix': self._create_priority_matrix(ai_recommendations),
                'implementation_timeline': self._create_implementation_timeline(ai_recommendations),
                'expected_outcomes': self._estimate_outcomes(ai_recommendations, project),
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return AgentResult(
                success=True,
                data=recommendations,
                message="Recommendations generated successfully",
                confidence=0.85,
                metadata={'project_id': str(project_id)}
            )
            
        except Exception as e:
            logger.error(f"Recommendations generation error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Recommendations generation failed",
                errors=[str(e)]
            )

    async def generate_dashboard(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate interactive dashboard data"""
        try:
            project = await self._get_project(project_id)
            if not project:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )
            
            # Prepare dashboard components
            dashboard = {
                'kpis': {
                    'overall_progress': {
                        'value': project.overall_progress.percentage,
                        'target': self._calculate_expected_progress(project),
                        'trend': 'up',
                        'color': self._get_kpi_color(project.overall_progress.percentage)
                    },
                    'quality_index': {
                        'value': self._calculate_quality_index(project),
                        'target': 85,
                        'trend': 'stable',
                        'color': self._get_kpi_color(self._calculate_quality_index(project))
                    },
                    'schedule_performance': {
                        'value': self._calculate_schedule_performance(project),
                        'target': 100,
                        'trend': 'down' if project.is_delayed() else 'up',
                        'color': 'red' if project.is_delayed() else 'green'
                    },
                    'locations_active': {
                        'value': len(project.locations),
                        'target': 3,
                        'trend': 'stable',
                        'color': 'blue'
                    }
                },
                'charts': {
                    'progress_timeline': self._generate_timeline_chart_data(project),
                    'location_comparison': self._generate_location_comparison_data(project),
                    'phase_distribution': self._generate_phase_distribution_data(project),
                    'quality_heatmap': self._generate_quality_heatmap_data(project)
                },
                'alerts': self._generate_alerts(project),
                'recent_activities': self._get_recent_activities(project),
                'forecast': {
                    'completion_date': self._forecast_completion(project),
                    'confidence': 0.75,
                    'risks': self._identify_risks(project)
                },
                'last_updated': datetime.utcnow().isoformat()
            }
            
            return AgentResult(
                success=True,
                data=dashboard,
                message="Dashboard generated successfully",
                confidence=0.95,
                metadata={
                    'project_id': str(project_id),
                    'dashboard_id': str(UUID()),
                    'refresh_interval': 3600  # Refresh every hour
                }
            )
            
        except Exception as e:
            logger.error(f"Dashboard generation error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Dashboard generation failed",
                errors=[str(e)]
            )

    async def generate_custom_report(self, project_id: UUID, template: str, context: AgentContext) -> AgentResult:
        """Generate custom report based on template"""
        try:
            project = await self._get_project(project_id)
            if not project:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Project not found",
                    errors=[f"Project {project_id} not found"]
                )
            
            # Load template configuration
            template_config = self._load_template_config(template)
            
            # Collect data based on template requirements
            report_data = {}
            for section in template_config.get('sections', []):
                if section == 'project_info':
                    report_data['project_info'] = self._get_project_summary(project)
                elif section == 'progress':
                    report_data['progress'] = self._get_progress_overview(project)
                elif section == 'locations':
                    report_data['locations'] = self._get_location_details(project)
                elif section == 'timeline':
                    report_data['timeline'] = self._get_timeline_summary(project)
                elif section == 'quality':
                    report_data['quality'] = self._get_quality_metrics(project)
                elif section == 'recommendations':
                    report_data['recommendations'] = project.get_recommendations()
            
            # Apply template formatting
            formatted_report = self._apply_template(report_data, template_config)
            
            return AgentResult(
                success=True,
                data=formatted_report,
                message=f"Custom report '{template}' generated successfully",
                confidence=0.90,
                metadata={
                    'project_id': str(project_id),
                    'template': template
                }
            )
            
        except Exception as e:
            logger.error(f"Custom report generation error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Custom report generation failed",
                errors=[str(e)]
            )

    async def _get_project(self, project_id: UUID) -> Optional[Project]:
        """Get project from repository"""
        if self.project_repository:
            return await self.project_repository.get_project(str(project_id))
        return None

    def _get_project_summary(self, project: Project) -> Dict[str, Any]:
        """Get project summary information"""
        return {
            'id': str(project.id),
            'name': project.info.project_name if project.info else 'Unknown',
            'type': project.info.project_type if project.info else 'Unknown',
            'address': project.info.address if project.info else 'Unknown',
            'responsible': project.info.responsible_engineer if project.info else 'Unknown',
            'start_date': project.info.start_date.isoformat() if project.info and project.info.start_date else None,
            'expected_completion': project.info.expected_completion.isoformat() if project.info and project.info.expected_completion else None,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat()
        }

    def _get_progress_overview(self, project: Project) -> Dict[str, Any]:
        """Get progress overview"""
        return {
            'overall_percentage': project.overall_progress.percentage,
            'phase': project.overall_progress.phase,
            'quality_score': project.overall_progress.quality_score,
            'is_delayed': project.is_delayed(),
            'status': self._determine_overall_status(project)
        }

    def _get_location_details(self, project: Project) -> List[Dict[str, Any]]:
        """Get detailed location information"""
        return [
            {
                'id': str(loc.id),
                'name': loc.name,
                'type': loc.location_type,
                'progress': loc.progress.percentage,
                'phase': loc.current_phase.name if loc.current_phase else 'unknown',
                'quality_score': loc.quality_score,
                'last_photo': loc.last_photo_date.isoformat() if loc.last_photo_date else None,
                'elements': loc.elements_detected,
                'recommendations': loc.get_recommendations()
            }
            for loc in project.locations
        ]

    def _get_timeline_summary(self, project: Project) -> Dict[str, Any]:
        """Get timeline summary"""
        if not project.timeline:
            return {'events': [], 'duration': 0}
        
        return {
            'total_events': len(project.timeline.events),
            'duration_days': project.timeline.calculate_duration(),
            'event_frequency': project.timeline.get_event_frequency(),
            'milestones': [
                {
                    'date': e.timestamp.isoformat(),
                    'description': e.description
                }
                for e in project.timeline.get_milestones()
            ],
            'recent_events': [
                {
                    'date': e.timestamp.isoformat(),
                    'type': e.event_type,
                    'description': e.description
                }
                for e in project.timeline.events[-5:]
            ]
        }

    def _get_quality_metrics(self, project: Project) -> Dict[str, Any]:
        """Get quality metrics"""
        quality_scores = [loc.quality_score for loc in project.locations if loc.quality_score]
        
        return {
            'average_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'min_score': min(quality_scores) if quality_scores else 0,
            'max_score': max(quality_scores) if quality_scores else 0,
            'locations_with_issues': [
                loc.name for loc in project.locations
                if loc.quality_score and loc.quality_score < 70
            ]
        }

    def _determine_overall_status(self, project: Project) -> str:
        """Determine overall project status"""
        if project.overall_progress.percentage >= 100:
            return 'completed'
        elif project.is_delayed():
            return 'delayed'
        elif project.overall_progress.percentage > 0:
            return 'in_progress'
        else:
            return 'not_started'

    def _get_key_metrics(self, project: Project) -> Dict[str, Any]:
        """Get key project metrics"""
        return {
            'progress': project.overall_progress.percentage,
            'quality': self._calculate_quality_index(project),
            'schedule_performance': self._calculate_schedule_performance(project),
            'locations_active': len(project.locations)
        }

    def _identify_critical_issues(self, project: Project) -> List[str]:
        """Identify critical issues"""
        issues = []
        
        if project.is_delayed():
            issues.append("Project behind schedule")
        
        for loc in project.locations:
            if loc.quality_score and loc.quality_score < 60:
                issues.append(f"Quality issues at {loc.name}")
            if loc.progress.percentage < 20:
                issues.append(f"Slow progress at {loc.name}")
        
        return issues

    def _get_upcoming_milestones(self, project: Project) -> List[Dict[str, Any]]:
        """Get upcoming milestones"""
        # This would typically come from project schedule
        # For now, return estimated milestones
        milestones = []
        
        if project.overall_progress.percentage < 30:
            milestones.append({
                'name': 'Foundation Completion',
                'estimated_date': (datetime.utcnow() + timedelta(days=30)).isoformat()
            })
        elif project.overall_progress.percentage < 60:
            milestones.append({
                'name': 'Structure Completion',
                'estimated_date': (datetime.utcnow() + timedelta(days=60)).isoformat()
            })
        elif project.overall_progress.percentage < 90:
            milestones.append({
                'name': 'Finishing Phase',
                'estimated_date': (datetime.utcnow() + timedelta(days=45)).isoformat()
            })
        
        return milestones

    def _get_budget_status(self, project: Project) -> Dict[str, Any]:
        """Get budget status (mock implementation)"""
        return {
            'status': 'on_budget',
            'variance': 0,
            'projected': project.info.budget if project.info else 0
        }

    def _get_timeline_status(self, project: Project) -> Dict[str, Any]:
        """Get timeline status"""
        status = 'on_schedule'
        variance_days = 0
        
        if project.is_delayed():
            status = 'delayed'
            if project.info and project.info.start_date and project.info.expected_completion:
                days_elapsed = (datetime.utcnow().date() - project.info.start_date).days
                total_days = (project.info.expected_completion - project.info.start_date).days
                expected_progress = (days_elapsed / total_days * 100) if total_days > 0 else 0
                progress_gap = expected_progress - project.overall_progress.percentage
                variance_days = int(progress_gap)  # Simplified calculation
        
        return {
            'status': status,
            'variance_days': variance_days
        }

    def _get_action_items(self, project: Project) -> List[Dict[str, Any]]:
        """Get action items for executives"""
        items = []
        
        if project.is_delayed():
            items.append({
                'priority': 'high',
                'action': 'Review resource allocation',
                'owner': 'Project Manager'
            })
        
        quality_issues = [loc for loc in project.locations if loc.quality_score and loc.quality_score < 70]
        if quality_issues:
            items.append({
                'priority': 'high',
                'action': 'Quality audit required',
                'owner': 'Quality Manager'
            })
        
        return items

    async def _generate_progress_charts(self, project: Project) -> Dict[str, str]:
        """Generate progress visualization charts"""
        charts = {}

        if not PLOTTING_AVAILABLE:
            return charts

        # Progress bar chart
        fig, ax = plt.subplots()
        locations = [loc.name for loc in project.locations]
        progress = [loc.progress.percentage for loc in project.locations]

        ax.barh(locations, progress)
        ax.set_xlabel('Progress (%)')
        ax.set_title('Location Progress Comparison')
        ax.set_xlim(0, 100)

        chart_path = f"{self.output_path}progress_{project.id}.png"
        plt.savefig(chart_path)
        plt.close()
        
        charts['progress_bar'] = chart_path
        
        return charts

    async def _generate_narrative(self, report_data: Dict[str, Any], report_type: str) -> str:
        """Generate narrative description using AI"""

        # Get prompts from centralized YAML
        system_msg = self.prompt_manager.get_prompt('report', 'narrative_generation_system')
        user_prompt = self.prompt_manager.get_prompt(
            'report',
            'narrative_generation_prompt',
            report_type=report_type,
            report_data=json.dumps(report_data, indent=2)[:4000]  # Limit size
        )

        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.model.ainvoke(messages)
        return response.content

    async def _generate_pdf_report(self, report_data: Dict[str, Any], project_id: UUID) -> str:
        """Generate PDF report"""
        pdf_path = f"{self.output_path}report_{project_id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

        if not PDF_AVAILABLE:
            # Fallback to text report if PDF generation is not available
            text_path = pdf_path.replace('.pdf', '.txt')
            with open(text_path, 'w') as f:
                f.write(f"Construction Progress Report\n\n")
                f.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")
                for section, content in report_data.items():
                    f.write(f"{section.upper()}:\n{content}\n\n")
            return text_path

        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Construction Progress Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Project Info
        if 'project_info' in report_data:
            story.append(Paragraph("Project Information", styles['Heading1']))
            for key, value in report_data['project_info'].items():
                story.append(Paragraph(f"{key}: {value}", styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Progress Overview
        if 'progress_overview' in report_data:
            story.append(Paragraph("Progress Overview", styles['Heading1']))
            story.append(Paragraph(
                f"Overall Progress: {report_data['progress_overview']['overall_percentage']}%",
                styles['Normal']
            ))
            story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        
        return pdf_path

    def _initialize_styles(self) -> Dict[str, Any]:
        """Initialize report styles"""
        return {
            'colors': {
                'primary': '#1976D2',
                'secondary': '#FF9800',
                'success': '#4CAF50',
                'warning': '#FFC107',
                'danger': '#F44336'
            },
            'fonts': {
                'heading': 'Helvetica-Bold',
                'body': 'Helvetica',
                'code': 'Courier'
            }
        }

    def _calculate_quality_index(self, project: Project) -> float:
        """Calculate overall quality index"""
        quality_scores = [loc.quality_score for loc in project.locations if loc.quality_score]
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0

    def _calculate_schedule_performance(self, project: Project) -> float:
        """Calculate schedule performance index"""
        if not project.info or not project.info.start_date or not project.info.expected_completion:
            return 100
        
        days_elapsed = (datetime.utcnow().date() - project.info.start_date).days
        total_days = (project.info.expected_completion - project.info.start_date).days
        
        if total_days <= 0 or days_elapsed <= 0:
            return 100
        
        expected_progress = (days_elapsed / total_days) * 100
        actual_progress = project.overall_progress.percentage
        
        return (actual_progress / expected_progress * 100) if expected_progress > 0 else 100

    def _calculate_expected_progress(self, project: Project) -> float:
        """Calculate expected progress based on timeline"""
        if not project.info or not project.info.start_date or not project.info.expected_completion:
            return 0
        
        days_elapsed = (datetime.utcnow().date() - project.info.start_date).days
        total_days = (project.info.expected_completion - project.info.start_date).days
        
        if total_days <= 0:
            return 0
        
        return min((days_elapsed / total_days) * 100, 100)

    def _get_kpi_color(self, value: float) -> str:
        """Get KPI color based on value"""
        if value >= 90:
            return 'green'
        elif value >= 70:
            return 'yellow'
        elif value >= 50:
            return 'orange'
        else:
            return 'red'

    def _generate_timeline_chart_data(self, project: Project) -> Dict[str, Any]:
        """Generate timeline chart data"""
        return {
            'type': 'line',
            'data': {
                'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],  # Simplified
                'datasets': [{
                    'label': 'Progress',
                    'data': [10, 25, 45, project.overall_progress.percentage]
                }]
            }
        }

    def _generate_location_comparison_data(self, project: Project) -> Dict[str, Any]:
        """Generate location comparison data"""
        return {
            'type': 'bar',
            'data': {
                'labels': [loc.name for loc in project.locations],
                'datasets': [{
                    'label': 'Progress %',
                    'data': [loc.progress.percentage for loc in project.locations]
                }]
            }
        }

    def _generate_phase_distribution_data(self, project: Project) -> Dict[str, Any]:
        """Generate phase distribution data"""
        phase_counts = {}
        for loc in project.locations:
            if loc.current_phase:
                phase = loc.current_phase.name
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        return {
            'type': 'pie',
            'data': {
                'labels': list(phase_counts.keys()),
                'datasets': [{
                    'data': list(phase_counts.values())
                }]
            }
        }

    def _generate_quality_heatmap_data(self, project: Project) -> Dict[str, Any]:
        """Generate quality heatmap data"""
        return {
            'type': 'heatmap',
            'data': [
                {
                    'location': loc.name,
                    'quality': loc.quality_score if loc.quality_score else 0
                }
                for loc in project.locations
            ]
        }

    def _generate_alerts(self, project: Project) -> List[Dict[str, Any]]:
        """Generate system alerts"""
        alerts = []
        
        if project.is_delayed():
            alerts.append({
                'type': 'warning',
                'message': 'Project is behind schedule',
                'severity': 'high'
            })
        
        for loc in project.locations:
            if loc.quality_score and loc.quality_score < 60:
                alerts.append({
                    'type': 'danger',
                    'message': f'Quality issues at {loc.name}',
                    'severity': 'high'
                })
        
        return alerts

    def _get_recent_activities(self, project: Project) -> List[Dict[str, Any]]:
        """Get recent project activities"""
        activities = []
        
        if project.timeline:
            for event in project.timeline.events[-10:]:
                activities.append({
                    'date': event.timestamp.isoformat(),
                    'type': event.event_type,
                    'description': event.description
                })
        
        return activities

    def _forecast_completion(self, project: Project) -> Optional[str]:
        """Forecast project completion date"""
        if project.overall_progress.percentage >= 100:
            return datetime.utcnow().date().isoformat()
        
        if project.overall_progress.percentage == 0:
            return None
        
        # Simple linear forecast
        if project.info and project.info.start_date:
            days_elapsed = (datetime.utcnow().date() - project.info.start_date).days
            if days_elapsed > 0 and project.overall_progress.percentage > 0:
                rate = project.overall_progress.percentage / days_elapsed
                remaining = 100 - project.overall_progress.percentage
                days_to_complete = remaining / rate if rate > 0 else 365
                
                return (datetime.utcnow().date() + timedelta(days=int(days_to_complete))).isoformat()
        
        return None

    def _identify_risks(self, project: Project) -> List[Dict[str, Any]]:
        """Identify project risks"""
        risks = []
        
        if project.is_delayed():
            risks.append({
                'type': 'schedule',
                'description': 'Project delay risk',
                'probability': 'high',
                'impact': 'high'
            })
        
        quality_issues = [loc for loc in project.locations if loc.quality_score and loc.quality_score < 70]
        if quality_issues:
            risks.append({
                'type': 'quality',
                'description': 'Quality standard risk',
                'probability': 'medium',
                'impact': 'medium'
            })
        
        return risks

    def _create_priority_matrix(self, recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Create priority matrix for recommendations"""
        # Simplified priority matrix
        return {
            'high_impact_high_effort': [],
            'high_impact_low_effort': [],
            'low_impact_high_effort': [],
            'low_impact_low_effort': []
        }

    def _create_implementation_timeline(self, recommendations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create implementation timeline for recommendations"""
        # Simplified timeline
        return [
            {
                'week': 1,
                'actions': ['Immediate actions']
            },
            {
                'week': 2,
                'actions': ['Resource optimization']
            },
            {
                'week': 3,
                'actions': ['Quality improvements']
            }
        ]

    def _estimate_outcomes(self, recommendations: Dict[str, Any], project: Project) -> Dict[str, Any]:
        """Estimate outcomes of recommendations"""
        return {
            'expected_progress_improvement': '10-15%',
            'quality_improvement': '5-10 points',
            'schedule_recovery': '7-14 days'
        }

    def _load_template_config(self, template: str) -> Dict[str, Any]:
        """Load template configuration"""
        # Simplified template loading
        return {
            'name': template,
            'sections': ['project_info', 'progress', 'locations', 'recommendations']
        }

    def _apply_template(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply template formatting to data"""
        # Simplified template application
        return {
            'template': config['name'],
            'data': data,
            'formatted': True
        }
