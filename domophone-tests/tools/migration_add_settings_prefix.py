import sqlite3

db_path = 'domophone-tests/resources/domophone.db'

with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    
    # Выбираем все param_uuid, которые не начинаются с 'settings.'
    cursor.execute("SELECT param_uuid FROM config_parameters WHERE param_uuid NOT LIKE 'settings.%'")
    rows_to_update = cursor.fetchall()
    
    print(f"Найдено {len(rows_to_update)} записей для обновления.")
    
    updated_count = 0
    for row in rows_to_update:
        old_uuid = row[0]
        # Проверяем, есть ли уже запись с новым uuid, чтобы избежать дубликатов
        new_uuid = f"settings.{old_uuid}"
        cursor.execute("SELECT 1 FROM config_parameters WHERE param_uuid = ?", (new_uuid,))
        if cursor.fetchone():
            print(f"  -> Пропуск {old_uuid}, так как {new_uuid} уже существует.")
            continue
            
        # Обновляем запись
        print(f"  -> Обновление {old_uuid} -> {new_uuid}")
        cursor.execute("UPDATE config_parameters SET param_uuid = ? WHERE param_uuid = ?", (new_uuid, old_uuid))
        updated_count += 1
        
    conn.commit()
    print(f"\nМиграция завершена. Обновлено {updated_count} записей.")
