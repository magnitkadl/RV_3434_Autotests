# core/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List
from .models import (
    FirmwareVersion, ConfigParameter, ApiMethod,
    ApiMethodParam, UiElementType, ParameterUiMapping
)


@contextmanager
def get_db_connection(db_path: str):
    """Контекстный менеджер для безопасного подключения к БД."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _row_to_model(row, model_class):
    """Преобразует sqlite3.Row в Pydantic-модель."""
    return model_class(**{k: row[k] for k in row.keys()})


# --- Firmware ---
def get_firmware_by_id(conn: sqlite3.Connection, fw_id: int) -> Optional[FirmwareVersion]:
    cursor = conn.execute("SELECT * FROM firmware_versions WHERE id = ?", (fw_id,))
    row = cursor.fetchone()
    return _row_to_model(row, FirmwareVersion) if row else None


def get_firmware_by_version(conn: sqlite3.Connection, version: str) -> Optional[FirmwareVersion]:
    cursor = conn.execute("SELECT * FROM firmware_versions WHERE version = ?", (version,))
    row = cursor.fetchone()
    return _row_to_model(row, FirmwareVersion) if row else None


def get_all_firmware_versions(conn: sqlite3.Connection) -> List[FirmwareVersion]:
    cursor = conn.execute("SELECT * FROM firmware_versions ORDER BY release_date")
    return [_row_to_model(row, FirmwareVersion) for row in cursor.fetchall()]


# --- Parameters ---
def get_parameter(
    conn: sqlite3.Connection, param_uuid: str, firmware_version_id: int
) -> Optional[ConfigParameter]:
    cursor = conn.execute("""
        SELECT * FROM config_parameters
        WHERE param_uuid = ? AND firmware_version_id = ?
    """, (param_uuid, firmware_version_id))
    row = cursor.fetchone()
    return _row_to_model(row, ConfigParameter) if row else None


def get_parameters_for_firmware(
    conn: sqlite3.Connection, firmware_version_id: int
) -> List[ConfigParameter]:
    cursor = conn.execute("""
        SELECT * FROM config_parameters
        WHERE firmware_version_id = ?
    """, (firmware_version_id,))
    return [_row_to_model(row, ConfigParameter) for row in cursor.fetchall()]


# --- API Methods ---
def get_api_method_by_name_and_fw(
    conn: sqlite3.Connection, method_name: str, firmware_version_id: int
) -> Optional[ApiMethod]:
    cursor = conn.execute("""
        SELECT * FROM api_methods
        WHERE method_name = ? AND firmware_version_id = ?
    """, (method_name, firmware_version_id))
    row = cursor.fetchone()
    return _row_to_model(row, ApiMethod) if row else None


def get_api_method_params(
    conn: sqlite3.Connection, method_name: str, firmware_version_id: int
) -> List[ApiMethodParam]:
    """Выдает список объектов класса ApiMethodParam"""
    cursor = conn.execute("""
        SELECT 
            amp.json_path,
            amp.is_required,
            amp.in_request,
            amp.condition_expr,
            amp.example_value,
            cp.param_uuid,
            cp.location,
            cp.name,
            cp.migration_down,
            cp.migration_up,
            cp.description,
            cp.data_type_id,
            cp.default_value,
            cp.format_hint,
            cp.min_value,
            cp.max_value,
            cp.allowed_values,
            cp.unit
        FROM api_method_params amp
        JOIN api_methods am ON amp.method_id = am.id
        JOIN config_parameters cp ON amp.param_uuid = cp.param_uuid
        WHERE am.method_name = ? AND amp.firmware_version_id = ?
    """, (method_name, firmware_version_id))
    return [_row_to_model(row, ApiMethodParam) for row in cursor.fetchall()]

def get_positive_status(
    conn: sqlite3.Connection, method_name: str, firmware_version_id: int
) -> List[ApiMethodParam]:
        # получаем ожидаемый статус для позитивного теста
        cursor = conn.execute("""
            SELECT am.positive_status FROM api_methods am
            WHERE method_name = ? AND firmware_version_id = ?
        """, (method_name, firmware_version_id))
        row = cursor.fetchone()
        return row['positive_status'] if row else None
