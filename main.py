import asyncio
import logging
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, PROXY_URL

# Импорт роутеров
from functions.common import common_router
from functions.edit import edit_router
from functions.items import items_router
from functions.orders import orders_router

TELEGRAM_API_URL = "https://api.telegram.org"


async def is_telegram_reachable(proxy_url: Optional[str] = None, timeout: float = 5.0) -> bool:
    """Ping Telegram API to detect network availability."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.get(TELEGRAM_API_URL, proxy=proxy_url) as response:
                return 200 <= response.status < 500
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
        return False

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    if not BOT_TOKEN:
        logging.error("BOT_TOKEN не найден в переменных окружения!")
        return

    session = None
    if await is_telegram_reachable():
        logging.debug("Telegram API доступен напрямую.")
    else:
        if not PROXY_URL:
            logging.error(
                "Нет прямого доступа к Telegram API. Укажите PROXY_URL (например, http://proxy.server:3128) в .env."
            )
            return

        if await is_telegram_reachable(PROXY_URL):
            logging.info("Переключаемся на прокси из PROXY_URL для соединения с Telegram.")
            session = AiohttpSession(proxy=PROXY_URL)
        else:
            logging.error("Telegram API недоступен даже через заданный прокси. Проверьте PROXY_URL.")
            return

    bot = Bot(token=BOT_TOKEN, session=session) if session else Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация middleware
    from utils.media_handler import MediaGroupMiddleware
    dp.message.middleware(MediaGroupMiddleware())

    # Регистрация роутеров
    dp.include_router(common_router)
    dp.include_router(items_router)
    dp.include_router(edit_router)
    dp.include_router(orders_router)

    logging.info("Бот AM Muse (Refactored) запущен.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
