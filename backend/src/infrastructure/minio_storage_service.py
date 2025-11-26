"""
MinIO Storage Service - S3-Compatible Object Storage
Complete implementation with validation, image processing, and security
"""

import os
import json
import hashlib
import io
import uuid
import magic
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, BinaryIO
from urllib.parse import quote
import logging

from minio import Minio
from minio.error import S3Error, InvalidResponseError
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
import aiofiles

logger = logging.getLogger(__name__)


class MinIOStorageService:
    """
    Serviço completo de armazenamento MinIO
    Suporta upload, download, processamento de imagens e validação de segurança
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa serviço MinIO

        Args:
            config: Configuração MinIO
                - endpoint: MinIO endpoint (ex: localhost:9000)
                - access_key: Chave de acesso
                - secret_key: Chave secreta
                - secure: Usar HTTPS (default: False)
                - default_bucket: Bucket padrão
                - max_file_size_mb: Tamanho máximo em MB
                - allowed_extensions: Extensões permitidas
        """
        self.config = config
        self.endpoint = config.get('endpoint', 'localhost:9000')
        self.access_key = config.get('access_key', 'minioadmin')
        self.secret_key = config.get('secret_key', 'minioadmin')
        self.secure = config.get('secure', False)
        self.default_bucket = config.get('default_bucket', 'construction-files')
        self.max_file_size = config.get('max_file_size_mb', 50) * 1024 * 1024
        self.allowed_extensions = set(config.get('allowed_extensions', [
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
            'txt', 'csv', 'json', 'xml', 'md'
        ]))

        # Inicializar cliente MinIO
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        # Configurar buckets
        self._setup_buckets()

    def _setup_buckets(self):
        """Criar e configurar buckets necessários"""
        buckets = [
            self.default_bucket,
            'construction-images',
            'construction-documents',
            'construction-reports',
            'construction-thumbnails'
        ]

        for bucket_name in buckets:
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info(f"Bucket criado: {bucket_name}")

                    # Configurar política para thumbnails (público)
                    if bucket_name == 'construction-thumbnails':
                        self._set_public_bucket_policy(bucket_name)

            except Exception as e:
                logger.error(f"Erro ao criar bucket {bucket_name}: {e}")

    def _set_public_bucket_policy(self, bucket_name: str):
        """Configurar política de acesso público para bucket"""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                }
            ]
        }

        try:
            self.client.set_bucket_policy(bucket_name, json.dumps(policy))
            logger.info(f"Política pública configurada para {bucket_name}")
        except Exception as e:
            logger.warning(f"Erro ao configurar política para {bucket_name}: {e}")

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        project_id: str,
        user_id: str,
        content_type: Optional[str] = None,
        category: str = 'general'
    ) -> Dict[str, Any]:
        """
        Upload de arquivo com validação completa e processamento

        Args:
            file_content: Conteúdo do arquivo em bytes
            filename: Nome original do arquivo
            project_id: ID do projeto
            user_id: ID do usuário
            content_type: Tipo MIME (detectado automaticamente se None)
            category: Categoria do arquivo

        Returns:
            Dicionário com informações do arquivo armazenado
        """
        # Validar arquivo
        validation = await self._validate_file(file_content, filename)
        if not validation['valid']:
            raise ValueError(f"Validação falhou: {validation['error']}")

        # Gerar identificadores únicos
        file_id = str(uuid.uuid4())
        file_ext = Path(filename).suffix.lower()
        stored_name = f"{file_id}{file_ext}"

        # Detectar tipo MIME se não fornecido
        if not content_type:
            content_type = magic.from_buffer(file_content, mime=True)

        # Gerar hash do conteúdo
        content_hash = hashlib.sha256(file_content).hexdigest()

        # Determinar bucket baseado no tipo de arquivo
        bucket = self._get_bucket_for_content_type(content_type)

        # Criar caminho do arquivo
        file_path = f"{project_id}/{category}/{stored_name}"

        # Metadata do arquivo
        metadata = {
            'project_id': project_id,
            'user_id': user_id,
            'original_name': filename,
            'content_hash': content_hash,
            'category': category,
            'uploaded_at': datetime.utcnow().isoformat()
        }

        # Upload do arquivo principal
        file_stream = io.BytesIO(file_content)

        try:
            self.client.put_object(
                bucket,
                file_path,
                file_stream,
                len(file_content),
                content_type=content_type,
                metadata=metadata
            )
            logger.info(f"Arquivo uploaded: {file_path} ({len(file_content)} bytes)")

        except Exception as e:
            logger.error(f"Erro no upload: {e}")
            raise

        # Processar se for imagem
        dimensions = {}
        thumbnails = {}
        exif_data = {}

        if content_type.startswith('image/'):
            try:
                dimensions = await self._get_image_dimensions(file_content)
                thumbnails = await self._create_thumbnails(
                    file_content, stored_name, project_id, category
                )
                exif_data = await self._extract_exif_data(file_content)
            except Exception as e:
                logger.warning(f"Erro no processamento de imagem: {e}")

        return {
            'file_id': file_id,
            'project_id': project_id,
            'user_id': user_id,
            'original_name': filename,
            'stored_name': stored_name,
            'bucket': bucket,
            'path': file_path,
            'mime_type': content_type,
            'size_bytes': len(file_content),
            'dimensions': dimensions,
            'thumbnails': thumbnails,
            'metadata': {
                'content_hash': content_hash,
                'exif_data': exif_data,
                'category': category
            },
            'created_at': datetime.utcnow(),
            'tags': []
        }

    async def _validate_file(self, content: bytes, filename: str) -> Dict[str, Any]:
        """Validação completa de arquivo"""
        # Verificar tamanho
        if len(content) > self.max_file_size:
            return {
                'valid': False,
                'error': f'Arquivo muito grande. Máximo: {self.max_file_size/1024/1024:.1f}MB'
            }

        # Verificar se está vazio
        if len(content) == 0:
            return {'valid': False, 'error': 'Arquivo vazio'}

        # Verificar extensão
        file_ext = Path(filename).suffix.lower().lstrip('.')
        if file_ext not in self.allowed_extensions:
            return {
                'valid': False,
                'error': f'Extensão não permitida: .{file_ext}'
            }

        # Verificar tipo MIME real
        try:
            detected_mime = magic.from_buffer(content, mime=True)
        except Exception:
            return {'valid': False, 'error': 'Não foi possível detectar tipo do arquivo'}

        # Validar consistência extensão/conteúdo
        mime_validation = self._validate_mime_consistency(file_ext, detected_mime)
        if not mime_validation['valid']:
            return mime_validation

        # Scan básico de segurança
        security_check = await self._security_scan(content, detected_mime)
        if not security_check['valid']:
            return security_check

        return {'valid': True}

    def _validate_mime_consistency(self, extension: str, mime_type: str) -> Dict[str, Any]:
        """Validar consistência entre extensão e tipo MIME"""
        mime_map = {
            'jpg': ['image/jpeg'],
            'jpeg': ['image/jpeg'],
            'png': ['image/png'],
            'gif': ['image/gif'],
            'bmp': ['image/bmp'],
            'webp': ['image/webp'],
            'pdf': ['application/pdf'],
            'doc': ['application/msword'],
            'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'xls': ['application/vnd.ms-excel'],
            'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
            'txt': ['text/plain'],
            'csv': ['text/csv', 'application/csv'],
            'json': ['application/json', 'text/json'],
            'xml': ['application/xml', 'text/xml'],
            'md': ['text/markdown', 'text/plain']
        }

        expected_mimes = mime_map.get(extension, [])
        if expected_mimes and not any(mime_type.startswith(expected) for expected in expected_mimes):
            return {
                'valid': False,
                'error': f'Conteúdo do arquivo não corresponde à extensão .{extension}'
            }

        return {'valid': True}

    async def _security_scan(self, content: bytes, mime_type: str) -> Dict[str, Any]:
        """Scan básico de segurança"""
        # Verificar conteúdo malicioso básico
        content_lower = content.lower()

        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'onload=',
            b'onerror=',
            b'<?php',
            b'<%',
            b'eval(',
            b'exec(',
            b'system(',
            b'shell_exec('
        ]

        for pattern in suspicious_patterns:
            if pattern in content_lower:
                return {
                    'valid': False,
                    'error': 'Conteúdo potencialmente malicioso detectado'
                }

        # Validações específicas por tipo
        if mime_type.startswith('image/'):
            try:
                # Tentar abrir como imagem para validar
                Image.open(io.BytesIO(content))
            except Exception:
                return {
                    'valid': False,
                    'error': 'Arquivo de imagem corrompido ou inválido'
                }

        return {'valid': True}

    def _get_bucket_for_content_type(self, content_type: str) -> str:
        """Determinar bucket baseado no tipo de conteúdo"""
        if content_type.startswith('image/'):
            return 'construction-images'
        elif content_type == 'application/pdf' or content_type.startswith('application/vnd.'):
            return 'construction-documents'
        else:
            return self.default_bucket

    async def _get_image_dimensions(self, content: bytes) -> Dict[str, int]:
        """Obter dimensões da imagem"""
        try:
            with Image.open(io.BytesIO(content)) as img:
                return {
                    'width': img.width,
                    'height': img.height
                }
        except Exception as e:
            logger.warning(f"Erro ao obter dimensões da imagem: {e}")
            return {}

    async def _extract_exif_data(self, content: bytes) -> Dict[str, Any]:
        """Extrair dados EXIF de imagens"""
        try:
            with Image.open(io.BytesIO(content)) as img:
                exif_dict = {}
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)

                        # Converter valores para strings JSON-compatíveis
                        if isinstance(value, (bytes, tuple)):
                            value = str(value)
                        elif isinstance(value, dict):
                            value = {str(k): str(v) for k, v in value.items()}

                        exif_dict[str(tag)] = value

                # Dados específicos úteis
                return {
                    'datetime': exif_dict.get('DateTime'),
                    'camera_make': exif_dict.get('Make'),
                    'camera_model': exif_dict.get('Model'),
                    'orientation': exif_dict.get('Orientation'),
                    'gps_info': exif_dict.get('GPSInfo', {}),
                    'flash': exif_dict.get('Flash'),
                    'focal_length': exif_dict.get('FocalLength')
                }
        except Exception as e:
            logger.warning(f"Erro ao extrair EXIF: {e}")
            return {}

    async def _create_thumbnails(
        self,
        content: bytes,
        filename: str,
        project_id: str,
        category: str
    ) -> Dict[str, str]:
        """Criar thumbnails em diferentes tamanhos"""
        thumbnails = {}
        sizes = {
            'small': (150, 150),
            'medium': (500, 500),
            'large': (1024, 1024)
        }

        try:
            with Image.open(io.BytesIO(content)) as img:
                # Corrigir orientação baseada em EXIF
                img = ImageOps.exif_transpose(img)

                for size_name, dimensions in sizes.items():
                    # Criar thumbnail mantendo proporção
                    thumb = img.copy()
                    thumb.thumbnail(dimensions, Image.Resampling.LANCZOS)

                    # Converter para RGB se necessário (para JPEG)
                    if thumb.mode in ('RGBA', 'LA', 'P'):
                        # Criar fundo branco
                        background = Image.new('RGB', thumb.size, (255, 255, 255))
                        if thumb.mode == 'P':
                            thumb = thumb.convert('RGBA')
                        background.paste(thumb, mask=thumb.split()[-1] if thumb.mode in ['RGBA', 'LA'] else None)
                        thumb = background

                    # Salvar como JPEG otimizado
                    thumb_io = io.BytesIO()
                    thumb.save(thumb_io, format='JPEG', quality=85, optimize=True)
                    thumb_bytes = thumb_io.getvalue()

                    # Path do thumbnail
                    thumb_path = f"{project_id}/{category}/thumbnails/{size_name}_{filename}"

                    # Upload thumbnail
                    self.client.put_object(
                        'construction-thumbnails',
                        thumb_path,
                        io.BytesIO(thumb_bytes),
                        len(thumb_bytes),
                        content_type='image/jpeg',
                        metadata={
                            'original_file': filename,
                            'size': size_name,
                            'project_id': project_id
                        }
                    )

                    thumbnails[size_name] = thumb_path
                    logger.info(f"Thumbnail criado: {size_name} -> {thumb_path}")

        except Exception as e:
            logger.error(f"Erro ao criar thumbnails: {e}")

        return thumbnails

    async def get_download_url(
        self,
        file_path: str,
        bucket: Optional[str] = None,
        expires_in: int = 3600
    ) -> str:
        """Gerar URL presigned para download"""
        bucket = bucket or self.default_bucket

        try:
            url = self.client.presigned_get_object(
                bucket,
                file_path,
                expires=timedelta(seconds=expires_in)
            )
            return url
        except Exception as e:
            logger.error(f"Erro ao gerar URL de download: {e}")
            raise

    async def get_upload_url(
        self,
        file_path: str,
        bucket: Optional[str] = None,
        expires_in: int = 3600,
        content_type: Optional[str] = None
    ) -> str:
        """Gerar URL presigned para upload direto"""
        bucket = bucket or self.default_bucket

        try:
            conditions = []
            if content_type:
                conditions.append(['eq', '$Content-Type', content_type])

            url = self.client.presigned_put_object(
                bucket,
                file_path,
                expires=timedelta(seconds=expires_in)
            )
            return url
        except Exception as e:
            logger.error(f"Erro ao gerar URL de upload: {e}")
            raise

    async def delete_file(
        self,
        file_path: str,
        bucket: Optional[str] = None,
        delete_thumbnails: bool = True
    ) -> bool:
        """Remover arquivo e thumbnails do storage"""
        bucket = bucket or self.default_bucket

        try:
            # Remover arquivo principal
            self.client.remove_object(bucket, file_path)
            logger.info(f"Arquivo removido: {file_path}")

            # Remover thumbnails se solicitado
            if delete_thumbnails:
                await self._delete_thumbnails(file_path)

            return True

        except Exception as e:
            logger.error(f"Erro ao remover arquivo {file_path}: {e}")
            return False

    async def _delete_thumbnails(self, original_path: str):
        """Remover thumbnails associados ao arquivo"""
        try:
            # Extrair informações do path original
            path_parts = original_path.split('/')
            if len(path_parts) >= 3:
                project_id = path_parts[0]
                category = path_parts[1]
                filename = path_parts[-1]

                # Padrão dos thumbnails
                thumb_prefix = f"{project_id}/{category}/thumbnails/"

                # Listar e remover thumbnails
                objects = self.client.list_objects(
                    'construction-thumbnails',
                    prefix=thumb_prefix
                )

                for obj in objects:
                    if filename in obj.object_name:
                        self.client.remove_object('construction-thumbnails', obj.object_name)
                        logger.info(f"Thumbnail removido: {obj.object_name}")

        except Exception as e:
            logger.warning(f"Erro ao remover thumbnails: {e}")

    async def list_files(
        self,
        project_id: str,
        category: Optional[str] = None,
        bucket: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Listar arquivos de um projeto"""
        bucket = bucket or self.default_bucket
        prefix = f"{project_id}/"

        if category:
            prefix += f"{category}/"

        files = []

        try:
            objects = self.client.list_objects(
                bucket,
                prefix=prefix,
                recursive=True
            )

            count = 0
            for obj in objects:
                if count >= limit:
                    break

                # Pular thumbnails se estiver listando bucket principal
                if 'thumbnails/' in obj.object_name:
                    continue

                files.append({
                    'path': obj.object_name,
                    'bucket': bucket,
                    'name': Path(obj.object_name).name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'etag': obj.etag,
                    'metadata': obj.metadata or {}
                })
                count += 1

        except Exception as e:
            logger.error(f"Erro ao listar arquivos: {e}")

        return files

    async def optimize_image(
        self,
        file_path: str,
        bucket: Optional[str] = None,
        max_width: int = 2048,
        quality: int = 85
    ) -> Dict[str, Any]:
        """Otimizar imagem existente no storage"""
        bucket = bucket or 'construction-images'

        try:
            # Baixar imagem original
            response = self.client.get_object(bucket, file_path)
            original_content = response.read()
            response.close()
            response.release_conn()

            # Otimizar
            optimized_content = await self._optimize_image_content(
                original_content, max_width, quality
            )

            # Upload da versão otimizada
            optimized_path = file_path.replace('.', '_optimized.')

            self.client.put_object(
                bucket,
                optimized_path,
                io.BytesIO(optimized_content),
                len(optimized_content),
                content_type='image/jpeg',
                metadata={'optimized': 'true', 'original_path': file_path}
            )

            return {
                'original_path': file_path,
                'optimized_path': optimized_path,
                'original_size': len(original_content),
                'optimized_size': len(optimized_content),
                'compression_ratio': len(optimized_content) / len(original_content)
            }

        except Exception as e:
            logger.error(f"Erro ao otimizar imagem: {e}")
            raise

    async def _optimize_image_content(
        self,
        content: bytes,
        max_width: int = 2048,
        quality: int = 85
    ) -> bytes:
        """Otimizar conteúdo de imagem"""
        with Image.open(io.BytesIO(content)) as img:
            # Corrigir orientação
            img = ImageOps.exif_transpose(img)

            # Redimensionar se necessário
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Converter para RGB se necessário
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ['RGBA', 'LA'] else None)
                img = background

            # Salvar otimizado
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            return output.getvalue()

    async def get_storage_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Obter estatísticas de uso do storage"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_bucket': {},
            'by_type': {}
        }

        buckets = [
            self.default_bucket,
            'construction-images',
            'construction-documents',
            'construction-reports',
            'construction-thumbnails'
        ]

        for bucket_name in buckets:
            try:
                prefix = f"{project_id}/" if project_id else ""
                objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)

                bucket_stats = {'files': 0, 'size': 0}

                for obj in objects:
                    bucket_stats['files'] += 1
                    bucket_stats['size'] += obj.size

                    # Estatísticas por tipo
                    ext = Path(obj.object_name).suffix.lower().lstrip('.')
                    if ext not in stats['by_type']:
                        stats['by_type'][ext] = {'files': 0, 'size': 0}
                    stats['by_type'][ext]['files'] += 1
                    stats['by_type'][ext]['size'] += obj.size

                stats['by_bucket'][bucket_name] = bucket_stats
                stats['total_files'] += bucket_stats['files']
                stats['total_size'] += bucket_stats['size']

            except Exception as e:
                logger.warning(f"Erro ao obter stats do bucket {bucket_name}: {e}")
                stats['by_bucket'][bucket_name] = {'files': 0, 'size': 0}

        return stats

    def health_check(self) -> Dict[str, Any]:
        """Verificar saúde do serviço MinIO"""
        try:
            # Tentar listar buckets
            buckets = self.client.list_buckets()

            return {
                'status': 'healthy',
                'endpoint': self.endpoint,
                'secure': self.secure,
                'buckets_count': len(buckets),
                'buckets': [bucket.name for bucket in buckets]
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'endpoint': self.endpoint,
                'error': str(e)
            }