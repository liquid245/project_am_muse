import asyncio
import logging
import os
import json
import datetime
import uuid

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
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

ORDER_CHAT_ID = -1003497103344  # User provided chat ID
ORDER_TOPIC_ID = 43            # User provided topic ID

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
lock = asyncio.Lock()
CATALOG_FILE = "docs/catalog/catalog.json"

def get_cancel_keyboard():
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Прервать добавление товара", callback_data="cancel_add_item")]
        ]
    )
    return keyboard

def get_save_and_cancel_keyboard():
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Сохранить", callback_data="save_item")],
            [types.InlineKeyboardButton(text="Прервать добавление товара", callback_data="cancel_add_item")]
        ]
    )
    return keyboard

@dp.callback_query(lambda c: c.data == "cancel_add_item")
async def cancel_add_item(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.answer("Добавление товара прервано.", reply_markup=types.ReplyKeyboardRemove())
    await callback_query.answer()

class Form(StatesGroup):
    title = State()
    description = State()
    price = State()
    stock = State()
    waiting_for_images = State()  # New state to collect multiple images
    process_images = State()      # New state to process collected images

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
    await message.answer(f"{user_id_text}
{chat_topic_text}")


async def get_chat_id_text(message: types.Message) -> str:
    chat_id = message.chat.id
    text = f"ID этого чата: {chat_id}"
    if message.is_topic_message and message.message_thread_id:
        topic_id = message.message_thread_id
        text += f"
ID этой темы: {topic_id}"
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
    await message.answer("Введите описание товара:", reply_markup=get_cancel_keyboard())

@dp.message(Form.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(Form.price)
    await message.answer("Введите цену товара:", reply_markup=get_cancel_keyboard())

@dp.message(Form.price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(Form.stock)
    await message.answer("Введите количество товара на складе:", reply_markup=get_cancel_keyboard())

@dp.message(Form.stock)
async def process_stock(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(stock=int(message.text), temp_image_file_ids=[]) # Initialize list for image file_ids
    await state.set_state(Form.waiting_for_images)
    await message.answer("Отправьте одно или несколько изображений для товара. Используйте кнопку 'Прервать добавление товара' если хотите отменить. После добавления хотя бы одного фото появится кнопка 'Сохранить'.", reply_markup=get_cancel_keyboard())



@dp.message(Form.waiting_for_images)
async def process_waiting_for_images(message: types.Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id  # Get the largest photo
        async with lock: # Ensure thread-safe operations for state data
            data = await state.get_data()
            image_file_ids = data.get('temp_image_file_ids', [])
            image_file_ids.append(file_id)
            await state.update_data(temp_image_file_ids=image_file_ids)
            
            # Send message with save and cancel buttons
            await message.answer("Изображение получено. Отправьте еще, нажмите 'Сохранить' для завершения, или 'Прервать добавление товара'.", reply_markup=get_save_and_cancel_keyboard())
    else:
        # If no photo, but text, check for '/done' (though it should be handled by the button now)
        # Or if just text, prompt again for an image
        await message.answer("Пожалуйста, отправьте изображение, нажмите 'Сохранить' для завершения, или 'Прервать добавление товара'.", reply_markup=get_save_and_cancel_keyboard())


@dp.callback_query(lambda c: c.data == "save_item")
async def save_item_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get('temp_image_file_ids'):
        await callback_query.answer("Пожалуйста, сначала отправьте хотя бы одно изображение.", show_alert=True)
        return
    await state.set_state(Form.process_images)
    await process_new_item(callback_query.message, state)
    await callback_query.answer()


async def process_new_item(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    # Create the images directory if it doesn't exist
    images_dir = "docs/catalog/images"
    os.makedirs(images_dir, exist_ok=True)
    
    saved_image_names = []
    for file_id in data["temp_image_file_ids"]:
        try:
            file_info = await bot.get_file(file_id)
            downloaded_file_path = file_info.file_path
            
            # Generate a unique filename using UUID
            # import uuid - uuid imported at top
            unique_filename = f"{uuid.uuid4().hex}.jpeg" # Assuming jpeg, but can be dynamic
            destination_path = os.path.join(images_dir, unique_filename)
            
            await bot.download_file(downloaded_file_path, destination_path)
            saved_image_names.append(unique_filename)
            logging.info(f"Image saved to {destination_path}")
        except Exception as e:
            logging.error(f"Error saving image {file_id}: {e}")
            await message.answer(f"Ошибка при сохранении изображения: {e}")
            # Decide whether to continue or abort if an image fails to save

    catalog_data = await get_catalog_data()
    if catalog_data is None:
        await message.answer("Ошибка получения каталога.")
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
        "images": saved_image_names # Use the list of saved image names
    }

    catalog_data["items"].append(new_item)

    if await update_catalog_data(catalog_data):
        await message.answer("Товар добавлен!")
        user_id = str(message.from_user.id)
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
            await message.answer("Готово. Вы можете продолжить работу.", reply_markup=admin_keyboard)
    else:
        await message.answer("Ошибка добавления товара.")

async def update_catalog_data(new_data):
    """Updates the catalog data on the local filesystem and optionally on GitHub."""
    # 1. Update local catalog.json
    try:
        os.makedirs(os.path.dirname(CATALOG_FILE), exist_ok=True)
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        logging.info("Local catalog.json updated successfully.")
    except Exception as e:
        logging.error(f"Error updating local catalog.json: {e}")
        return False

    # 2. Optionally update catalog.json on GitHub
    if GITHUB_TOKEN and REPO_NAME:
        try:
            g = Github(GITHUB_TOKEN)
            # Assuming REPO_NAME is in format "owner/repo"
            repo = g.get_repo(REPO_NAME)
            
            contents = repo.get_contents(CATALOG_FILE)
            
            # Encode new_data to JSON string
            new_content_str = json.dumps(new_data, indent=2, ensure_ascii=False)
            
            repo.update_file(
                path=CATALOG_FILE,
                message="Update catalog.json via bot",
                content=new_content_str,
                sha=contents.sha
            )
            logging.info(f"catalog.json updated successfully on GitHub in repository {REPO_NAME}.")
            return True
        except Exception as e:
            logging.error(f"Error updating catalog.json on GitHub: {e}")
            return False
    else:
        logging.info("GitHub token or repository name not provided. Skipping GitHub update.")
        return True # Local update was successful, so return True

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
        caption = f"""{item['title']}

{item['description']}

Цена: {item['price']} руб."""
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Заказать этот товар", callback_data=f"order_{item['id']}")]
            ]
        )
        
        # Send all images for the item
        if item.get('images'):
            media_group = []
            for img_name in item['images']:
                image_path = f"docs/catalog/images/{img_name}"
                if os.path.exists(image_path):
                    media_group.append(types.InputMediaPhoto(media=types.FSInputFile(image_path)))
                else:
                    logging.warning(f"Image file not found: {image_path}")
            
            if media_group:
                # Add caption to the first photo in the media group
                media_group[0].caption = caption
                await message.answer_media_group(media=media_group)
                await message.answer(" ", reply_markup=keyboard) # Send keyboard separately if using media group
            else:
                await message.answer(f"Изображения для '{item['title']}' не найдены.", reply_markup=keyboard)
        else:
            await message.answer(f"Изображения для '{item['title']}' не найдены.", reply_markup=keyboard)


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


