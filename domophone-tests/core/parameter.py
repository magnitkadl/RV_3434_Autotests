# core/parameter.py
"""
Модуль для работы с параметрами конфигурации.
Содержит вспомогательные функции и логику (в будущем — миграции).
Сейчас — просто переэкспорт из db для удобства.
"""
import random
import json
import re
import string
from jsonpath_ng import parse
from .db import (
    get_parameter,
    get_api_method_params,
    get_firmware_by_version,
    get_method_info,
)

def _generate_test_value(param, exclude_value=None):
    """
    Универсальный генератор корректного значения для любого типа данных.
    Гарантирует несовпадение с exclude_value и соблюдение границ.
    """
    dt_id = param.data_type_id
    
    # 1. int (Целое число)
    if dt_id == 1:
        min_v = int(param.min_value) if param.min_value is not None else None
        max_v = int(param.max_value) if param.max_value is not None else None
        if min_v is not None and max_v is not None and max_v - min_v >= 2:
            low, high = min_v + 1, max_v - 1
            if exclude_value is not None and low <= exclude_value <= high and (high - low) >= 1:
                n = high - low + 1
                k = random.randint(0, n - 2)
                test_value = low + k
                if test_value >= exclude_value:
                    test_value += 1
                return test_value
            return random.randint(low, high)
        if min_v is not None and max_v is not None:
            return min_v if exclude_value != min_v else max_v
        return (exclude_value + 1) if isinstance(exclude_value, (int, float)) else 1

    # 2. float (Дробное число)
    elif dt_id == 2:
        min_v = float(param.min_value) if param.min_value is not None else 0.0
        max_v = float(param.max_value) if param.max_value is not None else 100.0
        # Генерируем случайное число в диапазоне, отличное от текущего
        val = random.uniform(min_v, max_v)
        if exclude_value is not None and abs(val - exclude_value) < 0.001:
            val = (val + 1.0) if val + 1.0 <= max_v else (val - 1.0)
        return round(val, 2)

    # 3. string (Строковое значение)
    elif dt_id == 3:
        # Если есть пример значения и он отличается от текущего - берем его
        if hasattr(param, 'example_value') and param.example_value and param.example_value != exclude_value:
            return param.example_value
        # Иначе генерируем случайную строку
        chars = string.ascii_letters + string.digits
        new_val = ''.join(random.choice(chars) for _ in range(8))
        return f"test_{new_val}"

    # 4. bool (Булево значение)
    elif dt_id == 4:
        return not exclude_value if exclude_value is not None else True

    # 5. enum (Список значений)
    elif dt_id == 5:
        allowed = json.loads(param.allowed_values) if param.allowed_values else []
        candidates = [v for v in allowed if v != exclude_value]
        return random.choice(candidates) if candidates else exclude_value

    # 6. json (JSON объект)
    elif dt_id == 6:
        if hasattr(param, 'example_value') and param.example_value:
            try:
                return json.loads(param.example_value)
            except:
                pass
        return exclude_value if exclude_value is not None else {}

    # 7. array (Массив)
    elif dt_id == 7:
        if hasattr(param, 'example_value') and param.example_value:
            try:
                return json.loads(param.example_value)
            except:
                pass
        return exclude_value if exclude_value is not None else []
    
    elif dt_id == 12:
        '''Временная заглушка до обработки этого типа данных'''
        
        exclude_value = '{"s8CngMode":1,"s8NearAllPassEnergy":1,"s8NearCleanSupEnergy":1,"s16DTHnlSortQTh":16384,"s16EchoBandLow":10,"s16EchoBandHigh":41,"s16EchoBandLow2":47,"s16EchoBandHigh2":63,"s16ERLBand":[4,6,36,49,50,51],"s16ERL":[7,10,16,10,18,18,18],"s16VioceProtectFreqL":3,"s16VioceProtectFreqL1":6}'
        return exclude_value if exclude_value is not None else {}

    return exclude_value


def generate_correct_value(db, api_client, firmware_version, param_uuid):    return exclude_value


def generate_correct_value(db, api_client, firmware_version, param_uuid):
    fw_model = get_firmware_by_version(db, firmware_version)
    param_from_db = get_parameter(db, param_uuid, fw_model.id)
    assert param_from_db is not None, f"Параметр {param_uuid} не найден для прошивки {firmware_version}"
    
    actual_value = api_client.get_parameter(db, param_uuid, firmware_version)
    return _generate_test_value(param_from_db, actual_value)


def generate_correct_api_method_params(db, method_params, api_client, firmware_version_id, method_name):
    """ Получает для метода параметры, считывает актуальное значение и генерирует новое, не совпадающее с текущим
        и не попадающее на границы (границы будут проверяться отдельным тестом) """
    
    method_info = get_method_info(db, method_name, firmware_version_id)
    if method_info is None:
        raise ValueError(f"Метод {method_name} не найден в БД для прошивки с ID {firmware_version_id}")

    if not method_info.control_method_name:
        if not method_params:
            return {}
        raise ValueError(f"Для метода {method_name} не указан control_method_name в БД")

    actual_values = api_client.running_method(db, method_info.control_method_name, firmware_version_id).json()
    test_values = {}

    for parameter in method_params:
        # Извлекаем текущее значение по JSONPath
        matches = [m.value for m in parse(parameter.json_path).find(actual_values)]
        exclude = matches[0] if matches else None
        
        # Генерируем новое значение
        test_value = _generate_test_value(parameter, exclude)
        
        # Устанавливаем в результирующий словарь
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