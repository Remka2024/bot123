import logging
import os
import json
from telegram import (Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup)
from telegram.ext import (ApplicationBuilder, CommandHandler,
                          ContextTypes, MessageHandler, filters,
                          CallbackQueryHandler)
from threading import Timer
import pathlib
import signal
from PIL import Image

from datetime import  datetime
# Список для хранения идентификаторов сообщений
message_ids = []

logging.basicConfig(level=logging.INFO)

# TOKEN = 'YOUR_TOKEN_HERE'  # замените на ваш токен доступа

# Файл с базой данных
#DATABASE_FILE = 'database.json'
DATABASE_FILE = 'cartine.json'
cartine = []

# Загрузка базы данных из файла
def load_database():
    try:
        with open(DATABASE_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []
# Сохранение базы данных в файл
def save_database(database):
    with open(DATABASE_FILE, 'w') as file:
        json.dump(database, file)
###
load_database()
# Функция сжатия изображений
def compress_image(input_path, output_path, max_size_mb=10, quality=85):
    max_size_bytes = max_size_mb * 1024 * 1024  # переводим лимит размера в байты
    with Image.open(input_path) as img:
        file_size = os.path.getsize(input_path)
        if file_size <= max_size_bytes:
            return input_path  # если файл уже меньше 10 МБ, не сжимаем его

        img.save(output_path, optimize=True, quality=quality)

        compressed_size = os.path.getsize(output_path)
        while compressed_size > max_size_bytes and quality > 10:
            quality -= 5
            img.save(output_path, optimize=True, quality=quality)
            compressed_size = os.path.getsize(output_path)

        return output_path

# База данных для хранения информации о картинах
cartine = load_database()

# Состояние пользователя
USER_STATE = {}

# Счетчик фотографий
photo_index = 0

# Папка с фотографиями
PHOTO_FOLDER = None

# Текущая папка
CURRENT_FOLDER = pathlib.Path(".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['start_message_id'] = update.message.message_id


    user = update.message.from_user
    user_info = {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language_code": user.language_code,
    }
    print(user_info)

    # Добавление записи о входе
    add_user_login(
        first_name=user.first_name,
        last_name=user.last_name,
        user_id=user.id,

        login_date=datetime.now().strftime('%Y-%m-%d'),
        login_time=datetime.now().strftime('%H:%M:%S')
    )
    USER_STATE[update.effective_user.id] = {"mode": "start"}
    await update.message.reply_text(f"Привет, {user.first_name}!\nДобро пожаловать в галерею моих картин!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Продавец", callback_data="seller")],
        [InlineKeyboardButton("Покупатель", callback_data="buyer")]
    ]))
    await delete_start_message(context, chat_id=update.effective_chat.id)
    #await delete_restart_message(context, chat_id=update.effective_chat.id)
    # или этот способ
    await delete_restart_message(context, update.effective_chat.id)

    # Сохранение идентификатора сообщения

# создаем базу данных для юзеров
def init_json_db(filename='users.json'):
    if not os.path.exists(filename):
        data = {"users": []}
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
init_json_db()


def add_user_login(first_name, last_name, user_id, login_date, login_time, filename='users.json'):
    with open(filename, 'r') as file:
        data = json.load(file)

    user = next((u for u in data["users"] if u["user_id"] == user_id), None)

    if not user:
        user = {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "logins": []
        }
        data["users"].append(user)

    user["logins"].append({
        "login_date": login_date,
        "login_time": login_time,
        "logout_date": None,
        "logout_time": None
    })

    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)


# Пример добавления записи
#add_user_login(
#    first_name="John",
#    last_name="Doe",
#    user_id=1,
#    login_date=datetime.now().strftime('%Y-%m-%d'),
#    login_time=datetime.now().strftime('%H:%M:%S')
#)

def update_user_logout(user_id, logout_date, logout_time, filename='users.json'):
    with open(filename, 'r') as file:
        data = json.load(file)

    user = next((u for u in data["users"] if u["user_id"] == user_id), None)

    if user:
        last_login = next(
            (login for login in user["logins"] if login["logout_date"] is None and login["logout_time"] is None), None)

        if last_login:
            last_login["logout_date"] = logout_date
            last_login["logout_time"] = logout_time

    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)


# Пример обновления записи
update_user_logout(
    user_id=1,
    logout_date=datetime.now().strftime('%Y-%m-%d'),
    logout_time=datetime.now().strftime('%H:%M:%S')
)


def get_user_logins(filename='users.json'):
    with open(filename, 'r') as file:
        data = json.load(file)

    return data["users"]


logins = get_user_logins()
for user in logins:
    print(f"User ID: {user['user_id']}, Name: {user['first_name']} {user['last_name']}")
    for login in user['logins']:
        print(
            f"  Login: {login['login_date']} {login['login_time']}, Logout: {login['logout_date']} {login['logout_time']}")

# Функция для обработки сигнала завершения работы
def handle_exit_signals(signum, frame):
    # Здесь можно добавить логику для обновления времени выхода всех активных пользователей
    # Например:
    for user_id in ACTIVE_USERS:
        update_user_logout(
            user_id=user_id,
            logout_date=datetime.now().strftime('%Y-%m-%d'),
            logout_time=datetime.now().strftime('%H:%M:%S')
        )

    print("Bot is shutting down...")

# Регистрация обработчика сигналов завершения работы
signal.signal(signal.SIGINT, handle_exit_signals)
signal.signal(signal.SIGTERM, handle_exit_signals)
# конец работы с юзерами
async def end_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    # Обновление записи о выходе
    update_user_logout(
        user_id=user.id,
        logout_date=datetime.now().strftime('%Y-%m-%d'),
        logout_time=datetime.now().strftime('%H:%M:%S')
    )

    await update.message.reply_text("Сессия завершена. До свидания!")

async def seller_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USER_STATE[update.effective_user.id] = {"mode": "seller", "step": "awaiting_password"}
    message =  await update.callback_query.edit_message_text("Вы входите как продавец!\nВведите, пожалуйста, пароль:")
    # Сохраняем идентификатор сообщения в состоянии пользователя
    USER_STATE[update.effective_user.id] = {
        "mode": "seller",
        "step": "awaiting_password",
        "message_id": message.message_id
    }

async def buyer_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #USER_STATE = {}
    #query = update.callback_query
    #await query.answer()
    USER_STATE[update.effective_user.id] = {"mode": "buyer"}
    USER_MESSAGES = {}
    await update.callback_query.edit_message_text("Меню покупателя:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Просмотреть все картины", callback_data="view_cartine_buyer")],
        [InlineKeyboardButton("Выбрать картины по сюжетам", callback_data="select_theme")],
        [InlineKeyboardButton("Выбрать картины по размерам", callback_data="select_by_size")],
        [InlineKeyboardButton("Выбрать картины по ценам", callback_data="select_by_price")],
        [InlineKeyboardButton("Выйти из бота", callback_data="exitbot")]
    ]))


async def select_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Выберите папку для загрузки фотографий:",
                                                  reply_markup=get_folder_keyboard())

def get_folder_keyboard():
    keyboard = []
    for item in CURRENT_FOLDER.iterdir():
        if item.is_dir():
            keyboard.append([InlineKeyboardButton(item.name, callback_data=f"folder_{item.name}")])
    keyboard.append([InlineKeyboardButton(f"Выбрать текущую папку: {CURRENT_FOLDER.name}", callback_data="select_current_folder")])
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back")]),
    keyboard.append([InlineKeyboardButton("Вернуться в меню продавца", callback_data="seller_menu")])
    return InlineKeyboardMarkup(keyboard)


async def handle_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_FOLDER
    folder_name = update.callback_query.data.split("_")[1]
    if folder_name == "back":
        CURRENT_FOLDER = CURRENT_FOLDER.parent
    else:
        CURRENT_FOLDER = CURRENT_FOLDER / folder_name
    await update.callback_query.edit_message_text("Выберите папку:", reply_markup=get_folder_keyboard())


async def select_current_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PHOTO_FOLDER
    PHOTO_FOLDER = str(CURRENT_FOLDER)
    await update.callback_query.edit_message_text(f"Папка {CURRENT_FOLDER.name} выбрана успешно!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Загрузить фотографию", callback_data="upload_photo")],
        [InlineKeyboardButton("Отмена", callback_data="seller_menu")],
        [InlineKeyboardButton("Вернуться в меню продавца", callback_data="seller_menu")]
    ]))

### прроверка файла в базе данных
async def upload_photo_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global photo_index
    if PHOTO_FOLDER is None:
        await update.callback_query.edit_message_text("Папка с фотографиями не выбрана!")
        return

    photo_files = [f for f in os.listdir(PHOTO_FOLDER) if f.endswith(('.jpg', '.png', '.jpeg'))]
    if not photo_files:
        await update.callback_query.edit_message_text("Нет фотографий для загрузки!")
        return

    if photo_index < len(photo_files):
        number_of_1=len(photo_files)
        print(f"Количество картин в папке =: {number_of_1}")
       # await update.message.reply_text(f"Количество картин в базе данных: {number_of_cartine}")
        number_of_cartine= len(cartine)
        print(f"Картин в БД=: {number_of_cartine}")
        photo_path = os.path.join(PHOTO_FOLDER, photo_files[photo_index])

        # Проверяем и сжимаем изображение, если его размер больше 10 МБ
        compressed_path = os.path.join(PHOTO_FOLDER, f"compressed_{photo_files[photo_index]}")
        compressed_image_path = compress_image(photo_path, compressed_path)

        # Проверка, существует ли картина с таким именем в базе данных
        existing_cartina = next((item for item in cartine if item["name"] == photo_files[photo_index]), None)

        if existing_cartina:
            # Если картина с таким именем уже существует, предложить перезаписать информацию
            await update.callback_query.edit_message_text(
                f"Картина '{photo_files[photo_index]}' уже существует. "
                "Вы хотите перезаписать информацию о ней?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Перезаписать", callback_data=f"overwrite_{existing_cartina['id']}")],
                    [InlineKeyboardButton("Оставить без изменений и загрузить следующую", callback_data="keep_existing")],
                    [InlineKeyboardButton("Вернуться в меню продавца", callback_data="seller_menu")]
                ])
            )
            # Сохраняем путь к сжатому изображению в состоянии пользователя для возможного перезаписи
            USER_STATE[update.effective_user.id] = {
                "mode": "seller",
                "step": "awaiting_overwrite_decision",
                "photo_path": compressed_image_path,
                "cartina_id": existing_cartina["id"]
            }
        else:
            # Если картины с таким именем нет, добавляем её в базу данных
            with open(compressed_image_path, 'rb') as file:
                photo = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file)
                new_cartina = {
                    "id": len(cartine) + 1,
                    "name": photo_files[photo_index],
                    "description": "",
                    "sku": "",
                    "size": "",
                    "price": 0,
                    "photo": photo.photo[-1].file_id,  # Сохраняем file_id вместо file_path
                    "comments": []
                }
                cartine.append(new_cartina)
                save_database(cartine)

            USER_STATE[update.effective_user.id] = {
                "mode": "seller",
                "step": "awaiting_details",
                "photo_id": new_cartina["id"]
            }

            await update.callback_query.edit_message_text(
                "Картина загружена!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Внести название картины!", callback_data=f"add_details_{new_cartina['id']}")]
                ])
            )
            photo_index += 1
            # Удаляем временные файлы, если необходимо
            os.remove(compressed_image_path)
    else:
        await update.callback_query.edit_message_text("Нет фотографий для загрузки!")
# Обработчик для перезаписи информации о картине
async def handle_overwrite_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = USER_STATE.get(update.effective_user.id, {})
    if user_data.get("mode") == "seller" and user_data.get("step") == "awaiting_overwrite_decision":
        decision = update.callback_query.data.split("_")[0]
        if decision == "overwrite":
            cartina_id = user_data["cartina_id"]
            cartina = next(item for item in cartine if item["id"] == cartina_id)
            # Обновляем информацию о картине
            with open(user_data["photo_path"], 'rb') as file:
                photo = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file)
                cartina["photo"] = photo.photo[-1].file_id  # Обновляем file_id

            save_database(cartine)

            await update.callback_query.edit_message_text(
                "Информация о картине обновлена! Теперь введите название картины.")
            USER_STATE[update.effective_user.id] = {
                "mode": "seller",
                "step": "awaiting_details",
                "photo_id": cartina_id
            }
        elif decision == "keep_existing":
            await update.callback_query.edit_message_text("Картина оставлена без изменений.")
            os.remove(user_data["photo_path"])  # Удаляем временный файл, если не используется

#проверка файла в базе данных окончаие
async def count_cartine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number_of_cartine = len(cartine)
    await update.message.reply_text(f"Количество картин в базе данных: {number_of_cartine}")
###gпросмотр картин
USER_MESSAGES = {}

async def view_cartine_seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USER_MESSAGES[user_id] = []  # Инициализация списка для сообщений пользователя
    query = update.callback_query

    if not cartine:
        message = await query.edit_message_text("На данный момент в базе данных нет картин.")
        USER_MESSAGES[user_id].append(message.message_id)
        return

    for cartiny in cartine:
        message = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=cartiny["photo"],
                                               caption=f"Название: {cartiny['name']}\n"
                                                       f"Описание: {cartiny['description']}\n"
                                                       f"Сюжет: {cartiny['sku']}\n"
                                                       f"Размеры: {cartiny['size']}\n"
                                                       f"Цена: {cartiny['price']} руб.")
        USER_MESSAGES[user_id].append(message.message_id)
    # Создаем кнопку для очистки
    keyboard = [
        [InlineKeyboardButton("Очистить чат", callback_data='clear_chat')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение с кнопкой очистки чата
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text="Вы можете очистить чат, нажав кнопку ниже:",
                                             reply_markup=reply_markup)
    USER_MESSAGES[user_id].append(message.message_id)

    await query.answer()
    # Очищаем список сообщений пользователя
    #USER_MESSAGES[user_id] = []
    # Словарь для хранения сообщений, отправленных ботом
USER_MESSAGES = {}
async def view_cartine_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        USER_MESSAGES[user_id] = []  # Инициализация списка для сообщений пользователя

        query = update.callback_query

        if not cartine:
            message = await query.edit_message_text("На данный момент в базе данных нет картин.")
            USER_MESSAGES[user_id].append(message.message_id)
            return

        for cartin in cartine:
            message = await context.bot.send_photo(chat_id=update.effective_chat.id, photo=cartin["photo"],
                                                   caption=f"Название: {cartin['name']}\n"
                                                           f"Описание: {cartin['description']}\n"
                                                           f"Сюжет: {cartin['sku']}\n"
                                                           f"Размеры: {cartin['size']}\n"
                                                           f"Цена: {cartin['price']} руб.")
            USER_MESSAGES[user_id].append(message.message_id)

        # Создаем кнопку для очистки
        keyboard = [
            [InlineKeyboardButton("Очистить чат", callback_data='clear_chat')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение с кнопкой очистки чата
        message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                                 text="Вы можете очистить чат, нажав кнопку ниже:",
                                                 reply_markup=reply_markup)
        USER_MESSAGES[user_id].append(message.message_id)

        await query.answer()

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Удаляем все сообщения, сохраненные в USER_MESSAGES
        if user_id in USER_MESSAGES:
            for message_id in USER_MESSAGES[user_id]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                except Exception as e:
                    print(f"Не удалось удалить сообщение {message_id}: {e}")

        await update.callback_query.answer("Чат очищен.")
        # Очищаем список сообщений пользователя
        USER_MESSAGES[user_id] = []
       #cartine.clear()

async def select_by_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass  # Реализуйте функцию фильтрации по сюжету картин
#filter_and_sort_cartine(cartine, theme=None, min_price=None, max_price=None, sort_by=None):
async def show_theme_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Создаем кнопки для выбора сюжета
    keyboard = [
        [InlineKeyboardButton("Люди", callback_data='theme_people')],
        [InlineKeyboardButton("Пейзаж", callback_data='theme_landscape')],
        [InlineKeyboardButton("Город", callback_data='theme_city')],
        [InlineKeyboardButton("Село", callback_data='theme_village')],
        [InlineKeyboardButton("Натюрморт", callback_data='theme_still_life')],
        [InlineKeyboardButton("Цветы", callback_data='theme_flowers')],
        [InlineKeyboardButton("Столбы", callback_data='theme_poles')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение, показывая новые кнопки
    await query.edit_message_text('Выберите сюжет:', reply_markup=reply_markup)

async def select_by_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass  # Реализуйте функцию фильтрации по размеру картин


async def select_by_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass  # Реализуйте функцию фильтрации по цене картин
async def add_details_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cartina_id = int(update.callback_query.data.split("_")[2])
    USER_STATE[update.effective_user.id] = {
        "mode": "seller",
        "step": "awaiting_details",
        "photo_id": cartina_id,
        "message_id": message.message_id
    }
    await update.callback_query.edit_message_text("Введите название картины.")
###пароль и текст
async def check_password_and_handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = USER_STATE.get(user_id, {})

    if user_data.get("mode") == "seller" and user_data.get("step") == "awaiting_password":
        password = update.message.text
        if password == "1234":
            await update.message.delete()
            ###
            if "message_id" in user_data:
                message_id = user_data["message_id"]
                print(f"Сохраняем идентификатор сообщения: {message_id}")

                # Удаляем предыдущее сообщение с запросом на ввод пароля
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
                    print(f"Сообщение с запросом на ввод пароля с идентификатором {message_id} удалено.")
                except Exception as e:
                    print(f"Не удалось удалить предыдущее сообщение: {e}")
            else:
                print("Идентификатор сообщения не найден!")

            ###

            #if "message_id" in user_data:
             #   message_id = user_data["message_id"]
              #  print(f"Сохраняем идентификатор сообщения: {message_id}")
            #else:
             #   print("Идентификатор сообщения не найден!")
               #print(f"Сохраняем идентификатор сообщения: {message.message_id}")
            # Удаляем предыдущее сообщение с запросом на ввод пароля
            #if "message_id" in user_data:
             #   await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_data["message_id"])

            USER_STATE[user_id]["step"] = "seller_menu"
            await update.message.reply_text("Меню продавца:", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Загрузить картины", callback_data="select_folder")],
                [InlineKeyboardButton("Просмотреть картины", callback_data="view_cartine_seller")],
                [InlineKeyboardButton("Редактировать картины", callback_data="edit_cartine")],
                [InlineKeyboardButton("Зайти в режим покупателя", callback_data="buyer_mode")],
                [InlineKeyboardButton("Выйти из бота", callback_data="exitbot")]
            ]))
        else:
            await update.message.reply_text("Неверный пароль!")
            USER_STATE[user_id] = {"mode": "start"}
            await update.message.reply_text("Добро пожаловать в галерею моих картин!",
                                            reply_markup=InlineKeyboardMarkup([
                                                [InlineKeyboardButton("Продавец", callback_data="seller")],
                                                [InlineKeyboardButton("Покупатель", callback_data="buyer")]
                                            ]))

    elif user_data.get("mode") == "seller" and user_data.get("step") == "awaiting_details":
        cartine[-1]["name"] = update.message.text
        await update.message.reply_text("Введите описание картины:")
        USER_STATE[user_id]["step"] = "awaiting_description"
    elif user_data.get("mode") == "seller" and user_data.get("step") == "awaiting_description":
        cartine[-1]["description"] = update.message.text
        # Отправляем сообщения с выбором сюжета
        await update.message.reply_text("Введите сюжет картины. Выберите один из следующих:\n\n"
                                        "Люди\n"
                                        "Пейзаж\n"
                                        "Город\n"
                                        "Село\n"
                                        "Натюрморт\n"
                                        "Цветы\n"
                                        "Столбы")

        # Обновление состояния
        USER_STATE[user_id]["step"] = "awaiting_sku"
    elif user_data.get("mode") == "seller" and user_data.get("step") == "awaiting_sku":
        # Проверяем введенный текст и сопоставляем с сюжетом
        selected_theme = update.message.text.strip()
        themes_dict = {
            "Люди": "Люди",
            "Пейзаж": "Пейзаж",
            "Город": "Город",
            "Село": "Село",
            "Натюрморт": "Натюрморт",
            "Цветы": "Цветы",
            "Столбы": "Столбы"
        }

        if selected_theme in themes_dict:
            cartine[-1]["theme"] = themes_dict[selected_theme]
            await update.message.reply_text(f"Выбран сюжет: {themes_dict[selected_theme]}")
            await update.message.reply_text("Введите размеры картины:")
            USER_STATE[user_id]["step"] = "awaiting_size"
        else:
            await update.message.reply_text("Неверный сюжет. Попробуйте снова.")
    elif user_data.get("mode") == "seller" and user_data.get("step") == "awaiting_size":
        cartine[-1]["size"] = update.message.text
        await update.message.reply_text("Введите цену картины:")
        USER_STATE[user_id]["step"] = "awaiting_price"
    elif user_data.get("mode") == "seller" and user_data.get("step") == "awaiting_price":
        try:
            cartine[-1]["price"] = float(update.message.text)
            save_database(cartine)
            await update.message.reply_text("Картина успешно добавлена в базу данных!",
                                            reply_markup=InlineKeyboardMarkup([
                                                [InlineKeyboardButton("Загрузить еще картину",
                                                                      callback_data="upload_another")],
                                                [InlineKeyboardButton("Выйти", callback_data="exit")]
                                            ])
                                            )
            USER_STATE[user_id]["step"] = "awaiting_next_action"
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректную цену.")
# Асинхронная функция для выбора темы
async def select_theme(update: Update, context: ContextTypes.DEFAULT_TYPE, input_field_text=None):
    query = update.callback_query
    user_id = update.effective_user.id

    # Соответствие между callback_data и текстом сюжета
    themes = {
        "theme_people": "Люди",
        "theme_landscape": "Пейзаж",
        "theme_city": "Город",
        "theme_village": "Село",
        "theme_still_life": "Натюрморт",
        "theme_flowers": "Цветы",
        "theme_poles": "Столбы"
    }

    # Получение выбранной темы из callback_data
    selected_theme = themes.get(query.data, "Неизвестная тема")

    # Формирование текста для поля ввода (например, симулируем отправку в какое-то поле)
    input_field_text = f"Выбранный сюжет: {selected_theme}"

    # Формирование клавиатуры с подтверждением выбранной темы
    #keyboard = [
     #   [InlineKeyboardButton(f"✔️ {selected_theme}", callback_data=query.data)]
    #
    # Формирование кнопки с предложением отправить этот текст
    keyboard = [
        [InlineKeyboardButton(selected_theme, switch_inline_query=selected_theme)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправка сообщения с выбранным сюжетом
    #await query.edit_message_text(f"Выбранный сюжет: {selected_theme}", reply_markup=reply_markup)
    await query.edit_message_text(input_field_text, reply_markup=reply_markup)
async def handle_next_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == "upload_another":
        await upload_photo_button(update, context)  # Перейти к загрузке следующей картины
    elif update.callback_query.data == "exit":
        await update.callback_query.edit_message_text("Вы внесли новые данные в галерею ваших картин!")
        USER_STATE[update.effective_user.id]["step"] = "seller_menu"
        await update.callback_query.message.reply_text("Меню продавца:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Загрузить фотографию", callback_data="select_folder")],
            [InlineKeyboardButton("Просмотреть картины", callback_data="view_cartine_seller")],
            [InlineKeyboardButton("Добавить новую картину", callback_data="add_cartine")],
            [InlineKeyboardButton("Изменить информацию о картине", callback_data="edit_cartine")],
            [InlineKeyboardButton("Просмотреть папки", callback_data="view_folders")]
        ]))
# Использование фильтрации и сортировки в боте
async def handle_filter_and_sorting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cartine = load_database()
    # Пример фильтрации и сортировки
    theme = "пейзаж"
    sorted_cartine = filter_and_sort_cartine(cartine, theme=theme, sort_by="price")
    message = "\n".join([f"{c['name']} - {c['theme']} - {c['price']}" for c in sorted_cartine])
    await update.message.reply_text(f"Картины по сюжету '{theme}':\n\n{message}")

### функции очистки чатов
# Функция обработки выбора меню с удалением сообщений
async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query_data = query.data
    user_id = query.from_user.id

    # Удаляем предыдущее сообщение
    if user_id in USER_MESSAGES:
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=USER_MESSAGES[user_id])

    current_state = USER_STATES.get(user_id, "main_menu")

    if query_data == "back":
        current_state = USER_STATES.get(user_id, "main_menu")
    else:
        USER_STATES[user_id] = current_state
        current_state = query_data

    message = await query.message.edit_text("Выберите опцию:", reply_markup=get_menu_keyboard(current_state))

    # Сохраняем ID нового сообщения
    USER_MESSAGES[user_id] = message.message_id
    USER_STATES[user_id] = current_state

# Функция-обработчик для нажатия кнопки "Выйти из бота"

# Функция для обработки ответов
async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получение идентификатора последнего сообщения
    last_message_id = context.user_data.get('last_message_id')
    if last_message_id:
        try:
            # Удаление предыдущего сообщения
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=last_message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {last_message_id}: {e}")

    # Обработка ответа пользователя
    await update.message.reply_text(f"Вы ответили: {update.message.text}")

# Функция-обработчик для нажатия кнопки "Выйти"
async def exit_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Уведомление пользователя
    restart_message = await query.message.reply_text("Вы вышли из бота. Чтобы начать снова, отправьте команду /start.")
    context.user_data['restart_message_id'] = restart_message.message_id
    print(f"Сообщение с ID {restart_message.message_id} отправлено и сохранено.")

        # Проверяем наличие сообщения перед удалением

  #  context.user_data['exit_message_id'] = message_id
#    context.user_data['ext_message_id'] = update.message.message_id
    #await update.message.delete()

       # Очистка данных пользователя (опционально)
    context.user_data.clear()

    #context.user_data['start_message_id'] = update.message.message_id
    start_message_id = context.user_data.get('start_message_id')
    exit_message_id = context.user_data.get('exit_message_id')
    if start_message_id:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=start_message_id
        )

    if exit_message_id:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=exit_message_id
        )

    # Удаление сообщения с кнопками
    await query.message.delete()
###



# Удаление сообщения после 5 секунд
def delete_message(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    context.bot.delete_message(chat_id=job.context['chat_id'], message_id=job.context['message_id'])

###
async def delete_start_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    # Получаем ID сообщения /start из context.user_data
    start_message_id = context.user_data.get('start_message_id')
    if start_message_id:
        try:
            # Удаляем сообщение
            await context.bot.delete_message(chat_id=chat_id, message_id=start_message_id)
            print(f"Сообщение с ID {start_message_id} успешно удалено.")
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")
#context.user_data['ext_message_id'] = update.message.ext_message_id
async def delete_restart_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    #query = update.callback_query
    restart_message_id = context.user_data.get('restart_message_id')
    #await query.answer()

    # Удаляем новое сообщение с кнопкой
    if 'restart_message_id' in context.user_data:
        restart_message_id = context.user_data['restart_message_id']
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=restart_message_id)
            print(f"Сообщение с ID {restart_message_id} удалено.")
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")

async def handle_start_again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Удаляем сообщение "Вы вышли из бота..."
    exit_message_id = context.user_data.get('exit_message_id')
    if exit_message_id:
        await context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=exit_message_id
        )

    # Отправляем новое сообщение
    await query.message.reply_text("Вы снова в боте!")

def main():
    application = ApplicationBuilder().token('7373586628:AAGI3GvHfOMhiTAfO4WhVl9wu2cj_EzybP4').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(seller_mode, pattern="^seller$"))
    application.add_handler(CommandHandler('end_session', end_session))
    exit_button_handler = CallbackQueryHandler(exit_button, pattern='exitbot')

    application.add_handler(exit_button_handler)
    application.add_handler(CallbackQueryHandler(buyer_mode, pattern="buyer"))
    #application.add_handler(CallbackQueryHandler(buyer_mode, pattern="^buyer$"))
    application.add_handler(CallbackQueryHandler(select_folder, pattern="^select_folder$"))
    application.add_handler(CallbackQueryHandler(handle_folder, pattern="^folder_"))
    application.add_handler(CallbackQueryHandler(select_current_folder, pattern="^select_current_folder$"))
    application.add_handler(CallbackQueryHandler(upload_photo_button, pattern="^upload_photo$"))
    application.add_handler(CallbackQueryHandler(add_details_button, pattern="^add_details_"))

   # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
   # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details))

    #application.add_handler(CallbackQueryHandler(view_cartine_buyer, pattern="^view_cartine$"))
    #application.add_handler(CallbackQueryHandler(view_cartine_seller, pattern="^view_cartine$"))

    application.add_handler(CallbackQueryHandler(view_cartine_buyer, pattern="view_cartine_buyer"))
    application.add_handler(CallbackQueryHandler(view_cartine_seller, pattern="view_cartine_seller"))

    application.add_handler(CommandHandler("count_cartine", count_cartine))

    # Обработка фильтрации и сортировки
    application.add_handler(CommandHandler("filter_sort", handle_filter_and_sorting))
    application.add_handler(CallbackQueryHandler(show_theme_options, pattern="select_theme"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password_and_handle_details))
    application.add_handler(CallbackQueryHandler(handle_next_action, pattern="^(upload_another|exit)$"))
  #  application.add_handler(CallbackQueryHandler(select_theme, pattern="theme_"))

    #application.add_handler(CommandHandler("clear", clear_chat_2))  # Команда для очистки чата
    application.add_handler(CallbackQueryHandler(clear_chat, pattern='clear_chat'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))
    application.add_handler(CallbackQueryHandler(select_theme, pattern="theme_"))

   # application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_start_again, pattern="start_again"))
    application.add_handler(CommandHandler('delete_start_message', delete_start_message))
    application.add_handler(CommandHandler('delete_restart_message', delete_restart_message))

    application.run_polling()

if __name__ == '__main__':
    main()
