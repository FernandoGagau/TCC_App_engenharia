"""
Storage API Routes - MinIO File Management
Complete API for file upload, download, and management
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
import aiofiles

from domain.file_metadata_mongo import (
    FileStorage, StorageQuota, FileAccessLog,
    FileCategory, ProcessingStatus, EntityType
)
from infrastructure.minio_storage_service import MinIOStorageService
from infrastructure.image_processor import ImageProcessor
from presentation.api.auth import get_current_user

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Router setup
router = APIRouter(prefix="/api/storage", tags=["storage"])


# Pydantic models for requests/responses
class FileUploadResponse(BaseModel):
    """Resposta do upload de arquivo"""
    file_id: str
    original_name: str
    stored_name: str
    size_bytes: int
    mime_type: str
    category: str
    bucket: str
    thumbnails: Dict[str, str] = {}
    processing_status: str
    created_at: datetime


class BatchUploadResponse(BaseModel):
    """Resposta do upload em lote"""
    files: List[FileUploadResponse]
    total_files: int
    total_size: int
    failed_files: List[Dict[str, str]] = []


class FileMetadataResponse(BaseModel):
    """Resposta com metadados do arquivo"""
    file_id: str
    project_id: str
    user_id: str
    original_name: str
    stored_name: str
    category: str
    bucket: str
    path: str
    mime_type: str
    size_bytes: int
    dimensions: Optional[Dict[str, int]] = None
    thumbnails: Dict[str, str] = {}
    metadata: Dict[str, Any] = {}
    processing_status: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []
    version: int


class QuotaResponse(BaseModel):
    """Resposta com informações de quota"""
    entity_id: str
    entity_type: str
    used_bytes: int
    quota_bytes: int
    file_count: int
    usage_percentage: float
    available_bytes: int
    is_over_limit: bool
    is_near_limit: bool
    warnings: List[str] = []
    usage_by_category: Dict[str, int] = {}


class StorageStatsResponse(BaseModel):
    """Resposta com estatísticas de storage"""
    total_files: int
    total_size: int
    by_bucket: Dict[str, Dict[str, Any]] = {}
    by_type: Dict[str, Dict[str, Any]] = {}


# Dependency injection
async def get_storage_service() -> MinIOStorageService:
    """Obter instância do serviço de storage"""
    config = {
        'endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
        'access_key': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        'secret_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
        'secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
        'default_bucket': os.getenv('MINIO_DEFAULT_BUCKET', 'construction-files'),
        'max_file_size_mb': int(os.getenv('MAX_FILE_SIZE_MB', '50')),
        'allowed_extensions': os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,pdf,docx,xlsx').split(',')
    }
    return MinIOStorageService(config)


async def log_file_access(
    file_id: str,
    user_id: str,
    action: str,
    request: Request,
    success: bool = True,
    error_message: Optional[str] = None
):
    """Log de acesso a arquivo"""
    await FileAccessLog.log_access(
        file_id=file_id,
        user_id=user_id,
        action=action,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        success=success,
        error_message=error_message
    )


# Routes
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    category: FileCategory = Form(FileCategory.GENERAL),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: Request = None,
    current_user: Dict = Depends(get_current_user),
    storage_service: MinIOStorageService = Depends(get_storage_service)
):
    """Upload de arquivo único com validação e processamento"""
    try:
        user_id = current_user.get("user_id", "anonymous")

        # Verificar quota do usuário
        quota = await StorageQuota.get_or_create_quota(user_id, EntityType.USER)
        if not await quota.can_add_file(file.size):
            raise HTTPException(400, "Quota de armazenamento excedida")

        # Ler conteúdo do arquivo
        content = await file.read()

        # Upload para MinIO
        result = await storage_service.upload_file(
            file_content=content,
            filename=file.filename,
            project_id=project_id,
            user_id=user_id,
            content_type=file.content_type,
            category=category.value
        )

        # Criar documento MongoDB
        file_doc = FileStorage(
            file_id=result['file_id'],
            project_id=project_id,
            user_id=user_id,
            original_name=result['original_name'],
            stored_name=result['stored_name'],
            category=category,
            bucket=result['bucket'],
            path=result['path'],
            mime_type=result['mime_type'],
            size_bytes=result['size_bytes'],
            dimensions=result.get('dimensions'),
            thumbnails=result.get('thumbnails', {}),
            metadata=result['metadata'],
            processing_status=ProcessingStatus.COMPLETED
        )

        await file_doc.insert()

        # Atualizar quota
        await quota.add_usage(result['size_bytes'], category.value)

        # Log de acesso
        background_tasks.add_task(
            log_file_access, result['file_id'], user_id, "upload", request
        )

        return FileUploadResponse(
            file_id=result['file_id'],
            original_name=result['original_name'],
            stored_name=result['stored_name'],
            size_bytes=result['size_bytes'],
            mime_type=result['mime_type'],
            category=category.value,
            bucket=result['bucket'],
            thumbnails=result.get('thumbnails', {}),
            processing_status=ProcessingStatus.COMPLETED.value,
            created_at=datetime.utcnow()
        )

    except ValueError as e:
        await log_file_access("", user_id, "upload", request, False, str(e))
        raise HTTPException(400, str(e))
    except Exception as e:
        await log_file_access("", user_id, "upload", request, False, str(e))
        logger.error(f"Erro no upload: {e}")
        raise HTTPException(500, "Erro interno no upload")


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_batch(
    files: List[UploadFile] = File(...),
    project_id: str = Form(...),
    category: FileCategory = Form(FileCategory.GENERAL),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: Request = None,
    current_user: Dict = Depends(get_current_user),
    storage_service: MinIOStorageService = Depends(get_storage_service)
):
    """Upload de múltiplos arquivos"""
    user_id = current_user.get("user_id", "anonymous")
    quota = await StorageQuota.get_or_create_quota(user_id, EntityType.USER)

    # Limite de 10 arquivos por batch
    if len(files) > 10:
        raise HTTPException(400, "Máximo 10 arquivos por upload")

    # Verificar quota total
    total_size = sum(file.size for file in files)
    if not await quota.can_add_file(total_size):
        raise HTTPException(400, "Quota de armazenamento excedida")

    uploaded_files = []
    failed_files = []
    total_uploaded_size = 0

    for file in files:
        try:
            # Upload individual
            content = await file.read()
            result = await storage_service.upload_file(
                file_content=content,
                filename=file.filename,
                project_id=project_id,
                user_id=user_id,
                content_type=file.content_type,
                category=category.value
            )

            # Salvar no MongoDB
            file_doc = FileStorage(
                file_id=result['file_id'],
                project_id=project_id,
                user_id=user_id,
                original_name=result['original_name'],
                stored_name=result['stored_name'],
                category=category,
                bucket=result['bucket'],
                path=result['path'],
                mime_type=result['mime_type'],
                size_bytes=result['size_bytes'],
                dimensions=result.get('dimensions'),
                thumbnails=result.get('thumbnails', {}),
                metadata=result['metadata'],
                processing_status=ProcessingStatus.COMPLETED
            )

            await file_doc.insert()

            uploaded_files.append(FileUploadResponse(
                file_id=result['file_id'],
                original_name=result['original_name'],
                stored_name=result['stored_name'],
                size_bytes=result['size_bytes'],
                mime_type=result['mime_type'],
                category=category.value,
                bucket=result['bucket'],
                thumbnails=result.get('thumbnails', {}),
                processing_status=ProcessingStatus.COMPLETED.value,
                created_at=datetime.utcnow()
            ))

            total_uploaded_size += result['size_bytes']

        except Exception as e:
            failed_files.append({
                "filename": file.filename,
                "error": str(e)
            })

    # Atualizar quota apenas para arquivos bem-sucedidos
    if total_uploaded_size > 0:
        await quota.add_usage(total_uploaded_size, category.value)

    # Log em background
    background_tasks.add_task(
        log_file_access, f"batch_{len(uploaded_files)}", user_id, "batch_upload", request
    )

    return BatchUploadResponse(
        files=uploaded_files,
        total_files=len(uploaded_files),
        total_size=total_uploaded_size,
        failed_files=failed_files
    )


@router.get("/file/{file_id}", response_model=FileMetadataResponse)
async def get_file_metadata(
    file_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Obter metadados de um arquivo"""
    file_doc = await FileStorage.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(404, "Arquivo não encontrado")

    # Verificar permissão (simplificado - pode ser expandido)
    user_id = current_user.get("user_id", "anonymous")
    if file_doc.user_id != user_id and not current_user.get("is_admin", False):
        raise HTTPException(403, "Acesso negado")

    return FileMetadataResponse(
        file_id=file_doc.file_id,
        project_id=file_doc.project_id,
        user_id=file_doc.user_id,
        original_name=file_doc.original_name,
        stored_name=file_doc.stored_name,
        category=file_doc.category.value,
        bucket=file_doc.bucket,
        path=file_doc.path,
        mime_type=file_doc.mime_type,
        size_bytes=file_doc.size_bytes,
        dimensions=file_doc.dimensions.dict() if file_doc.dimensions else None,
        thumbnails=file_doc.thumbnails.dict(),
        metadata=file_doc.metadata.dict(),
        processing_status=file_doc.processing_status.value,
        created_at=file_doc.created_at,
        updated_at=file_doc.updated_at,
        tags=file_doc.tags,
        version=file_doc.version
    )


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: Request = None,
    current_user: Dict = Depends(get_current_user),
    storage_service: MinIOStorageService = Depends(get_storage_service)
):
    """Download de arquivo via URL presigned"""
    file_doc = await FileStorage.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(404, "Arquivo não encontrado")

    user_id = current_user.get("user_id", "anonymous")

    # Verificar permissão
    if file_doc.user_id != user_id and not current_user.get("is_admin", False):
        await log_file_access(file_id, user_id, "download", request, False, "Access denied")
        raise HTTPException(403, "Acesso negado")

    try:
        # Gerar URL presigned
        download_url = await storage_service.get_download_url(
            file_doc.path, file_doc.bucket, expires_in=3600
        )

        # Log de acesso
        background_tasks.add_task(
            log_file_access, file_id, user_id, "download", request
        )

        # Redirecionar para URL presigned
        return RedirectResponse(url=download_url)

    except Exception as e:
        await log_file_access(file_id, user_id, "download", request, False, str(e))
        logger.error(f"Erro no download: {e}")
        raise HTTPException(500, "Erro interno no download")


@router.delete("/file/{file_id}")
async def delete_file(
    file_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: Request = None,
    current_user: Dict = Depends(get_current_user),
    storage_service: MinIOStorageService = Depends(get_storage_service)
):
    """Remover arquivo do storage e banco"""
    file_doc = await FileStorage.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(404, "Arquivo não encontrado")

    user_id = current_user.get("user_id", "anonymous")

    # Verificar permissão
    if file_doc.user_id != user_id and not current_user.get("is_admin", False):
        await log_file_access(file_id, user_id, "delete", request, False, "Access denied")
        raise HTTPException(403, "Acesso negado")

    try:
        # Remover do MinIO
        await storage_service.delete_file(file_doc.path, file_doc.bucket)

        # Atualizar quota
        quota = await StorageQuota.get_or_create_quota(user_id, EntityType.USER)
        await quota.remove_usage(file_doc.size_bytes, file_doc.category.value)

        # Remover do banco
        await file_doc.delete()

        # Log de acesso
        background_tasks.add_task(
            log_file_access, file_id, user_id, "delete", request
        )

        return {"message": "Arquivo removido com sucesso"}

    except Exception as e:
        await log_file_access(file_id, user_id, "delete", request, False, str(e))
        logger.error(f"Erro na remoção: {e}")
        raise HTTPException(500, "Erro interno na remoção")


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    current_user: Dict = Depends(get_current_user)
):
    """Verificar quota do usuário"""
    user_id = current_user.get("user_id", "anonymous")
    quota = await StorageQuota.get_or_create_quota(user_id, EntityType.USER)

    return QuotaResponse(
        entity_id=quota.entity_id,
        entity_type=quota.entity_type.value,
        used_bytes=quota.used_bytes,
        quota_bytes=quota.quota_bytes,
        file_count=quota.file_count,
        usage_percentage=quota.usage_percentage,
        available_bytes=quota.available_bytes,
        is_over_limit=quota.is_over_limit,
        is_near_limit=quota.is_near_limit,
        warnings=quota.warnings,
        usage_by_category=quota.usage_by_category
    )


@router.post("/optimize/{file_id}")
async def optimize_image(
    file_id: str,
    max_width: int = Form(2048),
    quality: int = Form(85),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: Request = None,
    current_user: Dict = Depends(get_current_user),
    storage_service: MinIOStorageService = Depends(get_storage_service)
):
    """Otimizar imagem existente"""
    file_doc = await FileStorage.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(404, "Arquivo não encontrado")

    if not file_doc.mime_type.startswith('image/'):
        raise HTTPException(400, "Arquivo não é uma imagem")

    user_id = current_user.get("user_id", "anonymous")

    # Verificar permissão
    if file_doc.user_id != user_id and not current_user.get("is_admin", False):
        raise HTTPException(403, "Acesso negado")

    try:
        # Otimizar imagem
        result = await storage_service.optimize_image(
            file_doc.path, file_doc.bucket, max_width, quality
        )

        # Log de acesso
        background_tasks.add_task(
            log_file_access, file_id, user_id, "optimize", request
        )

        return {
            "message": "Imagem otimizada com sucesso",
            "original_size": result['original_size'],
            "optimized_size": result['optimized_size'],
            "compression_ratio": result['compression_ratio'],
            "optimized_path": result['optimized_path']
        }

    except Exception as e:
        await log_file_access(file_id, user_id, "optimize", request, False, str(e))
        logger.error(f"Erro na otimização: {e}")
        raise HTTPException(500, "Erro interno na otimização")


@router.get("/project/{project_id}/files")
async def list_project_files(
    project_id: str,
    category: Optional[FileCategory] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Listar arquivos de um projeto"""
    files = await FileStorage.find_by_project(project_id, category, limit, skip)

    return {
        "files": [
            {
                "file_id": file.file_id,
                "original_name": file.original_name,
                "mime_type": file.mime_type,
                "size_bytes": file.size_bytes,
                "category": file.category.value,
                "created_at": file.created_at,
                "thumbnails": file.thumbnails.dict(),
                "tags": file.tags
            }
            for file in files
        ],
        "total": len(files),
        "project_id": project_id
    }


@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    project_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    storage_service: MinIOStorageService = Depends(get_storage_service)
):
    """Obter estatísticas de uso do storage"""
    stats = await storage_service.get_storage_stats(project_id)

    return StorageStatsResponse(
        total_files=stats['total_files'],
        total_size=stats['total_size'],
        by_bucket=stats['by_bucket'],
        by_type=stats['by_type']
    )


@router.get("/health")
async def storage_health_check(
    storage_service: MinIOStorageService = Depends(get_storage_service)
):
    """Verificar saúde do serviço de storage"""
    return storage_service.health_check()


@router.get("/file/{file_id}/access-log")
async def get_file_access_log(
    file_id: str,
    limit: int = 50,
    current_user: Dict = Depends(get_current_user)
):
    """Obter log de acesso de um arquivo"""
    # Verificar se o usuário tem permissão para ver o arquivo
    file_doc = await FileStorage.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(404, "Arquivo não encontrado")

    user_id = current_user.get("user_id", "anonymous")
    if file_doc.user_id != user_id and not current_user.get("is_admin", False):
        raise HTTPException(403, "Acesso negado")

    # Obter logs
    logs = await FileAccessLog.get_file_access_history(file_id, limit)

    return {
        "file_id": file_id,
        "access_log": [
            {
                "user_id": log.user_id,
                "action": log.action,
                "timestamp": log.timestamp,
                "ip_address": log.ip_address,
                "success": log.success,
                "error_message": log.error_message
            }
            for log in logs
        ]
    }