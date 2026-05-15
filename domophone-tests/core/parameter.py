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
from jsonpath_ng.ext import parse
from typing import Any, List

def _generate_test_value(param, exclude_values=None):
    """
    Универсальный генератор корректного значения для любого типа данных.
    Гарантирует несовпадение с exclude_values и соблюдение границ.
    """

    # 1. Нормализуем исключения в set для быстрого поиска O(1)
    if exclude_values is None:
        exclude_set = set()
    elif isinstance(exclude_values, (list, tuple, set)):
        exclude_set = set(exclude_values)
    else:
        exclude_set = {exclude_values}

    dt_id = param.data_type_id
    
    # 1. int (Целое число)
    if dt_id == 1:

        min_v = int(param.min_value) if param.min_value is not None else None
        max_v = int(param.max_value) if param.max_value is not None else None

        if min_v is None or max_v is None:
            print(f'В БД нет данных мин и макс для параметра {param.uuid}')
            raise RuntimeError(f"Отсутствуют данные min/max для параметра {param.uuid}")

        if min_v is not None and max_v is not None and max_v - min_v >= 1:

            # Для небольших диапазонов: собираем всех кандидатов и выбираем случайно
            if max_v - min_v <= 1100:
                candidates = [v for v in range(min_v, max_v + 1) if v not in exclude_set]
                if candidates:
                    return random.choice(candidates)
            else:
                # Для больших диапазонов: rejection sampling с ограничением попыток
                for _ in range(100):
                    val = random.randint(min_v, max_v)
                    if val not in exclude_set:
                        return val

            return min_v  # Fallback, если всё исключено

         return min_v  # Fallback, если всё исключено

    # 2. float (Дробное число)
    elif dt_id == 2:
        min_v = float(param.min_value) if param.min_value is not None else None
        max_v = float(param.max_value) if param.max_value is not None else None

        if min_v is None or max_v is None:
            print(f'В БД нет данных мин и макс для параметра {param.uuid}')
            raise RuntimeError(f"Отсутствуют данные min/max для параметра {param.uuid}")

        # Генерируем случайное число в диапазоне, отличное от текущего
        for _ in range(50):  # Ограничиваем попытки, чтобы не уйти в бесконечный цикл
            val = round(random.uniform(min_v, max_v), 2)
            if val not in exclude_set:
                return val
        return round(min_v, 2)

    # 3. string (Строковое значение)
    elif dt_id == 3:
        '''Временное решение для генерации новой строки'''
        # Если есть пример значения и он отличается от текущего - берем его
        example = getattr(param, 'example_value', None)
        if example and example not in exclude_set:
            return example
        # Иначе генерируем случайную строку
        for _ in range(20):
            new_val = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
            cand = f"test_{new_val}"
            if cand not in exclude_set:
                return cand
        return "test_fallback_000"

    # 4. bool (Булево значение)
    elif dt_id == 4:
        if True not in exclude_set:
            return True
        if False not in exclude_set:
            return False
        return True  # Fallback


    # 5. enum (Список значений)
    elif dt_id == 5:
        # Поддержка как JSON-массива, так и CSV-строки
        allowed = []
        if param.allowed_values:
            try:
                allowed = json.loads(param.allowed_values)
            except json.JSONDecodeError:
                allowed = [v.strip() for v in param.allowed_values.split(',') if v.strip()]
        
        # Сравниваем как строки, чтобы избежать проблем с типами (int 3 vs str "3")
        exclude_strs = {str(v) for v in exclude_set}
        candidates = [v for v in allowed if str(v) not in exclude_strs]
        
        return random.choice(candidates) if candidates else (allowed[0] if allowed else None)


    # 6. json / 7. array (Сложные структуры)
    elif dt_id in (6, 7):
        example = getattr(param, 'example_value', None)
        if example:
            try:
                return json.loads(example)
            except json.JSONDecodeError:
                pass
        return {} if dt_id == 6 else []
    
    elif dt_id == 12:
        '''Временная заглушка до обработки этого типа данных'''
        
       
        return '{"s8CngMode":1,"s8NearAllPassEnergy":1,"s8NearCleanSupEnergy":1,"s16DTHnlSortQTh":16384,"s16EchoBandLow":10,"s16EchoBandHigh":41,"s16EchoBandLow2":47,"s16EchoBandHigh2":63,"s16ERLBand":[4,6,36,49,50,51],"s16ERL":[7,10,16,10,18,18,18],"s16VioceProtectFreqL":3,"s16VioceProtectFreqL1":6}'

    return None

def type_conversion_from_api_to_config(exclude, rule_type, parameter_rules_convertations_api):
    # Перевод значения из апи для поиска по значениям конфигурации
    try:
        rule_type = rule_type.upper() if rule_type else ""
        print (rule_type)
        
        if rule_type == "MAP":
            print (rule_type)
            mapping = parameter_rules_convertations_api.get("mapping", {})
            print (mapping)
            #reverse_mapping = {v: k for k, v in mapping.items()}

            print(f"правила из апи - {mapping}  значение -  {exclude} результат - {mapping.get(exclude)}")
            return mapping.get(exclude)
        
        elif rule_type == "FORMAT":
            #  реализовать позже
            return exclude
        
        elif rule_type == "FORMULA":
            #  реализовать позже
            return exclude
        
        else:
            return exclude
    

    except Exception as e:
        #logger.error(f"Ошибка конвертации: {e}, rule_type={rule_type}, value={exclude}")
        # на будущее сделать единое логирование
        return exclude  # Возвращаем как есть при ошибке

def type_conversion_from_config_to_api(value, rule_type, parameter_rules_convertations_api):
    # Перевод значения из апи для поиска по значениям конфигурации
    try:
        rule_type = rule_type.upper() if rule_type else ""
        #print (f' итог {rule_type}')
        
        if rule_type == "MAP":
            mapping = parameter_rules_convertations_api.get("mapping", {})
            reverse_mapping = {v: k for k, v in mapping.items()}
            print(f" итог MAP: {type(mapping)}, {value}, {reverse_mapping.get(str(value))}")
            return reverse_mapping.get(str(value))
        
        elif rule_type == "FORMAT":
            #  реализовать позже
            return value
        
        elif rule_type == "FORMULA":
            #  реализовать позже
            return value
        
        else:
            #print('problem')
            return value
    

    except Exception as e:
        #logger.error(f"Ошибка конвертации: {e}, rule_type={rule_type}, value={exclude}")
        # на будущее сделать единое логирование
        #print(e, 'ex')
        return value  # Возвращаем как есть при ошибке

def generate_correct_value(db, api_client, firmware_version, param_uuid):    return exclude_value


def generate_correct_value(db, api_client, firmware_version, param_uuid):
    fw_model = get_firmware_by_version(db, firmware_version)
    param_from_db = get_parameter(db, param_uuid, fw_model.id)
    assert param_from_db is not None, f"Параметр {param_uuid} не найден для прошивки {firmware_version}"
    
    actual_value = api_client.get_parameter(db, param_uuid, firmware_version)
    return _generate_test_value(param_from_db, actual_value)


def generate_correct_api_method_params(db, method_params, api_client, firmware_version_id, method_name):
    """ Получает для метода параметры, считывает актуальное значение и генерирует новое, не совпадающее 
        с текущим"""
    
    method_info = get_method_info(db, method_name, firmware_version_id)
    if method_info is None:
        raise ValueError(f"Метод {method_name} не найден в БД для прошивки с ID {firmware_version_id}")

    if not method_info.control_method_name:
        if not method_params:
            return {}
        raise ValueError(f"Для метода {method_name} не указан control_method_name в БД")

    actual_values = api_client.running_method(db, method_info.control_method_name, firmware_version_id).json()
    test_values = {}
    print('actual_values - ', actual_values)

    for parameter in method_params:
        
        print(f"анализ параметра {parameter.json_path}")

        if parameter.gen_rule == 1:

            # Извлекаем текущее значение по JSONPath
            json_path = escape_json_path_key(parameter.json_path)
            print(json_path, type(json_path))
            print(type(json_path))
            print([m.value for m in parse(f'$.{json_path}').find(actual_values)])
            matches = [m.value for m in parse(json_path).find(actual_values)]
            exclude = matches[0] if matches else None

            # Получаем правила конвертации параметра и переводим значение из апи в конфиг
            parameter_rules_convertations_api = parameter.rule_payload if parameter.rule_payload else None
            print(f'для параметра {parameter.json_path} правила {parameter_rules_convertations_api}')
            
            if parameter_rules_convertations_api:
                
                parameter_rules_convertations_api = json.loads(parameter_rules_convertations_api)
                #parameter_rules_convertations_api = parameter_rules_convertations_api['mapping']
                
                #print(parameter_rules_convertations_api, type(parameter_rules_convertations_api))
                rule_type = parameter.rule_type
                exclude = type_conversion_from_api_to_config(exclude, rule_type, parameter_rules_convertations_api)

            # Генерируем новое значение
            test_value = _generate_test_value(parameter, exclude)

            # Переводим значение из конфига в апи
            if parameter_rules_convertations_api:
                
                test_value = type_conversion_from_config_to_api(test_value, rule_type, parameter_rules_convertations_api)
            #print(f' готовое значение = {test_value}')
            # Устанавливаем в результирующий словарь
            _set_by_path(test_values, parameter.json_path, test_value)
        if parameter.gen_rule == 2:
            # заглушка для типа 2
            _set_by_path(test_values, parameter.json_path, 'channel2')
        if parameter.gen_rule == 3:
            if test_values.get('aspect_ratio_4:3') is True:
                resolution_map = {
                "640x480": "3",
                "704x576": "8",
                "720x480": "4", "352x288": "1",
                "1920x1440": "12", "1280x960": "11"
                }
            else:
                resolution_map = {
                "1920x1080": "7", "1280x720": "6",
                "768x432": "10", "704x576": "8",
                "720x480": "4", "352x288": "1", "640x360": "2",
                "2560x1440": "9"
                }
            # 3. random.choice() выбирает случайный элемент из последовательности
            test_value = random.choice(list(resolution_map.keys()))
        
            _set_by_path(test_values, parameter.json_path, test_value)

        if parameter.gen_rule == 4:
            if test_values.get('aspect_ratio_4:3') is True:
                resolution_map = {
                "640x480": "3",
                "704x576": "8",
                "720x480": "4", "352x288": "1"
                }
            else:
                resolution_map = {
                "1280x720": "6",
                "704x576": "8",
                "720x480": "4", "352x288": "1", "640x360": "2"
                }
            # 3. random.choice() выбирает случайный элемент из последовательности
            test_value = random.choice(list(resolution_map.keys()))
        
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

def escape_json_path_key(path: str) -> str:
    """Автоматически экранирует ключи со спецсимволами в JSONPath."""
    if not path.startswith('$'):
        path = '$.' + path
    
    # Если путь уже в bracket-нотации, возвращаем как есть
    #if '[' in path:
    #    return path
        
    segments = path[1:].split('.')
    parts = ['$']
    
    for seg in segments:
        if not seg:
            continue
        # Безопасные для dot-notation: начинаются с буквы/_, содержат только a-z, A-Z, 0-9, _
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', seg):
            parts.append(f'.{seg}')
        else:
            parts.append(f"['{seg}']")
            
    return ''.join(parts)
