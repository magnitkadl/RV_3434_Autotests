# services/api_client.py
import json
import time
import requests
from typing import Any, Dict, Optional
import yaml
import os
from loguru import logger
from core import get_firmware_by_version, get_method_info
from jsonpath_ng import parse


class ApiClient:
    def __init__(self, config_path: str = "config/test_config.yaml", db_connection=None, timeout: Optional[int] = None):
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
        self.username = os.getenv("DEVICE_USER", device["username"])
        self.password = os.getenv("DEVICE_PASS", device["password"])
        self.auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.timeout = 10
        self.db_path = self.config.get("db_path")
        self.timeout = timeout if timeout is not None else int(self.config.get("http_timeout", 10))

        # без автоматических ретраев: тесты должны видеть исходную ошибку

    def get_firmware_version(self) -> str:
        """Пример: получение версии прошивки через /api/v1/version"""
        t0 = time.monotonic()
        resp = self.session.get(f"{self.base_url}/api/v1/version", timeout=self.timeout)
        resp.raise_for_status()
        logger.info("GET {} -> {} in {:.3f}s", f"{self.base_url}/api/v1/version", resp.status_code, time.monotonic()-t0)
        return resp.json().get("firmware_version")

    def running_method(self, db, method_name, firmware_version_id, test_values=None) -> str:
        """получает url метода и его тип, а дальше выполняет метод"""
        method_info = get_method_info(db, method_name, firmware_version_id)
        t0 = time.monotonic()
        url = f"{self.base_url}{method_info.method_url}"
        method = method_info.http_method.upper()
        payload = test_values if (test_values is not None and method in {"POST", "PUT", "PATCH"}) else None
        try:
            resp = self.session.request(
                method=method,
                url=url,
                json=payload,
                timeout=self.timeout,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.error("{} {} failed: {}", method, url, e)
            raise
        resp.raise_for_status()
        logger.info("{} {} -> {} in {:.3f}s", method, url, resp.status_code, time.monotonic()-t0)
        return resp

    def get_parameter(self, db, param_uuid: str, firmware_version) -> Any:
        """
        Получает значение параметра через правильный API-метод и JSONPath,
        используя метаданные из БД.
        """
        # Шаг 1: найдём текущую прошивку устройства
        current_fw_version = firmware_version
        fw = get_firmware_by_version(db, current_fw_version)

        # Шаг 2: найдём метод, который отдаёт этот параметр
        # Ищем в api_method_params запись для (param_uuid, fw.id)
        cursor = db.execute("""
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
        url = self._resolve_method_url(method_url)
        if not url:
            raise ValueError(f"Неизвестный метод API: {method_url}")

        # Шаг 4: вызовем API
        t0 = time.monotonic()
        try:
            if http_method.upper() == "GET":
                resp = self.session.get(url, timeout=self.timeout)
            elif http_method.upper() == "POST":
                resp = self.session.post(url, timeout=self.timeout)
            else:
                raise NotImplementedError(f"HTTP метод {http_method} не поддерживается")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.error("{} {} failed: {}", http_method.upper(), url, e)
            raise

        resp.raise_for_status()
        logger.info("{} {} -> {} in {:.3f}s", http_method.upper(), url, resp.status_code, time.monotonic()-t0)
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
        self._ensure_db_conn()
        conn = self.db_conn

        # Шаг 1: найдём текущую прошивку устройства
        # current_fw_version = self.get_firmware_version()  # ← должен работать!
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
            return f"{self.base_url}{method_url}"
        return f"{self.base_url}{path}"

    def close(self):
        self.session.close()