"""
Cache Manager

Sistema de caché en memoria con TTL y invalidación activa.
Implementa estrategias de caching basadas en evidencia de timing.
"""

import time
import json
import hashlib
from typing import Any, Optional, Callable, Dict
from functools import wraps
import logging

logger = logging.getLogger("cache")
logger.setLevel(logging.INFO)


class CacheEntry:
    """Entrada de caché con timestamp y TTL"""

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl  # Segundos

    def is_expired(self) -> bool:
        """Verificar si entrada ha expirado"""
        return time.time() - self.created_at > self.ttl

    def age_seconds(self) -> float:
        """Edad de la entrada en segundos"""
        return time.time() - self.created_at


class CacheManager:
    """
    Gestor de caché en memoria con TTL.

    Features:
    - TTL configurable por clave
    - Invalidación manual (purge)
    - Invalidación por patrón (wildcard)
    - Estadísticas (hits/misses)
    """

    def __init__(self):
        self._store: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Obtener valor de caché.

        Returns:
            - Valor si existe y no ha expirado
            - None si no existe o expiró
        """
        entry = self._store.get(key)

        if entry is None:
            self._misses += 1
            logger.debug(f"CACHE MISS: {key}")
            return None

        if entry.is_expired():
            del self._store[key]
            self._misses += 1
            logger.debug(f"CACHE EXPIRED: {key} (age: {entry.age_seconds():.1f}s)")
            return None

        self._hits += 1
        logger.debug(f"CACHE HIT: {key} (age: {entry.age_seconds():.1f}s)")
        return entry.value

    def set(self, key: str, value: Any, ttl: int = 300):
        """
        Guardar valor en caché con TTL.

        Args:
            key: Clave única
            value: Valor a cachear (debe ser JSON-serializable)
            ttl: Time-to-live en segundos (default: 5 min)
        """
        self._store[key] = CacheEntry(value, ttl)
        logger.info(f"CACHE SET: {key} (TTL: {ttl}s)")

    def invalidate(self, key: str) -> bool:
        """
        Invalidar entrada específica.

        Returns:
            True si existía y se eliminó
        """
        if key in self._store:
            del self._store[key]
            logger.info(f"CACHE INVALIDATE: {key}")
            return True
        return False

    def invalidate_pattern(self, pattern: str):
        """
        Invalidar todas las claves que coincidan con patrón.

        Ejemplo:
            invalidate_pattern("incidents:*")  # Invalida todas las incidencias
            invalidate_pattern("*:summary")    # Invalida todos los summaries
        """
        keys_to_delete = [
            k for k in self._store.keys()
            if self._match_pattern(k, pattern)
        ]

        for key in keys_to_delete:
            del self._store[key]

        if keys_to_delete:
            logger.info(f"CACHE INVALIDATE PATTERN: {pattern} ({len(keys_to_delete)} keys)")

    def clear(self):
        """Limpiar toda la caché"""
        count = len(self._store)
        self._store.clear()
        logger.warning(f"CACHE CLEAR: {count} entries removed")

    def stats(self) -> dict:
        """Estadísticas de caché"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "entries": len(self._store),
            "total_requests": total
        }

    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Match simple de wildcards (* al principio o final)"""
        if "*" not in pattern:
            return key == pattern

        if pattern.startswith("*") and pattern.endswith("*"):
            # *foo*
            return pattern[1:-1] in key
        elif pattern.startswith("*"):
            # *foo
            return key.endswith(pattern[1:])
        elif pattern.endswith("*"):
            # foo*
            return key.startswith(pattern[:-1])

        return key == pattern


# Instancia global de caché
cache = CacheManager()


def cache_key(*args, **kwargs) -> str:
    """
    Generar clave de caché determinística a partir de argumentos.

    Ejemplo:
        cache_key("incidents", status="open", branch="miami")
        # → "incidents:status=open:branch=miami"
    """
    parts = [str(arg) for arg in args]

    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        parts.extend([f"{k}={v}" for k, v in sorted_kwargs])

    return ":".join(parts)


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorador para cachear resultados de funciones async.

    Args:
        ttl: Time-to-live en segundos
        key_prefix: Prefijo para la clave de caché

    Ejemplo:
        @cached(ttl=60, key_prefix="incidents")
        async def list_incidents(status=None, branch=None):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generar clave de caché
            key = cache_key(key_prefix or func.__name__, *args, **kwargs)

            # Intentar obtener de caché
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value

            # Ejecutar función
            result = await func(*args, **kwargs)

            # Guardar en caché
            cache.set(key, result, ttl)

            return result

        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str):
    """Helper para invalidar desde rutas de escritura"""
    cache.invalidate_pattern(pattern)
