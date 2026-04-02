import asyncio
import logging
import os
import json
import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from github import Github

# Load environment variables from .env file
# Configure logging
logging.basicConfig(level=logging.INFO)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
MANAGER_USER_ID = os.getenv("MANAGER_USER_ID")
REPO_NAME = os.getenv("REPO_NAME")

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
g = Github(GITHUB_TOKEN)
lock = asyncio.Lock()

class Form(StatesGroup):
    title = State()
    description = State()
    price = State()
    stock = State()
    images = State()

class OrderForm(StatesGroup):
    name = State()
    phone = State()
    address = State()

class WriteToManager(StatesGroup):
    message_to_manager = State()

# Command handlers
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` command
    """
    user_id = str(message.from_user.id)
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🛍 Каталог")],
            [types.KeyboardButton(text="💬 Написать менеджеру")],
            [types.KeyboardButton(text="Показать ID пользователя")],
        ],
        resize_keyboard=True,
    )

    if user_id == ADMIN_USER_ID:
        admin_keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Добавить товар")],
                [types.KeyboardButton(text="Список товаров")],
                [types.KeyboardButton(text="Активные заказы")],
                [types.KeyboardButton(text="🛍 Каталог")],
                [types.KeyboardButton(text="💬 Написать менеджеру")],
                [types.KeyboardButton(text="Показать ID пользователя")],
            ],
            resize_keyboard=True,
        )
        await message.reply("Hi, Admin! Ready to work!", reply_markup=admin_keyboard)
    else:
        await message.reply("Hi! I'm Project AM Muse Bot. Ready to work!", reply_markup=keyboard)

@dp.message(lambda message: message.text == "Показать ID пользователя")
async def show_user_id(message: types.Message):
    await message.answer(f"Ваш ID пользователя: {message.from_user.id}")


@dp.message(lambda message: message.text == "💬 Написать менеджеру")
async def write_to_manager(message: types.Message, state: FSMContext):
    await state.set_state(WriteToManager.message_to_manager)
    await message.answer("Напишите ваше сообщение менеджеру:")


@dp.message(WriteToManager.message_to_manager)
async def forward_message_to_manager(message: types.Message, state: FSMContext):
    user_info = f"Сообщение от {message.from_user.full_name} (ID: {message.from_user.id}):"
    await bot.send_message(MANAGER_USER_ID, user_info)
    await bot.forward_message(MANAGER_USER_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("Ваше сообщение отправлено менеджеру.")
    await state.clear()



@dp.message(lambda message: message.text == "Добавить товар")
async def add_item(message: types.Message, state: FSMContext):
    """
    This handler will be called when user clicks on the "Добавить товар" button
    """
    await state.set_state(Form.title)
    await message.answer("Введите название товара:")

@dp.message(Form.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(Form.description)
    await message.answer("Введите описание товара:")

@dp.message(Form.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(Form.price)
    await message.answer("Введите цену товара:")

@dp.message(Form.price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(Form.stock)
    await message.answer("Введите количество товара на складе:")

@dp.message(Form.stock)
async def process_stock(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(stock=int(message.text))
    await state.set_state(Form.images)
    await message.answer("Отправьте имя файла изображения (например, photo.jpg):")

@dp.message(Form.images)
async def process_images(message: types.Message, state: FSMContext):
    await state.update_data(images=[message.text])
    data = await state.get_data()
    await state.clear()

    catalog_data = await get_catalog_data()
    if catalog_data is None:
        await message.answer("Ошибка получения каталога с GitHub.")
        return

    new_id_num = len(catalog_data["items"]) + 1
    new_id = f"brooch-{new_id_num:04d}"
    
    today = datetime.date.today().isoformat()

    new_item = {
        "id": new_id,
        "title": data["title"],
        "description": data["description"],
        "price": data["price"],
        "stock": data["stock"],
        "status": "available",
        "created_at": today,
        "updated_at": today,
        "images": data["images"]
    }

    catalog_data["items"].append(new_item)

    if await update_catalog_data(catalog_data):
        await message.answer("Товар добавлен!")
    else:
        await message.answer("Ошибка добавления товара на GitHub.")



@dp.message(lambda message: message.text == "Список товаров")
async def list_items(message: types.Message):
    """
    This handler will be called when user clicks on the "Список товаров" button
    """
    catalog_data = await get_catalog_data()
    if catalog_data is None:
        await message.answer("Ошибка получения каталога с GitHub.")
        return
        
    if not catalog_data["items"]:
        await message.answer("Каталог пуст.")
        return

    for item in catalog_data["items"]:
        text = f"{item['title']} - {item['price']} руб."
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="Edit", callback_data=f"edit_{item['id']}"),
                    types.InlineKeyboardButton(text="Delete", callback_data=f"delete_{item['id']}")
                ]
            ]
        )
        await message.answer(text, reply_markup=keyboard)



@dp.message(lambda message: message.text == "Активные заказы")
async def active_orders(message: types.Message):
    """
    This handler will be called when user clicks on the "Активные заказы" button
    """
    orders_data = await get_orders_data()
    if orders_data is None:
        await message.answer("Ошибка получения заказов с GitHub.")
        return

    if not orders_data["orders"]:
        await message.answer("Активных заказов нет.")
        return

    for order in orders_data["orders"]:
        text = f"""Заказ: {order['order_id']}
Покупатель: {order['user_name']}
Товар: {order['item_title']}
Дата: {order['order_date']}"""
        await message.answer(text)

async def update_catalog_data(new_data):
    """Updates the catalog data on the GitHub repository."""
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents("catalog/catalog.json")
        repo.update_file(
            contents.path,
            "Update catalog",
            json.dumps(new_data, indent=2, ensure_ascii=False),
            contents.sha,
        )
        return True
    except Exception as e:
        logging.error(f"Error updating catalog on GitHub: {e}")
        return False

async def get_orders_data():
    """Gets and parses the orders data from the GitHub repository."""
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents("data/orders.json")
        orders_data = json.loads(contents.decoded_content.decode())
        return orders_data
    except Exception as e:
        logging.error(f"Error getting orders from GitHub: {e}")
        # If the file doesn't exist, return a default structure
        return {"orders": []}

async def update_orders_data(new_data):
    """Updates the orders data on the GitHub repository."""
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents("data/orders.json")
        repo.update_file(
            contents.path,
            "Update orders",
            json.dumps(new_data, indent=2, ensure_ascii=False),
            contents.sha,
        )
        return True
    except Exception as e:
        logging.error(f"Error updating orders on GitHub: {e}")
        return False

async def get_catalog_data():
    """Gets and parses the catalog data from the GitHub repository."""
    try:
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents("catalog/catalog.json")
        catalog_data = json.loads(contents.decoded_content.decode())
        return catalog_data
    except Exception as e:
        logging.error(f"Error getting catalog from GitHub: {e}")
        return None

@dp.message(lambda message: message.text == "🛍 Каталог")
async def show_catalog(message: types.Message):
    """
    This handler will be called when user clicks on the "Каталог" button
    """
    catalog_data = await get_catalog_data()

    if catalog_data is None:
        await message.answer("Ошибка получения каталога с GitHub.")
        return
        
    available_items = [item for item in catalog_data["items"] if item.get("stock", 0) > 0 and item.get("status") == "available"]

    if not available_items:
        await message.answer("В данный момент доступных товаров нет.")
        return

    for item in available_items:
        image_path = f"catalog/images/{item['images'][0]}"
        caption = f"""{item['title']}

{item['description']}

Цена: {item['price']} руб."""
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Заказать эту брошь", callback_data=f"order_{item['id']}")]
            ]
        )
        try:
            photo = types.FSInputFile(image_path)
            await message.answer_photo(photo=photo, caption=caption, reply_markup=keyboard)
        except FileNotFoundError:
            await message.answer(f"Изображение для '{item['title']}' не найдено.")

@dp.callback_query(lambda c: c.data and c.data.startswith('order_'))
async def process_order(callback_query: types.CallbackQuery, state: FSMContext):
    item_id = callback_query.data.split('_')[1]
    await state.update_data(item_id=item_id)
    await state.set_state(OrderForm.name)
    await callback_query.message.answer("Введите ваше ФИО:")
    await callback_query.answer()

@dp.message(OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.phone)
    await message.answer("Введите ваш номер телефона:")

@dp.message(OrderForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(OrderForm.address)
    await message.answer("Введите ваш адрес:")

@dp.message(OrderForm.address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()
    await state.clear()

    async with lock:
        orders_data = await get_orders_data()
        if orders_data is None:
            await message.answer("Ошибка получения заказов с GitHub.")
            return

        catalog_data = await get_catalog_data()
        if catalog_data is None:
            await message.answer("Ошибка получения каталога с GitHub.")
            return
            
        item_id = data["item_id"]
        logging.info(f"Processing order for item_id: {item_id}")
        item_title = ""
        item_in_stock = False
        for item in catalog_data["items"]:
            if item["id"] == item_id:
                logging.info(f"Found item in catalog. Stock: {item.get('stock')}")
                if item["stock"] > 0:
                    item_title = item["title"]
                    item["stock"] -= 1
                    if item["stock"] == 0:
                        item["status"] = "sold"
                    item_in_stock = True
                break
        
        if not item_in_stock:
            await message.answer("Извините, этот товар закончился.")
            return

        new_order_id_num = len(orders_data["orders"]) + 1
        new_order_id = f"order-{new_order_id_num:04d}"
        today = datetime.date.today().isoformat()

        new_order = {
            "order_id": new_order_id,
            "user_id": message.from_user.id,
            "user_name": data["name"],
            "item_id": item_id,
            "item_title": item_title,
            "quantity": 1,
            "order_date": today,
        }

        orders_data["orders"].append(new_order)

        if await update_orders_data(orders_data) and await update_catalog_data(catalog_data):
            await message.answer("Ваш заказ принят!")
            # Notify admin and manager
            await bot.send_message(ADMIN_USER_ID, f"Новый заказ: {new_order_id}")
            await bot.send_message(MANAGER_USER_ID, f"Новый заказ: {new_order_id}")
        else:
            await message.answer("Ошибка создания заказа на GitHub.")


class EditForm(StatesGroup):
    field = State()
    value = State()

@dp.callback_query(lambda c: c.data and c.data.startswith('edit_'))
async def process_edit(callback_query: types.CallbackQuery, state: FSMContext):
    item_id = callback_query.data.split('_')[1]
    await state.update_data(item_id=item_id)
    
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Название", callback_data="edit_field_title")],
            [types.InlineKeyboardButton(text="Описание", callback_data="edit_field_description")],
            [types.InlineKeyboardButton(text="Цена", callback_data="edit_field_price")],
            [types.InlineKeyboardButton(text="Количество", callback_data="edit_field_stock")],
            [types.InlineKeyboardButton(text="Изображения", callback_data="edit_field_images")],
        ]
    )
    await callback_query.message.answer("Какое поле вы хотите отредактировать?", reply_markup=keyboard)
    await state.set_state(EditForm.field)
    await callback_query.answer()


@dp.callback_query(EditForm.field)
async def process_edit_field(callback_query: types.CallbackQuery, state: FSMContext):
    field = callback_query.data.split('_')[2]
    await state.update_data(field=field)
    await callback_query.message.answer(f"Введите новое значение для поля '{field}':")
    await state.set_state(EditForm.value)
    await callback_query.answer()

@dp.message(EditForm.value)
async def process_edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item_id = data["item_id"]
    field = data["field"]
    new_value = message.text

    if field in ["price", "stock"]:
        if not new_value.isdigit():
            await message.answer("Пожалуйста, введите число.")
            return
        new_value = int(new_value)

    catalog_data = await get_catalog_data()
    if catalog_data is None:
        await message.answer("Ошибка получения каталога с GitHub.")
        await state.clear()
        return

    for item in catalog_data["items"]:
        if item["id"] == item_id:
            if field == "images":
                item[field] = [new_value]
            else:
                item[field] = new_value
            break
    
    if await update_catalog_data(catalog_data):
        await message.answer("Товар обновлен!")
    else:
        await message.answer("Ошибка обновления товара на GitHub.")

    await state.clear()



@dp.callback_query(lambda c: c.data and c.data.startswith('confirm_delete_'))
async def confirm_delete(callback_query: types.CallbackQuery):
    item_id = callback_query.data.split('_')[2]
    
    catalog_data = await get_catalog_data()
    if catalog_data is None:
        await callback_query.message.answer("Ошибка получения каталога с GitHub.")
        await callback_query.answer()
        return

    catalog_data["items"] = [item for item in catalog_data["items"] if item["id"] != item_id]

    if await update_catalog_data(catalog_data):
        await callback_query.message.answer(f"Товар с ID: {item_id} удален.")
    else:
        await callback_query.message.answer("Ошибка удаления товара на GitHub.")
    
    await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data == 'cancel_delete')
async def cancel_delete(callback_query: types.CallbackQuery):
    await callback_query.message.answer("Удаление отменено.")
    await callback_query.answer()



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
