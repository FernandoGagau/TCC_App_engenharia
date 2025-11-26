"""
API Routes para Gerenciamento de Projetos de Construção
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from pathlib import Path
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

from domain.construction_project_mongo import ProjectManagerMongo as ProjectManager
from infrastructure.database.project_models import ProjectStatus, ConstructionPhase
from infrastructure.image_analysis import ConstructionImageAnalyzer
from infrastructure.storage_service import StorageService
from domain.image_timeline import ImageTimelineManager

# Inicializa serviços
project_manager = ProjectManager()
image_analyzer = ConstructionImageAnalyzer()
image_timeline = ImageTimelineManager()

# Configuração do storage (pode vir de env vars)
storage_config = {
    'type': os.getenv('STORAGE_TYPE', 'local'),
    'bucket': os.getenv('STORAGE_BUCKET', 'construction-images'),
    'base_path': os.getenv('STORAGE_PATH', 'backend/storage')
}
storage_service = StorageService(storage_config)

router = APIRouter()


# ===== MODELS =====
class CreateProjectRequest(BaseModel):
    name: str
    description: str
    location: Dict[str, Any]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    current_phase: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AddCameraRequest(BaseModel):
    name: str
    position: Dict[str, float]  # x, y, z
    rotation: Dict[str, float]  # pitch, yaw, roll
    fov: float = 60.0
    resolution: str = "1920x1080"
    stream_url: Optional[str] = None


class AnalyzeImageRequest(BaseModel):
    project_id: str
    camera_id: Optional[str] = None
    image_url: Optional[str] = None


# ===== PROJECT ENDPOINTS =====
@router.post("/create")
async def create_project(request: CreateProjectRequest):
    """Cria novo projeto de construção"""
    try:
        project = project_manager.create_project(
            name=request.name,
            description=request.description,
            location=request.location,
            start_date=request.start_date,
            end_date=request.end_date
        )
        return {"project": project.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Obtém detalhes completos do projeto"""
    try:
        from infrastructure.database.project_models import ConstructionProjectModel

        # Busca projeto no MongoDB
        doc = await ConstructionProjectModel.find_one(
            ConstructionProjectModel.project_id == project_id
        )

        if not doc:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")

        # Extrai cronograma se existir
        cronograma = None

        # Inicializa progress_info com dois níveis de progresso
        progress_info = {
            "schedule_progress": 0,      # Progresso esperado do cronograma (baseado em datas)
            "actual_progress": 0,         # Progresso real consolidado (imagens + histórico)
            "overall_progress": doc.overall_progress,  # Progresso geral exibido (real)
            "variance": 0,                # Diferença entre real e esperado
            "has_schedule": False,        # Se tem cronograma cadastrado
            "has_images": False           # Se tem análises de imagem
        }

        if doc.metadata and doc.metadata.get('cronograma'):
            cronograma_data = doc.metadata['cronograma']
            summary = cronograma_data.get('summary', {})

            # Extrai os dois tipos de progresso
            schedule_progress = summary.get('expected_progress_until_today', 0)
            actual_progress = summary.get('actual_progress', 0)

            # Atualiza progress_info com os dois níveis
            progress_info.update({
                "schedule_progress": round(schedule_progress, 2),
                "actual_progress": round(actual_progress, 2),
                "overall_progress": round(actual_progress, 2),
                "variance": round(actual_progress - schedule_progress, 2),
                "has_schedule": True,
                "has_images": actual_progress > 0
            })

            cronograma = {
                "activities": cronograma_data.get('activities', {}),
                "summary": summary,
                "updated_at": cronograma_data.get('updated_at'),
                "calculated_at": cronograma_data.get('calculated_at')
            }

        return {
            "project_id": doc.project_id,
            "name": doc.name,
            "description": doc.description,
            "project_type": doc.project_type if hasattr(doc, 'project_type') else "residential",
            "location": doc.location,
            "status": doc.status,
            "overall_progress": doc.overall_progress,
            "progress_info": progress_info,  # ← NOVO: Detalha o tipo de progresso
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            "start_date": doc.start_date.isoformat() if doc.start_date else None,
            "end_date": doc.end_date.isoformat() if doc.end_date else None,
            "current_phase": doc.current_phase if hasattr(doc, 'current_phase') else None,
            "cronograma": cronograma
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Atualiza projeto"""
    try:
        updates = request.dict(exclude_unset=True)
        project = project_manager.update_project(project_id, updates)
        return {"project": project.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_projects(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100)
):
    """Lista todos os projetos cadastrados"""
    try:
        # Busca projetos do MongoDB
        projects = await project_manager.list_projects(limit=limit)

        # Converte para formato de resposta
        projects_data = []
        for project in projects:
            # Extrai informações de progresso do cronograma se existir
            progress_info = {
                "schedule_progress": 0,
                "actual_progress": 0,
                "overall_progress": project.overall_progress,
                "variance": 0,
                "has_schedule": False,
                "has_images": False
            }

            if project.metadata and project.metadata.get('cronograma'):
                summary = project.metadata['cronograma'].get('summary', {})
                schedule_progress = summary.get('expected_progress_until_today', 0)
                actual_progress = summary.get('actual_progress', 0)

                progress_info.update({
                    "schedule_progress": round(schedule_progress, 2),
                    "actual_progress": round(actual_progress, 2),
                    "overall_progress": round(schedule_progress, 2),
                    "variance": round(actual_progress - schedule_progress, 2),
                    "has_schedule": True,
                    "has_images": actual_progress > 0
                })

            projects_data.append({
                "project_id": project.project_id,
                "name": project.name,
                "description": project.description,
                "project_type": project.project_type if hasattr(project, 'project_type') else "residential",
                "location": project.location,
                "status": project.status.value if hasattr(project.status, 'value') else str(project.status),
                "overall_progress": project.overall_progress,
                "progress_info": progress_info,  # ← NOVO: Detalha os dois níveis de progresso
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "end_date": project.end_date.isoformat() if project.end_date else None
            })

        return {
            "projects": projects_data,
            "total": len(projects_data)
        }
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}", exc_info=True)
        return {
            "projects": [],
            "total": 0
        }


# ===== BIM ENDPOINTS =====
@router.post("/{project_id}/bim")
async def upload_bim_model(
    project_id: str,
    file: UploadFile = File(...),
    format: str = Form(...),
    version: str = Form(...)
):
    """Upload de modelo BIM"""
    try:
        # Salva arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Upload para storage
        storage_path = storage_service.upload_image(
            tmp_path,
            project_id,
            category='bim',
            metadata={'format': format, 'version': version}
        )

        # Adiciona ao projeto
        bim_model = project_manager.add_bim_model(
            project_id,
            storage_path,
            format,
            version,
            metadata={'original_name': file.filename}
        )

        # Remove temporário
        os.unlink(tmp_path)

        return {"bim_model": bim_model.__dict__}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== CAMERA ENDPOINTS =====
@router.post("/{project_id}/cameras")
async def add_camera(project_id: str, request: AddCameraRequest):
    """Adiciona câmera ao projeto"""
    try:
        camera = project_manager.add_camera(
            project_id,
            name=request.name,
            position=request.position,
            rotation=request.rotation,
            fov=request.fov,
            resolution=request.resolution,
            stream_url=request.stream_url
        )
        return {"camera": camera.__dict__}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/cameras")
async def list_cameras(project_id: str):
    """Lista câmeras do projeto"""
    try:
        project = project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")

        return {"cameras": [c.__dict__ for c in project.cameras]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== IMAGE ANALYSIS ENDPOINTS =====
@router.post("/{project_id}/analyze")
async def analyze_image(
    project_id: str,
    file: UploadFile = File(...)
):
    """Analisa imagem de construção"""
    try:
        # Salva arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Upload para storage
        storage_path = storage_service.upload_image(
            tmp_path,
            project_id,
            category='construction'
        )

        # Analisa imagem
        analysis_result = image_analyzer.analyze_image(
            tmp_path,
            return_annotated=True
        )

        # Atualiza progresso dos componentes detectados
        for detection in analysis_result.detections:
            if detection.component_id:
                phase = ConstructionPhase(detection.class_name)
                project_manager.update_component_progress(
                    project_id,
                    detection.component_id,
                    phase,
                    detection.confidence,
                    images=[storage_path]
                )

        # Remove temporário
        os.unlink(tmp_path)

        # Prepara resposta
        response = {
            'image_url': storage_path,
            'detections': [
                {
                    'class': d.class_name,
                    'confidence': d.confidence,
                    'bbox': d.bbox,
                    'component_id': d.component_id
                }
                for d in analysis_result.detections
            ],
            'metrics': image_analyzer.calculate_progress_metrics(analysis_result.detections)
        }

        if 'annotated_image' in analysis_result.metadata:
            response['annotated_image'] = analysis_result.metadata['annotated_image']

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/batch-analyze")
async def batch_analyze_images(
    project_id: str,
    files: List[UploadFile] = File(...)
):
    """Analisa múltiplas imagens em lote"""
    try:
        results = []
        all_detections = []

        for file in files:
            # Salva temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # Upload
            storage_path = storage_service.upload_image(
                tmp_path,
                project_id,
                category='construction'
            )

            # Analisa
            analysis_result = image_analyzer.analyze_image(tmp_path)

            results.append({
                'file': file.filename,
                'url': storage_path,
                'detections': len(analysis_result.detections)
            })

            all_detections.extend(analysis_result.detections)

            # Atualiza componentes
            for detection in analysis_result.detections:
                if detection.component_id:
                    phase = ConstructionPhase(detection.class_name)
                    project_manager.update_component_progress(
                        project_id,
                        detection.component_id,
                        phase,
                        detection.confidence,
                        images=[storage_path]
                    )

            # Remove temporário
            os.unlink(tmp_path)

        # Gera relatório
        report = image_analyzer.generate_progress_report(
            [{'detections': all_detections}]
        )

        return {
            'files_processed': len(files),
            'results': results,
            'report': report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== PROGRESS ENDPOINTS =====
@router.get("/{project_id}/progress")
async def get_project_progress(project_id: str):
    """Obtém progresso do projeto"""
    try:
        project = project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")

        analytics = project_manager.get_project_analytics(project_id)
        alerts = project_manager.generate_alerts(project_id)

        return {
            'project_id': project_id,
            'overall_progress': project.overall_progress.percentage,
            'current_phase': project.current_phase.value if project.current_phase else None,
            'components': {
                comp_id: {
                    'phase': comp.current_phase.value,
                    'confidence': comp.detection_confidence,
                    'last_updated': comp.last_updated.isoformat()
                }
                for comp_id, comp in project.components.items()
            },
            'analytics': analytics,
            'alerts': alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/components")
async def get_project_components(project_id: str):
    """Lista componentes do projeto com progresso"""
    try:
        project = project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")

        components = []
        for comp_id, comp in project.components.items():
            components.append({
                'id': comp_id,
                'type': comp.component_type,
                'current_phase': comp.current_phase.value,
                'confidence': comp.detection_confidence,
                'last_updated': comp.last_updated.isoformat(),
                'images_count': len(comp.images),
                'history_count': len(comp.detection_history)
            })

        return {
            'project_id': project_id,
            'total_components': len(components),
            'components': components
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== STORAGE ENDPOINTS =====
# Removed duplicate endpoint - real implementation is at line 496

@router.delete("/{project_id}/images")
async def delete_image(
    project_id: str,
    image_url: str = Query(...)
):
    """Deleta imagem do projeto"""
    try:
        success = storage_service.delete_image(image_url)
        if success:
            return {"message": "Imagem deletada com sucesso"}
        else:
            raise HTTPException(status_code=400, detail="Erro ao deletar imagem")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== CRONOGRAMA ENDPOINTS =====
@router.get("/{project_id}/cronograma")
async def get_project_cronograma(project_id: str):
    """Obtém cronograma do projeto com cálculo de progresso baseado em datas"""
    try:
        from infrastructure.database.project_models import ConstructionProjectModel
        from infrastructure.timezone_utils import now_brazil
        from datetime import datetime as dt

        # Busca projeto no MongoDB
        doc = await ConstructionProjectModel.find_one(
            ConstructionProjectModel.project_id == project_id
        )

        if not doc:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")

        if not doc.metadata or not doc.metadata.get('cronograma'):
            return {
                "has_cronograma": False,
                "message": "Nenhum cronograma cadastrado para este projeto"
            }

        cronograma_data = doc.metadata['cronograma']
        activities = cronograma_data.get('activities', {})
        summary = cronograma_data.get('summary', {})

        # Calcular status atual de cada atividade
        current_date = now_brazil().date()
        activities_with_status = []

        for activity_name, activity_data in activities.items():
            if isinstance(activity_data, dict):
                start_date_str = activity_data.get('start_date')
                end_date_str = activity_data.get('end_date')

                # Determinar status atual
                status = "não_iniciada"
                days_elapsed = 0
                days_remaining = 0

                if start_date_str and end_date_str:
                    start_date = dt.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = dt.strptime(end_date_str, '%Y-%m-%d').date()

                    if current_date >= end_date:
                        status = "deveria_estar_concluída"
                        days_elapsed = (current_date - start_date).days
                    elif current_date >= start_date:
                        status = "em_andamento"
                        days_elapsed = (current_date - start_date).days
                        days_remaining = (end_date - current_date).days
                    else:
                        status = "não_iniciada"
                        days_remaining = (start_date - current_date).days

                activities_with_status.append({
                    "name": activity_name,
                    "percentage": activity_data.get('percentage', 0),
                    "duration_days": activity_data.get('duration_days', 0),
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "expected_progress": activity_data.get('expected_progress', 0),
                    "actual_progress": activity_data.get('actual_progress', 0),
                    "status": status,
                    "days_elapsed": days_elapsed,
                    "days_remaining": days_remaining
                })

        return {
            "has_cronograma": True,
            "project_id": project_id,
            "project_name": doc.name,
            "current_date": current_date.isoformat(),
            "summary": {
                "total_weight_completed": summary.get('total_weight_completed', 0),
                "total_weight_in_progress": summary.get('total_weight_in_progress', 0),
                "total_weight_remaining": summary.get('total_weight_remaining', 0),
                "expected_progress_until_today": summary.get('expected_progress_until_today', 0),
                "actual_progress": summary.get('actual_progress', 0),
                "variance": summary.get('actual_progress', 0) - summary.get('expected_progress_until_today', 0)
            },
            "activities": activities_with_status,
            "total_activities": len(activities_with_status),
            "updated_at": cronograma_data.get('updated_at'),
            "calculated_at": cronograma_data.get('calculated_at')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cronograma for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== ANALYTICS ENDPOINTS =====
@router.get("/{project_id}/analytics")
async def get_project_analytics(project_id: str):
    """Obtém análise completa do projeto"""
    try:
        analytics = project_manager.get_project_analytics(project_id)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/alerts")
async def get_project_alerts(project_id: str):
    """Obtém alertas do projeto"""
    try:
        alerts = project_manager.generate_alerts(project_id)
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== IMAGE GALLERY ENDPOINTS =====
@router.get("/{project_id}/images")
async def get_project_images(
    project_id: str,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0)
):
    """Lista todas as imagens do projeto com análises"""
    try:
        from infrastructure.database.project_models import ProjectImageModel, AnalysisReport

        logger.info(f"📸 GET /api/projects/{project_id}/images called")
        logger.info(f"   limit={limit}, skip={skip}")

        # Busca imagens do projeto
        images = await ProjectImageModel.find(
            ProjectImageModel.project_id == project_id
        ).sort("-analyzed_at").skip(skip).limit(limit).to_list()

        logger.info(f"✅ Found {len(images)} images for project {project_id}")

        result = []
        for i, img in enumerate(images):
            logger.info(f"  Processing image {i+1}: {img.image_id}, project_id={img.project_id}")

            # Busca análise mais recente da imagem
            analysis = await AnalysisReport.find_one(
                AnalysisReport.image_id == img.image_id
            )

            if analysis:
                logger.info(f"    ✅ Found analysis report for image {img.image_id}")
            else:
                logger.info(f"    ⚠️ No analysis report for image {img.image_id}")

            # Gera URL pública da imagem
            image_url = None
            if img.bucket and img.file_path:
                # MinIO/S3 URL
                image_url = f"http://localhost:9000/{img.bucket}/{img.file_path}"

            result.append({
                "image_id": img.image_id,
                "file_path": img.file_path,
                "url": image_url,
                "mime_type": img.mime_type,
                "size_bytes": img.size_bytes,
                "analyzed_at": img.analyzed_at,
                "phase": img.phase_detected,
                "confidence": img.confidence_score,
                "components": img.components_detected,
                "analysis": {
                    "phase": analysis.phase_detected if analysis else None,
                    "progress": analysis.progress_percentage if analysis else 0,
                    "quality_score": analysis.quality_score if analysis else 0,
                    "safety_severity": analysis.safety_severity if analysis else "unknown",
                    "recommendations": analysis.recommendations if analysis else []
                } if analysis else None
            })

        logger.info(f"📦 Returning {len(result)} images to client")

        return {
            "project_id": project_id,
            "total": len(result),
            "images": result
        }

    except Exception as e:
        logger.error(f"Error fetching project images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/{image_id}")
async def get_image_details(image_id: str):
    """Retorna detalhes da imagem e análise completa"""
    try:
        from infrastructure.database.project_models import ProjectImageModel, AnalysisReport

        # Busca imagem
        image = await ProjectImageModel.find_one(
            ProjectImageModel.image_id == image_id
        )

        if not image:
            raise HTTPException(status_code=404, detail="Imagem não encontrada")

        # Busca análise
        analysis = await AnalysisReport.find_one(
            AnalysisReport.image_id == image_id
        )

        # Gera URL pública
        image_url = None
        if image.bucket and image.file_path:
            image_url = f"http://localhost:9000/{image.bucket}/{image.file_path}"

        return {
            "image": {
                "image_id": image.image_id,
                "project_id": image.project_id,
                "file_path": image.file_path,
                "url": image_url,
                "mime_type": image.mime_type,
                "size_bytes": image.size_bytes,
                "analyzed_at": image.analyzed_at,
                "metadata": image.metadata
            },
            "analysis": {
                "report_id": analysis.report_id if analysis else None,
                "analyzer_model": analysis.analyzer_model if analysis else None,
                "phase_detected": analysis.phase_detected if analysis else None,
                "phase_confidence": analysis.phase_confidence if analysis else 0,
                "phase_details": analysis.phase_details if analysis else "",
                "elements_found": analysis.elements_found if analysis else [],
                "components_detected": analysis.components_detected if analysis else [],
                "progress_percentage": analysis.progress_percentage if analysis else 0,
                "progress_justification": analysis.progress_justification if analysis else "",
                "quality_score": analysis.quality_score if analysis else 0,
                "quality_notes": analysis.quality_notes if analysis else "",
                "safety_issues": analysis.safety_issues if analysis else [],
                "safety_severity": analysis.safety_severity if analysis else "unknown",
                "recommendations": analysis.recommendations if analysis else [],
                "issues": analysis.issues if analysis else []
            } if analysis else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/{image_id}/file")
async def get_image_file(image_id: str):
    """Retorna arquivo da imagem para preview/download"""
    try:
        from fastapi.responses import Response
        from infrastructure.database.project_models import ProjectImageModel
        import requests

        logger.info(f"📸 GET /images/{image_id}/file called")

        # Busca imagem
        image = await ProjectImageModel.find_one(
            ProjectImageModel.image_id == image_id
        )

        if not image:
            logger.warning(f"❌ Image not found in database: {image_id}")
            raise HTTPException(status_code=404, detail="Imagem não encontrada")

        logger.info(f"✅ Found image: bucket={image.bucket}, file_path={image.file_path}, project_id={image.project_id}")

        # Se tiver bucket MinIO/S3, baixa de lá
        if image.bucket and image.file_path:
            # Constrói URL do MinIO (ajustar se usando AWS S3)
            minio_url = f"http://localhost:9000/{image.bucket}/{image.file_path}"
            logger.info(f"📥 Fetching from MinIO: {minio_url}")

            # Faz download do MinIO
            response = requests.get(minio_url, timeout=30)

            # If failed with 404, try intelligent fallback for legacy images
            if response.status_code == 404:
                logger.warning(f"⚠️ Image not found at {minio_url}, trying intelligent fallback...")

                # Try to find image by listing all files in project and matching by name/date
                try:
                    # Use minio client to list all objects in project folder
                    import boto3
                    from botocore.client import Config

                    s3 = boto3.client(
                        's3',
                        endpoint_url='http://localhost:9000',
                        aws_access_key_id='minioadmin',
                        aws_secret_access_key='minioadmin123',
                        config=Config(signature_version='s3v4'),
                        region_name='us-east-1'
                    )

                    # List all objects in project folder
                    paginator = s3.get_paginator('list_objects_v2')
                    filename = Path(image.file_path).name

                    logger.info(f"   Searching for file matching: {filename}")
                    logger.info(f"   In project folder: {image.project_id}/")

                    found_file = None
                    all_files = []
                    for page in paginator.paginate(Bucket=image.bucket, Prefix=f"{image.project_id}/"):
                        if 'Contents' in page:
                            for obj in page['Contents']:
                                key = obj['Key']
                                all_files.append(key)
                                obj_filename = Path(key).name

                                # Skip directories
                                if key.endswith('/'):
                                    continue

                                # Match by exact filename
                                if obj_filename == filename:
                                    found_file = key
                                    logger.info(f"   ✅ Found exact match: {key}")
                                    break

                                # Extract date from original filename (e.g., "2025-09-30" from "WhatsApp Image 2025-09-30 at 19.19.16.jpeg")
                                # And match with files that have similar date pattern
                                import re
                                date_pattern = r'(\d{4}-\d{2}-\d{2})'
                                filename_dates = re.findall(date_pattern, filename)

                                if filename_dates:
                                    # If original filename has date, try to match files from same date
                                    for date_str in filename_dates:
                                        if date_str in key:
                                            found_file = key
                                            logger.info(f"   ✅ Found date-based match: {key} (date: {date_str})")
                                            break

                            if found_file:
                                break

                    if not found_file:
                        logger.warning(f"   ⚠️ No match found. All files in project folder:")
                        for f in all_files[:20]:  # Show first 20 files
                            logger.warning(f"      - {f}")

                    if found_file:
                        # Try to fetch the found file
                        found_url = f"http://localhost:9000/{image.bucket}/{found_file}"
                        logger.info(f"   📥 Fetching from found path: {found_url}")
                        response = requests.get(found_url, timeout=30)

                        if response.status_code != 200:
                            logger.error(f"❌ Failed to fetch found file")
                            raise HTTPException(status_code=404, detail="Arquivo encontrado mas não pôde ser baixado")
                    else:
                        logger.error(f"❌ No matching file found in project folder")
                        raise HTTPException(status_code=404, detail="Arquivo da imagem não encontrado no storage")

                except Exception as e:
                    logger.error(f"❌ Error during intelligent fallback: {e}", exc_info=True)
                    raise HTTPException(status_code=404, detail=f"Arquivo da imagem não encontrado: {str(e)}")

            response.raise_for_status()

            logger.info(f"✅ Image fetched successfully: {len(response.content)} bytes")

            # Retorna imagem com headers corretos
            return Response(
                content=response.content,
                media_type=image.mime_type,
                headers={
                    "Content-Disposition": f'inline; filename="{Path(image.file_path).name}"',
                    "Cache-Control": "public, max-age=3600"
                }
            )
        else:
            logger.error(f"❌ Image has no bucket or file_path: bucket={image.bucket}, file_path={image.file_path}")
            raise HTTPException(status_code=404, detail="Arquivo da imagem não encontrado")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching image file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Deleta obra e todo histórico de chat associado"""
    try:
        from domain.chat.models import ChatSession, ChatMessage
        from infrastructure.database.project_models import (
            ProjectImageModel,
            AnalysisReport,
            ProjectAlertModel,
            ConstructionProjectModel,
            ProjectScheduleModel
        )

        logger.info(f"🗑️ DELETE /api/projects/{project_id} called")

        # Inicializa contadores
        messages_deleted = 0
        sessions_deleted = 0
        images_deleted = 0
        analysis_deleted = 0
        alerts_deleted = 0
        schedules_deleted = 0

        logger.info(f"Step 1: Deleting chat sessions...")
        # 1. Deleta todas as sessões de chat do projeto
        try:
            chat_sessions = await ChatSession.find(
                {"project_id": project_id}
            ).to_list()
        except Exception as e1:
            logger.error(f"Error finding chat sessions: {e1}", exc_info=True)
            chat_sessions = []

        session_ids = [session.session_id for session in chat_sessions]

        if session_ids:
            # Deleta todas as mensagens das sessões
            messages_result = await ChatMessage.find(
                {"session_id": {"$in": session_ids}}
            ).delete()
            messages_deleted = messages_result.deleted_count
            logger.info(f"   Deleted {messages_deleted} chat messages")

            # Deleta as sessões
            sessions_result = await ChatSession.find(
                ChatSession.project_id == project_id
            ).delete()
            sessions_deleted = sessions_result.deleted_count
            logger.info(f"   Deleted {sessions_deleted} chat sessions")

        # 2. Deleta todas as imagens do projeto
        images = await ProjectImageModel.find(
            ProjectImageModel.project_id == project_id
        ).to_list()

        image_ids = [img.image_id for img in images]

        if image_ids:
            # Deleta análises das imagens
            analysis_result = await AnalysisReport.find(
                {"image_id": {"$in": image_ids}}
            ).delete()
            analysis_deleted = analysis_result.deleted_count
            logger.info(f"   Deleted {analysis_deleted} analysis reports")

            # Deleta as imagens
            images_result = await ProjectImageModel.find(
                ProjectImageModel.project_id == project_id
            ).delete()
            images_deleted = images_result.deleted_count
            logger.info(f"   Deleted {images_deleted} project images")

        # 3. Deleta alertas do projeto
        alerts_result = await ProjectAlertModel.find(
            ProjectAlertModel.project_id == project_id
        ).delete()
        alerts_deleted = alerts_result.deleted_count
        logger.info(f"   Deleted {alerts_deleted} alerts")

        # 4. Deleta cronogramas do projeto
        try:
            schedules_result = await ProjectScheduleModel.find(
                {"project_id": project_id}
            ).delete()
            schedules_deleted = schedules_result.deleted_count
            logger.info(f"   Deleted {schedules_deleted} schedules")
        except Exception as schedule_error:
            logger.warning(f"Error deleting schedules: {schedule_error}")
            schedules_deleted = 0

        # 5. Finalmente, deleta o projeto
        project = await ConstructionProjectModel.find_one(
            ConstructionProjectModel.project_id == project_id
        )

        if not project:
            logger.warning(f"❌ Project {project_id} not found")
            raise HTTPException(status_code=404, detail="Projeto não encontrado")

        await project.delete()
        logger.info(f"   ✅ Project {project_id} deleted successfully")

        return {
            "message": "Projeto e histórico deletados com sucesso",
            "deleted": {
                "project": project_id,
                "chat_sessions": sessions_deleted,
                "chat_messages": messages_deleted,
                "images": images_deleted,
                "analysis_reports": analysis_deleted,
                "alerts": alerts_deleted,
                "schedules": schedules_deleted
            }
        }

    except HTTPException:
        raise
    except KeyError as e:
        logger.error(f"❌ KeyError deleting project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Missing key: {str(e)}")
    except AttributeError as e:
        logger.error(f"❌ AttributeError deleting project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Attribute error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error deleting project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {type(e).__name__}: {str(e)}")


# ===== CRONOGRAMA ENDPOINTS =====
@router.get("/{project_id}/schedule")
async def get_project_schedule(project_id: str):
    """Obtém cronograma do projeto"""
    try:
        from infrastructure.database.project_models import ProjectScheduleModel
        from datetime import datetime

        logger.info(f"📅 GET /api/projects/{project_id}/schedule called")

        # Busca cronograma
        try:
            schedule = await ProjectScheduleModel.find_one(
                ProjectScheduleModel.project_id == project_id
            )
        except Exception as find_error:
            logger.warning(f"Error finding schedule (may not exist yet): {find_error}")
            schedule = None

        # Se não existe ProjectScheduleModel, tenta criar a partir do metadata
        if not schedule:
            logger.info(f"No ProjectScheduleModel found, checking metadata...")

            from infrastructure.database.project_models import ConstructionProjectModel
            project = await ConstructionProjectModel.find_one(
                ConstructionProjectModel.project_id == project_id
            )

            if project and project.metadata and 'cronograma' in project.metadata:
                logger.info(f"Found cronograma in metadata, creating schedule from it...")

                # Extrai activities do metadata
                activities = project.metadata.get('cronograma', {}).get('activities', {})

                if activities:
                    # Importa função do supervisor para criar schedule
                    from agents.supervisor import SupervisorAgent
                    supervisor = SupervisorAgent({'llm': None, 'project_repository': None})

                    # Cria schedule a partir das atividades
                    created = await supervisor._create_schedule_from_activities(project_id, activities)

                    if created:
                        logger.info(f"✅ Schedule created from metadata")
                        # Busca novamente
                        schedule = await ProjectScheduleModel.find_one(
                            ProjectScheduleModel.project_id == project_id
                        )
                    else:
                        logger.warning("Failed to create schedule from metadata")

            if not schedule:
                logger.info(f"No schedule found for project {project_id}")
                return {
                    "project_id": project_id,
                    "schedule": None,
                    "message": "Nenhum cronograma cadastrado"
                }

        # Calcula dias decorridos e restantes
        now = datetime.utcnow()
        days_elapsed = (now - schedule.project_start).days if schedule.project_start else 0
        days_remaining = (schedule.project_end - now).days if schedule.project_end else 0

        # Atualiza status dos milestones
        for milestone in schedule.milestones:
            if milestone.actual_end:
                milestone.status = "completed"
            elif milestone.actual_start:
                milestone.status = "in_progress"
            elif now > milestone.planned_end and milestone.status == "pending":
                milestone.status = "delayed"

        return {
            "project_id": project_id,
            "schedule": {
                "schedule_id": schedule.schedule_id,
                "name": schedule.name,
                "description": schedule.description,
                "project_start": schedule.project_start.isoformat(),
                "project_end": schedule.project_end.isoformat(),
                "overall_progress": schedule.overall_progress,
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "milestones": [
                    {
                        "milestone_id": m.milestone_id,
                        "name": m.name,
                        "description": m.description,
                        "phase": m.phase.value if hasattr(m.phase, 'value') else str(m.phase),
                        "planned_start": m.planned_start.isoformat(),
                        "planned_end": m.planned_end.isoformat(),
                        "actual_start": m.actual_start.isoformat() if m.actual_start else None,
                        "actual_end": m.actual_end.isoformat() if m.actual_end else None,
                        "status": m.status.value if hasattr(m.status, 'value') else str(m.status),
                        "progress_percentage": m.progress_percentage,
                        "dependencies": m.dependencies,
                        "notes": m.notes
                    }
                    for m in schedule.milestones
                ],
                "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
                "updated_at": schedule.updated_at.isoformat() if schedule.updated_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching schedule: {e}", exc_info=True)
        # Retorna vazio ao invés de erro 500
        return {
            "project_id": project_id,
            "schedule": None,
            "message": f"Erro ao buscar cronograma: {str(e)}"
        }


@router.post("/{project_id}/schedule")
async def create_project_schedule(project_id: str, schedule_data: Dict[str, Any]):
    """Cria ou atualiza cronograma do projeto"""
    try:
        from infrastructure.database.project_models import (
            ProjectScheduleModel,
            ProjectMilestone,
            MilestoneStatus,
            ConstructionPhase,
            ConstructionProjectModel
        )
        from datetime import datetime

        logger.info(f"📅 POST /api/projects/{project_id}/schedule called")

        # Verifica se projeto existe
        project = await ConstructionProjectModel.find_one(
            ConstructionProjectModel.project_id == project_id
        )

        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")

        # Busca cronograma existente
        schedule = await ProjectScheduleModel.find_one(
            ProjectScheduleModel.project_id == project_id
        )

        # Parse dates
        project_start = datetime.fromisoformat(schedule_data['project_start'].replace('Z', '+00:00'))
        project_end = datetime.fromisoformat(schedule_data['project_end'].replace('Z', '+00:00'))

        # Parse milestones
        milestones = []
        for m_data in schedule_data.get('milestones', []):
            milestone = ProjectMilestone(
                name=m_data['name'],
                description=m_data.get('description'),
                phase=ConstructionPhase(m_data['phase']),
                planned_start=datetime.fromisoformat(m_data['planned_start'].replace('Z', '+00:00')),
                planned_end=datetime.fromisoformat(m_data['planned_end'].replace('Z', '+00:00')),
                status=MilestoneStatus(m_data.get('status', 'pending')),
                progress_percentage=m_data.get('progress_percentage', 0.0),
                dependencies=m_data.get('dependencies', []),
                notes=m_data.get('notes')
            )
            milestones.append(milestone)

        if schedule:
            # Atualiza existente
            schedule.name = schedule_data.get('name', schedule.name)
            schedule.description = schedule_data.get('description', schedule.description)
            schedule.project_start = project_start
            schedule.project_end = project_end
            schedule.milestones = milestones
            schedule.updated_at = datetime.utcnow()

            # Calcula progresso geral
            if milestones:
                schedule.overall_progress = sum(m.progress_percentage for m in milestones) / len(milestones)

            await schedule.save()
            logger.info(f"✅ Schedule updated for project {project_id}")
        else:
            # Cria novo
            schedule = ProjectScheduleModel(
                project_id=project_id,
                name=schedule_data.get('name', 'Cronograma do Projeto'),
                description=schedule_data.get('description'),
                project_start=project_start,
                project_end=project_end,
                milestones=milestones,
                overall_progress=sum(m.progress_percentage for m in milestones) / len(milestones) if milestones else 0
            )
            await schedule.save()
            logger.info(f"✅ Schedule created for project {project_id}")

        return {
            "message": "Cronograma salvo com sucesso",
            "schedule_id": schedule.schedule_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating/updating schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
