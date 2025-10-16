# core/firmware.py
import sqlite3
from typing import List, Optional
from .models import FirmwareVersion
from .db import get_firmware_by_version, get_all_firmware_versions


def get_firmware_versions_ordered(conn: sqlite3.Connection) -> List[FirmwareVersion]:
    """Возвращает прошивки, отсортированные по дате выпуска (от старых к новым)."""
    return get_all_firmware_versions(conn)


def is_firmware_older(
    fw1: FirmwareVersion, fw2: FirmwareVersion
) -> bool:
    """Возвращает True, если fw1 старше fw2."""
    return fw1.release_date < fw2.release_date