# core/api_spec.py
from .models import ApiMethod, ApiMethodParam
from .db import DBRepository


# Простой кеш на уровне модуля (можно заменить на TTL-кеш позже)
_api_method_cache: Dict[Tuple[str, int], ApiMethod] = {}
_api_method_params_cache: Dict[Tuple[str, int], list] = {}


def get_api_method(
    db: DBRepository, method_name: str, firmware_version_id: int
) -> Optional[ApiMethod]:
    key = (method_name, firmware_version_id)
    if key not in _api_method_cache:
        method = db.api.get_method(method_name, firmware_version_id)
        if method:
            _api_method_cache[key] = method
    return _api_method_cache.get(key)


def get_cached_api_method_params(
    db: DBRepository, method_name: str, firmware_version_id: int
) -> list[ApiMethodParam]:
    key = (method_name, firmware_version_id)
    if key not in _api_method_params_cache:
        _api_method_params_cache[key] = db.api.get_method_params(method_name, firmware_version_id)
    return _api_method_params_cache[key]