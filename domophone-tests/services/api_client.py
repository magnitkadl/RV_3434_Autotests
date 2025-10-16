# services/api_client.py
import requests
from typing import Any, Dict, Optional
import yaml
import os


class ApiClient:
    def __init__(self, config_path: str = "domophone-tests/config/test_config.yaml"):
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

    def get_firmware_version(self) -> str:
        """Пример: получение версии прошивки через /api/system/info"""
        resp = self.session.get(f"{self.base_url}/api/v1/version")
        resp.raise_for_status()
        return resp.json().get("firmware_version")

    def get_parameter(self, param_uuid: str) -> Any:
        """
        Получает значение параметра.
        Предполагается, что есть эндпоинт вроде /api/parameters/{uuid}
        """
        resp = self.session.get(f"{self.base_url}/api/parameters/{param_uuid}")
        resp.raise_for_status()
        return resp.json().get("value")

    def set_parameter(self, param_uuid: str, value: Any) -> bool:
        """Устанавливает значение параметра."""
        payload = {"value": value}
        resp = self.session.post(
            f"{self.base_url}/api/parameters/{param_uuid}",
            json=payload
        )
        resp.raise_for_status()
        return resp.status_code == 200

    def close(self):
        self.session.close()