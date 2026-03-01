import pytest
import allure
from tests.common.test_executor import run_method_test

@allure.feature("API")
@allure.story("Проверка изменения аудио настроек SIP")
def test_change_audio_sip_settings(db, api_client, firmware_version, test_case):
    """
    Тест изменения аудио настроек SIP.
    """
    run_method_test(
        db=db,
        api_client=api_client,
        firmware_version=firmware_version,
        method_name="Change Audio Sip settings",
        case=test_case
    )
