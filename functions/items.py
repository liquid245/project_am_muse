import os
import uuid
import datetime
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from filters.roles import IsAdmin
from utils.json_handler import read_catalog, write_catalog, generate_unique_id
from utils.github_client import sync_catalog_to_github
from utils.keyboards import get_cancel_inline, get_save_images_inline
from config import IMAGES_DIR

items_router = Router()

class ItemForm(StatesGroup):
    title = State()
    description = State()
    price = State()
    stock = State()
    waiting_for_images = State()

@items_router.message(F.text == "➕ Добавить товар", IsAdmin())
async def add_item_start(message: types.Message, state: FSMContext):
    """Начало сценария добавления."""
    await state.set_state(ItemForm.title)
    await message.answer("Название товара:", reply_markup=get_cancel_inline())

@items_router.message(ItemForm.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(ItemForm.description)
    await message.answer("Описание:", reply_markup=get_cancel_inline())

@items_router.message(ItemForm.description)
async def process_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(ItemForm.price)
    await message.answer("Цена (только число):", reply_markup=get_cancel_inline())

@items_router.message(ItemForm.price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введите число.")
    await state.update_data(price=int(message.text))
    await state.set_state(ItemForm.stock)
    await message.answer("Количество:", reply_markup=get_cancel_inline())

@items_router.message(ItemForm.stock)
async def process_stock(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Пожалуйста, введите число.")
    await state.update_data(stock=int(message.text), temp_images=[])
    await state.set_state(ItemForm.waiting_for_images)
    await message.answer(
        "Отправьте фотографии (одну за другой).\n"
        "Когда закончите, нажмите 'Сохранить'.", 
        reply_markup=get_save_images_inline()
    )

@items_router.message(ItemForm.waiting_for_images, F.photo)
async def process_photos(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    data = await state.get_data()
    temp_images = data.get("temp_images", [])
    
    os.makedirs(IMAGES_DIR, exist_ok=True)
    file_name = f"{uuid.uuid4().hex}.jpeg"
    file_path = os.path.join(IMAGES_DIR, file_name)
    await message.bot.download(photo, destination=file_path)
    
    temp_images.append(file_name)
    await state.update_data(temp_images=temp_images)
    await message.answer(f"Фото добавлено ({len(temp_images)}).", reply_markup=get_save_images_inline())

@items_router.callback_query(ItemForm.waiting_for_images, F.data == "save_images")
async def save_item_final(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("temp_images"):
        return await callback.answer("Нужно хотя бы одно фото!", show_alert=True)
    
    catalog = await read_catalog()
    
    new_id = generate_unique_id()
    today = datetime.date.today().isoformat()
    
    new_item = {
        "id": new_id,
        "title": data["title"],
        "description": data["description"],
        "price": data["price"],
        "stock": data["stock"],
        "status": "available",
        "created_at": today,
        "images": data["temp_images"]
    }
    
    # ТРЕБОВАНИЕ: Новый товар в начало списка
    catalog["items"].insert(0, new_item)
    
    if await write_catalog(catalog):
        await sync_catalog_to_github(catalog)
        await callback.message.answer(f"✅ Товар '{data['title']}' добавлен первым в списке!")
    else:
        await callback.message.answer("❌ Ошибка при записи JSON.")
    
    await state.clear()
    await callback.answer()
