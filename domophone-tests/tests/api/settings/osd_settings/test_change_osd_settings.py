import pytest
import allure
from tests.common.test_executor import run_method_test

@allure.feature("API")
@allure.story("Настройки OSD")
def test_change_osd_settings(db, api_client, firmware_version, test_case):
    """
    Тест изменения OSD.
    """
    run_method_test(
        db=db,
        api_client=api_client,
        firmware_version=firmware_version,
        method_name="Change OSD Settings",
        case=test_case
    )
