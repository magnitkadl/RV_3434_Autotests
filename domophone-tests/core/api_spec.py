# core/api_spec.py
import sqlite3
from typing import Dict, Tuple, Optional
from .models import ApiMethod, ApiMethodParam
from .db import get_method_info, get_api_method_params


# Простой кеш на уровне модуля (можно заменить на TTL-кеш позже)
_api_method_cache: Dict[Tuple[str, int], ApiMethod] = {}
_api_method_params_cache: Dict[Tuple[str, int], list] = {}


def get_api_method(
    conn: sqlite3.Connection, method_name: str, firmware_version_id: int
) -> Optional[ApiMethod]:
    key = (method_name, firmware_version_id)
    if key not in _api_method_cache:
        method = get_method_info(conn, method_name, firmware_version_id)
        if method:
            _api_method_cache[key] = method
    return _api_method_cache.get(key)


def get_cached_api_method_params(
    conn: sqlite3.Connection, method_name: str, firmware_version_id: int
) -> list[ApiMethodParam]:
    key = (method_name, firmware_version_id)
    if key not in _api_method_params_cache:
        _api_method_params_cache[key] = get_api_method_params(conn, method_name, firmware_version_id)
    return _api_method_params_cache[key]