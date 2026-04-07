from aiogram import types, Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from filters.roles import IsAdmin
from utils.json_handler import read_catalog, write_catalog
from utils.github_client import sync_catalog_to_github

delete_router = Router()

@delete_router.message(F.text == "🗑️ Удалить", IsAdmin())
async def delete_list_start(message: types.Message):
    """Выбор товара для удаления из последних 10."""
    catalog = await read_catalog()
    if not catalog["items"]:
        return await message.answer("Каталог пуст.")
    
    for item in catalog["items"][:10]:
        kb = InlineKeyboardBuilder()
        kb.button(text="🗑 Удалить это", callback_data=f"del_confirm_{item['id']}")
        await message.answer(
            f"ID: {item['id']}\nНазвание: {item['title']}",
            reply_markup=kb.as_markup()
        )

@delete_router.callback_query(F.data.startswith("del_confirm_"), IsAdmin())
async def process_delete_confirm(callback: types.CallbackQuery):
    item_id = callback.data.replace("del_confirm_", "")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"del_yes_{item_id}")
    kb.button(text="❌ Нет, отмена", callback_data="cancel_action")
    kb.adjust(1)
    
    await callback.message.answer(
        f"Вы уверены, что хотите удалить товар {item_id}?", 
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@delete_router.callback_query(F.data.startswith("del_yes_"), IsAdmin())
async def process_delete_final(callback: types.CallbackQuery):
    item_id = callback.data.replace("del_yes_", "")
    
    catalog = await read_catalog()
    original_len = len(catalog["items"])
    catalog["items"] = [item for item in catalog["items"] if item["id"] != item_id]
    
    if len(catalog["items"]) < original_len:
        if await write_catalog(catalog):
            await sync_catalog_to_github(catalog)
            await callback.message.answer(f"✅ Товар {item_id} успешно удален.")
    else:
        await callback.message.answer("❌ Товар не найден.")
    
    await callback.answer()
