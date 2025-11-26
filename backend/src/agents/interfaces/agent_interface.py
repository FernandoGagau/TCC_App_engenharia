"""
Agent Interface
Base interface for all agents following SOLID principles
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class AgentContext:
    """Context passed between agents"""
    project_id: UUID
    session_id: str
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class AgentResult:
    """Result returned by agents"""
    success: bool
    data: Any
    message: Optional[str] = None
    confidence: Optional[float] = None
    errors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class IAgent(ABC):
    """Interface for all agents - Interface Segregation Principle"""

    @abstractmethod
    def get_name(self) -> str:
        """Get agent name"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get agent description"""
        pass

    @abstractmethod
    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> AgentResult:
        """Process input and return result"""
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        pass


class IVisualAgent(IAgent):
    """Interface for visual analysis agents"""

    @abstractmethod
    async def analyze_image(self, image_path: str, context: AgentContext) -> AgentResult:
        """Analyze construction image"""
        pass

    @abstractmethod
    async def detect_phase(self, image_path: str, context: AgentContext) -> AgentResult:
        """Detect construction phase from image"""
        pass

    @abstractmethod
    async def calculate_progress(self, image_path: str, location_type: str, context: AgentContext) -> AgentResult:
        """Calculate progress from image"""
        pass


class IDocumentAgent(IAgent):
    """Interface for document processing agents"""

    @abstractmethod
    async def extract_text(self, document_path: str, context: AgentContext) -> AgentResult:
        """Extract text from document"""
        pass

    @abstractmethod
    async def extract_specifications(self, document_path: str, context: AgentContext) -> AgentResult:
        """Extract technical specifications"""
        pass

    @abstractmethod
    async def parse_schedule(self, document_path: str, context: AgentContext) -> AgentResult:
        """Parse project schedule"""
        pass


class IProgressAgent(IAgent):
    """Interface for progress monitoring agents"""

    @abstractmethod
    async def calculate_overall_progress(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Calculate overall project progress"""
        pass

    @abstractmethod
    async def detect_delays(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Detect project delays"""
        pass

    @abstractmethod
    async def generate_predictions(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate completion predictions"""
        pass


class IReportAgent(IAgent):
    """Interface for report generation agents"""

    @abstractmethod
    async def generate_progress_report(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate progress report"""
        pass

    @abstractmethod
    async def generate_executive_summary(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate executive summary"""
        pass

    @abstractmethod
    async def generate_recommendations(self, project_id: UUID, context: AgentContext) -> AgentResult:
        """Generate recommendations"""
        pass