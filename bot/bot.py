import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from bot.functions.admin import admin_router
from bot.functions.user import user_router
from bot.functions.orders import orders_router


async def main():
    load_dotenv()

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    PROXY_URL = os.getenv("PROXY_URL")

    if PROXY_URL:
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=BOT_TOKEN, session=session)
    else:
        bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Include routers
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(orders_router)

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
