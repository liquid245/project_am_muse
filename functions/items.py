import os
import io
import time
import logging
import datetime
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from filters.roles import IsAdmin
from utils.keyboards import get_cancel_inline, get_save_images_inline
from utils.storage_manager import StorageManager

items_router = Router()

class ItemForm(StatesGroup):
    title = State()
    description = State()
    price = State()
    stock = State()
    waiting_for_images = State()
    # temp_photos будет хранить список словарей: [{'filename': str, 'data': BytesIO}, ...]
    temp_photos = State()

@items_router.message(F.text == "➕ Добавить товар", IsAdmin())
async def add_item_start(message: types.Message, state: FSMContext):
    """Начало сценария добавления."""
    await state.set_state(ItemForm.title)
    await state.update_data(temp_photos=[])
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
    await state.update_data(stock=int(message.text))
    await state.set_state(ItemForm.waiting_for_images)
    await message.answer(
        "Отправьте фотографии (одну за другой).
"
        "Когда закончите, нажмите 'Сохранить'.", 
        reply_markup=get_save_images_inline()
    )

@items_router.message(ItemForm.waiting_for_images, F.photo)
async def process_photos(message: types.Message, state: FSMContext):
    """Скачивает фото в память (BytesIO) и сохраняет в FSM."""
    photo = message.photo[-1]
    data = await state.get_data()
    temp_photos = data.get("temp_photos", [])
    
    # Генерируем уникальное имя файла
    file_ext = photo.mime_subtype or 'jpeg'
    file_name = f"photo_{int(time.time() * 1000)}_{len(temp_photos)}.{file_ext}"

    # Скачиваем файл в память
    in_memory_file = io.BytesIO()
    await message.bot.download(photo, destination=in_memory_file)
    in_memory_file.seek(0) # Возвращаем курсор в начало файла
    
    temp_photos.append({'filename': file_name, 'data': in_memory_file.read()})
    await state.update_data(temp_photos=temp_photos)
    
    await message.answer(f"Фото добавлено ({len(temp_photos)}).", reply_markup=get_save_images_inline())

@items_router.callback_query(ItemForm.waiting_for_images, F.data == "save_images")
async def save_item_final(callback: types.CallbackQuery, state: FSMContext):
    """Атомарно сохраняет все данные через StorageManager."""
    data = await state.get_data()
    temp_photos = data.get("temp_photos")

    if not temp_photos:
        return await callback.answer("Нужно хотя бы одно фото!", show_alert=True)
    
    await callback.message.edit_text("Сохраняю... Это может занять некоторое время.")

    try:
        storage_manager = StorageManager()
        
        # 1. Сохраняем все фото
        saved_image_filenames = []
        for photo_data in temp_photos:
            filename = storage_manager.save_photo(photo_data['data'], photo_data['filename'])
            saved_image_filenames.append(filename)
        
        # 2. Если все фото сохранены, формируем и сохраняем данные о товаре
        new_id = f"item_{int(time.time())}"
        today = datetime.date.today().isoformat()
        
        new_item = {
            "id": new_id,
            "title": data["title"],
            "description": data["description"],
            "price": data["price"],
            "stock": data["stock"],
            "status": "available",
            "created_at": today,
            "images": saved_image_filenames
        }
        
        storage_manager.update_catalog(new_item)
        
        await callback.message.edit_text(f"✅ Товар '{data['title']}' успешно добавлен!")

    except Exception as e:
        logging.error(f"Критическая ошибка при сохранении товара: {e}", exc_info=True)
        # Опционально: можно добавить логику удаления уже загруженных фото, если что-то пошло не так
        await callback.message.edit_text("❌ Ошибка при сохранении. Товар не был добавлен. Попробуйте снова.")
    finally:
        await state.clear()
        await callback.answer()
