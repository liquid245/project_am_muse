import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from aiogram.client.session.aiohttp import AiohttpSession

# Импорт роутеров
from functions.common import common_router
from functions.items import items_router
from functions.edit import edit_router
from functions.orders import orders_router

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN не найден в переменных окружения!")
        return

    bot = Bot(token=BOT_TOKEN)
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
