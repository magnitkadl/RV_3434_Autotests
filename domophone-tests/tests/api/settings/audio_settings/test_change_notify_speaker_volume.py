import pytest
import allure
from tests.common.test_executor import run_method_test

@allure.feature("API")
@allure.story("Аудио настройки")
@pytest.mark.positive
def test_change_notify_speaker_volume(db, api_client, firmware_version, test_case):
    """
    Тест изменения громкости динамика уведомлений.
    """
    run_method_test(
        db=db,
        api_client=api_client,
        firmware_version=firmware_version,
        method_name="Change Notify speaker volume",
        case=test_case
    )
