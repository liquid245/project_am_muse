from aiogram import types, Router, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from utils.keyboards import get_main_keyboard, get_catalog_inline
from utils.json_handler import read_catalog
from config import IMAGES_DIR
import os

common_router = Router()

@common_router.message(Command("start"))
async def start_command(message: types.Message, command: CommandObject):
    """Приветствие и выдача меню по роли. Обработка Deep Link."""
    user_id = message.from_user.id
    args = command.args
    
    if args:
        catalog = await read_catalog()
        # Ищем товар по ID (как числу или строке)
        item = next((i for i in catalog["items"] if str(i["id"]) == args), None)
        
        if item:
            text = (
                f"🏷 <b>{item['title']}</b>\n\n"
                f"{item['description']}\n\n"
                f"💰 Цена: {item['price']} ₽\n"
                f"📦 В наличии: {item['stock']} шт."
            )
            
            if item["images"]:
                photo_path = os.path.join(IMAGES_DIR, item["images"][0])
                if os.path.exists(photo_path):
                    await message.answer_photo(
                        photo=FSInputFile(photo_path),
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=get_main_keyboard(user_id)
                    )
                else:
                    await message.answer(
                        text, 
                        parse_mode="HTML", 
                        reply_markup=get_main_keyboard(user_id)
                    )
            else:
                await message.answer(
                    text, 
                    parse_mode="HTML", 
                    reply_markup=get_main_keyboard(user_id)
                )
            
            await message.answer("Хотите заказать этот товар? Напишите менеджеру или используйте меню.")
            return

    welcome_text = (
        "👋 Привет! Добро пожаловать в AM Muse.\n\n"
        "Наш каталог доступен по кнопке ниже. "
        "Здесь вы можете выбрать понравившиеся броши и оформить заказ."
    )
    
    await message.answer(
        welcome_text, 
        reply_markup=get_main_keyboard(user_id)
    )
    await message.answer(
        "Нажмите на кнопку ниже, чтобы открыть сайт-каталог:",
        reply_markup=get_catalog_inline()
    )

@common_router.message(F.text == "🌐 Открыть каталог")
async def open_catalog_text(message: types.Message):
    """Дублирование ссылки на сайт по кнопке в меню."""
    await message.answer(
        "Наш сайт-каталог:",
        reply_markup=get_catalog_inline()
    )

@common_router.callback_query(F.data == "cancel_action")
async def cancel_action_handler(callback: types.CallbackQuery, state: FSMContext):
    """Общий обработчик отмены любых действий."""
    await state.clear()
    await callback.message.answer("Действие отменено.")
    await callback.answer()
