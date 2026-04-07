import os
import uuid
import datetime
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from filters.roles import IsAdmin
from utils.json_handler import read_catalog, write_catalog
from utils.github_client import sync_catalog_to_github
from utils.keyboards import get_cancel_inline, get_save_images_inline
from config import IMAGES_DIR

edit_router = Router()

class EditItem(StatesGroup):
    item_id = State()
    field = State()
    new_value = State()
    waiting_for_images = State()

@edit_router.message(F.text == "✏️ Редактировать", IsAdmin())
async def edit_list_start(message: types.Message):
    """Выбор товара для редактирования из последних 10."""
    catalog = await read_catalog()
    if not catalog["items"]:
        return await message.answer("Каталог пуст.")
    
    for item in catalog["items"][:10]:
        kb = InlineKeyboardBuilder()
        kb.button(text="📝 Редактировать это", callback_data=f"edit_start_{item['id']}")
        await message.answer(
            f"ID: {item['id']}\nНазвание: {item['title']}\nЦена: {item['price']} руб.",
            reply_markup=kb.as_markup()
        )

@edit_router.callback_query(F.data.startswith("edit_start_"), IsAdmin())
async def process_edit_start(callback: types.CallbackQuery, state: FSMContext):
    item_id = callback.data.replace("edit_start_", "")
    await state.update_data(item_id=item_id)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="Название", callback_data="edit_f_title")
    kb.button(text="Описание", callback_data="edit_f_description")
    kb.button(text="Цена", callback_data="edit_f_price")
    kb.button(text="Наличие", callback_data="edit_f_stock")
    kb.button(text="📸 Фотографии", callback_data="edit_f_images")
    kb.adjust(2)
    kb.row(types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"))
    
    await callback.message.answer(f"Что изменить в {item_id}?", reply_markup=kb.as_markup())
    await state.set_state(EditItem.field)
    await callback.answer()

@edit_router.callback_query(EditItem.field, F.data.startswith("edit_f_"))
async def process_edit_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_f_", "")
    await state.update_data(field=field)
    
    if field == "images":
        await state.update_data(temp_images=[])
        await state.set_state(EditItem.waiting_for_images)
        await callback.message.answer(
            "Отправьте НОВЫЕ фотографии. Старые будут удалены.\n"
            "Нажмите 'Сохранить', когда закончите.", 
            reply_markup=get_save_images_inline()
        )
    else:
        await state.set_state(EditItem.new_value)
        await callback.message.answer(f"Введите новое значение для {field}:", reply_markup=get_cancel_inline())
    await callback.answer()

@edit_router.message(EditItem.new_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item_id = data["item_id"]
    field = data["field"]
    new_val = message.text
    
    if field in ["price", "stock"]:
        if not new_val.isdigit():
            return await message.answer("Введите число.")
        new_val = int(new_val)
    
    catalog = await read_catalog()
    for item in catalog["items"]:
        if item["id"] == item_id:
            item[field] = new_val
            break
            
    if await write_catalog(catalog):
        await sync_catalog_to_github(catalog)
        await message.answer(f"✅ Поле '{field}' обновлено!")
    
    await state.clear()

@edit_router.message(EditItem.waiting_for_images, F.photo)
async def process_edit_photos(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    data = await state.get_data()
    temp_images = data.get("temp_images", [])
    
    file_name = f"{uuid.uuid4().hex}.jpeg"
    file_path = os.path.join(IMAGES_DIR, file_name)
    await message.bot.download(photo, destination=file_path)
    
    temp_images.append(file_name)
    await state.update_data(temp_images=temp_images)
    await message.answer(f"Фото добавлено ({len(temp_images)}).", reply_markup=get_save_images_inline())

@edit_router.callback_query(EditItem.waiting_for_images, F.data == "save_images")
async def save_edit_images_final(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("temp_images"):
        return await callback.answer("Нужно хотя бы одно фото!", show_alert=True)
    
    catalog = await read_catalog()
    for item in catalog["items"]:
        if item["id"] == data["item_id"]:
            # ТРЕБОВАНИЕ: Полная замена массива путей на новые
            item["images"] = data["temp_images"]
            break
            
    if await write_catalog(catalog):
        await sync_catalog_to_github(catalog)
        await callback.message.answer("✅ Фотографии обновлены!")
    
    await state.clear()
    await callback.answer()
