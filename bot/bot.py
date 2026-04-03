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



# Load environment variables from .env file
# Configure logging
logging.basicConfig(level=logging.INFO)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

ORDER_CHAT_ID = -1003497103344  # User provided chat ID
ORDER_TOPIC_ID = 43            # User provided topic ID

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
lock = asyncio.Lock()
CATALOG_FILE = "docs/catalog/catalog.json"

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
            [types.KeyboardButton(text="Показать ID пользователя, чата и темы")],
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
                [types.KeyboardButton(text="Показать ID пользователя, чата и темы")],
            ],
            resize_keyboard=True,
        )
        await message.reply("Hi, Admin! Ready to work!", reply_markup=admin_keyboard)
    else:
        await message.reply("Hi! I'm Project AM Muse Bot. Ready to work!", reply_markup=keyboard)

@dp.message(lambda message: message.text == "Показать ID пользователя, чата и темы")
async def show_user_chat_topic_id(message: types.Message):
    user_id_text = f"Ваш ID пользователя: {message.from_user.id}"
    chat_topic_text = await get_chat_id_text(message)
    await message.answer(f"{user_id_text}\n{chat_topic_text}")


async def get_chat_id_text(message: types.Message) -> str:
    chat_id = message.chat.id
    text = f"ID этого чата: {chat_id}"
    if message.is_topic_message and message.message_thread_id:
        topic_id = message.message_thread_id
        text += f"\nID этой темы: {topic_id}"
    return text






@dp.message(lambda message: message.text == "💬 Написать менеджеру")
async def write_to_manager(message: types.Message, state: FSMContext):
    await state.set_state(WriteToManager.message_to_manager)
    await message.answer("Напишите ваше сообщение менеджеру:")


@dp.message(WriteToManager.message_to_manager)
async def forward_message_to_manager(message: types.Message, state: FSMContext):
    user_info = f"Сообщение от {message.from_user.full_name} (ID: {message.from_user.id}):"
    
    # Forward the user's message to the specified chat and topic
    try:
        # Send user info as a separate message first
        await bot.send_message(
            chat_id=ORDER_CHAT_ID,
            message_thread_id=ORDER_TOPIC_ID,
            text=user_info
        )
        # Then forward the actual message for direct reply
        await bot.forward_message(
            chat_id=ORDER_CHAT_ID,
            message_thread_id=ORDER_TOPIC_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        logging.info(f"Message from user {message.from_user.id} forwarded to chat {ORDER_CHAT_ID}, topic {ORDER_TOPIC_ID}")
        await message.answer("Ваше сообщение отправлено менеджеру.")
    except Exception as e:
        logging.error(f"Error forwarding message to manager chat: {e}")
        await message.answer("Произошла ошибка при отправке вашего сообщения менеджеру.")
    finally:
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
        await message.answer("Ошибка получения каталога.") # Changed from GitHub error
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
        await message.answer("Ошибка добавления товара.") # Changed from GitHub error

async def update_catalog_data(new_data):
    """Updates the catalog data on the local filesystem."""
    try:
        os.makedirs(os.path.dirname(CATALOG_FILE), exist_ok=True)
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error updating catalog locally: {e}")
        return False

async def get_catalog_data():
    """Gets and parses the catalog data from the local filesystem."""
    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)
        return catalog_data
    except FileNotFoundError:
        return {"items": []}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding catalog.json: {e}")
        return None
    except Exception as e:
        logging.error(f"Error getting catalog locally: {e}")
        return None





@dp.message(lambda message: message.text == "🛍 Каталог")
async def show_catalog(message: types.Message):
    """
    This handler will be called when user clicks on the "Каталог" button
    """
    catalog_data = await get_catalog_data()

    if catalog_data is None:
        await message.answer("Ошибка получения каталога.")
        return
    
    logging.info(f"Full catalog data: {catalog_data}")
    logging.info(f"Items before filtering: {catalog_data.get('items', [])}")
        
    available_items = [item for item in catalog_data["items"] if item.get("stock", 0) > 0 and item.get("status") == "available"]

    logging.info(f"Filtered available items: {available_items}")

    if not available_items:
        await message.answer("В данный момент доступных товаров нет.")
        return

    for item in available_items:
        image_path = f"docs/catalog/images/{item['images'][0]}" # Adjusted path for local file
        caption = f"""{item['title']}

{item['description']}

Цена: {item['price']} руб."""
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Заказать этот товар", callback_data=f"order_{item['id']}")]
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
    data = await state.get_data()
    await state.clear()

    async with lock:
        catalog_data = await get_catalog_data()
        if catalog_data is None:
            await message.answer("Ошибка получения каталога.")
            return
            
        item_id = data["item_id"]
        logging.info(f"Processing order for item_id: {item_id}")
        item_title = ""
        item_price = 0
        item_in_stock = False
        for item in catalog_data["items"]:
            if item["id"] == item_id:
                logging.info(f"Found item in catalog. Stock: {item.get('stock')}")
                if item["stock"] > 0:
                    item_title = item["title"]
                    item_price = item["price"]
                    item["stock"] -= 1
                    if item["stock"] == 0:
                        item["status"] = "sold"
                    item_in_stock = True
                break
        
        if not item_in_stock:
            await message.answer("Извините, этот товар закончился.")
            return

        # Prepare order message for manager
        order_details = f"""
        ***НОВЫЙ ЗАКАЗ***

        **Товар:** {item_title} (ID: {item_id})
        **Цена:** {item_price} руб.
        **Количество:** 1
        **Покупатель:** {data["name"]} (ID: {message.from_user.id})
        **Телефон:** {data["phone"]}
        **Адрес:** {data["address"]}
        **Дата заказа:** {datetime.date.today().isoformat()}
        """

        if await update_catalog_data(catalog_data):
            await message.answer("Ваш заказ принят!")
            # Notify manager in the specified chat and topic
            try:
                await bot.send_message(
                    chat_id=ORDER_CHAT_ID,
                    message_thread_id=ORDER_TOPIC_ID,
                    text=order_details,
                    parse_mode="Markdown"
                )
                logging.info(f"Order {item_id} sent to manager chat {ORDER_CHAT_ID}, topic {ORDER_TOPIC_ID}")
            except Exception as e:
                logging.error(f"Error sending order message to manager: {e}")
                await message.answer("Ошибка при отправке деталей заказа менеджеру.")
        else:
            await message.answer("Ошибка обновления каталога.")

@dp.message(lambda message: message.text == "Список товаров")
async def list_items(message: types.Message):
    """
    This handler will be called when user clicks on the "Список товаров" button
    """
    catalog_data = await get_catalog_data()
    if catalog_data is None:
        await message.answer("Ошибка получения каталога.")
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
    await message.answer("Заказы не хранятся в боте. Все заказы отправляются менеджеру напрямую.")


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
        await message.answer("Ошибка получения каталога.")
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
        await message.answer("Ошибка обновления товара.")

    await state.clear()


@dp.callback_query(lambda c: c.data and c.data.startswith('delete_'))
async def request_delete_confirmation(callback_query: types.CallbackQuery):
    item_id = callback_query.data.split('_')[1]
    
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Да, удалить", callback_data=f"confirm_delete_{item_id}"),
                types.InlineKeyboardButton(text="Нет, отмена", callback_data="cancel_delete")
            ]
        ]
    )
    await callback_query.message.answer(f"Вы уверены, что хотите удалить товар с ID: {item_id}?", reply_markup=keyboard)
    await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith('confirm_delete_'))
async def confirm_delete(callback_query: types.CallbackQuery):
    item_id = callback_query.data.split('_')[2]
    
    catalog_data = await get_catalog_data()
    if catalog_data is None:
        await callback_query.message.answer("Ошибка получения каталога.")
        await callback_query.answer()
        return

    catalog_data["items"] = [item for item in catalog_data["items"] if item["id"] != item_id]

    if await update_catalog_data(catalog_data):
        await callback_query.message.answer(f"Товар с ID: {item_id} удален.")
    else:
        await callback_query.message.answer("Ошибка удаления товара.")
    
    await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data == 'cancel_delete')
async def cancel_delete(callback_query: types.CallbackQuery):
    await callback_query.message.answer("Удаление отменено.")
    await callback_query.answer()





async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
