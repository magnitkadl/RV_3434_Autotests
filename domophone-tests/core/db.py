# core/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List
from loguru import logger
from .models import (
    FirmwareVersion, ConfigParameter, ApiMethod,
    ApiMethodParam, UiElementType, ParameterUiMapping
)


class BaseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _row_to_model(self, row, model_class):
        """Преобразует sqlite3.Row в Pydantic-модель."""
        return model_class(**{k: row[k] for k in row.keys()})


class FirmwareRepository(BaseRepository):
    def get_by_id(self, fw_id: int) -> Optional[FirmwareVersion]:
        cursor = self.conn.execute("SELECT * FROM firmware_versions WHERE id = ?", (fw_id,))
        row = cursor.fetchone()
        return self._row_to_model(row, FirmwareVersion) if row else None

    def get_by_version(self, version: str) -> Optional[FirmwareVersion]:
        cursor = self.conn.execute("SELECT * FROM firmware_versions WHERE version = ?", (version,))
        row = cursor.fetchone()
        return self._row_to_model(row, FirmwareVersion) if row else None

    def get_all(self) -> List[FirmwareVersion]:
        cursor = self.conn.execute("SELECT * FROM firmware_versions ORDER BY release_date")
        return [self._row_to_model(row, FirmwareVersion) for row in cursor.fetchall()]


class ParameterRepository(BaseRepository):
    def get(self, param_uuid: str, firmware_version_id: int) -> Optional[ConfigParameter]:
        cursor = self.conn.execute("""
            SELECT * FROM config_parameters
            WHERE param_uuid = ? AND firmware_version_id = ?
        """, (param_uuid, firmware_version_id))
        row = cursor.fetchone()
        return self._row_to_model(row, ConfigParameter) if row else None

    def get_for_firmware(self, firmware_version_id: int) -> List[ConfigParameter]:
        cursor = self.conn.execute("""
            SELECT * FROM config_parameters
            WHERE firmware_version_id = ?
        """, (firmware_version_id,))
        return [self._row_to_model(row, ConfigParameter) for row in cursor.fetchall()]


class ApiRepository(BaseRepository):
    def get_method(self, method_name: str, firmware_version_id: int) -> Optional[ApiMethod]:
        name = method_name.strip().lower()
        logger.debug("Querying method_info for name='{}', fw_id={}", name, firmware_version_id)
        cursor = self.conn.execute("""
            SELECT am.id, am.method_name, am.http_method, am.firmware_version_id, 
                   am.method_url, am.positive_status, am.control_method_name 
            FROM api_methods am
            WHERE LOWER(am.method_name) = ? AND am.firmware_version_id = ?
        """, (name, firmware_version_id))
        row = cursor.fetchone()
        if not row:
            logger.warning("Method '{}' not found for firmware ID {}", name, firmware_version_id)
            return None
        return self._row_to_model(row, ApiMethod)

    def get_method_params(self, method_name: str, firmware_version_id: int) -> List[ApiMethodParam]:
        """Выдает список объектов класса ApiMethodParam"""
        name = method_name.strip().lower()
        logger.debug("Querying params for method='{}', fw_id={}", name, firmware_version_id)
        cursor = self.conn.execute("""
            SELECT 
                amp.json_path, amp.is_required, amp.in_request, amp.condition_expr,
                amp.example_value, amp.gen_rule, amp.related_params_uuid,
                cp.param_uuid, cp.location, cp.name, cp.migration_down, cp.migration_up,
                cp.description, cp.data_type_id, cp.default_value, cp.format_hint,
                cp.min_value, cp.max_value, cp.allowed_values, cp.unit,
                cra.rule_payload, cra.rule_type 
            FROM api_method_params amp
            JOIN api_methods am ON amp.method_id = am.id
            LEFT JOIN config_parameters cp ON amp.related_params_uuid = cp.param_uuid
            LEFT JOIN conversion_rules_api cra ON cra.json_path = amp.json_path AND cra.method_id = amp.method_id 
            WHERE LOWER(am.method_name) = ? AND am.firmware_version_id = ?
            ORDER BY amp.priority
        """, (name, firmware_version_id))
        params = [self._row_to_model(row, ApiMethodParam) for row in cursor.fetchall()]
        if not params:
            logger.warning("No parameters found for method '{}' and firmware ID {}", name, firmware_version_id)
        else:
            logger.debug("Found {} parameters for method '{}'", len(params), name)
        return params

    def get_positive_status(self, method_name: str, firmware_version_id: int) -> Optional[int]:
        """Получаем ожидаемый статус для позитивного теста"""
        cursor = self.conn.execute("""
            SELECT am.positive_status FROM api_methods am
            WHERE LOWER(am.method_name) = ? AND am.firmware_version_id = ?
        """, (method_name.lower(), firmware_version_id))
        row = cursor.fetchone()
        return row['positive_status'] if row else None

    def get_method_by_param(self, param_uuid: str, firmware_version_id: int):
        """Находит метод, который отвечает за получение/установку конкретного параметра"""
        cursor = self.conn.execute("""
            SELECT amp.json_path, am.method_url, am.http_method
            FROM api_method_params amp
            JOIN api_methods am ON amp.method_id = am.id
            WHERE amp.param_uuid = ? AND amp.firmware_version_id = ?
            LIMIT 1
        """, (param_uuid, firmware_version_id))
        return cursor.fetchone()


class UiRepository(BaseRepository):
    def get_mapping(self, param_uuid: str, firmware_version_id: int) -> Optional[ParameterUiMapping]:
        cursor = self.conn.execute("""
            SELECT * FROM parameter_ui_mapping
            WHERE param_uuid = ? AND firmware_version_id = ?
        """, (param_uuid, firmware_version_id))
        row = cursor.fetchone()
        return self._row_to_model(row, ParameterUiMapping) if row else None


class DBRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        self.firmware = None
        self.parameters = None
        self.api = None
        self.ui = None

    @property
    def connection(self):
        return self._conn

    def connect(self):
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self.firmware = FirmwareRepository(self._conn)
        self.parameters = ParameterRepository(self._conn)
        self.api = ApiRepository(self._conn)
        self.ui = UiRepository(self._conn)
        return self

    def close(self):
        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()