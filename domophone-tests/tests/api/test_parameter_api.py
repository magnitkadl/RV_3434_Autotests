# tests/api/test_parameter_api.py
import pytest
import allure
from core import DataTypeEnum


@allure.title("Проверка соответствия значения параметра дефолту из БД")
@allure.feature("API")
@allure.story("Чтение параметров")
def test_parameter_default_matches_db(db, api_client, firmware_version):
    # Arrange
    fw_model = db.firmware.get_by_version(firmware_version)
    #assert fw_model is not None, f"Прошивка {firmware_version} не найдена в БД"

    param_uuid = "system_audio.volume"

    # Act
    param_from_db = db.parameters.get(param_uuid, fw_model.id)
    assert param_from_db is not None, f"Параметр {param_uuid} не найден для прошивки {firmware_version}"

    actual_value = api_client.get_parameter(db, param_uuid, firmware_version)

    # Assert
    expected_default = param_from_db.default_value
    if param_from_db.data_type_id == DataTypeEnum.INT:
        expected_default = int(expected_default) if expected_default else None
    elif param_from_db.data_type_id == DataTypeEnum.FLOAT:
        expected_default = float(expected_default) if expected_default else None
    elif param_from_db.data_type_id == DataTypeEnum.BOOL:
        expected_default = expected_default.lower() == 'true' if expected_default else None

    with allure.step(f"Сравнение значения параметра {param_uuid}"):
        allure.attach(str(expected_default), "Ожидаемое (из БД)", allure.attachment_type.TEXT)
        allure.attach(str(actual_value), "Фактическое (из API)", allure.attachment_type.TEXT)
        assert actual_value == expected_default, \
            f"Значение параметра {param_uuid} не совпадает с дефолтом из БД"