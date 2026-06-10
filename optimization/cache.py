"""
Cache Coordinator - Sistema de caché inteligente para optimización de tokens
"""

import time
import json
import os
import hashlib
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import logging

from .config import CACHE_CONFIG, CACHE_DIR

logger = logging.getLogger(__name__)


class CacheCoordinator:
    """
    Coordina el sistema de caché inteligente con TTLs específicos por tipo de dato.
    
    Características:
    - TTLs configurables por tipo de consulta
    - Estrategias de invalidación (time-based, event-based, accuracy-based)
    - Limpieza automática (LRU)
    - Persistencia opcional en disco
    """
    
    def __init__(self, persistence: bool = True):
        """
        Inicializa el coordinador de caché.
        
        Args:
            persistence: Si True, persiste caché en disco
        """
        self.persistence = persistence
        self.memory_cache = {}  # key -> (data, timestamp, metadata)
        self.access_times = {}  # key -> último acceso (para LRU)
        
        # Cargar caché persistente si existe
        if persistence:
            self._load_persistent_cache()
        
        logger.info(f"CacheCoordinator inicializado (persistence: {persistence})")
    
    def get(self, cached_key: str) -> Optional[Dict]:
        """
        Obtiene datos del caché si existen y no han expirado.
        
        Args:
            cached_key: Clave de caché
            
        Returns:
            Datos cacheados o None si no existen o expiraron
        """
        if cached_key not in self.memory_cache:
            return None
        
        data, timestamp, metadata = self.memory_cache[cached_key]
        
        # Verificar TTL basado en tipo de consulta
        query_type = metadata.get('query_type', 'general')
        ttl = self._get_ttl_for_type(query_type)
        
        # Verificar si expiró
        if time.time() - timestamp > ttl:
            logger.debug(f"Cache EXPIRED para {cached_key} (TTL: {ttl}s)")
            self._remove(cached_key)
            return None
        
        # Actualizar tiempo de último acceso (para LRU)
        self.access_times[cached_key] = time.time()
        
        logger.debug(f"Cache HIT para {cached_key} (age: {time.time() - timestamp:.1f}s)")
        return {
            'data': data,
            'timestamp': timestamp,
            'metadata': metadata
        }
    
    def set(self, key: str, data: Dict, query_type: str = 'general'):
        """
        Almacena datos en caché.
        
        Args:
            key: Clave de caché
            data: Datos a cachear
            query_type: Tipo de consulta (para determinar TTL)
        """
        metadata = {
            'query_type': query_type,
            'created_at': datetime.now().isoformat(),
            'size_bytes': len(str(data).encode('utf-8')),
            'hash': self._generate_data_hash(data)
        }
        
        self.memory_cache[key] = (data, time.time(), metadata)
        self.access_times[key] = time.time()
        
        # Limpieza automática si excedemos límites
        self._cleanup_if_needed(query_type)
        
        # Persistir si está habilitado
        if self.persistence:
            self._save_to_persistent_cache(key, data, metadata)
        
        logger.debug(f"Cache SET para {key} (type: {query_type})")
    
    def clear(self, query_type: Optional[str] = None):
        """
        Limpia el caché, opcionalmente por tipo de consulta.
        
        Args:
            query_type: Si se especifica, solo limpia entradas de este tipo
        """
        if query_type:
            keys_to_remove = [
                key for key, (_, _, metadata) in self.memory_cache.items()
                if metadata.get('query_type') == query_type
            ]
            for key in keys_to_remove:
                self._remove(key)
            logger.info(f"Caché limpiado para tipo: {query_type} ({len(keys_to_remove)} entradas)")
        else:
            self.memory_cache.clear()
            self.access_times.clear()
            logger.info("Caché completamente limpiado")
    
    def get_status(self) -> Dict:
        """Retorna estado del caché."""
        total_entries = len(self.memory_cache)
        
        # Agrupar por tipo de consulta
        by_type = {}
        for key, (_, _, metadata) in self.memory_cache.items():
            qtype = metadata.get('query_type', 'unknown')
            by_type[qtype] = by_type.get(qtype, 0) + 1
        
        # Calcular tamaño total
        total_size = sum(
            metadata.get('size_bytes', 0)
            for _, _, metadata in self.memory_cache.values()
        )
        
        # Entradas más antiguas y más nuevas
        if self.memory_cache:
            timestamps = [ts for _, ts, _ in self.memory_cache.values()]
            oldest = min(timestamps)
            newest = max(timestamps)
        else:
            oldest = newest = 0
        
        return {
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'entries_by_type': by_type,
            'oldest_entry_age': time.time() - oldest if oldest else 0,
            'newest_entry_age': time.time() - newest if newest else 0,
            'persistence_enabled': self.persistence
        }
    
    def health_check(self) -> Dict:
        """Realiza check de salud del caché."""
        status = self.get_status()
        
        # Verificar límites
        max_entries_per_type = 100  # Límite razonable
        issues = []
        
        for qtype, count in status['entries_by_type'].items():
            if count > max_entries_per_type:
                issues.append(f"Demasiadas entradas para {qtype}: {count}")
        
        # Verificar tamaño total
        max_size_mb = 50  # 50MB máximo
        if status['total_size_bytes'] > max_size_mb * 1024 * 1024:
            issues.append(f"Caché muy grande: {status['total_size_bytes'] / (1024*1024):.1f}MB")
        
        return {
            'status': 'healthy' if not issues else 'degraded',
            'message': '; '.join(issues) if issues else 'OK',
            'stats': status
        }
    
    def _get_ttl_for_type(self, query_type: str) -> int:
        """Obtiene TTL para un tipo de consulta."""
        config = CACHE_CONFIG.get(query_type, CACHE_CONFIG.get('general', {}))
        return config.get('ttl', 300)  # Default 5 minutos
    
    def _generate_data_hash(self, data: Dict) -> str:
        """Genera hash para datos (para detección de cambios)."""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()[:16]
    
    def _cleanup_if_needed(self, query_type: str):
        """Limpia caché si excede límites para un tipo específico."""
        config = CACHE_CONFIG.get(query_type, {})
        max_entries = config.get('max_entries', 50)
        
        # Contar entradas de este tipo
        type_entries = [
            key for key, (_, _, metadata) in self.memory_cache.items()
            if metadata.get('query_type') == query_type
        ]
        
        if len(type_entries) > max_entries:
            # Ordenar por último acceso (LRU)
            type_entries_sorted = sorted(
                type_entries,
                key=lambda k: self.access_times.get(k, 0)
            )
            
            # Eliminar las más antiguas
            to_remove = type_entries_sorted[:len(type_entries) - max_entries]
            for key in to_remove:
                self._remove(key)
            
            logger.debug(f"LRU cleanup para {query_type}: removidas {len(to_remove)} entradas")
    
    def _remove(self, key: str):
        """Remueve entrada del caché."""
        if key in self.memory_cache:
            del self.memory_cache[key]
        if key in self.access_times:
            del self.access_times[key]
        
        # También remover de persistente si existe
        if self.persistence:
            self._remove_from_persistent_cache(key)
    
    def _load_persistent_cache(self):
        """Carga caché persistente desde disco."""
        cache_file = os.path.join(CACHE_DIR, 'cache.json')
        
        if not os.path.exists(cache_file):
            logger.debug("No existe archivo de caché persistente")
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                persistent_data = json.load(f)
            
            # Cargar entradas válidas (no expiradas)
            loaded_count = 0
            for key, entry in persistent_data.items():
                timestamp = entry.get('timestamp', 0)
                query_type = entry.get('metadata', {}).get('query_type', 'general')
                ttl = self._get_ttl_for_type(query_type)
                
                # Verificar si expiró
                if time.time() - timestamp <= ttl:
                    self.memory_cache[key] = (
                        entry['data'],
                        timestamp,
                        entry['metadata']
                    )
                    self.access_times[key] = timestamp
                    loaded_count += 1
                else:
                    logger.debug(f"Entrada persistente expirada: {key}")
            
            logger.info(f"Caché persistente cargado: {loaded_count} entradas válidas")
            
        except Exception as e:
            logger.error(f"Error cargando caché persistente: {e}")
    
    def _save_to_persistent_cache(self, key: str, data: Dict, metadata: Dict):
        """Guarda entrada en caché persistente."""
        cache_file = os.path.join(CACHE_DIR, 'cache.json')
        
        try:
            # Cargar caché existente
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
            else:
                all_data = {}
            
            # Actualizar entrada
            all_data[key] = {
                'data': data,
                'timestamp': time.time(),
                'metadata': metadata
            }
            
            # Limitar tamaño del archivo (mantener solo las 1000 entradas más recientes)
            if len(all_data) > 1000:
                # Ordenar por timestamp y mantener las más recientes
                sorted_keys = sorted(
                    all_data.keys(),
                    key=lambda k: all_data[k].get('timestamp', 0),
                    reverse=True
                )
                all_data = {k: all_data[k] for k in sorted_keys[:1000]}
            
            # Guardar
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error guardando en caché persistente: {e}")
    
    def _remove_from_persistent_cache(self, key: str):
        """Remueve entrada del caché persistente."""
        cache_file = os.path.join(CACHE_DIR, 'cache.json')
        
        if not os.path.exists(cache_file):
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            if key in all_data:
                del all_data[key]
                
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.error(f"Error removiendo del caché persistente: {e}")
    
    def invalidate_by_pattern(self, pattern: str):
        """
        Invalida entradas de caché que coincidan con un patrón.
        
        Args:
            pattern: Patrón para buscar en keys (substring)
        """
        keys_to_remove = [
            key for key in self.memory_cache.keys()
            if pattern in key
        ]
        
        for key in keys_to_remove:
            self._remove(key)
        
        logger.info(f"Invalidadas {len(keys_to_remove)} entradas con patrón: {pattern}")
        return len(keys_to_remove)
    
    def invalidate_by_trigger(self, trigger_type: str, context: Dict = None):
        """
        Invalida entradas basado en triggers definidos en configuración.
        
        Args:
            trigger_type: Tipo de trigger (ej: 'lineup_change', 'odds_change')
            context: Contexto adicional para el trigger
        """
        invalidated_count = 0
        
        for key, (_, _, metadata) in list(self.memory_cache.items()):
            query_type = metadata.get('query_type', 'general')
            config = CACHE_CONFIG.get(query_type, {})
            
            # Verificar si este tipo tiene este trigger
            triggers = config.get('invalidation_triggers', [])
            if trigger_type in triggers:
                # Verificar condiciones específicas del contexto
                if self._should_invalidate_for_trigger(key, metadata, trigger_type, context):
                    self._remove(key)
                    invalidated_count += 1
        
        logger.info(f"Invalidadas {invalidated_count} entradas por trigger: {trigger_type}")
        return invalidated_count
    
    def _should_invalidate_for_trigger(self, key: str, metadata: Dict, 
                                       trigger_type: str, context: Dict) -> bool:
        """Determina si una entrada debe invalidarse para un trigger específico."""
        # Implementación básica - siempre invalidar si el trigger aplica
        # En una implementación real, se verificarían condiciones específicas
        return True
    
    def get_entries_by_age(self, max_age_seconds: int) -> List[Dict]:
        """
        Obtiene entradas más antiguas que un límite de edad.
        
        Args:
            max_age_seconds: Edad máxima en segundos
            
        Returns:
            Lista de entradas antiguas
        """
        old_entries = []
        
        for key, (data, timestamp, metadata) in self.memory_cache.items():
            age = time.time() - timestamp
            if age > max_age_seconds:
                old_entries.append({
                    'key': key,
                    'age_seconds': age,
                    'query_type': metadata.get('query_type'),
                    'data_size': metadata.get('size_bytes', 0)
                })
        
        return sorted(old_entries, key=lambda x: x['age_seconds'], reverse=True)
    
    def optimize_memory(self):
        """Optimiza uso de memoria del caché."""
        # 1. Remover entradas expiradas
        expired_count = 0
        for key, (_, timestamp, metadata) in list(self.memory_cache.items()):
            query_type = metadata.get('query_type', 'general')
            ttl = self._get_ttl_for_type(query_type)
            
            if time.time() - timestamp > ttl:
                self._remove(key)
                expired_count += 1
        
        # 2. Aplicar LRU por tipo
        for query_type in set(m.get('query_type', 'general') 
                              for _, _, m in self.memory_cache.values()):
            self._cleanup_if_needed(query_type)
        
        # 3. Limpiar tiempos de acceso antiguos
        week_ago = time.time() - (7 * 24 * 3600)
        old_access_keys = [
            k for k, t in self.access_times.items()
            if t < week_ago and k not in self.memory_cache
        ]
        for key in old_access_keys:
            del self.access_times[key]
        
        logger.info(f"Memoria optimizada: {expired_count} expiradas removidas")
        return expired_count