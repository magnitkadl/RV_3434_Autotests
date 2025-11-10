# tests/api/settings/audio_settings/test_change_audio_sip_settings.py
import pytest
import allure
from deepdiff import DeepDiff
from core import get_parameter, get_firmware_by_version, get_api_method_params
from core import generate_correct_api_method_params
from core import get_positive_status


@allure.title("Позитивный сценарий проверки изменения аудио настроек SIP")
@allure.feature("API")
@allure.story("Проверка изменения аудио настроек SIP")
def test_positive_change_audio_sip_settings(db, api_client, firmware_version):

    # Arrange
    fw_model = get_firmware_by_version(db, firmware_version)
    #assert fw_model is not None, f"Прошивка {firmware_version} не найдена в БД"
    method_name = "Change System Audio settings"
    method_params = get_api_method_params(db, method_name, fw_model.id)
    sent_values = generate_correct_api_method_params(method_params, api_client, fw_model.id, method_name)
    expected_status = get_positive_status(db, method_name, fw_model.id)

    # Act
    response = api_client.change_method(method_name, sent_values, fw_model.id)
    actual_values_response = api_client.get_method(method_name, fw_model.id)
    actual_values = actual_values_response.json()
    different_values = DeepDiff(actual_values, sent_values)

    # Assert
    with allure.step(f"Проверка работы апи метода {method_name}"):
        allure.attach(str(sent_values), "Отправленные значения", allure.attachment_type.TEXT)
        allure.attach(str(actual_values), "Полученные значения (из API)", allure.attachment_type.TEXT)
        assert response.status_code == expected_status, f"Ожидался {expected_status}, получено {response.status_code}"
        assert sent_values == actual_values, \
            f"Значения параметров {different_values} отличаются от отправленных"