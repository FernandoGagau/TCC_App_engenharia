"""
Serviço de Armazenamento de Imagens em Cloud Storage
Suporta S3, Google Cloud Storage e armazenamento local
"""

import os
import json
import hashlib
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import logging
import mimetypes

logger = logging.getLogger(__name__)


class StorageService:
    """
    Serviço unificado de armazenamento
    Suporta múltiplos backends de storage
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa serviço de armazenamento

        Args:
            config: Configuração do storage
                - type: 'local', 's3', 'gcs'
                - bucket: Nome do bucket
                - credentials: Credenciais (se aplicável)
                - base_path: Caminho base para armazenamento local
        """
        self.config = config
        self.storage_type = config.get('type', 'local')
        self.bucket_name = config.get('bucket')

        if self.storage_type == 'local':
            self.base_path = Path(config.get('base_path', 'backend/storage'))
            self.base_path.mkdir(parents=True, exist_ok=True)
        elif self.storage_type == 's3':
            self._init_s3()
        elif self.storage_type == 'gcs':
            self._init_gcs()
        else:
            raise ValueError(f"Tipo de storage não suportado: {self.storage_type}")

    def _init_s3(self):
        """Inicializa cliente S3/MinIO"""
        try:
            import boto3

            # Configuração do cliente S3/MinIO
            client_config = {
                'aws_access_key_id': self.config.get('aws_access_key_id'),
                'aws_secret_access_key': self.config.get('aws_secret_access_key'),
                'region_name': self.config.get('region', 'us-east-1')
            }

            # Se tiver endpoint_url, é MinIO ou S3-compatible
            endpoint_url = self.config.get('endpoint_url')
            if endpoint_url:
                # Garante que MinIO/S3-compatible tenha porta (padrão 9000)
                if 'railway.internal' in endpoint_url and ':' not in endpoint_url.split('//')[-1]:
                    endpoint_url = endpoint_url.rstrip('/') + ':9000'
                    logger.warning(f"Porta MinIO não especificada, adicionando :9000 -> {endpoint_url}")

                client_config['endpoint_url'] = endpoint_url
                logger.info(f"Inicializando cliente MinIO/S3-compatible: {endpoint_url}")
            else:
                logger.info("Inicializando cliente AWS S3")

            self.s3_client = boto3.client('s3', **client_config)

            # Verifica/cria bucket
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' já existe")
            except:
                # Bucket não existe, cria
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Bucket '{self.bucket_name}' criado com sucesso")
                except Exception as bucket_error:
                    logger.warning(f"Não foi possível criar bucket: {bucket_error}")

            logger.info(f"Cliente S3/MinIO inicializado - Bucket: {self.bucket_name}")

        except ImportError:
            logger.error("boto3 não instalado. Execute: pip install boto3")
            self.storage_type = 'local'
            self.base_path = Path('backend/storage')
            self.base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Erro ao inicializar S3/MinIO: {e}")
            # Fallback para local
            self.storage_type = 'local'
            self.base_path = Path('backend/storage')
            self.base_path.mkdir(parents=True, exist_ok=True)

    def _init_gcs(self):
        """Inicializa cliente Google Cloud Storage"""
        try:
            from google.cloud import storage
            self.gcs_client = storage.Client.from_service_account_json(
                self.config.get('credentials_path')
            )
            self.gcs_bucket = self.gcs_client.bucket(self.bucket_name)
            logger.info("Cliente GCS inicializado")
        except ImportError:
            logger.error("google-cloud-storage não instalado. Execute: pip install google-cloud-storage")
            self.storage_type = 'local'
            self.base_path = Path('backend/storage')
            self.base_path.mkdir(parents=True, exist_ok=True)

    def upload_image(
        self,
        file_path: str,
        project_id: str,
        category: str = 'general',
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Faz upload de imagem para o storage

        Args:
            file_path: Caminho local da imagem
            project_id: ID do projeto
            category: Categoria da imagem (construction, bim, document, etc)
            metadata: Metadados adicionais

        Returns:
            URL/caminho da imagem no storage
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Gera nome único com estrutura organizada por data
        # project_id/YYYY-MM-DD/category/timestamp_hash.ext
        file_hash = self._generate_file_hash(file_path)
        extension = Path(file_path).suffix
        now = datetime.now()
        date_folder = now.strftime('%Y-%m-%d')
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        storage_name = f"{project_id}/{date_folder}/{category}/{timestamp}_{file_hash}{extension}"

        if self.storage_type == 'local':
            return self._upload_local(file_path, storage_name, metadata)
        elif self.storage_type == 's3':
            return self._upload_s3(file_path, storage_name, metadata)
        elif self.storage_type == 'gcs':
            return self._upload_gcs(file_path, storage_name, metadata)

    def _upload_local(
        self,
        file_path: str,
        storage_name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Upload para armazenamento local"""
        dest_path = self.base_path / storage_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copia arquivo
        import shutil
        shutil.copy2(file_path, dest_path)

        # Salva metadados
        if metadata:
            meta_path = dest_path.with_suffix('.meta.json')
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        logger.info(f"Imagem salva localmente: {dest_path}")
        return str(dest_path)

    def _upload_s3(
        self,
        file_path: str,
        storage_name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Upload para S3/MinIO"""
        try:
            # Detecta content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

            # Prepara metadados (converte valores para string)
            metadata_strings = {}
            if metadata:
                for key, value in metadata.items():
                    metadata_strings[key] = str(value)

            # Prepara argumentos extras
            extra_args = {
                'ContentType': content_type,
                'Metadata': metadata_strings
            }

            # Upload
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                storage_name,
                ExtraArgs=extra_args
            )

            # Gera URL (diferente para MinIO vs AWS S3)
            endpoint_url = self.config.get('endpoint_url')
            if endpoint_url:
                # MinIO ou S3-compatible
                url = f"{endpoint_url}/{self.bucket_name}/{storage_name}"
            else:
                # AWS S3 padrão
                url = f"https://{self.bucket_name}.s3.amazonaws.com/{storage_name}"

            logger.info(f"Imagem uploaded para S3/MinIO: {url}")
            return url

        except Exception as e:
            logger.error(f"Erro no upload S3/MinIO: {e}", exc_info=True)
            # Fallback para local
            return self._upload_local(file_path, storage_name, metadata)

    def _upload_gcs(
        self,
        file_path: str,
        storage_name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Upload para Google Cloud Storage"""
        try:
            blob = self.gcs_bucket.blob(storage_name)

            # Detecta content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type:
                blob.content_type = content_type

            # Adiciona metadados
            if metadata:
                blob.metadata = metadata

            # Upload
            blob.upload_from_filename(file_path)

            # Gera URL
            url = blob.public_url
            logger.info(f"Imagem uploaded para GCS: {url}")
            return url

        except Exception as e:
            logger.error(f"Erro no upload GCS: {e}")
            # Fallback para local
            return self._upload_local(file_path, storage_name, metadata)

    def download_image(
        self,
        storage_path: str,
        local_path: Optional[str] = None
    ) -> str:
        """
        Baixa imagem do storage

        Args:
            storage_path: Caminho/URL da imagem no storage
            local_path: Caminho local para salvar (opcional)

        Returns:
            Caminho local da imagem baixada
        """
        if not local_path:
            local_path = f"/tmp/{Path(storage_path).name}"

        if self.storage_type == 'local':
            # Para storage local, apenas copia
            import shutil
            shutil.copy2(storage_path, local_path)
        elif self.storage_type == 's3':
            # Extrai key do URL se necessário
            key = storage_path.replace(f"https://{self.bucket_name}.s3.amazonaws.com/", "")
            self.s3_client.download_file(self.bucket_name, key, local_path)
        elif self.storage_type == 'gcs':
            blob_name = storage_path.replace(f"https://storage.googleapis.com/{self.bucket_name}/", "")
            blob = self.gcs_bucket.blob(blob_name)
            blob.download_to_filename(local_path)

        return local_path

    def list_images(
        self,
        project_id: str,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Lista imagens de um projeto

        Args:
            project_id: ID do projeto
            category: Categoria específica (opcional)
            limit: Limite de resultados

        Returns:
            Lista de informações das imagens
        """
        prefix = f"{project_id}/"
        if category:
            prefix += f"{category}/"

        images = []

        if self.storage_type == 'local':
            base_dir = self.base_path / project_id
            if category:
                base_dir = base_dir / category

            if base_dir.exists():
                for file_path in base_dir.glob('**/*'):
                    if file_path.is_file() and not file_path.name.endswith('.meta.json'):
                        # Carrega metadados se existirem
                        meta_path = file_path.with_suffix('.meta.json')
                        metadata = {}
                        if meta_path.exists():
                            with open(meta_path) as f:
                                metadata = json.load(f)

                        images.append({
                            'path': str(file_path),
                            'name': file_path.name,
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                            'metadata': metadata
                        })

        elif self.storage_type == 's3':
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=limit
                )

                for obj in response.get('Contents', []):
                    images.append({
                        'path': f"https://{self.bucket_name}.s3.amazonaws.com/{obj['Key']}",
                        'name': Path(obj['Key']).name,
                        'size': obj['Size'],
                        'modified': obj['LastModified'].isoformat()
                    })
            except Exception as e:
                logger.error(f"Erro ao listar imagens S3: {e}")

        elif self.storage_type == 'gcs':
            try:
                blobs = self.gcs_bucket.list_blobs(prefix=prefix, max_results=limit)

                for blob in blobs:
                    images.append({
                        'path': blob.public_url,
                        'name': Path(blob.name).name,
                        'size': blob.size,
                        'modified': blob.updated.isoformat() if blob.updated else None,
                        'metadata': blob.metadata
                    })
            except Exception as e:
                logger.error(f"Erro ao listar imagens GCS: {e}")

        return images[:limit]

    def delete_image(self, storage_path: str) -> bool:
        """
        Deleta imagem do storage

        Args:
            storage_path: Caminho/URL da imagem

        Returns:
            True se deletada com sucesso
        """
        try:
            if self.storage_type == 'local':
                os.remove(storage_path)
                # Remove metadados se existirem
                meta_path = Path(storage_path).with_suffix('.meta.json')
                if meta_path.exists():
                    os.remove(meta_path)

            elif self.storage_type == 's3':
                key = storage_path.replace(f"https://{self.bucket_name}.s3.amazonaws.com/", "")
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)

            elif self.storage_type == 'gcs':
                blob_name = storage_path.replace(f"https://storage.googleapis.com/{self.bucket_name}/", "")
                blob = self.gcs_bucket.blob(blob_name)
                blob.delete()

            logger.info(f"Imagem deletada: {storage_path}")
            return True

        except Exception as e:
            logger.error(f"Erro ao deletar imagem: {e}")
            return False

    def _generate_file_hash(self, file_path: str) -> str:
        """Gera hash único para arquivo"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read(65536)  # 64kb chunks
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()[:8]

    def get_signed_url(
        self,
        storage_path: str,
        expiration: int = 3600
    ) -> str:
        """
        Gera URL assinada para acesso temporário

        Args:
            storage_path: Caminho da imagem
            expiration: Tempo de expiração em segundos

        Returns:
            URL assinada
        """
        if self.storage_type == 'local':
            # Para local, retorna caminho direto
            return storage_path

        elif self.storage_type == 's3':
            try:
                key = storage_path.replace(f"https://{self.bucket_name}.s3.amazonaws.com/", "")
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': key},
                    ExpiresIn=expiration
                )
                return url
            except Exception as e:
                logger.error(f"Erro ao gerar URL assinada S3: {e}")
                return storage_path

        elif self.storage_type == 'gcs':
            try:
                from datetime import timedelta
                blob_name = storage_path.replace(f"https://storage.googleapis.com/{self.bucket_name}/", "")
                blob = self.gcs_bucket.blob(blob_name)
                url = blob.generate_signed_url(
                    expiration=timedelta(seconds=expiration)
                )
                return url
            except Exception as e:
                logger.error(f"Erro ao gerar URL assinada GCS: {e}")
                return storage_path

        return storage_path