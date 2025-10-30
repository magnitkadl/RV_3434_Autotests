# core/parameter.py
"""
Модуль для работы с параметрами конфигурации.
Содержит вспомогательные функции и логику (в будущем — миграции).
Сейчас — просто переэкспорт из db для удобства.
"""

from .db import get_parameter

def generate_correct_value(db, api_client, firmware_version, param_uuid):

    fw_model = get_firmware_by_version(db, firmware_version)

    # Act
    param_from_db = get_parameter(db, param_uuid, fw_model.id)
    assert param_from_db is not None, f"Параметр {param_uuid} не найден для прошивки {current_fw_version}"

    actual_value = api_client.get_parameter(param_uuid, firmware_version)


    if param_from_db.data_type_id == 1:  # допустим, 1 = int
        min_value = int(param_from_db.min_value) if param_from_db.min_value else None
        max_value = int(param_from_db.max_value) if param_from_db.max_value else None
        test_value = random.randint(min_value, max_value)

        # Если оно >= исключаемого — сдвигаем на 1
        if test_value >= actual_value:
            test_value += 1

        return test_value