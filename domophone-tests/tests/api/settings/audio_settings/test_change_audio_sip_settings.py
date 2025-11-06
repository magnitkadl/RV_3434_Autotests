# tests/api/settings/audio_settings/test_change_audio_sip_settings.py
import pytest
import allure
#from core import get_parameter, get_firmware_by_version
#from core import generate_correct_value


@allure.title("Позитивный сценарий проверки изменения аудио настроек SIP")
@allure.feature("API")
@allure.story("Проверка изменения аудио настроек SIP")
def test_positive_change_audio_sip_settings(db, api_client, firmware_version):
    # Arrange
    fw_model = get_firmware_by_version(db, firmware_version)
    #assert fw_model is not None, f"Прошивка {firmware_version} не найдена в БД"

    method_name = "Change System Audio settings"

    # Act
    sent_values = generate_correct_values_for_method(db, api_client, firmware_version, method_name)
    response = change_method(db, method_name, fw_model.id, sent_values)
    expected_status = get_positive_status()

    assert response.status_code == expected_status, f"Ожидался {expected_status}, получено {response.status_code}"

    actual_values = api_client.get_parameters_for_method(method_name, firmware_version)

    # Assert
    actual_values = response.body

    with allure.step(f"Проверка работы апи метода {method_name}"):
        allure.attach(str(sent_values), "Отправленные значения", allure.attachment_type.TEXT)
        allure.attach(str(actual_values), "Полученные значения (из API)", allure.attachment_type.TEXT)
        assert sent_values == actual_values, \
            f"Значения параметров {different_values} отличаются от отправленных"