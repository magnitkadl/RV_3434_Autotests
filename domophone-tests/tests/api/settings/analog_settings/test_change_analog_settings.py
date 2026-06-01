import pytest
import allure
from tests.common.test_executor import run_method_test

@allure.feature("API")
@allure.story("Настройки аналоговой линии")
@pytest.mark.skip(reason="Not implemented yet")
def test_change_analog_settings(db, api_client, firmware_version, test_case):
    """
    Тест изменения настроек аналоговой линии.
    """
    run_method_test(
        db=db,
        api_client=api_client,
        firmware_version=firmware_version,
        method_name="Change Analog Settings",
        case=test_case
    )
