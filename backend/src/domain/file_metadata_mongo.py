"""
MongoDB Models for File Storage Metadata
Complete schema for file management and quota tracking
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from beanie import Document
from pymongo import IndexModel


class FileCategory(str, Enum):
    """Categorias de arquivos"""
    CONSTRUCTION = "construction"
    BIM = "bim"
    DOCUMENT = "document"
    REPORT = "report"
    IMAGE = "image"
    GENERAL = "general"


class ProcessingStatus(str, Enum):
    """Status de processamento do arquivo"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SecurityScanStatus(str, Enum):
    """Status do scan de segurança"""
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    SUSPICIOUS = "suspicious"
    ERROR = "error"


class ImageDimensions(BaseModel):
    """Dimensões de imagem"""
    width: int = Field(..., ge=1, description="Largura em pixels")
    height: int = Field(..., ge=1, description="Altura em pixels")


class ThumbnailInfo(BaseModel):
    """Informações de thumbnail"""
    small: Optional[str] = Field(None, description="Path do thumbnail pequeno (150x150)")
    medium: Optional[str] = Field(None, description="Path do thumbnail médio (500x500)")
    large: Optional[str] = Field(None, description="Path do thumbnail grande (1024x1024)")


class ExifData(BaseModel):
    """Dados EXIF de imagens"""
    camera_make: Optional[str] = Field(None, description="Fabricante da câmera")
    camera_model: Optional[str] = Field(None, description="Modelo da câmera")
    datetime_original: Optional[str] = Field(None, description="Data/hora original")
    gps_latitude: Optional[float] = Field(None, description="Latitude GPS")
    gps_longitude: Optional[float] = Field(None, description="Longitude GPS")
    gps_altitude: Optional[float] = Field(None, description="Altitude GPS")
    focal_length: Optional[str] = Field(None, description="Distância focal")
    iso_speed: Optional[int] = Field(None, description="ISO da foto")
    aperture: Optional[str] = Field(None, description="Abertura do diafragma")
    shutter_speed: Optional[str] = Field(None, description="Velocidade do obturador")
    flash: Optional[str] = Field(None, description="Informações do flash")
    orientation: Optional[int] = Field(None, description="Orientação da imagem")


class QualityMetrics(BaseModel):
    """Métricas de qualidade de imagem"""
    brightness: Optional[float] = Field(None, description="Brilho médio (0-255)")
    contrast: Optional[float] = Field(None, description="Contraste")
    sharpness: Optional[str] = Field(None, description="Nitidez (high/medium/low)")
    saturation: Optional[float] = Field(None, description="Saturação (%)")
    blur_score: Optional[float] = Field(None, description="Score de desfoque")
    overall_quality: Optional[str] = Field(None, description="Qualidade geral")
    quality_score: Optional[int] = Field(None, ge=0, le=100, description="Score de qualidade (0-100)")


class FileMetadata(BaseModel):
    """Metadados adicionais do arquivo"""
    content_hash: str = Field(..., description="Hash SHA-256 do conteúdo")
    exif_data: Optional[ExifData] = Field(None, description="Dados EXIF (imagens)")
    ocr_text: Optional[str] = Field(None, description="Texto extraído via OCR")
    quality_metrics: Optional[QualityMetrics] = Field(None, description="Métricas de qualidade")
    virus_scan: SecurityScanStatus = Field(SecurityScanStatus.PENDING, description="Status do scan de segurança")
    virus_scan_date: Optional[datetime] = Field(None, description="Data do scan de segurança")
    processing_info: Dict[str, Any] = Field(default_factory=dict, description="Informações de processamento")


class FileStorage(Document):
    """
    Documento principal para metadados de arquivos
    Armazena informações completas sobre arquivos no MinIO
    """

    # Identificação
    file_id: str = Field(..., description="UUID único do arquivo")
    project_id: str = Field(..., description="ID do projeto associado")
    user_id: str = Field(..., description="ID do usuário que fez upload")

    # Informações do arquivo
    original_name: str = Field(..., description="Nome original do arquivo")
    stored_name: str = Field(..., description="Nome do arquivo no storage (UUID + extensão)")
    category: FileCategory = Field(FileCategory.GENERAL, description="Categoria do arquivo")

    # Localização no storage
    bucket: str = Field(..., description="Bucket MinIO onde está armazenado")
    path: str = Field(..., description="Caminho completo no bucket")

    # Propriedades técnicas
    mime_type: str = Field(..., description="Tipo MIME do arquivo")
    size_bytes: int = Field(..., ge=0, description="Tamanho em bytes")
    dimensions: Optional[ImageDimensions] = Field(None, description="Dimensões (para imagens)")

    # Thumbnails (para imagens)
    thumbnails: ThumbnailInfo = Field(default_factory=ThumbnailInfo, description="Caminhos dos thumbnails")

    # Metadados avançados
    metadata: FileMetadata = Field(..., description="Metadados adicionais")

    # Controle de processamento
    processing_status: ProcessingStatus = Field(ProcessingStatus.PENDING, description="Status de processamento")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Data de criação")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Data de atualização")
    expires_at: Optional[datetime] = Field(None, description="Data de expiração (opcional)")

    # Tags e classificação
    tags: List[str] = Field(default_factory=list, description="Tags do arquivo")

    # Versioning
    version: int = Field(1, description="Versão do arquivo")
    parent_file_id: Optional[str] = Field(None, description="ID do arquivo pai (para versões)")

    # Controle de acesso
    is_public: bool = Field(False, description="Arquivo público")
    access_permissions: List[str] = Field(default_factory=list, description="Permissões de acesso")

    class Settings:
        name = "file_storage"

        # Índices para performance
        indexes = [
            IndexModel([("file_id",)], unique=True),
            IndexModel([("project_id",)]),
            IndexModel([("user_id",)]),
            IndexModel([("bucket", "path")]),
            IndexModel([("category",)]),
            IndexModel([("mime_type",)]),
            IndexModel([("created_at",)]),
            IndexModel([("metadata.content_hash",)]),
            IndexModel([("tags",)]),
            IndexModel([("processing_status",)]),
            # Índice composto para busca por projeto e categoria
            IndexModel([("project_id", "category")]),
            # Índice TTL para expiração automática
            IndexModel([("expires_at",)], expireAfterSeconds=0),
        ]

    def __str__(self) -> str:
        return f"FileStorage(file_id={self.file_id}, name={self.original_name})"

    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário"""
        return {
            "file_id": self.file_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "original_name": self.original_name,
            "stored_name": self.stored_name,
            "category": self.category,
            "bucket": self.bucket,
            "path": self.path,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "dimensions": self.dimensions.dict() if self.dimensions else None,
            "thumbnails": self.thumbnails.dict(),
            "metadata": self.metadata.dict(),
            "processing_status": self.processing_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "tags": self.tags,
            "version": self.version,
            "parent_file_id": self.parent_file_id,
            "is_public": self.is_public,
            "access_permissions": self.access_permissions
        }

    async def update_metadata(self, **kwargs) -> None:
        """Atualizar metadados do arquivo"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.updated_at = datetime.now(timezone.utc)
        await self.save()

    async def add_tag(self, tag: str) -> None:
        """Adicionar tag ao arquivo"""
        if tag not in self.tags:
            self.tags.append(tag)
            await self.update_metadata()

    async def remove_tag(self, tag: str) -> None:
        """Remover tag do arquivo"""
        if tag in self.tags:
            self.tags.remove(tag)
            await self.update_metadata()

    @classmethod
    async def find_by_project(
        cls,
        project_id: str,
        category: Optional[FileCategory] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List["FileStorage"]:
        """Buscar arquivos por projeto"""
        query = {"project_id": project_id}
        if category:
            query["category"] = category

        return await cls.find(query).skip(skip).limit(limit).to_list()

    @classmethod
    async def find_by_content_hash(cls, content_hash: str) -> Optional["FileStorage"]:
        """Buscar arquivo por hash do conteúdo (deduplicação)"""
        return await cls.find_one({"metadata.content_hash": content_hash})

    @classmethod
    async def get_project_stats(cls, project_id: str) -> Dict[str, Any]:
        """Obter estatísticas de arquivos do projeto"""
        pipeline = [
            {"$match": {"project_id": project_id}},
            {
                "$group": {
                    "_id": None,
                    "total_files": {"$sum": 1},
                    "total_size": {"$sum": "$size_bytes"},
                    "by_category": {
                        "$push": {
                            "category": "$category",
                            "size": "$size_bytes"
                        }
                    }
                }
            }
        ]

        result = await cls.aggregate(pipeline).to_list()
        return result[0] if result else {}


class EntityType(str, Enum):
    """Tipos de entidade para quota"""
    USER = "user"
    PROJECT = "project"
    ORGANIZATION = "organization"


class StorageQuota(Document):
    """
    Documento para controle de quotas de armazenamento
    Rastreia uso por usuário, projeto ou organização
    """

    # Identificação da entidade
    entity_id: str = Field(..., description="ID da entidade (user_id, project_id, etc)")
    entity_type: EntityType = Field(..., description="Tipo da entidade")

    # Quotas
    used_bytes: int = Field(0, ge=0, description="Bytes utilizados")
    quota_bytes: int = Field(..., gt=0, description="Quota máxima em bytes")
    file_count: int = Field(0, ge=0, description="Número de arquivos")
    max_file_count: Optional[int] = Field(None, description="Limite máximo de arquivos")

    # Estatísticas por categoria
    usage_by_category: Dict[str, int] = Field(default_factory=dict, description="Uso por categoria")

    # Controle temporal
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Última atualização")

    # Alertas e avisos
    warnings: List[str] = Field(default_factory=list, description="Avisos de quota")
    alert_threshold: float = Field(0.8, description="Limite para alerta (% da quota)")

    # Configurações
    auto_cleanup: bool = Field(False, description="Limpeza automática quando quota excedida")
    cleanup_strategy: str = Field("oldest_first", description="Estratégia de limpeza")

    class Settings:
        name = "storage_quota"

        indexes = [
            IndexModel([("entity_id", "entity_type")], unique=True),
            IndexModel([("entity_type",)]),
            IndexModel([("last_updated",)]),
        ]

    def __str__(self) -> str:
        return f"StorageQuota(entity={self.entity_id}, used={self.used_bytes}/{self.quota_bytes})"

    @property
    def usage_percentage(self) -> float:
        """Percentual de uso da quota"""
        return (self.used_bytes / self.quota_bytes) * 100 if self.quota_bytes > 0 else 0.0

    @property
    def is_over_limit(self) -> bool:
        """Verifica se está acima do limite"""
        return self.used_bytes > self.quota_bytes

    @property
    def is_near_limit(self) -> bool:
        """Verifica se está próximo do limite"""
        return self.usage_percentage >= (self.alert_threshold * 100)

    @property
    def available_bytes(self) -> int:
        """Bytes disponíveis"""
        return max(0, self.quota_bytes - self.used_bytes)

    async def add_usage(self, size_bytes: int, category: Optional[str] = None) -> None:
        """Adicionar uso à quota"""
        self.used_bytes += size_bytes
        self.file_count += 1

        if category:
            if category not in self.usage_by_category:
                self.usage_by_category[category] = 0
            self.usage_by_category[category] += size_bytes

        self.last_updated = datetime.now(timezone.utc)

        # Verificar alertas
        await self._check_alerts()
        await self.save()

    async def remove_usage(self, size_bytes: int, category: Optional[str] = None) -> None:
        """Remover uso da quota"""
        self.used_bytes = max(0, self.used_bytes - size_bytes)
        self.file_count = max(0, self.file_count - 1)

        if category and category in self.usage_by_category:
            self.usage_by_category[category] = max(0, self.usage_by_category[category] - size_bytes)

        self.last_updated = datetime.now(timezone.utc)
        await self.save()

    async def _check_alerts(self) -> None:
        """Verificar e atualizar alertas"""
        self.warnings.clear()

        if self.is_over_limit:
            self.warnings.append("quota_exceeded")
        elif self.is_near_limit:
            self.warnings.append("quota_warning")

        if self.max_file_count and self.file_count >= self.max_file_count:
            self.warnings.append("file_count_limit")

    async def can_add_file(self, size_bytes: int) -> bool:
        """Verificar se pode adicionar arquivo"""
        if self.used_bytes + size_bytes > self.quota_bytes:
            return False

        if self.max_file_count and self.file_count >= self.max_file_count:
            return False

        return True

    @classmethod
    async def get_or_create_quota(
        cls,
        entity_id: str,
        entity_type: EntityType,
        default_quota_bytes: int = 5 * 1024 * 1024 * 1024  # 5GB default
    ) -> "StorageQuota":
        """Obter ou criar quota para entidade"""
        quota = await cls.find_one({"entity_id": entity_id, "entity_type": entity_type})

        if not quota:
            quota = cls(
                entity_id=entity_id,
                entity_type=entity_type,
                quota_bytes=default_quota_bytes
            )
            await quota.insert()

        return quota

    @classmethod
    async def get_system_stats(cls) -> Dict[str, Any]:
        """Obter estatísticas globais do sistema"""
        pipeline = [
            {
                "$group": {
                    "_id": "$entity_type",
                    "total_entities": {"$sum": 1},
                    "total_used": {"$sum": "$used_bytes"},
                    "total_quota": {"$sum": "$quota_bytes"},
                    "total_files": {"$sum": "$file_count"}
                }
            }
        ]

        result = await cls.aggregate(pipeline).to_list()
        return {item["_id"]: item for item in result}


class FileAccessLog(Document):
    """
    Log de acesso a arquivos para auditoria
    """

    file_id: str = Field(..., description="ID do arquivo acessado")
    user_id: str = Field(..., description="ID do usuário que acessou")
    action: str = Field(..., description="Ação realizada (view, download, upload, delete)")
    ip_address: Optional[str] = Field(None, description="Endereço IP")
    user_agent: Optional[str] = Field(None, description="User agent")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp do acesso")
    success: bool = Field(True, description="Se a ação foi bem-sucedida")
    error_message: Optional[str] = Field(None, description="Mensagem de erro se houver")

    class Settings:
        name = "file_access_log"

        indexes = [
            IndexModel([("file_id",)]),
            IndexModel([("user_id",)]),
            IndexModel([("timestamp",)]),
            IndexModel([("action",)]),
            # TTL para logs antigos (90 dias)
            IndexModel([("timestamp",)], expireAfterSeconds=7776000),
        ]

    @classmethod
    async def log_access(
        cls,
        file_id: str,
        user_id: str,
        action: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Registrar acesso a arquivo"""
        log_entry = cls(
            file_id=file_id,
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
        await log_entry.insert()

    @classmethod
    async def get_file_access_history(
        cls,
        file_id: str,
        limit: int = 50
    ) -> List["FileAccessLog"]:
        """Obter histórico de acesso de um arquivo"""
        return await cls.find({"file_id": file_id}).sort("-timestamp").limit(limit).to_list()


# Alias para compatibilidade
FileMetadataDocument = FileStorage
StorageQuotaDocument = StorageQuota
FileAccessLogDocument = FileAccessLog