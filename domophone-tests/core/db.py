# core/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List
from loguru import logger
from .models import (
    FirmwareVersion, ConfigParameter, ApiMethod,
    ApiMethodParam, UiElementType, ParameterUiMapping
)


@contextmanager
def get_db_connection(db_path: str):
    """Контекстный менеджер для безопасного подключения к БД."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON") 
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
def get_method_info(
    conn: sqlite3.Connection, method_name: str, firmware_version_id: int
) -> Optional[ApiMethod]:
    name = method_name.strip().lower()
    logger.debug("Querying method_info for name='{}', fw_id={}", name, firmware_version_id)
    cursor = conn.execute("""
        SELECT am.id, am.method_name, am.http_method, am.firmware_version_id, 
                                        am.method_url, am.positive_status, am.control_method_name  FROM api_methods am
        WHERE LOWER(am.method_name) = ? AND am.firmware_version_id = ?
    """, (name, firmware_version_id))
    row = cursor.fetchone()
    if not row:
        logger.warning("Method '{}' not found for firmware ID {}", name, firmware_version_id)
        return None
    return _row_to_model(row, ApiMethod)


def get_api_method_params(
    conn: sqlite3.Connection, method_name: str, firmware_version_id: int
) -> List[ApiMethodParam]:
    """Выдает список объектов класса ApiMethodParam"""
    name = method_name.strip().lower()
    logger.debug("Querying params for method='{}', fw_id={}", name, firmware_version_id)
    cursor = conn.execute("""
        SELECT 
            amp.json_path,
            amp.is_required,
            amp.in_request,
            amp.condition_expr,
            amp.example_value,
            amp.gen_rule,
            amp.related_params_uuid,
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
            cp.unit,
            cra.rule_payload,
            cra.rule_type 
        FROM api_method_params amp
        JOIN api_methods am ON amp.method_id = am.id
        LEFT JOIN config_parameters cp ON amp.related_params_uuid = cp.param_uuid
        lEFT JOIN conversion_rules_api cra ON cra.json_path = amp.json_path AND cra.method_id = amp.method_id 
        WHERE LOWER(am.method_name) = ? AND am.firmware_version_id = ?
        ORDER BY amp.priority
    """, (name, firmware_version_id))
    params = [_row_to_model(row, ApiMethodParam) for row in cursor.fetchall()]
    if not params:
        logger.warning("No parameters found for method '{}' and firmware ID {}", name, firmware_version_id)
    else:
        logger.debug("Found {} parameters for method '{}'", len(params), name)
    return params

def get_positive_status(
    conn: sqlite3.Connection, method_name: str, firmware_version_id: int
) -> Optional[int]:
    """Временно, потом перейти на get_method_properties"""
    # получаем ожидаемый статус для позитивного теста
    cursor = conn.execute("""
        SELECT am.positive_status FROM api_methods am
        WHERE method_name = ? AND firmware_version_id = ?
    """, (method_name, firmware_version_id))
    row = cursor.fetchone()
    return row['positive_status'] if row else None
