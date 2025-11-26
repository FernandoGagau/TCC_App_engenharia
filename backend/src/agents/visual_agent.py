"""
Visual Agent Implementation with OpenRouter Vision API
Agent specialized in image analysis using OpenRouter Vision models
Following SOLID principles
"""

import json
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import io
import requests

from langchain.schema import HumanMessage, SystemMessage
from PIL import Image
import numpy as np

from agents.interfaces.visual_agent_interface import VisualAgentInterface
from agents.interfaces.agent_interface import AgentContext, AgentResult
from domain.value_objects.phase import Phase
from domain.value_objects.progress import Progress
from domain.exceptions.domain_exceptions import DomainException
from infrastructure.llm_service import get_llm_service
from infrastructure.config.settings import Settings
from infrastructure.config.prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)


class VisualAgent(VisualAgentInterface):
    """
    Visual Agent - OpenRouter Vision Specialist
    Uses OpenRouter's Vision API (google/gemini-2.5-flash-image-preview) for construction image analysis
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize visual agent with OpenRouter configuration"""
        self.config = config

        # Use LLMService for proper OpenRouter configuration
        llm_service = get_llm_service()
        self.model = llm_service.get_llm(model_type="vision")

        self.phase_keywords = self._load_phase_keywords()
        self.settings = Settings()

        # Load prompts from centralized YAML
        self.prompt_manager = get_prompt_manager()

        logger.info(f"Visual Agent initialized with model: {self.settings.vision_model}")

    def get_name(self) -> str:
        return "VisualAgent"

    def get_description(self) -> str:
        return "OpenRouter Vision API agent for construction image analysis"

    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent metadata and capabilities"""
        return {
            "name": self.get_name(),
            "description": self.get_description(),
            "version": "2.0.0",
            "model": self.settings.vision_model,
            "capabilities": [
                "analyze_image",
                "detect_phase",
                "calculate_progress",
                "analyze_batch_images",
                "detect_construction_phase",
                "detect_safety_issues"
            ],
            "supported_formats": ["jpg", "jpeg", "png", "bmp"]
        }

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input has required image data"""
        if 'image_path' not in input_data and 'image_base64' not in input_data:
            return False
        return True

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> AgentResult:
        """Main processing method for visual analysis"""
        try:
            if not await self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    data={},
                    message="Invalid input: image_path or image_base64 required",
                    errors=["Missing image data"]
                )

            task = input_data.get('task', 'analyze')
            image_base64 = input_data.get('image_base64')  # Optional base64 data

            if task == 'analyze':
                return await self.analyze_image(
                    input_data.get('image_path', ''),
                    context,
                    image_base64=image_base64
                )
            elif task == 'detect_phase':
                return await self.detect_phase(
                    input_data.get('image_path', ''),
                    context,
                    image_base64=image_base64
                )
            elif task == 'calculate_progress':
                return await self.calculate_progress(
                    input_data.get('image_path', ''),
                    input_data.get('location_type', 'general'),
                    context,
                    image_base64=image_base64
                )
            else:
                return AgentResult(
                    success=False,
                    data=None,
                    message=f"Unknown task: {task}",
                    errors=[f"Task {task} not supported"]
                )

        except Exception as e:
            logger.error(f"Visual agent processing error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Processing failed",
                errors=[str(e)]
            )

    async def analyze_image(self, image_path: str, context: AgentContext, image_base64: Optional[str] = None) -> AgentResult:
        """Comprehensive image analysis using OpenRouter Vision API"""
        try:
            # Use provided base64 data or encode from path
            if not image_base64:
                image_base64 = self._encode_image(image_path)
            else:
                logger.info(f"Using provided base64 data (length: {len(image_base64)})")

            # Get prompts from centralized YAML
            system_prompt = self.prompt_manager.get_prompt('visual', 'comprehensive_analysis_prompt')

            # Call OpenRouter Vision API
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": """Analise esta imagem de obra de construção civil seguindo a metodologia ISARC 2024.

IMPORTANTE: Responda APENAS com JSON válido, sem texto antes ou depois. Use o formato exato especificado no sistema.

Identifique:
1. Fase construtiva (REBAR_TYING_COLUMNS, PRE_REBAR_TYING_WALLS, REBAR_TYING_WALLS, FORMWORK_ASSEMBLY_WALLS, FORMWORK_ASSEMBLY_COLUMNS, CONCRETE_POURING, COMPLETED)
2. Elementos visíveis (ferragens, fôrmas, concreto, pilares, vigas, paredes)
3. Progresso estimado (0-100%)
4. Qualidade da execução (0-10)
5. Problemas de segurança
6. Recomendações técnicas

Responda em JSON válido começando com { e terminando com }."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                )
            ]

            response = await self.model.ainvoke(messages)

            # Parse response
            analysis = self._parse_analysis_response(response.content)

            return AgentResult(
                success=True,
                data=analysis,
                message="Imagem analisada com sucesso via OpenRouter Vision",
                confidence=analysis.get('confidence', 0.85),
                metadata={
                    'image_path': image_path,
                    'model_used': self.settings.vision_model,
                    'context': context.metadata
                }
            )

        except Exception as e:
            logger.error(f"OpenRouter Vision analysis error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Falha na análise de imagem",
                errors=[str(e)]
            )

    async def analyze_batch_images(self, image_paths: List[str]) -> AgentResult:
        """Analyze multiple images in batch using OpenRouter Vision"""
        try:
            results = []
            for image_path in image_paths:
                # Analyze each image
                context = AgentContext(metadata={'batch': True})
                result = await self.analyze_image(image_path, context)
                results.append({
                    'path': image_path,
                    'analysis': result.data if result.success else None,
                    'error': result.errors[0] if result.errors else None
                })

            # Aggregate results
            successful = [r for r in results if r['analysis']]
            failed = [r for r in results if r['error']]

            return AgentResult(
                success=len(successful) > 0,
                data={
                    'total_images': len(image_paths),
                    'successful': len(successful),
                    'failed': len(failed),
                    'results': results,
                    'summary': self._generate_batch_summary(successful)
                },
                message=f"Analisadas {len(successful)} de {len(image_paths)} imagens",
                errors=failed if failed else None
            )

        except Exception as e:
            logger.error(f"Batch analysis error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Erro na análise em lote",
                errors=[str(e)]
            )

    async def detect_construction_phase(self, image_path: str) -> AgentResult:
        """Detect current construction phase from image (alias for detect_phase)"""
        context = AgentContext(metadata={'detection_only': True})
        return await self.detect_phase(image_path, context)

    async def detect_safety_issues(self, image_path: str) -> AgentResult:
        """Detect safety issues in construction site using OpenRouter Vision"""
        try:
            image_base64 = self._encode_image(image_path)

            # Get prompts from centralized YAML
            system_prompt = self.prompt_manager.get_prompt('visual', 'safety_detection_system')

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Identifique problemas de segurança nesta imagem"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                )
            ]

            response = await self.model.ainvoke(messages)
            safety_data = self._parse_json_response(response.content)

            return AgentResult(
                success=True,
                data={
                    'safety_issues': safety_data.get('problemas', []),
                    'severity': safety_data.get('gravidade', 'unknown'),
                    'recommendations': safety_data.get('recomendacoes', []),
                    'image_path': image_path
                },
                message=f"Análise de segurança concluída - Gravidade: {safety_data.get('gravidade', 'unknown')}",
                metadata={'model_used': self.settings.vision_model}
            )

        except Exception as e:
            logger.error(f"Safety detection error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Erro na detecção de problemas de segurança",
                errors=[str(e)]
            )

    async def detect_phase(self, image_path: str, context: AgentContext, image_base64: Optional[str] = None) -> AgentResult:
        """Detect construction phase using OpenRouter Vision"""
        try:
            # Use provided base64 data or encode from path
            if not image_base64:
                image_base64 = self._encode_image(image_path)
            else:
                logger.info(f"Using provided base64 data for phase detection")

            # Get prompts from centralized YAML
            system_prompt = self.prompt_manager.get_prompt('visual', 'phase_detection_system')

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Qual a fase desta construção?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                )
            ]

            response = await self.model.ainvoke(messages)
            phase_data = self._parse_json_response(response.content)

            # Map to Phase enum
            phase_map = {
                'fundação': Phase.FOUNDATION,
                'estrutura': Phase.STRUCTURE,
                'alvenaria': Phase.MASONRY,
                'acabamento': Phase.FINISHING
            }

            detected_phase = phase_map.get(
                phase_data.get('fase', '').lower(),
                Phase.FOUNDATION
            )

            return AgentResult(
                success=True,
                data={
                    'phase': detected_phase.value,
                    'confidence': phase_data.get('confianca', 0.8),
                    'details': phase_data.get('detalhes', '')
                },
                message=f"Fase detectada: {detected_phase.value}",
                confidence=phase_data.get('confianca', 0.8)
            )

        except Exception as e:
            logger.error(f"Phase detection error: {str(e)}")
            return AgentResult(
                success=False,
                data={'phase': Phase.FOUNDATION.value, 'confidence': 0.0},
                message="Erro na detecção de fase",
                errors=[str(e)]
            )

    async def calculate_progress(
        self,
        image_path: str,
        location_type: str,
        context: AgentContext,
        image_base64: Optional[str] = None
    ) -> AgentResult:
        """Calculate construction progress using OpenRouter Vision"""
        try:
            # Use provided base64 data or encode from path
            if not image_base64:
                image_base64 = self._encode_image(image_path)
            else:
                logger.info(f"Using provided base64 data for progress calculation")

            location_context = {
                'external': 'área externa/fachada',
                'internal': 'área interna principal',
                'technical': 'área técnica (banheiro/cozinha)',
                'general': 'área geral'
            }.get(location_type, 'área geral')

            # Get prompts from centralized YAML
            system_prompt = self.prompt_manager.get_prompt(
                'visual',
                'progress_calculation_system',
                location_context=location_context
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": f"Calcule o progresso desta {location_context}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                )
            ]

            response = await self.model.ainvoke(messages)
            progress_data = self._parse_json_response(response.content)

            return AgentResult(
                success=True,
                data={
                    'progress_percentage': progress_data.get('progresso', 0),
                    'phase': progress_data.get('fase', 'unknown'),
                    'location_type': location_type,
                    'justification': progress_data.get('justificativa', '')
                },
                message=f"Progresso calculado: {progress_data.get('progresso', 0)}%",
                confidence=0.85
            )

        except Exception as e:
            logger.error(f"Progress calculation error: {str(e)}")
            return AgentResult(
                success=False,
                data={'progress_percentage': 0, 'phase': 'unknown'},
                message="Erro no cálculo de progresso",
                errors=[str(e)]
            )

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for OpenRouter Vision API"""
        try:
            # Handle both file path and base64 input
            if image_path.startswith('data:image'):
                # Already base64
                return image_path.split(',')[1]

            # Handle HTTP URLs (MinIO/S3)
            if image_path.startswith('http://') or image_path.startswith('https://'):
                logger.info(f"Downloading image from URL: {image_path}")
                response = requests.get(image_path, timeout=30)
                response.raise_for_status()
                image_data = response.content
            else:
                # Load from local file
                with open(image_path, 'rb') as f:
                    image_data = f.read()

            # Optimize image size if needed
            img = Image.open(io.BytesIO(image_data))

            # Resize if too large (OpenRouter has limits)
            max_size = (1920, 1920)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Convert to JPEG for consistency
            buffer = io.BytesIO()
            if img.mode in ('RGBA', 'LA', 'P'):
                # Convert to RGB if needed
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img

            img.save(buffer, format='JPEG', quality=85)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')

        except Exception as e:
            logger.error(f"Image encoding error: {str(e)}")
            raise

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse OpenRouter Vision response"""
        import re

        logger.info(f"🔍 Parsing vision response (length: {len(response_text)})")
        logger.info(f"📝 Response preview: {response_text[:500]}")

        try:
            # Remove markdown code blocks if present
            cleaned = response_text
            if '```json' in cleaned:
                cleaned = re.sub(r'```json\s*', '', cleaned)
            if '```' in cleaned:
                cleaned = re.sub(r'```\s*', '', cleaned)

            # Try to find JSON object
            if '{' in cleaned and '}' in cleaned:
                # Find the outermost JSON object
                json_start = cleaned.index('{')

                # Count braces to find matching closing brace
                brace_count = 0
                json_end = json_start
                for i in range(json_start, len(cleaned)):
                    if cleaned[i] == '{':
                        brace_count += 1
                    elif cleaned[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                json_str = cleaned[json_start:json_end]
                logger.info(f"📦 Extracted JSON: {json_str[:300]}...")

                parsed = json.loads(json_str)
                logger.info(f"✅ Successfully parsed JSON with keys: {list(parsed.keys())}")
                return parsed

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            logger.error(f"Failed to parse: {response_text[:300]}")
        except Exception as e:
            logger.error(f"❌ Unexpected parsing error: {e}")

        # Fallback to structured parsing
        logger.warning("⚠️ Falling back to default structure - analysis may be incomplete")
        return {
            'phase_detected': 'unknown',
            'phase_confidence': 0.0,
            'phase_details': 'Análise incompleta - resposta não parseável',
            'elements_found': [],
            'components_detected': [],
            'progress_percentage': 0,
            'progress_justification': '',
            'quality_score': 0,
            'quality_notes': '',
            'safety_issues': [],
            'safety_severity': 'unknown',
            'issues': [],
            'recommendations': ['Por favor, reenvie a imagem para nova análise'],
            'confidence': 0.0,
            'raw_response': response_text[:500]  # Store preview
        }

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from model response"""
        try:
            # Clean and extract JSON
            if '{' in response_text and '}' in response_text:
                json_start = response_text.index('{')
                json_end = response_text.rindex('}') + 1
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")

        return {}

    def _generate_batch_summary(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Generate summary from batch analysis results"""
        if not successful_results:
            return {}

        phases = []
        progress_values = []
        quality_scores = []

        for result in successful_results:
            if result['analysis']:
                analysis = result['analysis']
                if 'phase_detected' in analysis:
                    phases.append(analysis['phase_detected'])
                if 'progress_percentage' in analysis:
                    progress_values.append(analysis['progress_percentage'])
                if 'quality_score' in analysis:
                    quality_scores.append(analysis['quality_score'])

        return {
            'dominant_phase': max(set(phases), key=phases.count) if phases else 'unknown',
            'average_progress': sum(progress_values) / len(progress_values) if progress_values else 0,
            'average_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'phases_detected': list(set(phases))
        }

    def _load_phase_keywords(self) -> Dict[str, List[str]]:
        """Load keywords for phase detection"""
        return {
            'foundation': ['escavação', 'estaca', 'baldrame', 'sapata', 'radier'],
            'structure': ['pilar', 'viga', 'laje', 'ferragem', 'forma', 'concreto'],
            'masonry': ['tijolo', 'bloco', 'parede', 'vedação', 'alvenaria'],
            'finishing': ['reboco', 'pintura', 'piso', 'azulejo', 'gesso', 'forro']
        }