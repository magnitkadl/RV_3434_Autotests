# tests/conftest.py
import pytest
import os
from core import get_db_connection, FirmwareVersion
from services.api_client import ApiClient


def pytest_addoption(parser):
    parser.addoption(
        "--control", 
        action="store", 
        default="api", 
        help="Backend for verification: api, web, config or comma-separated list"
    )


def pytest_generate_tests(metafunc):
    """
    Автоматическая параметризация для фикстуры 'test_case'.
    Смотрит на маркеры теста (positive/negative/boundary) и флаг --control.
    """
    if "test_case" in metafunc.fixturenames:
        # 1. Определяем типы кейсов по маркерам
        case_types = []
        if metafunc.definition.get_closest_marker("positive"):
            case_types.append("positive")
        if metafunc.definition.get_closest_marker("negative"):
            case_types.append("negative")
        if metafunc.definition.get_closest_marker("boundary"):
            case_types.append("boundary")
        
        # Если маркеров нет, по умолчанию positive
        if not case_types:
            case_types = ["positive"]
            
        # 2. Определяем бэкенды контроля из CLI
        control_opt = metafunc.config.getoption("control")
        controls = [c.strip() for c in control_opt.split(",")]
        
        # 3. Генерируем комбинации
        cases = []
        for ct in case_types:
            for ctrl in controls:
                cases.append({"type": ct, "control": ctrl})
        
        # 4. Параметризуем
        metafunc.parametrize("test_case", cases, ids=lambda c: f"{c['type']}:{c['control']}")


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
def api_client(db, test_config):
    client = ApiClient(test_config, db_connection=db)
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