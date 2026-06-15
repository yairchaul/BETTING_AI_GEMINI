"""
Token Monitor - Sistema de monitoreo y métricas para optimización de tokens
"""

import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from .config import METRICS_CONFIG, METRICS_DIR

logger = logging.getLogger(__name__)


class TokenMonitor:
    """
    Monitorea y analiza métricas de optimización de tokens.
    
    Métricas clave:
    - Tokens por consulta
    - Eficiencia (información/tokens)
    - Hit rate del caché
    - Tiempos de procesamiento
    - Ahorro total de tokens
    """
    
    def __init__(self):
        """Inicializa el monitor de métricas."""
        self.metrics_store = []
        self.aggregated_stats = {
            'daily': {},
            'hourly': {},
            'by_query_type': {}
        }
        
        # Cargar métricas históricas
        self._load_historical_metrics()
        
        logger.info("TokenMonitor inicializado")
    
    def track_query(self, query_info: Dict):
        """
        Registra métricas de una consulta procesada.
        
        Args:
            query_info: Información de la consulta
        """
        # Agregar timestamp si no existe
        if 'timestamp' not in query_info:
            query_info['timestamp'] = time.time()
        
        # Calcular eficiencia si no está presente
        if 'efficiency' not in query_info:
            query_info['efficiency'] = self._calculate_efficiency(query_info)
        
        # Agregar a store
        self.metrics_store.append(query_info)
        
        # Actualizar estadísticas agregadas
        self._update_aggregated_stats(query_info)
        
        # Verificar alertas
        self._check_alerts(query_info)
        
        # Persistir periódicamente
        if len(self.metrics_store) % 100 == 0:
            self._persist_metrics()
        
        logger.debug(f"Métricas registradas para consulta: {query_info.get('query_type', 'unknown')}")
    
    def get_metrics_summary(self, time_range: str = '24h') -> Dict:
        """
        Obtiene resumen de métricas para un rango de tiempo.
        
        Args:
            time_range: '1h', '24h', '7d', '30d'
            
        Returns:
            Resumen de métricas
        """
        # Filtrar métricas por tiempo
        cutoff_time = self._get_cutoff_time(time_range)
        recent_metrics = [
            m for m in self.metrics_store
            if m.get('timestamp', 0) >= cutoff_time
        ]
        
        if not recent_metrics:
            return {
                'time_range': time_range,
                'total_queries': 0,
                'message': 'No hay datos para el rango especificado'
            }
        
        # Calcular métricas agregadas
        total_queries = len(recent_metrics)
        
        # Tokens
        total_tokens = sum(m.get('tokens_used', 0) for m in recent_metrics)
        avg_tokens = total_tokens / total_queries if total_queries > 0 else 0
        
        # Eficiencia
        efficiencies = [m.get('efficiency', 0) for m in recent_metrics if 'efficiency' in m]
        avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
        
        # Cache
        cache_hits = sum(1 for m in recent_metrics if m.get('from_cache', False))
        cache_hit_rate = (cache_hits / total_queries) * 100 if total_queries > 0 else 0
        
        # Tiempos
        processing_times = [m.get('processing_time', 0) for m in recent_metrics if 'processing_time' in m]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Tokens ahorrados
        tokens_saved = sum(m.get('tokens_saved', 0) for m in recent_metrics if 'tokens_saved' in m)
        
        # Por tipo de consulta
        by_type = {}
        for metric in recent_metrics:
            qtype = metric.get('query_type', 'unknown')
            if qtype not in by_type:
                by_type[qtype] = {'count': 0, 'tokens': 0}
            by_type[qtype]['count'] += 1
            by_type[qtype]['tokens'] += metric.get('tokens_used', 0)
        
        # Calcular porcentajes
        for qtype in by_type:
            by_type[qtype]['percentage'] = (by_type[qtype]['count'] / total_queries) * 100
            by_type[qtype]['avg_tokens'] = by_type[qtype]['tokens'] / by_type[qtype]['count']
        
        return {
            'time_range': time_range,
            'total_queries': total_queries,
            'avg_tokens_per_query': round(avg_tokens, 1),
            'avg_efficiency': round(avg_efficiency, 3),
            'cache_hit_rate': round(cache_hit_rate, 1),
            'avg_processing_time': round(avg_processing_time, 3),
            'tokens_saved': tokens_saved,
            'by_query_type': by_type,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_efficiency_trend(self, time_range: str = '7d') -> List[Dict]:
        """
        Obtiene tendencia de eficiencia a lo largo del tiempo.
        
        Args:
            time_range: '24h', '7d', '30d'
            
        Returns:
            Lista de puntos de eficiencia por intervalo
        """
        cutoff_time = self._get_cutoff_time(time_range)
        recent_metrics = [
            m for m in self.metrics_store
            if m.get('timestamp', 0) >= cutoff_time and 'efficiency' in m
        ]
        
        if not recent_metrics:
            return []
        
        # Agrupar por intervalo de tiempo
        interval_seconds = self._get_interval_seconds(time_range)
        trend_data = []
        
        current_interval = int(min(m['timestamp'] for m in recent_metrics) / interval_seconds) * interval_seconds
        
        while current_interval <= time.time():
            interval_end = current_interval + interval_seconds
            
            # Métricas en este intervalo
            interval_metrics = [
                m for m in recent_metrics
                if current_interval <= m['timestamp'] < interval_end
            ]
            
            if interval_metrics:
                avg_efficiency = sum(m['efficiency'] for m in interval_metrics) / len(interval_metrics)
                query_count = len(interval_metrics)
                
                trend_data.append({
                    'timestamp': current_interval,
                    'datetime': datetime.fromtimestamp(current_interval).isoformat(),
                    'efficiency': round(avg_efficiency, 3),
                    'query_count': query_count
                })
            
            current_interval += interval_seconds
        
        return trend_data
    
    def get_top_inefficient_queries(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene las consultas más ineficientes (menor eficiencia).
        
        Args:
            limit: Número máximo de resultados
            
        Returns:
            Lista de consultas ineficientes
        """
        # Filtrar consultas con métricas de eficiencia
        queries_with_efficiency = [
            m for m in self.metrics_store
            if 'efficiency' in m and 'query_text' in m
        ]
        
        if not queries_with_efficiency:
            return []
        
        # Ordenar por eficiencia (ascendente)
        sorted_queries = sorted(
            queries_with_efficiency,
            key=lambda x: x.get('efficiency', 1)
        )
        
        # Formatear resultados
        results = []
        for i, query in enumerate(sorted_queries[:limit]):
            results.append({
                'rank': i + 1,
                'query_text': query.get('query_text', '')[:100],
                'query_type': query.get('query_type', 'unknown'),
                'efficiency': round(query.get('efficiency', 0), 3),
                'tokens_used': query.get('tokens_used', 0),
                'from_cache': query.get('from_cache', False),
                'timestamp': query.get('timestamp'),
                'datetime': datetime.fromtimestamp(query['timestamp']).isoformat() if 'timestamp' in query else None
            })
        
        return results
    
    def get_cache_analysis(self) -> Dict:
        """Analiza rendimiento del caché."""
        # Agrupar por tipo de consulta
        cache_analysis = {}
        
        for metric in self.metrics_store:
            qtype = metric.get('query_type', 'unknown')
            if qtype not in cache_analysis:
                cache_analysis[qtype] = {
                    'total': 0,
                    'hits': 0,
                    'misses': 0,
                    'tokens_with_cache': 0,
                    'tokens_without_cache': 0
                }
            
            cache_analysis[qtype]['total'] += 1
            
            if metric.get('from_cache', False):
                cache_analysis[qtype]['hits'] += 1
                cache_analysis[qtype]['tokens_with_cache'] += metric.get('tokens_used', 0)
            else:
                cache_analysis[qtype]['misses'] += 1
                cache_analysis[qtype]['tokens_without_cache'] += metric.get('tokens_used', 0)
        
        # Calcular métricas derivadas
        for qtype in cache_analysis:
            stats = cache_analysis[qtype]
            
            # Hit rate
            if stats['total'] > 0:
                stats['hit_rate'] = (stats['hits'] / stats['total']) * 100
            
            # Tokens promedio
            if stats['hits'] > 0:
                stats['avg_tokens_cache'] = stats['tokens_with_cache'] / stats['hits']
            if stats['misses'] > 0:
                stats['avg_tokens_no_cache'] = stats['tokens_without_cache'] / stats['misses']
            
            # Ahorro estimado
            if 'avg_tokens_cache' in stats and 'avg_tokens_no_cache' in stats:
                stats['tokens_saved_per_query'] = stats['avg_tokens_no_cache'] - stats['avg_tokens_cache']
                stats['total_tokens_saved'] = stats['tokens_saved_per_query'] * stats['hits']
        
        return cache_analysis
    
    def get_system_health(self) -> Dict:
        """Obtiene estado de salud del sistema basado en métricas."""
        # Métricas recientes (última hora)
        hour_ago = time.time() - 3600
        recent_metrics = [m for m in self.metrics_store if m.get('timestamp', 0) >= hour_ago]
        
        if not recent_metrics:
            return {
                'status': 'no_data',
                'message': 'No hay datos recientes',
                'timestamp': datetime.now().isoformat()
            }
        
        # Calcular métricas clave
        total_recent = len(recent_metrics)
        
        # Eficiencia promedio
        efficiencies = [m.get('efficiency', 0) for m in recent_metrics if 'efficiency' in m]
        avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
        
        # Cache hit rate
        cache_hits = sum(1 for m in recent_metrics if m.get('from_cache', False))
        cache_hit_rate = (cache_hits / total_recent) * 100 if total_recent > 0 else 0
        
        # Determinar estado
        issues = []
        
        if avg_efficiency < METRICS_CONFIG['alert_threshold']:
            issues.append(f"Baja eficiencia: {avg_efficiency:.3f} < {METRICS_CONFIG['alert_threshold']}")
        
        if cache_hit_rate < METRICS_CONFIG['min_cache_hit_rate'] * 100:
            issues.append(f"Bajo cache hit rate: {cache_hit_rate:.1f}% < {METRICS_CONFIG['min_cache_hit_rate'] * 100}%")
        
        # Tokens por consulta
        avg_tokens = sum(m.get('tokens_used', 0) for m in recent_metrics) / total_recent
        if avg_tokens > METRICS_CONFIG['max_tokens_per_query']:
            issues.append(f"Alto uso de tokens: {avg_tokens:.0f} > {METRICS_CONFIG['max_tokens_per_query']}")
        
        # Estado final
        if issues:
            status = 'degraded'
            message = f"Problemas detectados: {', '.join(issues)}"
        else:
            status = 'healthy'
            message = 'Todas las métricas dentro de rangos aceptables'
        
        return {
            'status': status,
            'message': message,
            'issues': issues,
            'metrics': {
                'avg_efficiency': round(avg_efficiency, 3),
                'cache_hit_rate': round(cache_hit_rate, 1),
                'avg_tokens_per_query': round(avg_tokens, 1),
                'total_queries_last_hour': total_recent
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_report(self, report_type: str = 'daily') -> Dict:
        """
        Genera un reporte de métricas.
        
        Args:
            report_type: 'daily', 'weekly', 'monthly'
            
        Returns:
            Reporte formateado
        """
        # Determinar rango de tiempo
        if report_type == 'daily':
            time_range = '24h'
            title = "Reporte Diario"
        elif report_type == 'weekly':
            time_range = '7d'
            title = "Reporte Semanal"
        elif report_type == 'monthly':
            time_range = '30d'
            title = "Reporte Mensual"
        else:
            time_range = '24h'
            title = "Reporte"
        
        # Obtener métricas
        summary = self.get_metrics_summary(time_range)
        efficiency_trend = self.get_efficiency_trend(time_range)
        cache_analysis = self.get_cache_analysis()
        system_health = self.get_system_health()
        inefficient_queries = self.get_top_inefficient_queries(5)
        
        # Construir reporte
        report = {
            'title': title,
            'generated_at': datetime.now().isoformat(),
            'time_range': time_range,
            'summary': summary,
            'system_health': system_health,
            'cache_analysis': cache_analysis,
            'efficiency_trend': efficiency_trend[-10:] if efficiency_trend else [],  # Últimos 10 puntos
            'top_inefficient_queries': inefficient_queries,
            'recommendations': self._generate_recommendations(summary, cache_analysis, system_health)
        }
        
        # Persistir reporte
        self._save_report(report, report_type)
        
        return report
    
    def _calculate_efficiency(self, query_info: Dict) -> float:
        """
        Calcula eficiencia de una consulta.
        
        Eficiencia = densidad de información / tokens usados
        """
        tokens_used = query_info.get('tokens_used', 0)
        
        if tokens_used <= 0:
            return 0.0
        
        # Densidad de información (proxy simple)
        # Podría ser más sofisticado basado en campos presentes, precisión, etc.
        info_density = self._estimate_information_density(query_info)
        
        return info_density / tokens_used
    
    def _estimate_information_density(self, query_info: Dict) -> float:
        """Estima densidad de información en una respuesta."""
        # Factores que contribuyen a información valiosa
        factors = []
        
        # Confianza
        confidence = query_info.get('confidence', 0)
        if confidence > 0:
            factors.append(confidence / 100)  # Normalizar a 0-1
        
        # Número de campos informativos
        informative_fields = ['pick', 'confidence', 'stake', 'reason', 'analysis']
        present_fields = sum(1 for field in informative_fields if field in query_info and query_info[field])
        factors.append(present_fields / len(informative_fields))
        
        # Precisión histórica (si está disponible)
        if 'historical_accuracy' in query_info:
            factors.append(query_info['historical_accuracy'])
        
        # Promedio de factores (ponderación simple)
        if factors:
            return sum(factors) / len(factors)
        else:
            return 0.5  # Valor por defecto
    
    def _update_aggregated_stats(self, query_info: Dict):
        """Actualiza estadísticas agregadas."""
        timestamp = query_info.get('timestamp', time.time())
        dt = datetime.fromtimestamp(timestamp)
        
        # Claves de agregación
        date_key = dt.strftime("%Y-%m-%d")
        hour_key = dt.strftime("%Y-%m-%d %H:00")
        query_type = query_info.get('query_type', 'unknown')
        
        # Actualizar daily
        if date_key not in self.aggregated_stats['daily']:
            self.aggregated_stats['daily'][date_key] = {
                'total_queries': 0,
                'total_tokens': 0,
                'total_efficiency': 0
            }
        
        daily = self.aggregated_stats['daily'][date_key]
        daily['total_queries'] += 1
        daily['total_tokens'] += query_info.get('tokens_used', 0)
        daily['total_efficiency'] += query_info.get('efficiency', 0)
        
        # Actualizar hourly
        if hour_key not in self.aggregated_stats['hourly']:
            self.aggregated_stats['hourly'][hour_key] = {
                'total_queries': 0,
                'total_tokens': 0
            }
        
        hourly = self.aggregated_stats['hourly'][hour_key]
        hourly['total_queries'] += 1
        hourly['total_tokens'] += query_info.get('tokens_used', 0)
        
        # Actualizar by_query_type
        if query_type not in self.aggregated_stats['by_query_type']:
            self.aggregated_stats['by_query_type'][query_type] = {
                'total_queries': 0,
                'total_tokens': 0,
                'cache_hits': 0
            }
        
        by_type = self.aggregated_stats['by_query_type'][query_type]
        by_type['total_queries'] += 1
        by_type['total_tokens'] += query_info.get('tokens_used', 0)
        
        if query_info.get('from_cache', False):
            by_type['cache_hits'] += 1
    
    def _check_alerts(self, query_info: Dict):
        """Verifica y dispara alertas basadas en métricas."""
        # Alertas de eficiencia baja
        efficiency = query_info.get('efficiency', 0)
        if efficiency > 0 and efficiency < METRICS_CONFIG['alert_threshold']:
            logger.warning(
                f"ALERTA: Baja eficiencia en consulta "
                f"(type: {query_info.get('query_type', 'unknown')}, "
                f"efficiency: {efficiency:.3f})"
            )
        
        # Alertas de tokens excesivos
        tokens_used = query_info.get('tokens_used', 0)
        if tokens_used > METRICS_CONFIG['max_tokens_per_query']:
            logger.warning(
                f"ALERTA: Alto uso de tokens en consulta "
                f"(type: {query_info.get('query_type', 'unknown')}, "
                f"tokens: {tokens_used})"
            )
    
    def _get_cutoff_time(self, time_range: str) -> float:
        """Obtiene timestamp de corte para un rango de tiempo."""
        now = time.time()
        
        if time_range == '1h':
            return now - 3600
        elif time_range == '24h':
            return now - 86400
        elif time_range == '7d':
            return now - 7 * 86400
        elif time_range == '30d':
            return now - 30 * 86400
        else:
            return now - 86400  # Default 24h
    
    def _get_interval_seconds(self, time_range: str) -> int:
        """Obtiene intervalo en segundos para agrupación de tendencias."""
        if time_range == '24h':
            return 3600  # 1 hora
        elif time_range == '7d':
            return 6 * 3600  # 6 horas
        elif time_range == '30d':
            return 24 * 3600  # 1 día
        else:
            return 3600  # Default 1 hora
    
    def _load_historical_metrics(self):
        """Carga métricas históricas desde almacenamiento persistente."""
        metrics_file = os.path.join(METRICS_DIR, 'metrics.json')
        
        if not os.path.exists(metrics_file):
            return
        
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                historical_data = json.load(f)
            
            # Cargar métricas (limitar a retención configurada)
            retention_days = METRICS_CONFIG.get('retention_days', 30)
            cutoff_time = time.time() - (retention_days * 86400)
            
            loaded_count = 0
            for metric in historical_data:
                if metric.get('timestamp', 0) >= cutoff_time:
                    self.metrics_store.append(metric)
                    loaded_count += 1
            
            logger.info(f"Métricas históricas cargadas: {loaded_count} entradas")
            
        except Exception as e:
            logger.error(f"Error cargando métricas históricas: {e}")
    
    def _persist_metrics(self):
        """Persiste métricas en almacenamiento permanente."""
        try:
            os.makedirs(METRICS_DIR, exist_ok=True)
            
            # Guardar todas las métricas
            metrics_file = os.path.join(METRICS_DIR, 'metrics.json')
            
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(self.metrics_store[-10000:], f, ensure_ascii=False, indent=2)  # Limitar a 10k entradas
            
            # Guardar estadísticas agregadas
            stats_file = os.path.join(METRICS_DIR, 'aggregated_stats.json')
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.aggregated_stats, f, ensure_ascii=False, indent=2)
            
            logger.debug("Métricas persistidas en disco")
            
        except Exception as e:
            logger.error(f"Error persistiendo métricas: {e}")
    
    def _save_report(self, report: Dict, report_type: str):
        """Guarda un reporte en disco."""
        try:
            reports_dir = os.path.join(METRICS_DIR, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # Nombre de archivo basado en tipo y fecha
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{report_type}_report_{date_str}.json"
            filepath = os.path.join(reports_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Reporte {report_type} guardado: {filename}")
            
        except Exception as e:
            logger.error(f"Error guardando reporte: {e}")
    
    def _generate_recommendations(self, summary: Dict, cache_analysis: Dict, 
                                 system_health: Dict) -> List[str]:
        """Genera recomendaciones basadas en métricas."""
        recommendations = []
        
        # Recomendaciones basadas en eficiencia
        avg_efficiency = summary.get('avg_efficiency', 0)
        if avg_efficiency < METRICS_CONFIG['target_efficiency']:
            recommendations.append(
                f"La eficiencia promedio ({avg_efficiency:.3f}) está por debajo del objetivo "
                f"({METRICS_CONFIG['target_efficiency']}). Considera optimizar plantillas."
            )
        
        # Recomendaciones basadas en cache
        cache_hit_rate = summary.get('cache_hit_rate', 0)
        target_hit_rate = METRICS_CONFIG['min_cache_hit_rate'] * 100
        
        if cache_hit_rate < target_hit_rate:
            recommendations.append(
                f"El cache hit rate ({cache_hit_rate:.1f}%) está por debajo del objetivo "
                f"({target_hit_rate}%). Considera aumentar TTLs o precalentar caché."
            )
        
        # Recomendaciones basadas en tipos de consulta
        by_type = summary.get('by_query_type', {})
        
        for qtype, stats in by_type.items():
            if stats.get('percentage', 0) > 50:  # Si un tipo domina >50%
                recommendations.append(
                    f"Las consultas de tipo '{qtype}' representan el {stats['percentage']:.1f}% "
                    f"del total. Considera optimizaciones específicas para este tipo."
                )
        
        # Recomendaciones basadas en tokens
        avg_tokens = summary.get('avg_tokens_per_query', 0)
        max_tokens = METRICS_CONFIG['max_tokens_per_query']
        
        if avg_tokens > max_tokens * 0.8:  # 80% del límite
            recommendations.append(
                f"El uso promedio de tokens ({avg_tokens:.0f}) se acerca al límite "
                f"({max_tokens}). Considera compresión más agresiva."
            )
        
        return recommendations
    
    def cleanup_old_metrics(self):
        """Limpia métricas antiguas basadas en retención configurada."""
        retention_days = METRICS_CONFIG.get('retention_days', 30)
        cutoff_time = time.time() - (retention_days * 86400)
        
        before_count = len(self.metrics_store)
        self.metrics_store = [
            m for m in self.metrics_store
            if m.get('timestamp', 0) >= cutoff_time
        ]
        after_count = len(self.metrics_store)
        
        removed_count = before_count - after_count
        if removed_count > 0:
            logger.info(f"Métricas antiguas limpiadas: {removed_count} entradas removidas")
            
            # Actualizar estadísticas agregadas
            self._recalculate_aggregated_stats()
        
        return removed_count
    
    def _recalculate_aggregated_stats(self):
        """Recalcula estadísticas agregadas desde métricas almacenadas."""
        # Reiniciar estadísticas
        self.aggregated_stats = {
            'daily': {},
            'hourly': {},
            'by_query_type': {}
        }
        
        # Recalcular desde métricas actuales
        for metric in self.metrics_store:
            self._update_aggregated_stats(metric)