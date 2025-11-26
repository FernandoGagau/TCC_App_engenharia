# Prompt: MinIO Storage Integration - Sistema de Armazenamento S3-Compatible

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, database).
- Siga os guias: agents/backend-development.md, agents/database-development.md.

Objetivo
- Completar integração do MinIO para armazenamento de objetos (imagens, documentos, relatórios).
- Implementar client S3-compatible com upload, download e gerenciamento de arquivos.
- Criar pipeline de otimização de imagens e validação de segurança.

Escopo
- S3 Client: configuração completa do cliente MinIO.
- Upload Endpoints: APIs para upload de arquivos com validação.
- Image Pipeline: otimização automática de imagens.
- Security Validation: verificação de tipos e conteúdo.
- Quota Management: controle de uso de armazenamento por projeto/usuário.

Requisitos de Configuração
- Dependências Python:
  - minio==7.2.0 para cliente S3
  - pillow==10.1.0 para processamento de imagens
  - python-magic==0.4.27 para detecção de tipo MIME
  - aiofiles==23.2.1 para I/O assíncrono
- Variáveis de ambiente:
  - MINIO_ENDPOINT=localhost:9000
  - MINIO_ACCESS_KEY=minioadmin
  - MINIO_SECRET_KEY=minioadmin
  - MINIO_SECURE=false (true em produção)
  - MAX_FILE_SIZE_MB=50
  - ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf,docx,xlsx

Arquitetura de Alto Nível
- Storage Service: backend/src/infrastructure/storage_service.py (expandir)
- Upload Handler: processamento e validação de arquivos
- Image Processor: redimensionamento e otimização
- Bucket Manager: criação e configuração de buckets
- Access Control: URLs presigned para download seguro

Modelagem de Dados (MongoDB)
```python
# FileMetadata Document
{
    "file_id": str,  # UUID
    "project_id": ObjectId,
    "user_id": str,
    "original_name": str,
    "stored_name": str,  # UUID + extension
    "bucket": str,
    "path": str,
    "mime_type": str,
    "size_bytes": int,
    "dimensions": {  # para imagens
        "width": int,
        "height": int
    },
    "thumbnails": {
        "small": str,   # 150x150
        "medium": str,  # 500x500
        "large": str    # 1024x1024
    },
    "metadata": {
        "content_hash": str,  # SHA-256
        "exif_data": {},  # para fotos
        "ocr_text": str,  # se aplicável
        "virus_scan": str  # status do scan
    },
    "created_at": datetime,
    "expires_at": datetime,  # opcional
    "tags": []
}

# StorageQuota Document
{
    "entity_id": str,  # user_id ou project_id
    "entity_type": "user" | "project",
    "used_bytes": int,
    "quota_bytes": int,
    "file_count": int,
    "last_updated": datetime,
    "warnings": []
}
```

APIs (Endpoints FastAPI)
- POST /api/storage/upload: upload de arquivo único
- POST /api/storage/upload/batch: upload múltiplo
- GET /api/storage/file/{file_id}: obter metadata
- GET /api/storage/download/{file_id}: download com presigned URL
- DELETE /api/storage/file/{file_id}: remover arquivo
- GET /api/storage/quota: verificar quota do usuário
- POST /api/storage/optimize/{file_id}: otimizar imagem

Implementação Completa do Storage Service
```python
# backend/src/infrastructure/storage_service.py
from minio import Minio
from minio.error import S3Error
import aiofiles
import hashlib
from PIL import Image
import io
from typing import Optional, Dict, Any, List
import magic
from datetime import timedelta
import uuid
from pathlib import Path

class MinioStorageService:
    def __init__(self, config: Dict[str, Any]):
        self.client = Minio(
            config['endpoint'],
            access_key=config['access_key'],
            secret_key=config['secret_key'],
            secure=config.get('secure', False)
        )
        self.default_bucket = config.get('default_bucket', 'construction-files')
        self._ensure_buckets()

    def _ensure_buckets(self):
        """Criar buckets necessários se não existirem"""
        buckets = [
            self.default_bucket,
            'construction-images',
            'construction-documents',
            'construction-reports',
            'construction-thumbnails'
        ]

        for bucket in buckets:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                # Configurar políticas de bucket
                self._set_bucket_policy(bucket)

    def _set_bucket_policy(self, bucket_name: str):
        """Configurar política de acesso do bucket"""
        if bucket_name == 'construction-thumbnails':
            # Thumbnails podem ser públicos
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                }]
            }
            self.client.set_bucket_policy(bucket_name, json.dumps(policy))

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        project_id: str,
        user_id: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload de arquivo com validação e processamento"""
        # Validar arquivo
        validation = await self._validate_file(file_content, filename)
        if not validation['valid']:
            raise ValueError(f"File validation failed: {validation['error']}")

        # Gerar nome único
        file_ext = Path(filename).suffix
        stored_name = f"{uuid.uuid4()}{file_ext}"
        file_path = f"{project_id}/{stored_name}"

        # Detectar tipo MIME
        if not content_type:
            content_type = magic.from_buffer(file_content, mime=True)

        # Hash do conteúdo
        content_hash = hashlib.sha256(file_content).hexdigest()

        # Upload para MinIO
        file_stream = io.BytesIO(file_content)
        self.client.put_object(
            self.default_bucket,
            file_path,
            file_stream,
            len(file_content),
            content_type=content_type,
            metadata={
                'project_id': project_id,
                'user_id': user_id,
                'original_name': filename,
                'content_hash': content_hash
            }
        )

        # Processar se for imagem
        thumbnails = {}
        dimensions = {}
        if content_type.startswith('image/'):
            dimensions = await self._get_image_dimensions(file_content)
            thumbnails = await self._create_thumbnails(
                file_content,
                stored_name,
                project_id
            )

        return {
            'file_id': str(uuid.uuid4()),
            'original_name': filename,
            'stored_name': stored_name,
            'bucket': self.default_bucket,
            'path': file_path,
            'mime_type': content_type,
            'size_bytes': len(file_content),
            'dimensions': dimensions,
            'thumbnails': thumbnails,
            'content_hash': content_hash
        }

    async def _validate_file(
        self,
        content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Validar arquivo antes do upload"""
        # Verificar tamanho
        max_size = 50 * 1024 * 1024  # 50MB
        if len(content) > max_size:
            return {
                'valid': False,
                'error': f'File too large. Max size: {max_size/1024/1024}MB'
            }

        # Verificar extensão
        allowed_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.txt', '.csv', '.json'
        ]

        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return {
                'valid': False,
                'error': f'File type not allowed: {file_ext}'
            }

        # Verificar conteúdo real vs extensão
        mime_type = magic.from_buffer(content, mime=True)
        expected_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf'
        }

        if file_ext in expected_types:
            if not mime_type.startswith(expected_types[file_ext].split('/')[0]):
                return {
                    'valid': False,
                    'error': 'File content does not match extension'
                }

        # Scan básico de segurança (implementar antivírus real em produção)
        if b'<script' in content.lower():
            return {
                'valid': False,
                'error': 'Potentially malicious content detected'
            }

        return {'valid': True}

    async def _get_image_dimensions(self, content: bytes) -> Dict[str, int]:
        """Obter dimensões da imagem"""
        img = Image.open(io.BytesIO(content))
        return {
            'width': img.width,
            'height': img.height
        }

    async def _create_thumbnails(
        self,
        content: bytes,
        filename: str,
        project_id: str
    ) -> Dict[str, str]:
        """Criar thumbnails em diferentes tamanhos"""
        thumbnails = {}
        sizes = {
            'small': (150, 150),
            'medium': (500, 500),
            'large': (1024, 1024)
        }

        img = Image.open(io.BytesIO(content))

        for size_name, dimensions in sizes.items():
            # Criar thumbnail
            thumb = img.copy()
            thumb.thumbnail(dimensions, Image.Resampling.LANCZOS)

            # Converter para bytes
            thumb_io = io.BytesIO()
            thumb.save(thumb_io, format=img.format or 'JPEG', optimize=True)
            thumb_bytes = thumb_io.getvalue()

            # Upload thumbnail
            thumb_path = f"{project_id}/thumbnails/{size_name}_{filename}"
            self.client.put_object(
                'construction-thumbnails',
                thumb_path,
                io.BytesIO(thumb_bytes),
                len(thumb_bytes),
                content_type=f"image/{img.format.lower() if img.format else 'jpeg'}"
            )

            thumbnails[size_name] = thumb_path

        return thumbnails

    async def get_download_url(
        self,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        """Gerar URL presigned para download"""
        return self.client.presigned_get_object(
            self.default_bucket,
            file_path,
            expires=timedelta(seconds=expires_in)
        )

    async def delete_file(self, file_path: str, bucket: Optional[str] = None):
        """Remover arquivo do storage"""
        bucket = bucket or self.default_bucket
        self.client.remove_object(bucket, file_path)

        # Remover thumbnails se existirem
        # ...

    async def get_quota_usage(
        self,
        entity_id: str,
        entity_type: str = 'user'
    ) -> Dict[str, Any]:
        """Verificar uso de quota"""
        # Implementar lógica de quota
        pass
```

Upload Handler para FastAPI
```python
# backend/src/presentation/api/storage_routes.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
import aiofiles

router = APIRouter(prefix="/api/storage", tags=["storage"])

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    current_user=Depends(get_current_user),
    storage_service=Depends(get_storage_service)
):
    """Upload de arquivo único"""
    # Validar quota
    quota = await storage_service.get_quota_usage(
        current_user.id,
        'user'
    )

    if quota['used_bytes'] + file.size > quota['quota_bytes']:
        raise HTTPException(400, "Storage quota exceeded")

    # Ler arquivo
    content = await file.read()

    # Upload
    result = await storage_service.upload_file(
        content,
        file.filename,
        project_id,
        current_user.id,
        file.content_type
    )

    # Salvar metadata no MongoDB
    await db.files.insert_one(result)

    return result

@router.post("/upload/batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    project_id: str = Form(...),
    current_user=Depends(get_current_user)
):
    """Upload múltiplo de arquivos"""
    results = []

    for file in files[:10]:  # Limite de 10 arquivos
        result = await upload_file(file, project_id, current_user)
        results.append(result)

    return {"files": results}
```

Image Processing Pipeline
```python
# backend/src/infrastructure/image_processor.py
class ImageProcessor:
    @staticmethod
    async def optimize_image(
        content: bytes,
        max_width: int = 2048,
        quality: int = 85
    ) -> bytes:
        """Otimizar imagem para web"""
        img = Image.open(io.BytesIO(content))

        # Redimensionar se necessário
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Converter para RGB se necessário
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Salvar otimizado
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()

    @staticmethod
    async def extract_exif(content: bytes) -> Dict:
        """Extrair dados EXIF de fotos"""
        img = Image.open(io.BytesIO(content))
        exif_data = img._getexif() or {}

        # Processar dados EXIF relevantes
        return {
            'gps': exif_data.get('GPS', {}),
            'datetime': exif_data.get('DateTime'),
            'camera': exif_data.get('Make'),
            'model': exif_data.get('Model')
        }
```

Testes
```python
# backend/tests/test_storage.py
import pytest
from unittest.mock import Mock, patch
import io

class TestStorageService:
    @pytest.mark.asyncio
    async def test_upload_file(self):
        # Test file upload
        pass

    @pytest.mark.asyncio
    async def test_file_validation(self):
        # Test validation logic
        pass

    @pytest.mark.asyncio
    async def test_thumbnail_generation(self):
        # Test thumbnail creation
        pass

    @pytest.mark.asyncio
    async def test_quota_enforcement(self):
        # Test storage quota
        pass
```

Frontend Upload Component
```jsx
// frontend/src/components/FileUpload.jsx
import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

const FileUpload = ({ projectId, onUploadComplete }) => {
    const onDrop = useCallback(async (acceptedFiles) => {
        const formData = new FormData();
        acceptedFiles.forEach(file => {
            formData.append('files', file);
        });
        formData.append('project_id', projectId);

        try {
            const response = await axios.post(
                '/api/storage/upload/batch',
                formData,
                {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    onUploadProgress: (progressEvent) => {
                        const percentCompleted = Math.round(
                            (progressEvent.loaded * 100) / progressEvent.total
                        );
                        console.log(`Upload progress: ${percentCompleted}%`);
                    }
                }
            );
            onUploadComplete(response.data);
        } catch (error) {
            console.error('Upload failed:', error);
        }
    }, [projectId, onUploadComplete]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.jpeg', '.jpg', '.png'],
            'application/pdf': ['.pdf']
        },
        maxFiles: 10,
        maxSize: 50 * 1024 * 1024  // 50MB
    });

    return (
        <div {...getRootProps()} className="dropzone">
            <input {...getInputProps()} />
            {isDragActive ? (
                <p>Solte os arquivos aqui...</p>
            ) : (
                <p>Arraste arquivos ou clique para selecionar</p>
            )}
        </div>
    );
};
```

Segurança e Performance
- Validação rigorosa de tipos de arquivo
- Scan antivírus (ClamAV em produção)
- Rate limiting para uploads
- Compressão automática de imagens
- CDN para servir thumbnails
- Cleanup automático de arquivos órfãos

Monitoramento
- Métricas de uso de storage por projeto
- Taxa de upload/download
- Erros de validação
- Performance de processamento de imagem

Entregáveis do PR
- Storage service completo com MinIO
- APIs de upload/download
- Pipeline de processamento de imagem
- Sistema de quotas
- Validação de segurança
- Testes unitários e integração
- Componente React de upload
- Documentação atualizada

Checklists úteis
- Revisar agents/backend-development.md para APIs
- Seguir agents/database-development.md para MongoDB
- Validar com agents/security-check.md
- Testar com diferentes tipos e tamanhos de arquivo

Notas
- Configurar lifecycle policies no MinIO para cleanup automático
- Implementar backup strategy para dados críticos
- Considerar integração com CDN (CloudFront/Cloudflare)
- Adicionar watermark em imagens se necessário
- Implementar versionamento de arquivos para auditoria