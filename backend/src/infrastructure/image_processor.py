"""
Image Processing Pipeline
Advanced image optimization, analysis and transformation
"""

import io
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS
import numpy as np

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Processador avançado de imagens
    Otimização, análise e transformações
    """

    @staticmethod
    async def optimize_image(
        content: bytes,
        max_width: int = 2048,
        max_height: int = 2048,
        quality: int = 85,
        format_output: str = 'JPEG'
    ) -> bytes:
        """
        Otimizar imagem para web mantendo qualidade visual

        Args:
            content: Conteúdo da imagem em bytes
            max_width: Largura máxima
            max_height: Altura máxima
            quality: Qualidade JPEG (1-100)
            format_output: Formato de saída (JPEG, PNG, WEBP)

        Returns:
            Imagem otimizada em bytes
        """
        try:
            with Image.open(io.BytesIO(content)) as img:
                # Corrigir orientação baseada em EXIF
                img = ImageOps.exif_transpose(img)

                # Redimensionar mantendo proporção
                img = await ImageProcessor._resize_maintain_ratio(
                    img, max_width, max_height
                )

                # Otimizar para formato específico
                if format_output.upper() == 'JPEG':
                    img = await ImageProcessor._optimize_for_jpeg(img)
                elif format_output.upper() == 'PNG':
                    img = await ImageProcessor._optimize_for_png(img)
                elif format_output.upper() == 'WEBP':
                    img = await ImageProcessor._optimize_for_webp(img)

                # Aplicar filtro de nitidez suave
                img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=50, threshold=3))

                # Salvar otimizado
                output = io.BytesIO()
                save_kwargs = {'format': format_output.upper(), 'optimize': True}

                if format_output.upper() == 'JPEG':
                    save_kwargs['quality'] = quality
                    save_kwargs['progressive'] = True
                elif format_output.upper() == 'PNG':
                    save_kwargs['compress_level'] = 6
                elif format_output.upper() == 'WEBP':
                    save_kwargs['quality'] = quality
                    save_kwargs['method'] = 6

                img.save(output, **save_kwargs)
                return output.getvalue()

        except Exception as e:
            logger.error(f"Erro na otimização de imagem: {e}")
            raise

    @staticmethod
    async def _resize_maintain_ratio(
        img: Image.Image,
        max_width: int,
        max_height: int
    ) -> Image.Image:
        """Redimensionar mantendo proporção"""
        if img.width <= max_width and img.height <= max_height:
            return img

        # Calcular nova dimensão mantendo proporção
        width_ratio = max_width / img.width
        height_ratio = max_height / img.height
        ratio = min(width_ratio, height_ratio)

        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)

        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    @staticmethod
    async def _optimize_for_jpeg(img: Image.Image) -> Image.Image:
        """Otimizar para formato JPEG"""
        # Converter para RGB se necessário
        if img.mode in ('RGBA', 'LA', 'P'):
            # Criar fundo branco para transparência
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        return img

    @staticmethod
    async def _optimize_for_png(img: Image.Image) -> Image.Image:
        """Otimizar para formato PNG"""
        # PNG suporta transparência, manter modo original se possível
        if img.mode not in ('RGB', 'RGBA', 'P', 'L'):
            if img.mode in ('LA', 'RGBA'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
        return img

    @staticmethod
    async def _optimize_for_webp(img: Image.Image) -> Image.Image:
        """Otimizar para formato WebP"""
        # WebP suporta tanto RGB quanto RGBA
        if img.mode not in ('RGB', 'RGBA'):
            if 'transparency' in img.info or img.mode in ('LA', 'RGBA'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
        return img

    @staticmethod
    async def create_thumbnail(
        content: bytes,
        size: Tuple[int, int],
        crop_strategy: str = 'center'
    ) -> bytes:
        """
        Criar thumbnail com diferentes estratégias de crop

        Args:
            content: Conteúdo da imagem
            size: Tuple (width, height) do thumbnail
            crop_strategy: 'center', 'smart', 'top', 'bottom'

        Returns:
            Thumbnail em bytes
        """
        try:
            with Image.open(io.BytesIO(content)) as img:
                # Corrigir orientação
                img = ImageOps.exif_transpose(img)

                if crop_strategy == 'center':
                    thumb = ImageOps.fit(img, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                elif crop_strategy == 'smart':
                    thumb = await ImageProcessor._smart_crop(img, size)
                elif crop_strategy == 'top':
                    thumb = ImageOps.fit(img, size, Image.Resampling.LANCZOS, centering=(0.5, 0.0))
                elif crop_strategy == 'bottom':
                    thumb = ImageOps.fit(img, size, Image.Resampling.LANCZOS, centering=(0.5, 1.0))
                else:
                    thumb = img.copy()
                    thumb.thumbnail(size, Image.Resampling.LANCZOS)

                # Aplicar nitidez no thumbnail
                thumb = thumb.filter(ImageFilter.UnsharpMask(radius=0.5, percent=100, threshold=2))

                # Converter para JPEG otimizado
                if thumb.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', thumb.size, (255, 255, 255))
                    if thumb.mode == 'P':
                        thumb = thumb.convert('RGBA')
                    background.paste(thumb, mask=thumb.split()[-1] if thumb.mode in ['RGBA', 'LA'] else None)
                    thumb = background

                output = io.BytesIO()
                thumb.save(output, format='JPEG', quality=90, optimize=True)
                return output.getvalue()

        except Exception as e:
            logger.error(f"Erro ao criar thumbnail: {e}")
            raise

    @staticmethod
    async def _smart_crop(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """
        Crop inteligente focando na área mais interessante
        Algoritmo simples baseado em variância de pixels
        """
        try:
            # Converter para grayscale para análise
            gray = img.convert('L')
            img_array = np.array(gray)

            # Calcular razão de aspecto
            target_ratio = size[0] / size[1]
            img_ratio = img.width / img.height

            if abs(img_ratio - target_ratio) < 0.1:
                # Proporções similares, usar crop central
                return ImageOps.fit(img, size, Image.Resampling.LANCZOS)

            # Determinar dimensões da área de crop
            if img_ratio > target_ratio:
                # Imagem mais larga, crop horizontal
                crop_width = int(img.height * target_ratio)
                crop_height = img.height

                # Encontrar melhor posição horizontal
                best_x = await ImageProcessor._find_best_horizontal_crop(
                    img_array, crop_width
                )
                crop_box = (best_x, 0, best_x + crop_width, crop_height)
            else:
                # Imagem mais alta, crop vertical
                crop_width = img.width
                crop_height = int(img.width / target_ratio)

                # Encontrar melhor posição vertical
                best_y = await ImageProcessor._find_best_vertical_crop(
                    img_array, crop_height
                )
                crop_box = (0, best_y, crop_width, best_y + crop_height)

            # Aplicar crop e redimensionar
            cropped = img.crop(crop_box)
            return cropped.resize(size, Image.Resampling.LANCZOS)

        except Exception as e:
            logger.warning(f"Erro no smart crop, usando crop central: {e}")
            return ImageOps.fit(img, size, Image.Resampling.LANCZOS)

    @staticmethod
    async def _find_best_horizontal_crop(img_array: np.ndarray, crop_width: int) -> int:
        """Encontrar melhor posição para crop horizontal"""
        max_variance = 0
        best_x = 0

        # Testar diferentes posições
        for x in range(0, img_array.shape[1] - crop_width, 20):
            crop_section = img_array[:, x:x + crop_width]
            variance = np.var(crop_section)

            if variance > max_variance:
                max_variance = variance
                best_x = x

        return best_x

    @staticmethod
    async def _find_best_vertical_crop(img_array: np.ndarray, crop_height: int) -> int:
        """Encontrar melhor posição para crop vertical"""
        max_variance = 0
        best_y = 0

        # Testar diferentes posições
        for y in range(0, img_array.shape[0] - crop_height, 20):
            crop_section = img_array[y:y + crop_height, :]
            variance = np.var(crop_section)

            if variance > max_variance:
                max_variance = variance
                best_y = y

        return best_y

    @staticmethod
    async def extract_detailed_exif(content: bytes) -> Dict[str, Any]:
        """
        Extrair dados EXIF detalhados incluindo GPS

        Args:
            content: Conteúdo da imagem

        Returns:
            Dicionário com dados EXIF organizados
        """
        try:
            with Image.open(io.BytesIO(content)) as img:
                exif_data = {}

                # Obter dados EXIF brutos
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()

                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, f"Tag{tag_id}")

                        # Processar dados GPS especialmente
                        if tag_name == 'GPSInfo':
                            gps_data = {}
                            for gps_tag_id, gps_value in value.items():
                                gps_tag_name = GPSTAGS.get(gps_tag_id, f"GPSTag{gps_tag_id}")
                                gps_data[gps_tag_name] = gps_value
                            exif_data['gps'] = await ImageProcessor._process_gps_data(gps_data)
                        else:
                            # Converter valores complexos para strings
                            if isinstance(value, (bytes, tuple)):
                                value = str(value)
                            elif isinstance(value, dict):
                                value = {str(k): str(v) for k, v in value.items()}

                            exif_data[tag_name] = value

                # Extrair dados específicos úteis
                return {
                    'camera_info': {
                        'make': exif_data.get('Make'),
                        'model': exif_data.get('Model'),
                        'software': exif_data.get('Software'),
                        'orientation': exif_data.get('Orientation')
                    },
                    'capture_info': {
                        'datetime': exif_data.get('DateTime'),
                        'datetime_original': exif_data.get('DateTimeOriginal'),
                        'datetime_digitized': exif_data.get('DateTimeDigitized')
                    },
                    'technical_info': {
                        'iso': exif_data.get('ISOSpeedRatings'),
                        'focal_length': exif_data.get('FocalLength'),
                        'aperture': exif_data.get('FNumber'),
                        'shutter_speed': exif_data.get('ExposureTime'),
                        'flash': exif_data.get('Flash'),
                        'white_balance': exif_data.get('WhiteBalance')
                    },
                    'gps_info': exif_data.get('gps', {}),
                    'raw_exif': exif_data
                }

        except Exception as e:
            logger.warning(f"Erro ao extrair EXIF: {e}")
            return {}

    @staticmethod
    async def _process_gps_data(gps_data: Dict) -> Dict[str, Any]:
        """Processar dados GPS do EXIF"""
        try:
            processed_gps = {}

            if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
                lat = await ImageProcessor._convert_gps_coordinate(
                    gps_data['GPSLatitude'], gps_data['GPSLatitudeRef']
                )
                processed_gps['latitude'] = lat

            if 'GPSLongitude' in gps_data and 'GPSLongitudeRef' in gps_data:
                lon = await ImageProcessor._convert_gps_coordinate(
                    gps_data['GPSLongitude'], gps_data['GPSLongitudeRef']
                )
                processed_gps['longitude'] = lon

            if 'GPSAltitude' in gps_data:
                alt = float(gps_data['GPSAltitude'])
                if 'GPSAltitudeRef' in gps_data and gps_data['GPSAltitudeRef'] == 1:
                    alt = -alt  # Below sea level
                processed_gps['altitude'] = alt

            if 'GPSTimeStamp' in gps_data:
                processed_gps['gps_timestamp'] = str(gps_data['GPSTimeStamp'])

            if 'GPSDateStamp' in gps_data:
                processed_gps['gps_datestamp'] = str(gps_data['GPSDateStamp'])

            return processed_gps

        except Exception as e:
            logger.warning(f"Erro ao processar GPS: {e}")
            return {}

    @staticmethod
    async def _convert_gps_coordinate(coordinate: tuple, reference: str) -> float:
        """Converter coordenada GPS de graus/minutos/segundos para decimal"""
        degrees, minutes, seconds = coordinate
        decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600

        if reference in ['S', 'W']:
            decimal = -decimal

        return decimal

    @staticmethod
    async def analyze_image_quality(content: bytes) -> Dict[str, Any]:
        """
        Analisar qualidade da imagem

        Args:
            content: Conteúdo da imagem

        Returns:
            Análise de qualidade
        """
        try:
            with Image.open(io.BytesIO(content)) as img:
                # Converter para arrays numpy para análise
                img_array = np.array(img.convert('RGB'))

                # Calcular métricas básicas
                brightness = np.mean(img_array)
                contrast = np.std(img_array)

                # Detectar blur (simplicidade via variância do Laplaciano)
                gray = np.array(img.convert('L'))
                laplacian_var = await ImageProcessor._calculate_laplacian_variance(gray)

                # Analisar cores
                color_analysis = await ImageProcessor._analyze_colors(img_array)

                # Detectar saturação
                hsv = img.convert('HSV')
                hsv_array = np.array(hsv)
                saturation = np.mean(hsv_array[:, :, 1])

                return {
                    'dimensions': {
                        'width': img.width,
                        'height': img.height,
                        'megapixels': round((img.width * img.height) / 1_000_000, 2)
                    },
                    'quality_metrics': {
                        'brightness': round(brightness, 2),
                        'contrast': round(contrast, 2),
                        'sharpness': await ImageProcessor._assess_sharpness(laplacian_var),
                        'saturation': round(saturation / 255 * 100, 2),
                        'blur_score': round(laplacian_var, 2)
                    },
                    'color_analysis': color_analysis,
                    'assessment': await ImageProcessor._overall_quality_assessment(
                        brightness, contrast, laplacian_var, saturation
                    )
                }

        except Exception as e:
            logger.error(f"Erro na análise de qualidade: {e}")
            return {}

    @staticmethod
    async def _calculate_laplacian_variance(gray_array: np.ndarray) -> float:
        """Calcular variância do Laplaciano para detectar blur"""
        try:
            # Filtro Laplaciano simples
            laplacian = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]])

            # Aplicar convolução
            from scipy import ndimage
            filtered = ndimage.convolve(gray_array.astype(float), laplacian)
            return float(np.var(filtered))
        except:
            # Fallback simples se scipy não estiver disponível
            return float(np.var(np.gradient(gray_array)))

    @staticmethod
    async def _analyze_colors(img_array: np.ndarray) -> Dict[str, Any]:
        """Analisar distribuição de cores"""
        try:
            # Cores dominantes (simplificado)
            colors = img_array.reshape(-1, 3)
            unique_colors, counts = np.unique(colors, axis=0, return_counts=True)

            # Top 5 cores mais comuns
            top_indices = np.argsort(counts)[-5:][::-1]
            dominant_colors = []

            for i in top_indices:
                color = unique_colors[i]
                percentage = counts[i] / len(colors) * 100
                dominant_colors.append({
                    'rgb': color.tolist(),
                    'hex': f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
                    'percentage': round(percentage, 2)
                })

            # Análise de temperatura de cor
            avg_red = np.mean(img_array[:, :, 0])
            avg_blue = np.mean(img_array[:, :, 2])
            temperature = 'warm' if avg_red > avg_blue else 'cool'

            return {
                'dominant_colors': dominant_colors,
                'color_temperature': temperature,
                'avg_rgb': [
                    round(np.mean(img_array[:, :, 0]), 2),
                    round(np.mean(img_array[:, :, 1]), 2),
                    round(np.mean(img_array[:, :, 2]), 2)
                ]
            }

        except Exception as e:
            logger.warning(f"Erro na análise de cores: {e}")
            return {}

    @staticmethod
    async def _assess_sharpness(laplacian_var: float) -> str:
        """Avaliar nitidez baseada na variância do Laplaciano"""
        if laplacian_var > 1000:
            return 'high'
        elif laplacian_var > 500:
            return 'medium'
        elif laplacian_var > 100:
            return 'low'
        else:
            return 'very_low'

    @staticmethod
    async def _overall_quality_assessment(
        brightness: float,
        contrast: float,
        sharpness: float,
        saturation: float
    ) -> Dict[str, Any]:
        """Avaliação geral da qualidade"""
        score = 0
        issues = []

        # Avaliar brilho (ideal entre 64-192)
        if 64 <= brightness <= 192:
            score += 25
        else:
            if brightness < 64:
                issues.append('too_dark')
            else:
                issues.append('too_bright')

        # Avaliar contraste (ideal > 30)
        if contrast > 30:
            score += 25
        else:
            issues.append('low_contrast')

        # Avaliar nitidez (ideal > 500)
        if sharpness > 500:
            score += 25
        else:
            issues.append('low_sharpness')

        # Avaliar saturação (ideal 20-80%)
        saturation_pct = saturation / 255 * 100
        if 20 <= saturation_pct <= 80:
            score += 25
        else:
            if saturation_pct < 20:
                issues.append('undersaturated')
            else:
                issues.append('oversaturated')

        # Determinar classificação
        if score >= 75:
            quality = 'excellent'
        elif score >= 50:
            quality = 'good'
        elif score >= 25:
            quality = 'fair'
        else:
            quality = 'poor'

        return {
            'score': score,
            'rating': quality,
            'issues': issues
        }