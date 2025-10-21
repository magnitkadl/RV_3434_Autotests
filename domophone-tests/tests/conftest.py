# tests/conftest.py
import pytest
import os
from core import get_db_connection, FirmwareVersion
from services.api_client import ApiClient


@pytest.fixture(scope="session")
def test_config():
    config_path = os.getenv("TEST_CONFIG", "config/test_config.yaml")
    return config_path


@pytest.fixture(scope="session")
def db(test_config):
    import yaml
    with open(test_config) as f:
        config = yaml.safe_load(f)
    db_path = config["db_path"]
    with get_db_connection(db_path) as conn:
        yield conn


@pytest.fixture(scope="session")
def api_client(test_config):
    client = ApiClient(test_config)
    yield client
    client.close()

@pytest.fixture(scope="session")
def firmware_version(api_client) -> str:
    """
    Получает версию прошивки один раз в начале тестовой сессии.
    """
    raw_version = api_client.get_firmware_version()  # ваш метод в ApiClient

    return raw_version