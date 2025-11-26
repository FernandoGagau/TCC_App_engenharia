"""
Timeline Service - Gera visualizações de timeline baseado em dados reais do MongoDB
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from infrastructure.database.project_models import ConstructionProjectModel, ProjectImageModel

logger = logging.getLogger(__name__)


class TimelineService:
    """Service para gerar dados de timeline baseado em projetos reais"""

    async def get_timeline_summary(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna resumo da timeline do projeto ou de todos os projetos

        Args:
            project_id: ID do projeto específico (opcional)

        Returns:
            Dict com resumo da timeline
        """
        try:
            # Busca imagens diretamente (não precisa buscar projeto primeiro)
            query = {}
            if project_id:
                query["project_id"] = project_id

            images = await ProjectImageModel.find(query).to_list()

            if not images:
                return {
                    "project": project_id or "all",
                    "total_images": 0,
                    "total_months": 0,
                    "periods": [],
                    "progress_timeline": []
                }

            # Organiza por período (mês)
            periods_data = defaultdict(lambda: {
                "images": [],
                "dates": set()
            })

            for img in images:
                # Usa captured_at ou uploaded_at
                date = img.captured_at or img.uploaded_at
                month_key = date.strftime("%Y-%m")  # 2025-03
                month_name = date.strftime("%B %Y")  # March 2025

                periods_data[month_key]["month_name"] = month_name
                periods_data[month_key]["images"].append(img)
                periods_data[month_key]["dates"].add(date.strftime("%Y-%m-%d"))

            # Monta resposta
            periods = []
            for month_key in sorted(periods_data.keys()):
                data = periods_data[month_key]

                # Calcula start_date e end_date do período
                dates_list = sorted(list(data["dates"]))
                start_date = datetime.fromisoformat(dates_list[0])
                end_date = datetime.fromisoformat(dates_list[-1])

                periods.append({
                    "month": data["month_name"],
                    "month_key": month_key,
                    "image_count": len(data["images"]),
                    "dates_count": len(data["dates"]),
                    "dates": dates_list,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                })

            # Timeline de progresso (baseado em fases detectadas)
            progress_timeline = []
            for period in periods:
                month_images = periods_data[period["month_key"]]["images"]
                phases_detected = [img.phase_detected for img in month_images if img.phase_detected]

                if phases_detected:
                    # Pega a fase mais comum
                    phase_counts = defaultdict(int)
                    for phase in phases_detected:
                        phase_counts[phase] += 1
                    most_common_phase = max(phase_counts.items(), key=lambda x: x[1])[0]

                    progress_timeline.append({
                        "period": period["month"],
                        "phase": most_common_phase,
                        "confidence": sum(img.confidence_score for img in month_images if img.confidence_score) / len(month_images)
                    })

            return {
                "project": project_id or "all",
                "total_images": len(images),
                "total_months": len(periods),
                "periods": periods,
                "progress_timeline": progress_timeline
            }

        except Exception as e:
            logger.error(f"Error getting timeline summary: {str(e)}", exc_info=True)
            return {
                "project": project_id or "all",
                "total_images": 0,
                "total_months": 0,
                "periods": [],
                "progress_timeline": []
            }

    async def get_progress_analysis(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analisa o progresso da obra baseado em dados reais

        Args:
            project_id: ID do projeto específico (opcional)

        Returns:
            Dict com análise de progresso
        """
        try:
            # Busca projetos
            if project_id:
                projects = await ConstructionProjectModel.find(
                    ConstructionProjectModel.project_id == project_id
                ).to_list()
            else:
                projects = await ConstructionProjectModel.find().to_list()

            if not projects:
                return {
                    "total_duration_days": 0,
                    "total_images": 0,
                    "periods_analyzed": 0,
                    "monthly_progress": [],
                    "activity_frequency": {}
                }

            # Busca imagens
            project_ids = [p.project_id for p in projects]
            images = await ProjectImageModel.find(
                {"project_id": {"$in": project_ids}}
            ).to_list()

            if not images:
                return {
                    "total_duration_days": 0,
                    "total_images": 0,
                    "periods_analyzed": 0,
                    "monthly_progress": [],
                    "activity_frequency": {}
                }

            # Calcula duração total
            dates = [img.captured_at or img.uploaded_at for img in images]
            first_date = min(dates)
            last_date = max(dates)
            total_duration = (last_date - first_date).days

            # Organiza por mês
            monthly_data = defaultdict(lambda: {
                "images": [],
                "dates": set()
            })

            for img in images:
                date = img.captured_at or img.uploaded_at
                month_key = date.strftime("%B %Y")
                monthly_data[month_key]["images"].append(img)
                monthly_data[month_key]["dates"].add(date.strftime("%Y-%m-%d"))

            # Análise mensal
            monthly_progress = []
            activity_frequency = {}

            for month, data in monthly_data.items():
                image_count = len(data["images"])
                dates_count = len(data["dates"])

                # Calcula frequência de documentação
                # Assume 30 dias por mês
                documentation_frequency = round((dates_count / 30) * 100, 1)

                monthly_progress.append({
                    "month": month,
                    "image_count": image_count,
                    "dates_documented": dates_count,
                    "documentation_frequency": documentation_frequency,
                    "period_start": min([img.captured_at or img.uploaded_at for img in data["images"]]).isoformat(),
                    "period_end": max([img.captured_at or img.uploaded_at for img in data["images"]]).isoformat()
                })

                activity_frequency[month] = {
                    "images_per_day": round(image_count / max(dates_count, 1), 1),
                    "documentation_days": dates_count
                }

            return {
                "total_duration_days": total_duration,
                "total_images": len(images),
                "periods_analyzed": len(monthly_data),
                "monthly_progress": monthly_progress,
                "activity_frequency": activity_frequency,
                "project_start": first_date.isoformat(),
                "project_end": last_date.isoformat(),
                "average_images_per_day": round(len(images) / max(total_duration, 1), 2)
            }

        except Exception as e:
            logger.error(f"Error getting progress analysis: {str(e)}", exc_info=True)
            return {
                "total_duration_days": 0,
                "total_images": 0,
                "periods_analyzed": 0,
                "monthly_progress": [],
                "activity_frequency": {}
            }

    async def get_images_by_period(self, month_key: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retorna imagens de um período específico

        Args:
            month_key: Chave do mês (formato: "2025-03")
            project_id: ID do projeto (opcional)

        Returns:
            Lista de imagens do período
        """
        try:
            # Busca imagens
            query = {}
            if project_id:
                query["project_id"] = project_id

            images = await ProjectImageModel.find(query).to_list()

            # Filtra por mês
            month_images = []
            for img in images:
                date = img.captured_at or img.uploaded_at
                if date.strftime("%Y-%m") == month_key or date.strftime("%B %Y") == month_key:
                    month_images.append({
                        "image_id": img.image_id,
                        "file_path": img.file_path,
                        "bucket": img.bucket,
                        "captured_at": date.isoformat(),
                        "phase": img.phase_detected,
                        "components": img.components_detected,
                        "confidence": img.confidence_score,
                        "tags": img.tags
                    })

            return month_images

        except Exception as e:
            logger.error(f"Error getting images by period: {str(e)}", exc_info=True)
            return []

    async def get_latest_images(self, limit: int = 10, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retorna as imagens mais recentes

        Args:
            limit: Quantidade de imagens
            project_id: ID do projeto (opcional)

        Returns:
            Lista das imagens mais recentes
        """
        try:
            query = {}
            if project_id:
                query["project_id"] = project_id

            images = await ProjectImageModel.find(query).sort("-captured_at").limit(limit).to_list()

            return [{
                "image_id": img.image_id,
                "project_id": img.project_id,
                "file_path": img.file_path,
                "bucket": img.bucket,
                "captured_at": (img.captured_at or img.uploaded_at).isoformat(),
                "phase": img.phase_detected,
                "components": img.components_detected,
                "confidence": img.confidence_score,
                "tags": img.tags
            } for img in images]

        except Exception as e:
            logger.error(f"Error getting latest images: {str(e)}", exc_info=True)
            return []
