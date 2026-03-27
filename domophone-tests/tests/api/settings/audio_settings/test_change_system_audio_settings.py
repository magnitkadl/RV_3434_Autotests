import pytest
import allure
from tests.common.test_executor import run_method_test

@allure.feature("API")
@allure.story("Проверка изменения аудио настроек системы")
def test_change_system_audio_settings(db, api_client, firmware_version, test_case):
    """
    Тест изменения аудио настроек системы.
    """
    run_method_test(
        db=db,
        api_client=api_client,
        firmware_version=firmware_version,
        method_name="Change System Audio settings",
        case=test_case
    )