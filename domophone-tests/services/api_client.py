# services/api_client.py
import json

import requests
from typing import Any, Dict, Optional
import yaml
import os
from core import get_parameter, get_firmware_by_version, get_db_connection, get_method_properties
from jsonpath_ng import parse


class ApiClient:
    def __init__(self, config_path: str = "config/test_config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        device = self.config["device"]
        # Переменные окружения имеют приоритет!
        self.host = os.getenv("DEVICE_HOST", device["host"])
        self.port = int(os.getenv("DEVICE_PORT", device["port"]))
        self.username = os.getenv("DEVICE_USER", device["username"])
        self.password = os.getenv("DEVICE_PASS", device["password"])
        self.protocol = os.getenv("DEVICE_PROTO", device["protocol"])

        self.base_url = f"{self.protocol}://{self.host}:{self.port}"
        self.auth = (self.username, self.password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.timeout = 10
        self._db_conn = None  # будем лениво открывать соединение
        self._db_path = None

    def _ensure_db_path(self):
        if self._db_path is None:
            import yaml
            with open("config/test_config.yaml") as f:
                cfg = yaml.safe_load(f)
            self._db_path = cfg["db_path"]

    def get_firmware_version(self) -> str:
        """Пример: получение версии прошивки через /api/v1/version"""
        resp = self.session.get(f"{self.base_url}/api/v1/version")
        resp.raise_for_status()
        return resp.json().get("firmware_version")

    def change_method(self, db, method_name, test_values, firmware_version_id) -> str:
        """временная заглушка"""
        test_values = json.dumps(test_values)
        method_params = get_method_properties(db, method_name, firmware_version_id)
        resp = self.session.request(method=method_params.http_method, url=f"{self.base_url}{method_params.method_url}",
                                    data=str(test_values))
        # resp = self.session.patch(f"{self.base_url}/api/v1/settings/audio/sip", data = str(test_values))
        resp.raise_for_status()
        return resp

    def get_method(self, method_name, fw_id) -> str:
        """временная заглушка"""
        resp = self.session.get(f"{self.base_url}/api/v1/settings/audio/sip")
        resp.raise_for_status()
        return resp

    def _get_db(self):
        if self._db_conn is None:
            from core import get_db_connection
            # Предположим, что путь к БД берём из того же конфига
            import yaml
            with open("config/test_config.yaml") as f:
                cfg = yaml.safe_load(f)
            self._db_conn = get_db_connection(cfg["db_path"])
        return self._db_conn

    def get_parameter(self, param_uuid: str, firmware_version) -> Any:
        """
        Получает значение параметра через правильный API-метод и JSONPath,
        используя метаданные из БД.
        """
        self._ensure_db_path()
        with get_db_connection(self._db_path) as conn:

            db = self._get_db()

            # Шаг 1: найдём текущую прошивку устройства
            #current_fw_version = self.get_firmware_version()  # ← должен работать!
            current_fw_version = firmware_version
            fw = get_firmware_by_version(conn, current_fw_version)
            # if not fw:
            #     raise ValueError(f"Прошивка {current_fw_version} не найдена в БД")

            # Шаг 2: найдём метод, который отдаёт этот параметр
            # Ищем в api_method_params запись для (param_uuid, fw.id)
            cursor = conn.execute("""
                SELECT amp.json_path, am.method_url, am.http_method
                FROM api_method_params amp
                JOIN api_methods am ON amp.method_id = am.id
                WHERE amp.param_uuid = ? AND amp.firmware_version_id = ?
                LIMIT 1
            """, (param_uuid, fw.id))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Параметр {param_uuid} не найден для прошивки {fw.version}")

            json_path, method_url, http_method = row

            # Шаг 3: получим спецификацию метода (URL и т.д.)
            # ← Здесь тебе нужно сопоставить method_name с реальным URL.
            # Например, через маппинг или таблицу в БД (пока хардкод)
            url = self._resolve_method_url(method_url)
            if not url:
                raise ValueError(f"Неизвестный метод API: {method_url}")

            # Шаг 4: вызовем API
            if http_method.upper() == "GET":
                resp = self.session.get(url)
            elif http_method.upper() == "POST":
                resp = self.session.post(url)
            else:
                raise NotImplementedError(f"HTTP метод {http_method} не поддерживается")

            resp.raise_for_status()
            response_data = resp.json()

            # Шаг 5: извлечём значение по JSONPath
            try:
                jsonpath_expr = parse(json_path)
                matches = [match.value for match in jsonpath_expr.find(response_data)]
                if not matches:
                    raise ValueError(f"JSONPath {json_path} не нашёл значение в ответе")
                return matches[0]  # берем первое совпадение
            except Exception as e:
                raise ValueError(f"Ошибка при извлечении по JSONPath {json_path}: {e}")

    # def _set_parameter(self, param_uuid: str, value: Any) -> None:
    #     """Надо переписать на основе get_parameter"""
    #     resp = self.session.patch(f"{self.base_url}/api/v1/version")
    #     resp.raise_for_status()
    #     return resp.json().get("firmware_version")

    def get_parameters_for_method(self, method_name: str, firmware_version) -> Any:
        """
        Отказался от этой функции, надо будет в будущем удалить
        Получает значение параметра через правильный API-метод и JSONPath,
        используя метаданные из БД.
        """
        self._ensure_db_path()
        with get_db_connection(self._db_path) as conn:

            db = self._get_db()

            # Шаг 1: найдём текущую прошивку устройства
            #current_fw_version = self.get_firmware_version()  # ← должен работать!
            current_fw_version = firmware_version
            fw = get_firmware_by_version(conn, current_fw_version)
            # if not fw:
            #     raise ValueError(f"Прошивка {current_fw_version} не найдена в БД")

            # Шаг 2: найдём метод, который отдаёт этот параметр
            # Ищем в api_method_params запись для (param_uuid, fw.id)
            cursor = conn.execute("""
                SELECT amp.json_path, cp.*
                FROM api_method_params amp
                JOIN api_methods am ON amp.method_id = am.id
                JOIN config_parameters cp ON amp.param_uuid = cp.param_uuid
                WHERE am.method_name = ? AND amp.firmware_version_id = ?
            """, (method_name, fw.id))

            row = cursor.fetchall()
            if not row:
                raise ValueError(f"Параметры метода {method_name} не найден для прошивки {fw.version}")

            # json_path, method_url, http_method = row

            # Шаг 3: получим спецификацию метода (URL и т.д.)
            # ← Здесь тебе нужно сопоставить method_name с реальным URL.
            # Например, через маппинг или таблицу в БД (пока хардкод)
            url = self._resolve_method_url(method_url)
            if not url:
                raise ValueError(f"Неизвестный метод API: {method_url}")

            # Шаг 4: вызовем API
            if http_method.upper() == "GET":
                resp = self.session.get(url)
            elif http_method.upper() == "POST":
                resp = self.session.post(url)
            else:
                raise NotImplementedError(f"HTTP метод {http_method} не поддерживается")

            resp.raise_for_status()
            response_data = resp.json()

            # Шаг 5: извлечём значение по JSONPath
            try:
                jsonpath_expr = parse(json_path)
                matches = [match.value for match in jsonpath_expr.find(response_data)]
                if not matches:
                    raise ValueError(f"JSONPath {json_path} не нашёл значение в ответе")
                return matches[0]  # берем первое совпадение
            except Exception as e:
                raise ValueError(f"Ошибка при извлечении по JSONPath {json_path}: {e}")

    def _resolve_method_url(self, method_url: str) -> str:
        """
        Преобразует имя метода (из БД) в реальный URL.
        Позже можно вынести в БД или конфиг.
        """
        # Пример маппинга (временно)
        method_to_url = {
            "get_security_config": "/api/v1/security/config",
            "get_network_settings": "/api/v1/network",
            "/api/v1/settings/audio/system": "/api/v1/settings/audio/system"
            # ... добавь все 200 методов или сделай шаблон
        }
        path = method_to_url.get(method_url)
        if not path:
            raise ValueError(f"URL для метода '{method_url}' не настроен")
        return f"{self.base_url}{path}"

    def close(self):
        self.session.close()