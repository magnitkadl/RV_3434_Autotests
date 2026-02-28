# core/parameter.py
"""
Модуль для работы с параметрами конфигурации.
Содержит вспомогательные функции и логику (в будущем — миграции).
Сейчас — просто переэкспорт из db для удобства.
"""
import random
from jsonpath_ng import parse
import re
from .db import (
    get_parameter,
    get_api_method_params,
    get_firmware_by_version,
    get_method_info,
)

def generate_correct_value(db, api_client, firmware_version, param_uuid):

    fw_model = get_firmware_by_version(db, firmware_version)

    # Act
    param_from_db = get_parameter(db, param_uuid, fw_model.id)
    assert param_from_db is not None, f"Параметр {param_uuid} не найден для прошивки {firmware_version}"

    actual_value = api_client.get_parameter(db, param_uuid, firmware_version)


    if param_from_db.data_type_id == 1:
        min_value = int(param_from_db.min_value) if param_from_db.min_value is not None else None
        max_value = int(param_from_db.max_value) if param_from_db.max_value is not None else None
        exclude = actual_value
        if min_value is not None and max_value is not None and max_value - min_value >= 2:
            low = min_value + 1
            high = max_value - 1
            if exclude is not None and low <= exclude <= high and (high - low) >= 1:
                n = high - low + 1
                k = random.randint(0, n - 2)
                test_value = low + k
                if test_value >= exclude:
                    test_value += 1
            else:
                test_value = random.randint(low, high)
            return test_value
        if min_value is not None and max_value is not None:
            return min_value if exclude != min_value else max_value
        if min_value is not None:
            candidate = min_value + 1
            return candidate if candidate != exclude else min_value
        if max_value is not None:
            candidate = max_value - 1
            return candidate if candidate != exclude else max_value
        return exclude + 1 if isinstance(exclude, int) else 1


def generate_correct_api_method_params(db, method_params, api_client, firmware_version_id, method_name):

    ''' Получает для метода параметры, считывает актуальное значение и генерирует новое, не совпадающее с текущим
        и не попадающее на границы (границы будут проверяться отдельным тестом) '''

    method_info = get_method_info(db, method_name, firmware_version_id)

    # Act
    actual_values = api_client.running_method(db, method_info.control_method_name, firmware_version_id).json()
    test_values = {}

    for parameter in method_params:

        if parameter.data_type_id == 1:
            min_value = int(parameter.min_value) if parameter.min_value is not None else None
            max_value = int(parameter.max_value) if parameter.max_value is not None else None
            matches = [m.value for m in parse(parameter.json_path).find(actual_values)]
            exclude = matches[0] if matches else None
            if min_value is not None and max_value is not None and max_value - min_value >= 2:
                low = min_value + 1
                high = max_value - 1
                if exclude is not None and low <= exclude <= high and (high - low) >= 1:
                    n = high - low + 1
                    k = random.randint(0, n - 2)
                    test_value = low + k
                    if test_value >= exclude:
                        test_value += 1
                else:
                    test_value = random.randint(low, high)
            elif min_value is not None and max_value is not None:
                test_value = min_value if exclude != min_value else max_value
            elif min_value is not None:
                candidate = min_value + 1
                test_value = candidate if exclude != candidate else min_value
            elif max_value is not None:
                candidate = max_value - 1
                test_value = candidate if exclude != candidate else max_value
            else:
                test_value = (exclude + 1) if isinstance(exclude, int) else 1
            _set_by_path(test_values, parameter.json_path, test_value)

    return test_values

def _set_by_path(target, path, value):
    p = path.strip()
    if p.startswith('$.'):
        p = p[2:]
    tokens = []
    for m in re.finditer(r'([^.\[\]]+)|\[(\d+)\]', p):
        key, idx = m.groups()
        if key is not None:
            tokens.append(("key", key))
        else:
            tokens.append(("index", int(idx)))
    cur = target
    for i, (t, v) in enumerate(tokens):
        last = i == len(tokens) - 1
        if t == "key":
            if last:
                cur[v] = value
            else:
                if v not in cur or not isinstance(cur.get(v), (dict, list)):
                    # Проверяем, какой тип данных будет следующим токеном
                    next_token_type = tokens[i + 1][0] if i + 1 < len(tokens) else None
                    cur[v] = [] if next_token_type == "index" else {}
                cur = cur[v]
        else:
            # Обработка индекса в списке
            while len(cur) <= v:
                cur.append({})
            
            if last:
                cur[v] = value
            else:
                # Если не последний, подготавливаем структуру для следующего токена
                next_token_type = tokens[i + 1][0] if i + 1 < len(tokens) else None
                if not isinstance(cur[v], (dict, list)):
                    cur[v] = [] if next_token_type == "index" else {}
                cur = cur[v]