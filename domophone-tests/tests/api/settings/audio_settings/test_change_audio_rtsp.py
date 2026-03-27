import pytest
import allure
from tests.common.test_executor import run_method_test

@allure.feature("API")
@allure.story("Проверка изменения аудио настроек RTSP")
def test_change_audio_rtsp(db, api_client, firmware_version, test_case):
    """
    Тест изменения аудио настроек RTSP.
    """
    run_method_test(
        db=db,
        api_client=api_client,
        firmware_version=firmware_version,
        method_name="Change Audio RTSP",
        case=test_case
    )