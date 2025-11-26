"""
Document Agent Implementation
Agent specialized in document processing and text extraction
Following SOLID principles
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime, date

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader as PDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pytesseract
from PIL import Image

from agents.interfaces.agent_interface import IDocumentAgent, AgentContext, AgentResult
from domain.value_objects.project_info import ProjectInfo
from domain.exceptions.domain_exceptions import DomainException
from infrastructure.config.prompt_manager import get_prompt_manager
from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class DocumentAgent(IDocumentAgent):
    """
    Document Agent - Document Processing Specialist
    Responsible for extracting and analyzing technical documents
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize document agent with configuration"""
        self.config = config
        settings = get_settings()
        self.model = config.get('llm')
        if self.model is None:
            self.model = ChatOpenAI(
                model=config.get('model', settings.chat_model),
                temperature=config.get('temperature', 0.2),
                max_tokens=config.get('max_tokens', 4096)
            )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.get('chunk_size', 2000),
            chunk_overlap=config.get('chunk_overlap', 200)
        )
        self.specification_patterns = self._load_specification_patterns()

        # Load prompts from centralized YAML
        self.prompt_manager = get_prompt_manager()

    def get_name(self) -> str:
        return "DocumentAgent"

    def get_description(self) -> str:
        return "Specialized agent for document processing, OCR, and technical specification extraction"

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input has required document data"""
        if 'document_path' not in input_data:
            return False
        
        document_path = Path(input_data['document_path'])
        if not document_path.exists():
            return False
        
        supported_formats = ['.pdf', '.txt', '.docx', '.png', '.jpg', '.jpeg']
        if document_path.suffix.lower() not in supported_formats:
            return False
        
        return True

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> AgentResult:
        """Main processing method for document analysis"""
        try:
            if not self.validate_input(input_data):
                return AgentResult(
                    success=False,
                    data=None,
                    message="Invalid input: valid document_path required",
                    errors=["Missing or invalid document"]
                )

            task = input_data.get('task', 'extract_text')
            document_path = input_data['document_path']
            
            if task == 'extract_text':
                return await self.extract_text(document_path, context)
            elif task == 'extract_specifications':
                return await self.extract_specifications(document_path, context)
            elif task == 'parse_schedule':
                return await self.parse_schedule(document_path, context)
            elif task == 'extract_project_info':
                return await self.extract_project_info(document_path, context)
            else:
                return AgentResult(
                    success=False,
                    data=None,
                    message=f"Unknown task: {task}",
                    errors=[f"Task {task} not supported"]
                )

        except Exception as e:
            logger.error(f"Document agent processing error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Processing failed",
                errors=[str(e)]
            )

    async def extract_text(self, document_path: str, context: AgentContext) -> AgentResult:
        """Extract text from document"""
        try:
            path = Path(document_path)
            text = ""
            
            if path.suffix.lower() == '.pdf':
                loader = PDFLoader(document_path)
                documents = loader.load()
                text = "\n".join([doc.page_content for doc in documents])
            
            elif path.suffix.lower() in ['.txt']:
                loader = TextLoader(document_path)
                documents = loader.load()
                text = documents[0].page_content
            
            elif path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                # OCR for images
                image = Image.open(document_path)
                text = pytesseract.image_to_string(image, lang='por')
            
            else:
                return AgentResult(
                    success=False,
                    data=None,
                    message="Unsupported document format",
                    errors=[f"Format {path.suffix} not supported"]
                )
            
            # Clean and structure text
            cleaned_text = self._clean_text(text)
            chunks = self.text_splitter.split_text(cleaned_text)
            
            return AgentResult(
                success=True,
                data={
                    'full_text': cleaned_text,
                    'chunks': chunks,
                    'word_count': len(cleaned_text.split()),
                    'page_count': len(chunks)
                },
                message="Text extracted successfully",
                metadata={'document_path': document_path}
            )
            
        except Exception as e:
            logger.error(f"Text extraction error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Text extraction failed",
                errors=[str(e)]
            )

    async def extract_specifications(self, document_path: str, context: AgentContext) -> AgentResult:
        """Extract technical specifications from document"""
        try:
            # First extract text
            text_result = await self.extract_text(document_path, context)
            if not text_result.success:
                return text_result
            
            text = text_result.data['full_text']

            # Get prompts from centralized YAML
            system_msg = self.prompt_manager.get_prompt('document', 'specification_extraction_system')
            user_prompt = self.prompt_manager.get_prompt(
                'document',
                'specification_extraction_prompt',
                text=text[:8000]  # Limit text size
            )

            messages = [
                SystemMessage(content=system_msg),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.model.ainvoke(messages)
            specifications = json.loads(response.content)
            
            return AgentResult(
                success=True,
                data=specifications,
                message="Specifications extracted successfully",
                confidence=0.85,
                metadata={'document_path': document_path}
            )
            
        except Exception as e:
            logger.error(f"Specification extraction error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Specification extraction failed",
                errors=[str(e)]
            )

    async def parse_schedule(self, document_path: str, context: AgentContext) -> AgentResult:
        """Parse project schedule from document"""
        try:
            # Extract text first
            text_result = await self.extract_text(document_path, context)
            if not text_result.success:
                return text_result
            
            text = text_result.data['full_text']

            # Get prompts from centralized YAML
            system_msg = self.prompt_manager.get_prompt('document', 'schedule_parsing_system')
            user_prompt = self.prompt_manager.get_prompt(
                'document',
                'schedule_parsing_prompt',
                text=text[:8000]
            )

            messages = [
                SystemMessage(content=system_msg),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.model.ainvoke(messages)
            schedule = json.loads(response.content)
            
            # Validate and parse dates
            schedule = self._validate_schedule_dates(schedule)
            
            return AgentResult(
                success=True,
                data=schedule,
                message="Schedule parsed successfully",
                confidence=0.80,
                metadata={'document_path': document_path}
            )
            
        except Exception as e:
            logger.error(f"Schedule parsing error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Schedule parsing failed",
                errors=[str(e)]
            )

    async def extract_project_info(self, document_path: str, context: AgentContext) -> AgentResult:
        """Extract project information to create ProjectInfo value object"""
        try:
            # Extract text
            text_result = await self.extract_text(document_path, context)
            if not text_result.success:
                return text_result
            
            text = text_result.data['full_text']

            # Get prompts from centralized YAML
            system_msg = self.prompt_manager.get_prompt('document', 'project_info_extraction_system')
            user_prompt = self.prompt_manager.get_prompt(
                'document',
                'project_info_extraction_prompt',
                text=text[:8000]
            )

            messages = [
                SystemMessage(content=system_msg),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.model.ainvoke(messages)
            info_data = json.loads(response.content)
            
            # Create ProjectInfo value object
            project_info = ProjectInfo(
                project_name=info_data['project_name'],
                project_type=info_data['project_type'],
                address=info_data['address'],
                responsible_engineer=info_data['responsible_engineer'],
                responsible_crea=info_data.get('responsible_crea'),
                start_date=self._parse_date(info_data.get('start_date')),
                expected_completion=self._parse_date(info_data.get('expected_completion')),
                budget=info_data.get('budget'),
                total_area_m2=info_data.get('total_area_m2'),
                number_of_floors=info_data.get('number_of_floors'),
                client_name=info_data.get('client_name'),
                client_contact=info_data.get('client_contact')
            )
            
            return AgentResult(
                success=True,
                data=project_info.to_dict(),
                message="Project info extracted successfully",
                confidence=0.85,
                metadata={'document_path': document_path}
            )
            
        except Exception as e:
            logger.error(f"Project info extraction error: {str(e)}")
            return AgentResult(
                success=False,
                data=None,
                message="Project info extraction failed",
                errors=[str(e)]
            )

    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep technical ones
        text = re.sub(r'[^\w\s\-\.\,\(\)\[\]\{\}\@\#\%\&\*\+\=\/\\]', '', text)
        return text.strip()

    def _load_specification_patterns(self) -> Dict[str, str]:
        """Load regex patterns for specification extraction"""
        return {
            'dimensions': r'\d+(?:\.\d+)?\s*(?:m|cm|mm|m²|m³)',
            'quantities': r'\d+(?:\.\d+)?\s*(?:un|pç|kg|ton|l)',
            'standards': r'(?:NBR|ABNT|ISO|DIN)\s*\d+',
            'concrete': r'(?:fck|FCK)\s*=?\s*\d+\s*MPa',
            'steel': r'(?:CA-50|CA-60|\d+mm)'
        }

    def _validate_schedule_dates(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and parse schedule dates"""
        try:
            if 'start_date' in schedule:
                schedule['start_date'] = self._parse_date(schedule['start_date'])
            if 'end_date' in schedule:
                schedule['end_date'] = self._parse_date(schedule['end_date'])
            
            for phase in schedule.get('phases', []):
                if 'start_date' in phase:
                    phase['start_date'] = self._parse_date(phase['start_date'])
                if 'end_date' in phase:
                    phase['end_date'] = self._parse_date(phase['end_date'])
            
            for milestone in schedule.get('milestones', []):
                if 'date' in milestone:
                    milestone['date'] = self._parse_date(milestone['date'])
        except:
            pass  # Keep original values if parsing fails
        
        return schedule

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').date()
            except:
                return None
