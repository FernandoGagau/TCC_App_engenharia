"""
Sistema de Análise de Timeline de Imagens da Obra
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import base64
import re
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConstructionImage:
    """Representa uma imagem da obra"""
    file_path: str
    date: datetime
    month: str
    day: str
    filename: str
    size: int
    analysis: Optional[Dict] = None

    def to_dict(self):
        data = asdict(self)
        data['date'] = self.date.isoformat()
        return data


@dataclass
class TimelinePeriod:
    """Representa um período da obra"""
    month: str
    month_number: int
    dates: List[str]
    image_count: int
    start_date: datetime
    end_date: datetime
    images: List[ConstructionImage]

    def to_dict(self):
        return {
            'month': self.month,
            'month_number': self.month_number,
            'dates': self.dates,
            'image_count': self.image_count,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'images': [img.to_dict() for img in self.images]
        }


class ImageTimelineManager:
    """Gerenciador de timeline de imagens da obra"""

    MONTH_MAP = {
        'Março': 3, 'Abril': 4, 'Maio': 5,
        'Junho': 6, 'Julho': 7, 'Agosto': 8
    }

    def __init__(self, uploads_path: str = "backend/uploads"):
        self.uploads_path = Path(uploads_path)
        self.timeline_cache = {}

    def parse_date_from_path(self, path: str) -> Tuple[datetime, str, str]:
        """Extrai data do caminho do arquivo"""
        parts = path.split('/')

        # Encontra o mês (ex: "1 - Março")
        month_part = None
        for part in parts:
            if ' - ' in part:
                month_part = part
                break

        if not month_part:
            return None, None, None

        month_name = month_part.split(' - ')[1]

        # Encontra a data (ex: "24.03.25")
        date_part = None
        for part in parts:
            if re.match(r'\d{2}\.\d{2}\.\d{2}', part):
                date_part = part
                break

        if not date_part:
            return None, month_name, None

        # Converte para datetime
        try:
            day, month, year = date_part.split('.')
            year = '20' + year  # Assume 20XX
            date = datetime(int(year), int(month), int(day))
            return date, month_name, date_part
        except:
            return None, month_name, date_part

    def scan_images(self, project_path: str = "24-03-2025") -> Dict[str, TimelinePeriod]:
        """Escaneia todas as imagens organizadas por período"""
        timeline = {}
        project_dir = self.uploads_path / project_path

        if not project_dir.exists():
            logger.warning(f"Diretório não encontrado: {project_dir}")
            return timeline

        # Percorre os meses
        for month_dir in sorted(project_dir.iterdir()):
            if not month_dir.is_dir():
                continue

            month_match = re.match(r'(\d+) - (.+)', month_dir.name)
            if not month_match:
                continue

            month_number = int(month_match.group(1))
            month_name = month_match.group(2)

            period = TimelinePeriod(
                month=month_name,
                month_number=month_number,
                dates=[],
                image_count=0,
                start_date=None,
                end_date=None,
                images=[]
            )

            # Percorre as datas dentro do mês
            for date_dir in sorted(month_dir.iterdir()):
                if not date_dir.is_dir():
                    continue

                period.dates.append(date_dir.name)

                # Percorre as imagens
                for img_file in date_dir.glob('*.jpg'):
                    date, _, day = self.parse_date_from_path(str(img_file))

                    if date:
                        if period.start_date is None or date < period.start_date:
                            period.start_date = date
                        if period.end_date is None or date > period.end_date:
                            period.end_date = date

                    image = ConstructionImage(
                        file_path=str(img_file),
                        date=date or datetime.now(),
                        month=month_name,
                        day=day or date_dir.name,
                        filename=img_file.name,
                        size=img_file.stat().st_size
                    )

                    period.images.append(image)
                    period.image_count += 1

            if period.image_count > 0:
                timeline[month_name] = period

        return timeline

    def get_timeline_summary(self, project_path: str = "24-03-2025") -> Dict:
        """Retorna resumo da timeline do projeto"""
        timeline = self.scan_images(project_path)

        total_images = sum(p.image_count for p in timeline.values())

        summary = {
            'project': project_path,
            'total_images': total_images,
            'total_months': len(timeline),
            'periods': [],
            'progress_timeline': []
        }

        for month_name, period in sorted(timeline.items(),
                                        key=lambda x: self.MONTH_MAP.get(x[0], 99)):
            summary['periods'].append({
                'month': month_name,
                'image_count': period.image_count,
                'dates_count': len(period.dates),
                'dates': period.dates,
                'start_date': period.start_date.isoformat() if period.start_date else None,
                'end_date': period.end_date.isoformat() if period.end_date else None
            })

        return summary

    def get_images_by_period(self, month: str, project_path: str = "24-03-2025") -> List[Dict]:
        """Retorna imagens de um período específico"""
        timeline = self.scan_images(project_path)

        if month not in timeline:
            return []

        period = timeline[month]
        return [img.to_dict() for img in period.images]

    def get_images_by_date(self, date: str, project_path: str = "24-03-2025") -> List[Dict]:
        """Retorna imagens de uma data específica"""
        timeline = self.scan_images(project_path)
        images = []

        for period in timeline.values():
            for img in period.images:
                if img.day == date:
                    images.append(img.to_dict())

        return images

    def compare_periods(self, month1: str, month2: str,
                       project_path: str = "24-03-2025") -> Dict:
        """Compara dois períodos da obra"""
        timeline = self.scan_images(project_path)

        if month1 not in timeline or month2 not in timeline:
            return {'error': 'Período não encontrado'}

        period1 = timeline[month1]
        period2 = timeline[month2]

        comparison = {
            'period1': {
                'month': month1,
                'image_count': period1.image_count,
                'dates': period1.dates,
                'start_date': period1.start_date.isoformat() if period1.start_date else None,
                'end_date': period1.end_date.isoformat() if period1.end_date else None
            },
            'period2': {
                'month': month2,
                'image_count': period2.image_count,
                'dates': period2.dates,
                'start_date': period2.start_date.isoformat() if period2.start_date else None,
                'end_date': period2.end_date.isoformat() if period2.end_date else None
            },
            'time_difference_days': None,
            'image_count_difference': period2.image_count - period1.image_count
        }

        if period1.start_date and period2.start_date:
            diff = period2.start_date - period1.start_date
            comparison['time_difference_days'] = diff.days

        return comparison

    def get_latest_images(self, limit: int = 10,
                         project_path: str = "24-03-2025") -> List[Dict]:
        """Retorna as imagens mais recentes"""
        timeline = self.scan_images(project_path)
        all_images = []

        for period in timeline.values():
            all_images.extend(period.images)

        # Ordena por data decrescente
        all_images.sort(key=lambda x: x.date, reverse=True)

        return [img.to_dict() for img in all_images[:limit]]

    def encode_image_base64(self, image_path: str) -> str:
        """Codifica imagem em base64"""
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Erro ao codificar imagem: {e}")
            return None

    def get_progress_analysis(self, project_path: str = "24-03-2025") -> Dict:
        """Analisa o progresso da obra baseado nas imagens"""
        timeline = self.scan_images(project_path)

        if not timeline:
            return {'error': 'Nenhuma imagem encontrada'}

        # Ordena períodos por mês
        sorted_periods = sorted(timeline.items(),
                               key=lambda x: self.MONTH_MAP.get(x[0], 99))

        progress = {
            'total_duration_days': 0,
            'total_images': 0,
            'periods_analyzed': len(sorted_periods),
            'monthly_progress': [],
            'activity_frequency': {}
        }

        first_date = None
        last_date = None

        for month_name, period in sorted_periods:
            if period.start_date:
                if first_date is None or period.start_date < first_date:
                    first_date = period.start_date
                if last_date is None or period.end_date > last_date:
                    last_date = period.end_date

            progress['total_images'] += period.image_count

            # Análise mensal
            monthly_data = {
                'month': month_name,
                'image_count': period.image_count,
                'dates_documented': len(period.dates),
                'documentation_frequency': round(len(period.dates) / 30 * 100, 1),  # % de dias documentados
                'period_start': period.start_date.isoformat() if period.start_date else None,
                'period_end': period.end_date.isoformat() if period.end_date else None
            }

            progress['monthly_progress'].append(monthly_data)

            # Frequência de atividade
            progress['activity_frequency'][month_name] = {
                'images_per_day': round(period.image_count / max(len(period.dates), 1), 1),
                'documentation_days': len(period.dates)
            }

        if first_date and last_date:
            progress['total_duration_days'] = (last_date - first_date).days
            progress['project_start'] = first_date.isoformat()
            progress['project_end'] = last_date.isoformat()
            progress['average_images_per_day'] = round(
                progress['total_images'] / max(progress['total_duration_days'], 1), 2
            )

        return progress