import pytest
import allure
from tests.common.test_executor import run_method_test

@allure.feature("API")
@allure.story("Проверка изменения аудио настроек WebRTC")
def test_change_audio_webrct(db, api_client, firmware_version, test_case):
    """
    Тест изменения аудио настроек WebRTC.
    """
    run_method_test(
        db=db,
        api_client=api_client,
        firmware_version=firmware_version,
        method_name="Change Audio WebRTC",
        case=test_case
    )