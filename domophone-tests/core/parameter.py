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
from loguru import logger
from .db import DBRepository
from .models import DataTypeEnum
from jsonpath_ng.ext import parse
from typing import Any, List

class ParameterGenerator:
    def __init__(self, db: DBRepository):
        self.db = db

    def generate_test_value(self, param, exclude_values=None):
        """Универсальный генератор корректного значения для любого типа данных."""
        if exclude_values is None:
            exclude_set = set()
        elif isinstance(exclude_values, (list, tuple, set)):
            exclude_set = set(exclude_values)
        else:
            exclude_set = {exclude_values}

        dt_id = param.data_type_id
        
        if dt_id == DataTypeEnum.INT:
            return self._generate_int(param, exclude_set)
        elif dt_id == DataTypeEnum.FLOAT:
            return self._generate_float(param, exclude_set)
        elif dt_id == DataTypeEnum.STRING:
            return self._generate_string(param, exclude_set)
        elif dt_id == DataTypeEnum.BOOL:
            return not list(exclude_set)[0] if exclude_set else True
        elif dt_id == DataTypeEnum.ENUM:
            return self._generate_enum(param, exclude_set)
        elif dt_id in (6, 7):
            return self._generate_complex(param, dt_id)
        elif dt_id == 12:
            return '{"s8CngMode":1,"s8NearAllPassEnergy":1,"s8NearCleanSupEnergy":1,"s16DTHnlSortQTh":16384,"s16EchoBandLow":10,"s16EchoBandHigh":41,"s16EchoBandLow2":47,"s16EchoBandHigh2":63,"s16ERLBand":[4,6,36,49,50,51],"s16ERL":[7,10,16,10,18,18,18],"s16VioceProtectFreqL":3,"s16VioceProtectFreqL1":6}'
        return None

    def _generate_int(self, param, exclude_set):
        min_v = int(param.min_value) if param.min_value is not None else 0
        max_v = int(param.max_value) if param.max_value is not None else 100
        
        if max_v - min_v >= 1:
            if max_v - min_v <= 1100:
                candidates = [v for v in range(min_v, max_v + 1) if v not in exclude_set]
                if candidates:
                    return random.choice(candidates)
            else:
                for _ in range(100):
                    val = random.randint(min_v, max_v)
                    if val not in exclude_set:
                        return val
        return min_v

    def _generate_float(self, param, exclude_set):
        min_v = float(param.min_value) if param.min_value is not None else 0.0
        max_v = float(param.max_value) if param.max_value is not None else 1.0
        for _ in range(50):
            val = round(random.uniform(min_v, max_v), 2)
            if val not in exclude_set:
                return val
        return round(min_v, 2)

    def _generate_string(self, param, exclude_set):
        example = getattr(param, 'example_value', None)
        if example and example not in exclude_set:
            return example
        for _ in range(20):
            new_val = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8))
            cand = f"test_{new_val}"
            if cand not in exclude_set:
                return cand
        return "test_fallback_000"

    def _generate_enum(self, param, exclude_set):
        allowed = []
        if param.allowed_values:
            try:
                allowed = json.loads(param.allowed_values)
            except json.JSONDecodeError:
                allowed = [v.strip() for v in param.allowed_values.split(',') if v.strip()]
        
        exclude_strs = {str(v) for v in exclude_set}
        candidates = [v for v in allowed if str(v) not in exclude_strs]
        return random.choice(candidates) if candidates else (allowed[0] if allowed else None)

    def _generate_complex(self, param, dt_id):
        """Обработка сложных структур (json/array)."""
        example = getattr(param, 'example_value', None)
        if example:
            try:
                return json.loads(example)
            except json.JSONDecodeError:
                pass
        return {} if dt_id == 6 else []

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

def generate_correct_value(db: DBRepository, api_client, firmware_version, param_uuid):
    fw_model = db.firmware.get_by_version(firmware_version)
    param_from_db = db.parameters.get(param_uuid, fw_model.id)
    assert param_from_db is not None, f"Параметр {param_uuid} не найден"
    
    actual_value = api_client.get_parameter(db, param_uuid, firmware_version)
    gen = ParameterGenerator(db)
    return gen.generate_test_value(param_from_db, actual_value)


def generate_correct_api_method_params(db: DBRepository, method_params, api_client, firmware_version_id, method_name):
    """ Получает для метода параметры, считывает актуальное значение и генерирует новое, не совпадающее 
        с текущим"""
    
    method_info = db.api.get_method(method_name, firmware_version_id)
    if method_info is None:
        raise ValueError(f"Метод {method_name} не найден в БД для прошивки с ID {firmware_version_id}")

    if not method_info.control_method_name:
        if not method_params:
            return {}
        raise ValueError(f"Для метода {method_name} не указан control_method_name в БД")

    actual_values = api_client.running_method(db, method_info.control_method_name, firmware_version_id).json()
    test_values = {}
    
    gen = ParameterGenerator(db)

    for parameter in method_params:
        if parameter.gen_rule == 1:
            # Извлекаем текущее значение по JSONPath
            json_path = escape_json_path_key(parameter.json_path)
            matches = [m.value for m in parse(json_path).find(actual_values)]
            exclude = matches[0] if matches else None

            # Получаем правила конвертации
            parameter_rules_convertations_api = parameter.rule_payload if parameter.rule_payload else None
            if parameter_rules_convertations_api:
                parameter_rules_convertations_api = json.loads(parameter_rules_convertations_api)
                rule_type = parameter.rule_type
                exclude = type_conversion_from_api_to_config(exclude, rule_type, parameter_rules_convertations_api)

            # Генерируем новое значение
            # Находим параметр в БД для получения его метаданных
            param_meta = db.parameters.get(parameter.param_uuid, firmware_version_id)
            if not param_meta:
                logger.warning(f"Метаданные для параметра {parameter.param_uuid} не найдены")
                continue

            test_value = gen.generate_test_value(param_meta, exclude)

            # Переводим обратно для API
            if parameter_rules_convertations_api:
                test_value = type_conversion_from_config_to_api(test_value, rule_type, parameter_rules_convertations_api)
            
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
