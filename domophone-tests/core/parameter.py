# core/parameter.py
"""
Модуль для работы с параметрами конфигурации.
Содержит вспомогательные функции и логику (в будущем — миграции).
Сейчас — просто переэкспорт из db для удобства.
"""
import random
from .db import get_parameter, get_api_method_params, get_firmware_by_version

def generate_correct_value(db, api_client, firmware_version, param_uuid):

    fw_model = get_firmware_by_version(db, firmware_version)

    # Act
    param_from_db = get_parameter(db, param_uuid, fw_model.id)
    assert param_from_db is not None, f"Параметр {param_uuid} не найден для прошивки {current_fw_version}"

    actual_value = api_client.get_parameter(param_uuid, firmware_version)


    if param_from_db.data_type_id == 1:  # допустим, 1 = int
        min_value = int(param_from_db.min_value) if param_from_db.min_value else None
        max_value = int(param_from_db.max_value) if param_from_db.max_value else None
        test_value = random.randint(min_value, max_value - 1)

        # Если оно >= исключаемого — сдвигаем на 1
        if test_value >= actual_value:
            test_value += 1

        return test_value


def generate_correct_api_method_params(db, method_params, api_client, firmware_version_id, method_name):

    ''' Временно, потом надо переписать через generate_correct_value и вынести получение актуального значения/значений
    в отдельную функцию, чтобы не дергать апи на каждый параметр '''


    # Act
    actual_values = api_client.get_method(db, "Get Audio Sip settings", firmware_version_id).json()
    test_values = {}

    for parameter in method_params:

        if parameter.data_type_id == 1:  # допустим, 1 = int
            min_value = int(parameter.min_value) if parameter.min_value else None
            max_value = int(parameter.max_value) if parameter.max_value else None
            test_value = random.randint(min_value + 1, max_value - 2)

            # Если оно >= исключаемого — сдвигаем на 1
            if test_value >= actual_values[parameter.json_path]:
                test_value += 1
            test_values[parameter.json_path] = test_value

#     test_values = {
#     "sip_mic_sensitivity": 15,
#     "sip_volume": 13,
#     "sip_incoming_volume": 13
# }
    return test_values