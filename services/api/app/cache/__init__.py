"""
Cache Module

Sistema de caching en memoria con TTL e invalidación activa.
"""

from .manager import cache, cached, invalidate_cache_pattern, cache_key

__all__ = ["cache", "cached", "invalidate_cache_pattern", "cache_key"]
