# core/models.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FirmwareVersion(BaseModel):
    id: int
    version: str
    release_date: int  # секунды с 2020-01-01
    description: Optional[str] = None
    supports_http: bool = False
    is_release: bool = False


class DataType(BaseModel):
    id: int
    name: str  # 'int', 'float', 'string', 'bool', 'enum'
    description: Optional[str] = None


class ConfigParameter(BaseModel):
    param_uuid: str
    firmware_version_id: int
    location: Optional[str] = None
    name: Optional[str] = None
    migration_down: Optional[str] = None  # пока не используем
    migration_up: Optional[str] = None    # пока не используем
    description: Optional[str] = None
    data_type_id: int
    default_value: Optional[str] = None
    format_hint: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[str] = None  # JSON-строка, например: '["on","off"]'
    unit: Optional[str] = None
    created_at: str
    updated_at: str


class ApiMethod(BaseModel):
    id: int
    method_name: str
    http_method: str
    firmware_version_id: int


class ApiMethodParam(BaseModel):
    id: int
    method_id: int
    param_uuid: str
    firmware_version_id: int
    json_path: str
    is_required: bool = True
    in_request: bool = True
    condition_expr: Optional[str] = None
    example_value: Optional[str] = None


class UiElementType(BaseModel):
    id: int
    name: str  # 'input', 'checkbox', 'slider', etc.
    description: Optional[str] = None
    handler_method: str  # 'fill', 'check', 'select_option', etc.


class ParameterUiMapping(BaseModel):
    param_uuid: str
    firmware_version_id: int
    selector: str
    element_type_id: int
    attributes: Optional[str] = None  # JSON, например: '{"min":0,"max":100}'
    page_section: Optional[str] = None
    is_visible: bool = True
    depends_on_param: Optional[str] = None
    depends_on_value: Optional[str] = None