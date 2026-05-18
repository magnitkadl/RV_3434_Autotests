# core/ui_spec.py
from typing import Optional
from .models import ParameterUiMapping
from .db import DBRepository


def get_ui_mapping(
    db: DBRepository, param_uuid: str, firmware_version_id: int
) -> Optional[ParameterUiMapping]:
    return db.ui.get_mapping(param_uuid, firmware_version_id)