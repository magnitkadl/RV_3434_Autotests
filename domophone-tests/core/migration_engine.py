# core/migration_engine.py
"""
Заглушка для механизма миграции параметров между прошивками.
Будет реализован позже.
"""

class MigrationEngine:
    def __init__(self, db_connection=None):
        self.db = db_connection

    def migrate_value(self, param, value, from_fw, to_fw):
        """
        Заглушка: возвращает значение без изменений.
        В будущем — применит цепочку миграций.
        """
        return value