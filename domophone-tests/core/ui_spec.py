# core/ui_spec.py
import sqlite3
from typing import Optional
from .models import ParameterUiMapping
from .db import get_parameter  # для проверки существования параметра


def get_ui_mapping(
    conn: sqlite3.Connection, param_uuid: str, firmware_version_id: int
) -> Optional[ParameterUiMapping]:
    cursor = conn.execute("""
        SELECT * FROM parameter_ui_mapping
        WHERE param_uuid = ? AND firmware_version_id = ?
    """, (param_uuid, firmware_version_id))
    row = cursor.fetchone()
    if row:
        return ParameterUiMapping(**{k: row[k] for k in row.keys()})
    return None