import sqlite3
import argparse
import sys
import os
import json
from datetime import datetime

# Добавляем путь к проекту, чтобы можно было импортировать core и services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import DBRepository

def get_fw_id(db: DBRepository, version):
    fw = db.firmware.get_by_version(version)
    if not fw:
        print(f"Ошибка: прошивка {version} не найдена.")
        return None
    return fw.id

def search_config_params(db: DBRepository, fw_id, query):
    """Поиск параметров в config_parameters по части имени или пути."""
    cursor = db.connection.execute("""
        SELECT param_uuid, name, location 
        FROM config_parameters 
        WHERE (param_uuid LIKE ? OR name LIKE ? OR location LIKE ?) 
        AND firmware_version_id = ?
        LIMIT 10
    """, (f'%{query}%', f'%{query}%', f'%{query}%', fw_id))
    return cursor.fetchall()

def add_api_method(conn, fw_id, name=None, http_method=None, url=None):
    print("\n--- Добавление нового API-метода ---")
    
    # Очистка имени по умолчанию (берем только последнюю часть пути в коллекции)
    if name and " / " in name:
        name = name.split(" / ")[-1]
        
    # Очистка URL по умолчанию (убираем http://{{...}} и оставляем /api/...)
    if url:
        if '{{' in url and '/api/' in url:
            url = '/api/' + url.split('/api/')[1]
        elif not url.startswith('/'):
            # Если нет протокола, но есть путь
            if '/api/' in url:
                url = '/api/' + url.split('/api/')[1]

    name = input(f"Введите имя метода (по умолчанию '{name}'): ") or name if name else input("Введите имя метода: ")
    http_method = input(f"Введите HTTP метод (по умолчанию '{http_method}'): ").upper() or http_method if http_method else input("Введите HTTP метод (GET, POST, PUT, PATCH): ").upper() or "POST"
    url = input(f"Введите URL метода (по умолчанию '{url}'): ") or url if url else input("Введите URL метода (например, '/api/v1/settings/audio/sip'): ")
    pos_status = input("Введите ожидаемый статус успеха (по умолчанию 200): ") or "200"
    control_method = input("Введите имя контрольного метода (для сверки результата), если есть: ")

    # ПРОВЕРКА НА ДУБЛИКАТЫ
    check = db.connection.execute("""
        SELECT id FROM api_methods 
        WHERE method_name = ? AND http_method = ? AND firmware_version_id = ?
    """, (name, http_method, fw_id)).fetchone()
    
    if check:
        print(f"  [!] ОШИБКА: Метод '{name}' [{http_method}] уже существует для этой прошивки (ID: {check[0]}).")
        return check[0], name

    cursor = db.connection.execute("""
        INSERT INTO api_methods (method_name, http_method, firmware_version_id, method_url, positive_status, control_method_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, http_method, fw_id, url, int(pos_status), control_method or None))
    
    method_id = cursor.lastrowid
    print(f"Метод добавлен с ID: {method_id}")
    return method_id, name

def add_param_to_method(db: DBRepository, method_id, fw_id, method_name):
    print(f"\n--- Добавление параметров для метода '{method_name}' ---")
    while True:
        param_uuid = input("\nВведите param_uuid (логическое имя параметра) или часть имени для поиска (или 'exit' для выхода): ")
        if param_uuid.lower() == 'exit':
            break

        # Проверяем точное совпадение
        cursor = db.connection.execute("SELECT name, location FROM config_parameters WHERE param_uuid = ? AND firmware_version_id = ?", (param_uuid, fw_id))
        config_param = cursor.fetchone()
        
        if not config_param:
            # Если не найдено, ищем похожие
            results = search_config_params(conn, fw_id, param_uuid)
            if results:
                print("\nНайдено несколько совпадений:")
                for i, r in enumerate(results):
                    print(f"  {i+1}. {r[0]} ({r[1]}) - {r[2]}")
                choice = input("\nВыберите номер (или Enter для ручного ввода): ")
                if choice.isdigit() and 1 <= int(choice) <= len(results):
                    param_uuid = results[int(choice)-1][0]
                    config_param = (results[int(choice)-1][1], results[int(choice)-1][2])
            
        if config_param:
            print(f"  -> Выбран параметр конфигурации: {config_param[0]} (путь: {config_param[1]})")
            json_path = input(f"  -> Введите JSONPath в ответе/запросе API (Enter для '{config_param[1]}'): ") or config_param[1]
        else:
            print("  -> Внимание: Параметр не найден в таблице config_parameters!")
            json_path = input("  -> Введите JSONPath для этого параметра: ")
            if not json_path:
                print("  -> Ошибка: JSONPath обязателен.")
                continue

        is_req = input("  -> Параметр обязателен? (y/n, по умолчанию y): ").lower() != 'n'
        in_req = input("  -> Передавать в запросе? (y/n, по умолчанию y): ").lower() != 'n'
        example = input("  -> Пример значения (необязательно): ")

        conn.execute("""
            INSERT INTO api_method_params (method_id, param_uuid, firmware_version_id, json_path, is_required, in_request, example_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (method_id, param_uuid, fw_id, json_path, 1 if is_req else 0, 1 if in_req else 0, example or None))
        print(f"  -> Параметр {param_uuid} привязан к методу.")

def traverse_json(data, path=''):
    """Рекурсивно обходит JSON и генерирует paths."""
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f'{path}.{key}' if path else key
            yield from traverse_json(value, new_path)
    elif isinstance(data, list):
        if data and all(isinstance(x, (int, str, bool, float)) for x in data):
            yield path, data
        else:
            for i, value in enumerate(data):
                new_path = f'{path}[{i}]'
                yield from traverse_json(value, new_path)
    else:
        yield path, data

def map_json_to_api_params(conn, method_id, fw_id, sample_json_str):
    """Интерактивное сопоставление JSON с параметрами конфигурации."""
    try:
        data = json.loads(sample_json_str)
    except Exception as e:
        print(f"Ошибка парсинга JSON: {e}")
        return

    print("\n--- Анализ JSON и привязка параметров ---")
    for json_path, value in traverse_json(data):
        print(f"\nОбнаружен путь в JSON: {json_path} (значение: {value})")
        
        # Пытаемся найти соответствие в БД
        # 1. По точному совпадению пути (location)
        cursor = conn.execute("SELECT param_uuid, name FROM config_parameters WHERE location = ? AND firmware_version_id = ?", (json_path, fw_id))
        match = cursor.fetchone()
        
        if not match:
            # 2. По совпадению с settings.path
            cursor = conn.execute("SELECT param_uuid, name FROM config_parameters WHERE location = ? AND firmware_version_id = ?", (f"settings.{json_path}", fw_id))
            match = cursor.fetchone()
            
        if not match:
            # 3. УМНОЕ СОПОСТАВЛЕНИЕ: поиск параметра, путь которого заканчивается на этот ключ (например volume -> settings.system_audio.volume)
            cursor = conn.execute("""
                SELECT param_uuid, name, location FROM config_parameters 
                WHERE (location LIKE ? OR param_uuid LIKE ?) AND firmware_version_id = ?
            """, (f'%.{json_path}', f'%.{json_path}', fw_id))
            match = cursor.fetchone()

        if match:
            print(f"  [АВТО] Найдено совпадение: {match[0]} ({match[1]})")
            if len(match) > 2: # Если это результат умного поиска
                 print(f"         Путь в БД: {match[2]}")
            action = input("  Привязать этот параметр? (y/n/skip/exit, по умолчанию y): ").lower() or 'y'
        else:
            print("  [!] Соответствие в конфигурации не найдено.")
            action = input("  Найти вручную (f) / Ввести param_uuid вручную (m) / Пропустить (s) / Выход (exit): ").lower()

        if action == 'y':
            param_uuid = match[0]
        elif action == 'f':
            query = input("    Введите часть имени или пути для поиска: ")
            results = search_config_params(conn, fw_id, query)
            if results:
                print("\n    Результаты поиска:")
                for i, r in enumerate(results):
                    print(f"      {i+1}. {r[0]} ({r[1]}) - {r[2]}")
                choice = input("\n    Выберите номер: ")
                if choice.isdigit() and 1 <= int(choice) <= len(results):
                    param_uuid = results[int(choice)-1][0]
                else:
                    print("    Пропущено.")
                    continue
            else:
                print("    Ничего не найдено.")
                continue
        elif action == 'm':
            param_uuid = input("    Введите param_uuid: ")
        elif action in ('exit', 'e'):
            break
        else:
            continue

        is_req = input("  -> Параметр обязателен? (y/n, по умолчанию y): ").lower() != 'n'
        in_req = input("  -> Передавать в запросе? (y/n, по умолчанию y): ").lower() != 'n'
        
        conn.execute("""
            INSERT INTO api_method_params (method_id, param_uuid, firmware_version_id, json_path, is_required, in_request, example_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (method_id, param_uuid, fw_id, json_path, 1 if is_req else 0, 1 if in_req else 0, str(value)))
        print(f"  -> Параметр {param_uuid} привязан.")

def extract_methods_from_postman(items, parent_name=''):
    """Рекурсивно извлекает все запросы из Postman-коллекции."""
    methods = []
    for item in items:
        name = f"{parent_name} / {item['name']}" if parent_name else item['name']
        if 'item' in item:
            methods.extend(extract_methods_from_postman(item['item'], name))
        elif 'request' in item:
            req = item['request']
            url = req['url']['raw'] if isinstance(req['url'], dict) else req['url']
            methods.append({
                'name': name,
                'method': req['method'],
                'url': url,
                'body': req.get('body', {}).get('raw', '')
            })
    return methods

def add_methods_from_postman(conn, fw_id, collection_path):
    """Интерактивное добавление методов из Postman-коллекции."""
    try:
        with open(collection_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения коллекции: {e}")
        return

    all_methods = extract_methods_from_postman(data.get('item', []))
    print(f"\nНайдено {len(all_methods)} методов в коллекции.")

    while True:
        query = input("\nВведите часть имени метода для поиска в коллекции (или 'exit' для выхода): ")
        if query.lower() == 'exit':
            break

        matches = [m for m in all_methods if query.lower() in m['name'].lower() or query.lower() in m['url'].lower()]
        if not matches:
            print("Методы не найдены.")
            continue

        print("\nНайденные методы:")
        for i, m in enumerate(matches[:20]): # Ограничим вывод
            print(f"  {i+1}. [{m['method']}] {m['name']} ({m['url']})")
        
        choice = input("\nВыберите номер для добавления (или Enter для нового поиска): ")
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            m = matches[int(choice)-1]
            method_id, method_name = add_api_method(conn, fw_id, m['name'], m['method'], m['url'])
            
            print("\n  1. Добавить параметры вручную")
            print("  2. Добавить параметры из Body запроса (Postman)")
            print("  3. Добавить параметры из JSON-образца (вставить вручную)")
            print("  4. Пропустить добавление параметров")
            
            subchoice = input("  Выберите действие: ")
            if subchoice == '1':
                add_param_to_method(conn, method_id, fw_id, method_name)
            elif subchoice == '2':
                if m['body']:
                    map_json_to_api_params(conn, method_id, fw_id, m['body'])
                else:
                    print("  [!] У этого метода нет Body в коллекции.")
            elif subchoice == '3':
                print("\nВставьте JSON и завершите ввод (Ctrl+D/Ctrl+Z):")
                sample_json = sys.stdin.read()
                if sample_json.strip():
                    map_json_to_api_params(conn, method_id, fw_id, sample_json)
            
            conn.commit()
            print(f"\nМетод '{method_name}' и его параметры сохранены.")

def copy_api_methods(conn, source_fw_id, target_fw_id):
    print(f"\n--- Копирование API-методов из FW ID {source_fw_id} в FW ID {target_fw_id} ---")
    
    # 1. Получаем все методы из исходной прошивки
    cursor = conn.execute("SELECT * FROM api_methods WHERE firmware_version_id = ?", (source_fw_id,))
    methods = cursor.fetchall()
    
    for method in methods:
        method_dict = dict(zip([c[0] for c in cursor.description], method))
        old_method_id = method_dict.pop('id')
        method_dict['firmware_version_id'] = target_fw_id
        
        # Проверяем, нет ли уже такого метода в целевой прошивке
        check = conn.execute("SELECT id FROM api_methods WHERE method_name = ? AND firmware_version_id = ?", 
                             (method_dict['method_name'], target_fw_id)).fetchone()
        if check:
            print(f"  -> Метод '{method_dict['method_name']}' уже существует, пропускаем.")
            continue
            
        print(f"  -> Копирование метода: {method_dict['method_name']}")
        
        columns = ", ".join(method_dict.keys())
        placeholders = ", ".join([":" + k for k in method_dict.keys()])
        cursor_new = conn.execute(f"INSERT INTO api_methods ({columns}) VALUES ({placeholders})", method_dict)
        new_method_id = cursor_new.lastrowid
        
        # 2. Копируем параметры этого метода
        cursor_params = conn.execute("SELECT * FROM api_method_params WHERE method_id = ? AND firmware_version_id = ?", 
                                     (old_method_id, source_fw_id))
        params = cursor_params.fetchall()
        
        for param in params:
            param_dict = dict(zip([c[0] for c in cursor_params.description], param))
            param_dict.pop('id')
            param_dict['method_id'] = new_method_id
            param_dict['firmware_version_id'] = target_fw_id
            
            p_cols = ", ".join(param_dict.keys())
            p_placeholders = ", ".join([":" + k for k in param_dict.keys()])
            conn.execute(f"INSERT INTO api_method_params ({p_cols}) VALUES ({p_placeholders})", param_dict)
            
    print("Копирование завершено.")

def sync_api(db_path, firmware_version, collection_path=None):
    with get_db_connection(db_path) as conn:
        fw_id = get_fw_id(conn, firmware_version)
        if not fw_id: return

        print(f"Работаем с прошивкой: {firmware_version} (ID: {fw_id})")
        
        while True:
            print("\n1. Добавить новый API-метод и параметры вручную")
            print("2. Добавить новый API-метод и параметры из JSON-образца")
            print("3. Добавить методы из Postman-коллекции")
            print("4. Добавить параметры к существующему методу")
            print("5. Копировать методы из другой прошивки")
            print("6. Выход")
            
            choice = input("Выберите действие: ")
            
            if choice == '1':
                method_id, method_name = add_api_method(conn, fw_id)
                add_param_to_method(conn, method_id, fw_id, method_name)
                conn.commit()
            elif choice == '2':
                method_id, method_name = add_api_method(conn, fw_id)
                print("\nВставьте JSON-образец (запроса или ответа) и нажмите Ctrl+D (или Ctrl+Z на Windows) для завершения:")
                sample_json = sys.stdin.read()
                if sample_json.strip():
                    map_json_to_api_params(conn, method_id, fw_id, sample_json)
                    conn.commit()
            elif choice == '3':
                path = collection_path or input("Введите путь к Postman-коллекции: ")
                if path:
                    add_methods_from_postman(conn, fw_id, path)
            elif choice == '4':
                cursor = conn.execute("SELECT id, method_name FROM api_methods WHERE firmware_version_id = ?", (fw_id,))
                methods = cursor.fetchall()
                if not methods:
                    print("Методы не найдены.")
                    continue
                
                print("\nСписок методов:")
                for m in methods:
                    print(f"{m[0]}. {m[1]}")
                
                m_id = input("Введите ID метода (или 'b' для возврата): ")
                if m_id.lower() == 'b': continue
                
                m_name = next((m[1] for m in methods if str(m[0]) == m_id), None)
                if m_name:
                    print("\n  a. Добавить вручную")
                    print("  b. Добавить из JSON-образца")
                    subchoice = input("  Выберите способ: ").lower()
                    if subchoice == 'a':
                        add_param_to_method(conn, int(m_id), fw_id, m_name)
                    elif subchoice == 'b':
                        print("\nВставьте JSON-образец и завершите ввод (Ctrl+D/Ctrl+Z):")
                        sample_json = sys.stdin.read()
                        if sample_json.strip():
                            map_json_to_api_params(conn, int(m_id), fw_id, sample_json)
                    conn.commit()
                else:
                    print("Неверный ID.")
            elif choice == '5':
                cursor = conn.execute("SELECT id, version FROM firmware_versions WHERE id != ?", (fw_id,))
                fws = cursor.fetchall()
                if not fws:
                    print("Другие прошивки не найдены.")
                    continue
                
                print("\nДоступные прошивки для копирования:")
                for f in fws:
                    print(f"{f[0]}. {f[1]}")
                
                source_id = input("Введите ID исходной прошивки (или 'b' для возврата): ")
                if source_id.lower() == 'b': continue
                
                if any(str(f[0]) == source_id for f in fws):
                    copy_api_methods(conn, int(source_id), fw_id)
                    conn.commit()
                else:
                    print("Неверный ID.")
            elif choice == '6':
                break
            else:
                print("Неверный выбор.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Утилита для наполнения БД API-методов.")
    parser.add_argument("firmware_version", help="Версия прошивки.")
    
    # Пытаемся автоматически найти БД
    default_db = "resources/domophone.db" if os.path.exists("resources/domophone.db") else "domophone-tests/resources/domophone.db"
    
    parser.add_argument("--db-path", default=default_db, help=f"Путь к БД (по умолчанию: {default_db}).")
    parser.add_argument("--collection", help="Путь к Postman-коллекции.", default=None)
    
    args = parser.parse_args()
    sync_api(args.db_path, args.firmware_version, args.collection)
