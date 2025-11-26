"""
MongoDB Models for Construction Projects
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from uuid import uuid4
from beanie import Document, Indexed
from pydantic import Field, BaseModel, field_validator


# Import timezone utilities
def _now_brazil():
    """Helper for default_factory - returns current Brazil time"""
    from infrastructure.timezone_utils import now_brazil
    return now_brazil()


class ProjectModel(BaseModel):
    """Simple project model for DDD architecture"""
    project_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    type: str
    address: str
    responsible_engineer: str
    start_date: Optional[datetime] = None
    expected_completion: Optional[datetime] = None
    overall_progress: float = 0.0
    created_at: datetime = Field(default_factory=_now_brazil)
    updated_at: datetime = Field(default_factory=_now_brazil)
    locations: List[Dict] = Field(default_factory=list)


class LocationModel(BaseModel):
    """Location model for project locations"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    progress: float = 0.0
    created_at: datetime = Field(default_factory=_now_brazil)
    images: List[str] = Field(default_factory=list)


class ConstructionPhase(str, Enum):
    """Construction phases - 28 specific activities"""
    PRUMADA = "prumada"
    ALVENARIA = "alvenaria"
    CONTRAMARCO = "contramarco"
    INSTALACOES_HIDRAULICAS = "instalacoes_hidraulicas"
    INFRA_ELETRICA = "infra_eletrica"
    FIACAO = "fiacao"
    CAIXINHAS_ELETRICAS = "caixinhas_eletricas"
    ARGAMASSA_AM = "argamassa_am"
    CONTRAPISO = "contrapiso"
    IMPERMEABILIZACAO = "impermeabilizacao"
    PROTECAO_MECANICA = "protecao_mecanica"
    GUARDA_CORPO = "guarda_corpo"
    CAPA_PEITORIL = "capa_peitoril"
    GESSO_EMBOCO = "gesso_emboco"
    GUIAS_MONTANTES_DRYWALL = "guias_montantes_drywall"
    INSTALACOES_ELETRICAS_DRYWALL = "instalacoes_eletricas_drywall"
    DRYWALL_FECHAMENTO = "drywall_fechamento"
    CERAMICA_SOLEIRA = "ceramica_soleira"
    FORRO = "forro"
    CAIXILHOS = "caixilhos"
    MASSA_PAREDES = "massa_paredes"
    DEMAO_PINTURA_FUNDO = "demao_pintura_fundo"
    PORTAS_MADEIRA = "portas_madeira"
    LOUCAS_METAIS = "loucas_metais"
    DESENGROSSO = "desengrosso"
    PINTURA_FINAL = "pintura_final"
    LIMPEZA_FINAL = "limpeza_final"
    COMUNICACAO_VISUAL = "comunicacao_visual"


class ProjectStatus(str, Enum):
    """Project status"""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BIMModel(BaseModel):
    """BIM model information"""
    file_path: str
    format: str  # IFC, RVT, etc
    version: str
    upload_date: datetime = Field(default_factory=_now_brazil)
    components: List[Dict] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Camera(BaseModel):
    """Camera configuration for monitoring"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    position: Dict[str, float]  # x, y, z
    rotation: Dict[str, float]  # pitch, yaw, roll
    fov: float = 60.0  # field of view
    resolution: str = "1920x1080"
    stream_url: Optional[str] = None
    active: bool = True


class ComponentProgress(BaseModel):
    """Progress of a construction component"""
    component_id: str
    component_type: str  # column, wall, slab, etc
    current_phase: ConstructionPhase
    detection_confidence: float
    last_updated: datetime = Field(default_factory=_now_brazil)
    detection_history: List[Dict] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)


class ConstructionProjectModel(Document):
    """MongoDB model for construction projects"""

    # Identifiers
    project_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    project_type: str = "residential"  # residential, commercial, industrial, reform, infrastructure

    # Location
    location: Dict[str, Any]

    # Timestamps
    created_at: datetime = Field(default_factory=_now_brazil)
    updated_at: datetime = Field(default_factory=_now_brazil)

    # Status
    status: ProjectStatus = ProjectStatus.PLANNING

    # BIM Integration
    bim_model: Optional[BIMModel] = None

    # Schedule
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    current_phase: Optional[ConstructionPhase] = None

    # Progress Tracking
    components: Dict[str, ComponentProgress] = Field(default_factory=dict)
    overall_progress: float = 0.0

    # Cameras & Monitoring
    cameras: List[Camera] = Field(default_factory=list)

    # Storage
    images_bucket: Optional[str] = None
    documents: List[Dict] = Field(default_factory=list)

    # Analytics
    analytics: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[Dict] = Field(default_factory=list)

    # Metadata (cronograma, custom fields, etc)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "construction_projects"
        indexes = [
            "project_id",
            "name",
            "status",
            "created_at",
            "updated_at"
        ]


class ProjectImageModel(Document):
    """MongoDB model for project images"""

    project_id: Indexed(str)
    image_id: str = Field(default_factory=lambda: str(uuid4()))

    # Image metadata
    file_path: str
    bucket: Optional[str] = None
    mime_type: str = "image/jpeg"
    size_bytes: int = 0

    # Image analysis
    phase_detected: Optional[ConstructionPhase] = None
    components_detected: List[Dict[str, Any]] = Field(default_factory=list)  # Changed from List[str] to List[Dict]
    confidence_score: float = 0.0

    # Camera info
    camera_id: Optional[str] = None
    camera_position: Optional[Dict[str, float]] = None

    # Timestamps
    captured_at: datetime = Field(default_factory=_now_brazil)
    uploaded_at: datetime = Field(default_factory=_now_brazil)
    analyzed_at: Optional[datetime] = None

    # Tags and metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('phase_detected', mode='before')
    @classmethod
    def validate_phase(cls, v):
        """Accept invalid old phase values but convert to None"""
        if v is None:
            return None

        # If it's already a valid enum, return it
        if isinstance(v, ConstructionPhase):
            return v

        # If it's a string, try to convert to enum
        if isinstance(v, str):
            try:
                return ConstructionPhase(v)
            except ValueError:
                # Invalid phase value (like 'completed' from old system) - return None
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Invalid phase_detected value '{v}' found in database - converting to None")
                return None

        return None

    class Settings:
        name = "project_images"
        indexes = [
            "project_id",
            "captured_at",
            "phase_detected",
            "camera_id"
        ]


class AnalysisReport(Document):
    """MongoDB model for detailed image analysis reports"""

    report_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: Indexed(str)
    image_id: Indexed(str)  # Reference to ProjectImageModel

    # Analysis metadata
    analyzed_at: datetime = Field(default_factory=_now_brazil)
    analyzer_model: str = "google/gemini-2.5-flash-image-preview"
    analysis_type: str = "comprehensive"  # comprehensive, phase_detection, safety, progress

    # Phase detection
    phase_detected: Optional[str] = None
    phase_confidence: float = 0.0
    phase_details: str = ""

    # Elements found
    elements_found: List[str] = Field(default_factory=list)
    components_detected: List[Dict[str, Any]] = Field(default_factory=list)

    # Progress analysis
    progress_percentage: float = 0.0
    progress_justification: str = ""

    # Quality assessment
    quality_score: float = 0.0
    quality_notes: str = ""

    # Safety issues
    safety_issues: List[Dict[str, Any]] = Field(default_factory=list)
    safety_severity: str = "unknown"  # low, medium, high, critical

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)

    # Raw analysis data
    raw_analysis: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0

    class Settings:
        name = "analysis_reports"
        indexes = [
            "project_id",
            "image_id",
            "analyzed_at",
            "analysis_type"
        ]


class ProjectAlertModel(Document):
    """MongoDB model for project alerts"""

    project_id: Indexed(str)
    alert_id: str = Field(default_factory=lambda: str(uuid4()))

    # Alert info
    type: str  # error, warning, info, success
    category: str  # delay, quality, safety, progress
    message: str
    details: Optional[str] = None

    # Status
    is_active: bool = True
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    # Resolution
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=_now_brazil)
    updated_at: datetime = Field(default_factory=_now_brazil)
    expires_at: Optional[datetime] = None

    # Metadata
    source: str = "system"  # system, user, ai
    priority: int = 0  # 0=low, 1=medium, 2=high, 3=critical
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "project_alerts"
        indexes = [
            "project_id",
            "created_at",
            "type",
            "is_active",
            "priority"
        ]


class MilestoneStatus(str, Enum):
    """Status de marco/etapa do cronograma"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class ProjectMilestone(BaseModel):
    """Modelo de marco/etapa do cronograma"""
    milestone_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    phase: ConstructionPhase
    planned_start: datetime
    planned_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    status: MilestoneStatus = MilestoneStatus.PENDING
    progress_percentage: float = 0.0
    dependencies: List[str] = Field(default_factory=list)  # IDs de outros milestones
    notes: Optional[str] = None


class ProjectScheduleModel(Document):
    """Cronograma do projeto com etapas e marcos"""
    schedule_id: Indexed(str) = Field(default_factory=lambda: str(uuid4()))
    project_id: Indexed(str)
    name: str = "Cronograma do Projeto"
    description: Optional[str] = None

    # Datas do projeto
    project_start: datetime
    project_end: datetime

    # Milestones/Etapas
    milestones: List[ProjectMilestone] = Field(default_factory=list)

    # Progresso
    overall_progress: float = 0.0
    days_elapsed: int = 0
    days_remaining: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=_now_brazil)
    updated_at: datetime = Field(default_factory=_now_brazil)

    class Settings:
        name = "project_schedules"
        indexes = [
            "schedule_id",
            "project_id",
            "created_at"
        ]