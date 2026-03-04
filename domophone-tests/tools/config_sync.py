import argparse
import argparse
import json
import yaml
import sys
import os
from datetime import datetime

# Добавляем путь к проекту, чтобы можно было импортировать core и services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_db_connection, get_parameter, get_firmware_by_version

def traverse_config(data, path=''):
    """Рекурсивно обходит словарь и генерирует (json_path, value)."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ['version', 'mac', 'ip', 'time'] and not path:
                continue
            
            new_path = f'{path}.{key}' if path else key
            yield from traverse_config(value, new_path)
    elif isinstance(data, list):
        if data and all(isinstance(x, (int, str, bool, float)) for x in data):
            yield path, data
        else:
            for i, value in enumerate(data):
                new_path = f'{path}[{i}]'
                yield from traverse_config(value, new_path)
    else:
        yield path, data

def get_type_id_from_value(value):
    if isinstance(value, bool): return 4
    if isinstance(value, int): return 1
    if isinstance(value, float): return 2
    if isinstance(value, str): return 3
    if isinstance(value, list): return 7
    if isinstance(value, dict): return 6
    return 3 # По умолчанию - строка

def sync_config(config_path, firmware_version=None, db_path="domophone-tests/resources/domophone.db", interactive=True):
    """Основная логика синхронизации."""
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f) if config_path.endswith('.json') or config_path.endswith('.dat') else yaml.safe_load(f)

    # Если версия прошивки не передана, пытаемся извлечь из конфига
    if not firmware_version:
        # Пытаемся найти в разных ключах (version, deviceVersion)
        firmware_version = config_data.get('version') or config_data.get('deviceVersion')
        if not firmware_version:
            print("Ошибка: не удалось определить версию прошивки ни из аргументов, ни из файла.")
            return

    with get_db_connection(db_path) as conn:
        fw = get_firmware_by_version(conn, firmware_version)
        if not fw:
            print(f"Ошибка: прошивка {firmware_version} не найдена в БД.")
            return
        
        print(f"Синхронизация для прошивки: {fw.version} (ID: {fw.id})")

        # Если есть ключ 'settings', начинаем обход с него, чтобы json_path был короче
        root_data = config_data.get('settings', config_data)
        root_path = 'settings' if 'settings' in config_data else ''

        try:
            for json_path, value in traverse_config(root_data, root_path):
                # Ищем параметр по его пути в конфиге (location)
                cursor = conn.execute("SELECT * FROM config_parameters WHERE location = ? AND firmware_version_id = ?", (json_path, fw.id))
                param = cursor.fetchone()

                if param:
                    # print(f"[OK] Параметр {json_path} уже существует.")
                    continue
                
                # Ищем параметр в старых прошивках, чтобы скопировать атрибуты
                cursor = conn.execute("SELECT * FROM config_parameters WHERE location = ? ORDER BY firmware_version_id DESC LIMIT 1", (json_path,))
                latest_param_row = cursor.fetchone()
                
                if latest_param_row:
                    print(f"[КОПИРОВАНИЕ] Найден аналог для {json_path}. Создание записи для новой прошивки...")
                    new_param_data = dict(latest_param_row)
                    new_param_data['firmware_version_id'] = fw.id
                    new_param_data['default_value'] = str(value)
                    new_param_data['created_at'] = new_param_data['updated_at'] = datetime.utcnow().isoformat()
                    
                    columns = ", ".join(new_param_data.keys())
                    placeholders = ", ".join(["?" for _ in new_param_data])
                    conn.execute(f"INSERT INTO config_parameters ({columns}) VALUES ({placeholders})", list(new_param_data.values()))
                    print(f"  -> Успешно скопировано.")
                else:
                    print(f"[НОВЫЙ] Обнаружен новый параметр: {json_path} со значением '{value}'")
                    if interactive:
                        action = input("  -> Добавить(y)/Пропустить(n)/Выйти(exit)?: ").lower()
                        if action == 'y':
                            name = input("    -> Введите человекочитаемое имя: ")
                            data_type_id = get_type_id_from_value(value)
                            print(f"    -> Тип данных определен как: {data_type_id}")
                            
                            min_v = max_v = allowed_v = None
                            if data_type_id in (1, 2): # int, float
                                min_v = input(f"    -> Минимум (Enter для пропуска): ")
                                max_v = input(f"    -> Максимум (Enter для пропуска): ")
                            elif data_type_id == 5: # enum
                                allowed_v = input(f"    -> Список значений (JSON, например [\"a\",\"b\"]): ")
                            
                            param_uuid = input(f"    -> Введите логическое имя (param_uuid, Enter, чтобы использовать {json_path}): ") or json_path
                            location = json_path
                            
                            new_param_data = {
                                'param_uuid': param_uuid,
                                'firmware_version_id': fw.id,
                                'name': name,
                                'location': location,
                                'data_type_id': data_type_id,
                                'default_value': str(value),
                                'min_value': float(min_v) if min_v else None,
                                'max_value': float(max_v) if max_v else None,
                                'allowed_values': allowed_v if allowed_v else None,
                                'created_at': datetime.utcnow().isoformat(),
                                'updated_at': datetime.utcnow().isoformat()
                            }
                            columns = ", ".join(new_param_data.keys())
                            placeholders = ", ".join(["?" for _ in new_param_data])
                            conn.execute(f"INSERT INTO config_parameters ({columns}) VALUES ({placeholders})", list(new_param_data.values()))
                            print(f"  -> Параметр {json_path} добавлен.")
                        elif action == 'exit':
                            print("Выход из цикла добавления...")
                            break
                        else:
                            print("  -> Пропущено пользователем.")
                    else:
                        print("  -> Пропущено (неинтерактивный режим).")
        except KeyboardInterrupt:
            print("\nПрервано пользователем. Сохранение внесенных изменений...")
        finally:
            conn.commit()
            print("Синхронизация завершена.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Синхронизация конфигурационного файла с БД параметров.")
    parser.add_argument("config_file", help="Путь к файлу конфигурации (JSON или YAML).")
    parser.add_argument("-fw", "--firmware_version", help="Версия прошивки (если не указана, будет взята из файла).", default=None)
    parser.add_argument("--db-path", default="domophone-tests/resources/domophone.db", help="Путь к файлу БД.")
    parser.add_argument("--non-interactive", action="store_true", help="Отключить интерактивный режим.")
    
    args = parser.parse_args()
    
    sync_config(args.config_file, args.firmware_version, args.db_path, not args.non_interactive)
