"""
Rate limiter — shared slowapi Limiter instance, keyed by client IP.

Import `limiter` in main.py to register the middleware and exception handler.
Import `limiter` in route modules to apply per-endpoint decorators.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
