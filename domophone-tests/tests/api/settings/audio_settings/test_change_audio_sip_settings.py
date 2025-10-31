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

    param_uuid = "system_audio.volume"

    # Act
    param_from_db = get_parameter(db, param_uuid, fw_model.id)
    assert param_from_db is not None, f"Параметр {param_uuid} не найден для прошивки {current_fw_version}"

    actual_value = api_client.get_parameter(param_uuid, firmware_version)

    # Assert
    expected_default = param_from_db.default_value
    # Приведение типов — зависит от твоего API (может возвращать int, а в БД строка)
    if param_from_db.data_type_id == 1:  # допустим, 1 = int
        expected_default = int(expected_default) if expected_default else None

    with allure.step(f"Сравнение значения параметра {param_uuid}"):
        allure.attach(str(expected_default), "Ожидаемое (из БД)", allure.attachment_type.TEXT)
        allure.attach(str(actual_value), "Фактическое (из API)", allure.attachment_type.TEXT)
        assert actual_value == expected_default, \
            f"Значение параметра {param_uuid} не совпадает с дефолтом из БД"