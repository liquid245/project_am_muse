import asyncio
import json
import logging
import os
import time
from config import CATALOG_FILE

lock = asyncio.Lock()

def generate_unique_id():
    """Генерирует уникальный ID на основе текущего времени."""
    return str(int(time.time()))

async def read_catalog():
    """Асинхронное чтение файла каталога."""
    async with lock:
        try:
            if not os.path.exists(CATALOG_FILE):
                return {"items": []}
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Ошибка при чтении {CATALOG_FILE}: {e}")
            return {"items": []}

async def write_catalog(data):
    """Асинхронная запись в файл каталога."""
    async with lock:
        try:
            os.makedirs(os.path.dirname(CATALOG_FILE), exist_ok=True)
            with open(CATALOG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Ошибка при записи {CATALOG_FILE}: {e}")
            return False
