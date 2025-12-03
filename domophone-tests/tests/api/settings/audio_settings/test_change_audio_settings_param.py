import pytest
import allure
from deepdiff import DeepDiff
from core import get_firmware_by_version, get_api_method_params, get_method_info
from core import generate_correct_api_method_params
from core import get_positive_status


@pytest.mark.parametrize(
    "method_name",
    [
        pytest.param("Change Audio Sip settings", id="audio_sip_positive"),
        pytest.param("Change Notify speaker volume", id="notify_speaker_positive"),
    ],
)
@allure.feature("API")
@allure.story("Аудио настройки")
def test_positive_change_audio_settings(db, api_client, firmware_version, method_name):
    fw_model = get_firmware_by_version(db, firmware_version)
    method_params = get_api_method_params(db, method_name, fw_model.id)
    sent_values = generate_correct_api_method_params(db, method_params, api_client, fw_model.id, method_name)
    expected_status = get_positive_status(db, method_name, fw_model.id)

    allure.dynamic.title(f"Позитивный сценарий: {method_name}")

    response = api_client.running_method(db, method_name, fw_model.id, sent_values)
    control_method = get_method_info(db, method_name, fw_model.id).control_method_name
    actual_values_response = api_client.running_method(db, control_method, fw_model.id)
    actual_values = actual_values_response.json()
    different_values = DeepDiff(actual_values, sent_values)

    with allure.step(f"Проверка работы апи метода {method_name}"):
        allure.attach(str(sent_values), "Отправленные значения", allure.attachment_type.TEXT)
        allure.attach(str(actual_values), "Полученные значения (из API)", allure.attachment_type.TEXT)
        assert response.status_code == expected_status, f"Ожидался {expected_status}, получено {response.status_code}"
        assert sent_values == actual_values, f"Значения параметров {different_values} отличаются от отправленных"