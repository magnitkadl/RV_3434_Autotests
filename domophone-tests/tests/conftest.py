# tests/conftest.py
import pytest
import os
from core import get_db_connection, FirmwareVersion
from services.api_client import ApiClient

def pytest_addoption(parser):
    """Добавляет опции командной строки для pytest."""
    parser.addoption(
        "--control",
        action="store",
        default="api",
        choices=["api", "web", "config"],
        help="Способ проверки результата: api, web или config"
    )
    parser.addoption(
        "--type",
        action="store",
        default="positive",
        choices=["positive", "negative", "boundary"],
        help="Тип тестового сценария: positive, negative или boundary"
    )

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
def firmware_version(api_client, test_config) -> str:
    """
    Получает версию прошивки один раз в начале тестовой сессии.
    """
    import yaml
    with open(test_config) as f:
        config = yaml.safe_load(f)
    version_source = config["firmware"]["version_source"]

    if version_source == "api":
        raw_version = api_client.get_firmware_version()
    elif version_source == "config":
        raw_version = config["firmware"]["expected_version"]

    return raw_version

@pytest.fixture
def test_case(request):
    """
    Фикстура для передачи параметров кейса в run_method_test.
    Берет значения из CLI флагов --control и --type.
    """
    return {
        "control": request.config.getoption("--control"),
        "type": request.config.getoption("--type")
    }
