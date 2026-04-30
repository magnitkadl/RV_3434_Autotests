import pytest
import allure
from tests.common.test_executor import run_method_test

@allure.feature("API")
@allure.story("Настройки видео")
def test_set_video_settings(db, api_client, firmware_version, test_case):
    """
    Тест изменения настроек видео.
    """
    run_method_test(
        db=db,
        api_client=api_client,
        firmware_version=firmware_version,
        method_name="Set Video Settings",
        case=test_case
    )
