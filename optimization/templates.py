"""
Template Renderer - Sistema de plantillas optimizadas para reducir tokens
"""

import re
import json
from typing import Dict, Any, Optional
import logging

from .config import TEMPLATE_CONFIG, TEMPLATES_DIR

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """
    Renderiza respuestas usando plantillas optimizadas para reducir tokens.
    
    Características:
    - Plantillas específicas por tipo de consulta
    - Compresión inteligente de texto
    - Uso de emojis para conceptos comunes
    - Límites de tokens configurables
    """
    
    def __init__(self):
        """Inicializa el renderizador de plantillas."""
        self.templates = self._load_templates()
        logger.info(f"TemplateRenderer inicializado con {len(self.templates)} plantillas")
    
    def render(self, template_name: str, data: Dict) -> Dict:
        """
        Renderiza datos usando una plantilla específica.
        
        Args:
            template_name: Nombre de la plantilla a usar
            data: Datos a renderizar
            
        Returns:
            Dict con respuesta renderizada
        """
        # Obtener configuración de la plantilla
        template_config = TEMPLATE_CONFIG.get(template_name, {})
        
        # Seleccionar método de renderizado basado en formato
        format_type = template_config.get('format', 'compact')
        
        if format_type == 'compact':
            rendered = self._render_compact(template_config, data)
        elif format_type == 'comparison':
            rendered = self._render_comparison(template_config, data)
        elif format_type == 'hierarchical':
            rendered = self._render_hierarchical(template_config, data)
        elif format_type == 'summary':
            rendered = self._render_summary(template_config, data)
        else:
            # Fallback: renderizado básico
            rendered = self._render_basic(data)
        
        # Aplicar límite de tokens si existe
        max_tokens = template_config.get('max_tokens')
        if max_tokens:
            rendered = self._enforce_token_limit(rendered, max_tokens)
        
        # Agregar metadatos de renderizado
        rendered['_template'] = {
            'name': template_name,
            'format': format_type,
            'max_tokens': max_tokens
        }
        
        return rendered
    
    def _render_compact(self, config: Dict, data: Dict) -> Dict:
        """Renderiza en formato compacto (ideal para picks individuales)."""
        # Extraer campos requeridos
        fields = config.get('fields', ['pick', 'confidence', 'stake', 'reason_short'])
        
        # Construir respuesta compacta
        response_parts = []
        
        # Emoji basado en confianza
        confidence = data.get('confidence', 0)
        emoji_mapping = config.get('emoji_mapping', {})
        
        if confidence >= 70 and 'high_confidence' in emoji_mapping:
            emoji = emoji_mapping['high_confidence']
        elif confidence >= 50 and 'medium_confidence' in emoji_mapping:
            emoji = emoji_mapping['medium_confidence']
        elif confidence >= 30 and 'low_confidence' in emoji_mapping:
            emoji = emoji_mapping['low_confidence']
        else:
            emoji = emoji_mapping.get('avoid', '')
        
        response_parts.append(emoji)
        
        # Agregar campos
        for field in fields:
            if field in data:
                value = data[field]
                
                # Formatear específicamente por campo
                if field == 'confidence':
                    value = f"{value}%"
                elif field == 'stake':
                    value = f"{value}u"
                elif field == 'reason_short' and isinstance(value, str) and len(value) > 40:
                    value = value[:37] + "..."
                
                response_parts.append(str(value))
        
        # Unir todo
        response_text = " ".join(response_parts).strip()
        
        return {
            'text': response_text,
            'confidence': confidence,
            'stake': data.get('stake', 'N/A'),
            'reason': data.get('reason_short', data.get('reason', '')),
            'pick': data.get('pick', '')
        }
    
    def _render_comparison(self, config: Dict, data: Dict) -> Dict:
        """Renderiza en formato de comparación (ideal para peleas UFC)."""
        # Extraer datos de comparación
        fighter1 = data.get('fighter1', {})
        fighter2 = data.get('fighter2', {})
        
        # Construir comparación
        comparison_lines = []
        
        # Encabezado
        comparison_lines.append(f"🥊 {fighter1.get('name', 'Fighter 1')} vs {fighter2.get('name', 'Fighter 2')}")
        
        # Stats a mostrar
        show_stats = config.get('show_stats', ['record', 'age', 'reach', 'ko_rate'])
        
        for stat in show_stats:
            value1 = fighter1.get(stat, 'N/A')
            value2 = fighter2.get(stat, 'N/A')
            
            # Formatear específicamente
            if stat == 'ko_rate' and isinstance(value1, (int, float)):
                value1 = f"{value1:.1f}%"
            if stat == 'ko_rate' and isinstance(value2, (int, float)):
                value2 = f"{value2:.1f}%"
            
            stat_display = {
                'record': '📊 Record',
                'age': '📅 Edad',
                'reach': '📏 Alcance',
                'ko_rate': '💥 KO Rate'
            }.get(stat, stat.title())
            
            comparison_lines.append(f"{stat_display}: {value1} vs {value2}")
        
        # Análisis
        heuristic = data.get('heuristic_pick', {})
        ai_pick = data.get('ai_pick', {})
        
        if heuristic:
            comparison_lines.append(f"📈 Heurístico: {heuristic.get('pick', 'N/A')} @ {heuristic.get('confidence', 0)}%")
        
        if ai_pick:
            comparison_lines.append(f"🤖 IA: {ai_pick.get('pick', 'N/A')} ({ai_pick.get('confidence', 0)}%)")
        
        # Edge rating
        edge = data.get('edge_rating', 0)
        if edge:
            stars = "★" * min(10, int(edge)) + "☆" * (10 - min(10, int(edge)))
            comparison_lines.append(f"🔬 Edge: {stars}")
        
        response_text = "\n".join(comparison_lines)
        
        return {
            'text': response_text,
            'fighter1': fighter1.get('name'),
            'fighter2': fighter2.get('name'),
            'heuristic_pick': heuristic.get('pick') if heuristic else None,
            'ai_pick': ai_pick.get('pick') if ai_pick else None,
            'edge_rating': edge
        }
    
    def _render_hierarchical(self, config: Dict, data: Dict) -> Dict:
        """Renderiza en formato jerárquico (ideal para fútbol)."""
        # Extraer picks
        picks = data.get('picks', [])
        hierarchy = config.get('hierarchy', [])
        max_picks = config.get('max_picks', 3)
        
        # Filtrar y ordenar picks según jerarquía
        filtered_picks = []
        for pick_type in hierarchy:
            type_picks = [p for p in picks if p.get('type') == pick_type]
            filtered_picks.extend(type_picks[:2])  # Máximo 2 por tipo
        
        # Limitar número total
        filtered_picks = filtered_picks[:max_picks]
        
        # Construir respuesta jerárquica
        response_lines = []
        
        # Encabezado con liga
        league = data.get('league', '')
        if league:
            response_lines.append(f"⚽ {league} - TOP {len(filtered_picks)} PICKS")
        else:
            response_lines.append(f"⚽ TOP {len(filtered_picks)} PICKS")
        
        # Agregar picks con emojis de ranking
        ranking_emojis = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']
        
        for i, pick in enumerate(filtered_picks):
            if i < len(ranking_emojis):
                rank_emoji = ranking_emojis[i]
            else:
                rank_emoji = f"{i+1}️⃣"
            
            pick_text = pick.get('pick', '')
            confidence = pick.get('confidence', 0)
            reason = pick.get('reason', '')
            
            # Acortar razón si es muy larga
            if isinstance(reason, str) and len(reason) > 50:
                reason = reason[:47] + "..."
            
            line = f"{rank_emoji} {pick_text} @ {confidence}%"
            if reason:
                line += f" ({reason})"
            
            response_lines.append(line)
        
        # Agregar stats si están disponibles
        stats = data.get('stats', {})
        if stats:
            stats_line = []
            
            if 'shots' in stats:
                stats_line.append(f"Tiros {stats['shots']}")
            if 'possession' in stats:
                stats_line.append(f"Posesión {stats['possession']}%")
            if 'corners' in stats:
                stats_line.append(f"Corners {stats['corners']}")
            
            if stats_line:
                response_lines.append(f"📊 {' | '.join(stats_line)}")
        
        response_text = "\n".join(response_lines)
        
        return {
            'text': response_text,
            'picks': filtered_picks,
            'league': league,
            'total_picks': len(picks),
            'filtered_picks': len(filtered_picks)
        }
    
    def _render_summary(self, config: Dict, data: Dict) -> Dict:
        """Renderiza en formato de resumen."""
        fields = config.get('fields', ['best_pick', 'confidence', 'expected_value', 'stake'])
        
        # Construir resumen
        summary_parts = []
        
        # Emoji si está habilitado
        if config.get('include_emoji', True):
            summary_parts.append("📋")
        
        # Agregar campos
        for field in fields:
            if field in data:
                value = data[field]
                
                # Formatear
                if field == 'confidence':
                    value = f"{value}%"
                elif field == 'expected_value' and isinstance(value, (int, float)):
                    value = f"EV: {value:.2f}"
                elif field == 'stake':
                    value = f"Stake: {value}"
                elif field == 'best_pick':
                    value = f"Best: {value}"
                
                summary_parts.append(str(value))
        
        response_text = " | ".join(summary_parts)
        
        return {
            'text': response_text,
            'best_pick': data.get('best_pick'),
            'confidence': data.get('confidence', 0),
            'expected_value': data.get('expected_value', 0),
            'stake': data.get('stake', 'N/A')
        }
    
    def _render_basic(self, data: Dict) -> Dict:
        """Renderizado básico (fallback)."""
        # Extraer los campos más importantes
        important_fields = ['pick', 'confidence', 'stake', 'reason']
        
        response_parts = []
        for field in important_fields:
            if field in data and data[field]:
                value = data[field]
                
                # Formatear
                if field == 'confidence':
                    value = f"{value}%"
                elif field == 'stake':
                    value = f"{value}u"
                elif field == 'reason' and isinstance(value, str) and len(value) > 60:
                    value = value[:57] + "..."
                
                response_parts.append(str(value))
        
        response_text = " | ".join(response_parts)
        
        return {
            'text': response_text,
            **{k: v for k, v in data.items() if k in important_fields}
        }
    
    def _enforce_token_limit(self, rendered: Dict, max_tokens: int) -> Dict:
        """Aplica límite de tokens a la respuesta renderizada."""
        text = rendered.get('text', '')
        
        # Estimar tokens actuales
        current_tokens = self._estimate_tokens(text)
        
        if current_tokens <= max_tokens:
            return rendered
        
        # Reducir texto para cumplir límite
        logger.debug(f"Reduciendo texto de {current_tokens} a ~{max_tokens} tokens")
        
        # Estrategia de reducción
        if '\n' in text:
            # Texto multilínea - mantener primeras líneas
            lines = text.split('\n')
            reduced_lines = []
            accumulated_tokens = 0
            
            for line in lines:
                line_tokens = self._estimate_tokens(line)
                if accumulated_tokens + line_tokens <= max_tokens * 0.8:  # Dejar margen
                    reduced_lines.append(line)
                    accumulated_tokens += line_tokens
                else:
                    reduced_lines.append("...")
                    break
            
            reduced_text = '\n'.join(reduced_lines)
        else:
            # Texto de una línea - truncar
            chars_per_token = 2.5  # Aproximación para español
            max_chars = int(max_tokens * chars_per_token * 0.9)  # 90% para margen
            
            if len(text) > max_chars:
                reduced_text = text[:max_chars - 3] + "..."
            else:
                reduced_text = text
        
        rendered['text'] = reduced_text
        rendered['_truncated'] = True
        rendered['_original_tokens'] = current_tokens
        rendered['_truncated_tokens'] = self._estimate_tokens(reduced_text)
        
        return rendered
    
    def _estimate_tokens(self, text: str) -> int:
        """Estima número de tokens en un texto."""
        if not text:
            return 0
        
        # Aproximación simple para español
        # Español: ~2.5 caracteres por token en promedio
        return max(1, int(len(text) / 2.5))
    
    def _load_templates(self) -> Dict:
        """Carga plantillas desde archivos."""
        templates = {}
        
        # Cargar plantillas predefinidas desde configuración
        for name, config in TEMPLATE_CONFIG.items():
            templates[name] = {
                'config': config,
                'type': 'builtin'
            }
        
        # Intentar cargar plantillas personalizadas desde directorio
        try:
            if os.path.exists(TEMPLATES_DIR):
                for filename in os.listdir(TEMPLATES_DIR):
                    if filename.endswith('.json'):
                        template_name = filename[:-5]
                        filepath = os.path.join(TEMPLATES_DIR, filename)
                        
                        with open(filepath, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                        
                        templates[template_name] = {
                            'config': template_data,
                            'type': 'custom',
                            'file': filename
                        }
                        
                        logger.debug(f"Plantilla personalizada cargada: {template_name}")
        except Exception as e:
            logger.error(f"Error cargando plantillas personalizadas: {e}")
        
        return templates
    
    def get_template_info(self, template_name: str = None) -> Dict:
        """Obtiene información sobre plantillas."""
        if template_name:
            if template_name in self.templates:
                template = self.templates[template_name]
                return {
                    'name': template_name,
                    'type': template.get('type', 'unknown'),
                    'config': template.get('config', {}),
                    'fields': template.get('config', {}).get('fields', []),
                    'max_tokens': template.get('config', {}).get('max_tokens')
                }
            else:
                return {'error': f'Plantilla no encontrada: {template_name}'}
        else:
            # Listar todas las plantillas
            return {
                'templates': list(self.templates.keys()),
                'count': len(self.templates),
                'types': {
                    'builtin': len([t for t in self.templates.values() if t.get('type') == 'builtin']),
                    'custom': len([t for t in self.templates.values() if t.get('type') == 'custom'])
                }
            }
    
    def create_custom_template(self, name: str, config: Dict) -> bool:
        """
        Crea una plantilla personalizada.
        
        Args:
            name: Nombre de la plantilla
            config: Configuración de la plantilla
            
        Returns:
            True si se creó exitosamente
        """
        try:
            # Validar configuración básica
            required_fields = ['format', 'max_tokens', 'fields']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Campo requerido faltante: {field}")
            
            # Guardar en archivo
            filepath = os.path.join(TEMPLATES_DIR, f"{name}.json")
            os.makedirs(TEMPLATES_DIR, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # Actualizar caché de plantillas
            self.templates[name] = {
                'config': config,
                'type': 'custom',
                'file': f"{name}.json"
            }
            
            logger.info(f"Plantilla personalizada creada: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creando plantilla {name}: {e}")
            return False
    
    def delete_custom_template(self, name: str) -> bool:
        """Elimina una plantilla personalizada."""
        try:
            # Verificar que existe y es personalizada
            if name not in self.templates:
                return False
            
            template = self.templates[name]
            if template.get('type') != 'custom':
                logger.warning(f"No se puede eliminar plantilla builtin: {name}")
                return False
            
            # Eliminar archivo
            filename = template.get('file')
            if filename:
                filepath = os.path.join(TEMPLATES_DIR, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            # Eliminar de caché
            del self.templates[name]
            
            logger.info(f"Plantilla personalizada eliminada: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando plantilla {name}: {e}")
            return False
    
    def test_template(self, template_name: str, test_data: Dict) -> Dict:
        """
        Prueba una plantilla con datos de prueba.
        
        Args:
            template_name: Nombre de la plantilla
            test_data: Datos de prueba
            
        Returns:
            Resultados de la prueba
        """
        try:
            # Renderizar con plantilla
            rendered = self.render(template_name, test_data)
            
            # Calcular métricas
            text = rendered.get('text', '')
            tokens = self._estimate_tokens(text)
            
            # Información de la plantilla
            template_info = self.get_template_info(template_name)
            max_tokens = template_info.get('config', {}).get('max_tokens', 0)
            
            return {
                'success': True,
                'template': template_name,
                'rendered_text': text,
                'tokens_used': tokens,
                'max_tokens_allowed': max_tokens,
                'within_limit': tokens <= max_tokens if max_tokens > 0 else True,
                'compression_ratio': None,  # Necesitaríamos texto original para calcular
                'rendered_data': rendered
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'template': template_name
            }