"""
Quota Management Service
Advanced quota management and cleanup strategies
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from domain.file_metadata_mongo import (
    StorageQuota, FileStorage, EntityType,
    FileCategory, ProcessingStatus
)
from infrastructure.minio_storage_service import MinIOStorageService

logger = logging.getLogger(__name__)


class QuotaManagementService:
    """
    Serviço de gerenciamento de quotas
    Inclui limpeza automática e otimização de espaço
    """

    def __init__(self, storage_service: MinIOStorageService):
        self.storage_service = storage_service

    async def check_quota_compliance(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> Dict[str, Any]:
        """
        Verificar conformidade de quota para uma entidade

        Args:
            entity_id: ID da entidade
            entity_type: Tipo da entidade

        Returns:
            Status da quota e ações recomendadas
        """
        quota = await StorageQuota.get_or_create_quota(entity_id, entity_type)

        compliance_status = {
            "entity_id": entity_id,
            "entity_type": entity_type.value,
            "current_usage": {
                "bytes": quota.used_bytes,
                "files": quota.file_count,
                "percentage": quota.usage_percentage
            },
            "limits": {
                "quota_bytes": quota.quota_bytes,
                "max_files": quota.max_file_count
            },
            "status": "compliant",
            "warnings": quota.warnings,
            "recommended_actions": []
        }

        # Determinar status
        if quota.is_over_limit:
            compliance_status["status"] = "over_limit"
            compliance_status["recommended_actions"].append("immediate_cleanup")
        elif quota.is_near_limit:
            compliance_status["status"] = "warning"
            compliance_status["recommended_actions"].append("cleanup_suggested")

        # Verificar quota de arquivos
        if quota.max_file_count and quota.file_count >= quota.max_file_count:
            compliance_status["status"] = "file_limit_reached"
            compliance_status["recommended_actions"].append("file_cleanup")

        # Sugestões baseadas no uso por categoria
        category_analysis = await self._analyze_category_usage(entity_id, entity_type)
        compliance_status["category_analysis"] = category_analysis

        return compliance_status

    async def _analyze_category_usage(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> Dict[str, Any]:
        """Analisar uso por categoria"""
        if entity_type == EntityType.USER:
            query = {"user_id": entity_id}
        elif entity_type == EntityType.PROJECT:
            query = {"project_id": entity_id}
        else:
            return {}

        # Agregação por categoria
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": "$category",
                    "file_count": {"$sum": 1},
                    "total_size": {"$sum": "$size_bytes"},
                    "avg_size": {"$avg": "$size_bytes"},
                    "oldest_file": {"$min": "$created_at"},
                    "newest_file": {"$max": "$created_at"}
                }
            },
            {"$sort": {"total_size": -1}}
        ]

        results = await FileStorage.aggregate(pipeline).to_list()

        analysis = {
            "by_category": {},
            "recommendations": []
        }

        total_size = sum(item["total_size"] for item in results)

        for item in results:
            category = item["_id"]
            percentage = (item["total_size"] / total_size * 100) if total_size > 0 else 0

            analysis["by_category"][category] = {
                "file_count": item["file_count"],
                "total_size": item["total_size"],
                "avg_size": round(item["avg_size"], 2),
                "percentage": round(percentage, 2),
                "oldest_file": item["oldest_file"],
                "newest_file": item["newest_file"]
            }

            # Recomendações baseadas em uso
            if percentage > 50:
                analysis["recommendations"].append(
                    f"Category {category} uses {percentage:.1f}% of storage"
                )

        return analysis

    async def auto_cleanup(
        self,
        entity_id: str,
        entity_type: EntityType,
        target_percentage: float = 80.0,
        strategy: str = "oldest_first"
    ) -> Dict[str, Any]:
        """
        Limpeza automática baseada em estratégia

        Args:
            entity_id: ID da entidade
            entity_type: Tipo da entidade
            target_percentage: Percentual alvo de uso (padrão: 80%)
            strategy: Estratégia de limpeza

        Returns:
            Relatório da limpeza
        """
        quota = await StorageQuota.get_or_create_quota(entity_id, entity_type)

        if quota.usage_percentage <= target_percentage:
            return {
                "action": "no_cleanup_needed",
                "current_usage": quota.usage_percentage,
                "target": target_percentage
            }

        # Calcular quanto espaço precisa ser liberado
        target_bytes = int(quota.quota_bytes * (target_percentage / 100))
        bytes_to_free = quota.used_bytes - target_bytes

        logger.info(f"Starting cleanup for {entity_id}: need to free {bytes_to_free} bytes")

        # Buscar arquivos para remoção baseado na estratégia
        files_to_remove = await self._select_files_for_cleanup(
            entity_id, entity_type, bytes_to_free, strategy
        )

        removed_files = []
        total_freed = 0

        for file_doc in files_to_remove:
            try:
                # Remover do MinIO
                await self.storage_service.delete_file(
                    file_doc.path, file_doc.bucket, delete_thumbnails=True
                )

                # Remover do banco
                await file_doc.delete()

                removed_files.append({
                    "file_id": file_doc.file_id,
                    "name": file_doc.original_name,
                    "size": file_doc.size_bytes,
                    "category": file_doc.category.value,
                    "created_at": file_doc.created_at
                })

                total_freed += file_doc.size_bytes

                # Verificar se atingiu o alvo
                if total_freed >= bytes_to_free:
                    break

            except Exception as e:
                logger.error(f"Error removing file {file_doc.file_id}: {e}")

        # Atualizar quota
        await quota.remove_usage(total_freed)

        return {
            "action": "cleanup_completed",
            "strategy": strategy,
            "target_percentage": target_percentage,
            "files_removed": len(removed_files),
            "bytes_freed": total_freed,
            "new_usage_percentage": quota.usage_percentage,
            "removed_files": removed_files
        }

    async def _select_files_for_cleanup(
        self,
        entity_id: str,
        entity_type: EntityType,
        bytes_needed: int,
        strategy: str
    ) -> List[FileStorage]:
        """Selecionar arquivos para limpeza baseado na estratégia"""

        if entity_type == EntityType.USER:
            base_query = {"user_id": entity_id}
        elif entity_type == EntityType.PROJECT:
            base_query = {"project_id": entity_id}
        else:
            return []

        if strategy == "oldest_first":
            # Remover arquivos mais antigos primeiro
            files = await FileStorage.find(base_query).sort("created_at", 1).to_list()
        elif strategy == "largest_first":
            # Remover arquivos maiores primeiro
            files = await FileStorage.find(base_query).sort("size_bytes", -1).to_list()
        elif strategy == "unused_first":
            # Remover arquivos menos acessados (baseado em logs de acesso)
            # Por simplicidade, usar data de criação como proxy
            files = await FileStorage.find(base_query).sort("created_at", 1).to_list()
        elif strategy == "thumbnails_only":
            # Remover apenas thumbnails e versões otimizadas
            query = {**base_query, "path": {"$regex": "thumbnails/"}}
            files = await FileStorage.find(query).to_list()
        else:
            # Estratégia padrão: oldest_first
            files = await FileStorage.find(base_query).sort("created_at", 1).to_list()

        # Selecionar arquivos até atingir o tamanho necessário
        selected_files = []
        accumulated_size = 0

        for file_doc in files:
            selected_files.append(file_doc)
            accumulated_size += file_doc.size_bytes

            if accumulated_size >= bytes_needed:
                break

        return selected_files

    async def optimize_storage_usage(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> Dict[str, Any]:
        """
        Otimizar uso de storage através de várias estratégias

        Args:
            entity_id: ID da entidade
            entity_type: Tipo da entidade

        Returns:
            Relatório de otimização
        """
        optimization_report = {
            "entity_id": entity_id,
            "entity_type": entity_type.value,
            "optimizations": [],
            "total_saved_bytes": 0,
            "recommendations": []
        }

        # 1. Identificar e remover duplicatas
        duplicates_saved = await self._remove_duplicates(entity_id, entity_type)
        if duplicates_saved > 0:
            optimization_report["optimizations"].append({
                "type": "duplicate_removal",
                "bytes_saved": duplicates_saved
            })
            optimization_report["total_saved_bytes"] += duplicates_saved

        # 2. Otimizar imagens grandes
        image_savings = await self._optimize_large_images(entity_id, entity_type)
        if image_savings > 0:
            optimization_report["optimizations"].append({
                "type": "image_optimization",
                "bytes_saved": image_savings
            })
            optimization_report["total_saved_bytes"] += image_savings

        # 3. Remover arquivos temporários/processamento
        temp_cleaned = await self._clean_temporary_files(entity_id, entity_type)
        if temp_cleaned > 0:
            optimization_report["optimizations"].append({
                "type": "temporary_cleanup",
                "bytes_saved": temp_cleaned
            })
            optimization_report["total_saved_bytes"] += temp_cleaned

        # 4. Gerar recomendações
        optimization_report["recommendations"] = await self._generate_optimization_recommendations(
            entity_id, entity_type
        )

        return optimization_report

    async def _remove_duplicates(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> int:
        """Remover arquivos duplicados baseado no hash do conteúdo"""
        if entity_type == EntityType.USER:
            base_query = {"user_id": entity_id}
        elif entity_type == EntityType.PROJECT:
            base_query = {"project_id": entity_id}
        else:
            return 0

        # Buscar duplicatas agrupando por hash
        pipeline = [
            {"$match": base_query},
            {
                "$group": {
                    "_id": "$metadata.content_hash",
                    "files": {"$push": "$$ROOT"},
                    "count": {"$sum": 1}
                }
            },
            {"$match": {"count": {"$gt": 1}}}
        ]

        duplicates = await FileStorage.aggregate(pipeline).to_list()
        total_saved = 0

        for group in duplicates:
            files = group["files"]
            # Manter o arquivo mais recente, remover os outros
            files.sort(key=lambda x: x["created_at"], reverse=True)
            files_to_remove = files[1:]  # Todos exceto o primeiro (mais recente)

            for file_data in files_to_remove:
                try:
                    file_doc = await FileStorage.find_one({"_id": file_data["_id"]})
                    if file_doc:
                        await self.storage_service.delete_file(
                            file_doc.path, file_doc.bucket
                        )
                        total_saved += file_doc.size_bytes
                        await file_doc.delete()

                except Exception as e:
                    logger.error(f"Error removing duplicate {file_data['_id']}: {e}")

        return total_saved

    async def _optimize_large_images(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> int:
        """Otimizar imagens grandes"""
        if entity_type == EntityType.USER:
            base_query = {"user_id": entity_id}
        elif entity_type == EntityType.PROJECT:
            base_query = {"project_id": entity_id}
        else:
            return 0

        # Buscar imagens grandes (> 5MB)
        query = {
            **base_query,
            "mime_type": {"$regex": "^image/"},
            "size_bytes": {"$gt": 5 * 1024 * 1024}
        }

        large_images = await FileStorage.find(query).to_list()
        total_saved = 0

        for file_doc in large_images:
            try:
                # Otimizar imagem
                result = await self.storage_service.optimize_image(
                    file_doc.path, file_doc.bucket, max_width=2048, quality=85
                )

                if result["compression_ratio"] < 0.8:  # Salvou pelo menos 20%
                    savings = result["original_size"] - result["optimized_size"]
                    total_saved += savings

            except Exception as e:
                logger.error(f"Error optimizing image {file_doc.file_id}: {e}")

        return total_saved

    async def _clean_temporary_files(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> int:
        """Limpar arquivos temporários e com falha no processamento"""
        if entity_type == EntityType.USER:
            base_query = {"user_id": entity_id}
        elif entity_type == EntityType.PROJECT:
            base_query = {"project_id": entity_id}
        else:
            return 0

        # Buscar arquivos com processamento falho ou temporários antigos
        cutoff_date = datetime.utcnow() - timedelta(hours=24)
        query = {
            **base_query,
            "$or": [
                {"processing_status": ProcessingStatus.FAILED},
                {
                    "processing_status": ProcessingStatus.PENDING,
                    "created_at": {"$lt": cutoff_date}
                }
            ]
        }

        temp_files = await FileStorage.find(query).to_list()
        total_saved = 0

        for file_doc in temp_files:
            try:
                await self.storage_service.delete_file(
                    file_doc.path, file_doc.bucket
                )
                total_saved += file_doc.size_bytes
                await file_doc.delete()

            except Exception as e:
                logger.error(f"Error removing temp file {file_doc.file_id}: {e}")

        return total_saved

    async def _generate_optimization_recommendations(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> List[str]:
        """Gerar recomendações de otimização"""
        recommendations = []

        # Analisar distribuição de arquivos
        category_analysis = await self._analyze_category_usage(entity_id, entity_type)

        for category, data in category_analysis.get("by_category", {}).items():
            if data["percentage"] > 40:
                recommendations.append(
                    f"Consider archiving old {category} files - they use {data['percentage']:.1f}% of storage"
                )

            if data["avg_size"] > 10 * 1024 * 1024:  # > 10MB
                recommendations.append(
                    f"Large {category} files detected - consider compression or optimization"
                )

        # Verificar quota
        quota = await StorageQuota.get_or_create_quota(entity_id, entity_type)
        if quota.usage_percentage > 75:
            recommendations.append("Storage usage is high - consider enabling auto-cleanup")

        return recommendations

    async def set_quota_limits(
        self,
        entity_id: str,
        entity_type: EntityType,
        quota_bytes: Optional[int] = None,
        max_files: Optional[int] = None,
        alert_threshold: Optional[float] = None,
        auto_cleanup: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Configurar limites de quota para uma entidade

        Args:
            entity_id: ID da entidade
            entity_type: Tipo da entidade
            quota_bytes: Limite de bytes (opcional)
            max_files: Limite de arquivos (opcional)
            alert_threshold: Threshold de alerta (opcional)
            auto_cleanup: Habilitar limpeza automática (opcional)

        Returns:
            Configuração atualizada
        """
        quota = await StorageQuota.get_or_create_quota(entity_id, entity_type)

        # Atualizar configurações
        if quota_bytes is not None:
            quota.quota_bytes = quota_bytes

        if max_files is not None:
            quota.max_file_count = max_files

        if alert_threshold is not None:
            quota.alert_threshold = alert_threshold

        if auto_cleanup is not None:
            quota.auto_cleanup = auto_cleanup

        await quota.save()

        return {
            "entity_id": entity_id,
            "entity_type": entity_type.value,
            "quota_bytes": quota.quota_bytes,
            "max_files": quota.max_file_count,
            "alert_threshold": quota.alert_threshold,
            "auto_cleanup": quota.auto_cleanup,
            "current_usage": {
                "bytes": quota.used_bytes,
                "files": quota.file_count,
                "percentage": quota.usage_percentage
            }
        }

    async def get_quota_report(
        self,
        entity_ids: List[str],
        entity_type: EntityType
    ) -> Dict[str, Any]:
        """
        Gerar relatório de quota para múltiplas entidades

        Args:
            entity_ids: Lista de IDs das entidades
            entity_type: Tipo das entidades

        Returns:
            Relatório consolidado
        """
        report = {
            "entity_type": entity_type.value,
            "entities": [],
            "summary": {
                "total_entities": len(entity_ids),
                "over_limit": 0,
                "near_limit": 0,
                "total_usage_bytes": 0,
                "total_quota_bytes": 0
            }
        }

        for entity_id in entity_ids:
            quota = await StorageQuota.get_or_create_quota(entity_id, entity_type)

            entity_data = {
                "entity_id": entity_id,
                "used_bytes": quota.used_bytes,
                "quota_bytes": quota.quota_bytes,
                "usage_percentage": quota.usage_percentage,
                "file_count": quota.file_count,
                "status": "compliant",
                "warnings": quota.warnings
            }

            if quota.is_over_limit:
                entity_data["status"] = "over_limit"
                report["summary"]["over_limit"] += 1
            elif quota.is_near_limit:
                entity_data["status"] = "near_limit"
                report["summary"]["near_limit"] += 1

            report["entities"].append(entity_data)
            report["summary"]["total_usage_bytes"] += quota.used_bytes
            report["summary"]["total_quota_bytes"] += quota.quota_bytes

        # Calcular percentual geral
        if report["summary"]["total_quota_bytes"] > 0:
            report["summary"]["overall_usage_percentage"] = (
                report["summary"]["total_usage_bytes"] /
                report["summary"]["total_quota_bytes"] * 100
            )
        else:
            report["summary"]["overall_usage_percentage"] = 0

        return report