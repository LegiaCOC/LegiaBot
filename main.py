import json
import requests
import logging
import telebot
import os

# Налаштування токену бота та токену API Clash of Clans
BOT_TOKEN = "6923264970:AAG-UK-643h-f7FNvDZPDR-819Gc66h86yY"
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6ImQ5MWEwZmFiLWUxZTgtNDA0Yi1hNjM0LTBlMjY4ZWE4ZDRkMiIsImlhdCI6MTcxNjA0Mzg3MSwic3ViIjoiZGV2ZWxvcGVyLzdiY2E0ZjIxLWVkZjktYzhjNS1jMDJmLWIxNTU4NmY2YWEyMiIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjMxLjEyOC4yNDkuMTQ0IiwiNDYuMjU1LjMyLjciLCIxMDkuMjI3LjEwNy4xOCJdLCJ0eXBlIjoiY2xpZW50In1dfQ.M7T_2Qr7RTDkF4m5YzdnS56TviootR5jntxvsZhJwbEj6FERQHT3Li0e0Zw7AXhGaNk2gGsr7-B_YVA6JZaxXA"
CLAN_TAG = '2G98GL9QC'  # Тег вашого клану

# Налаштування логування
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Обробник логування для виводу в термінал
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Обробник логування для виводу у файл
file_handler = logging.FileHandler("bot.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Функція для отримання списку учасників клану з API Clash of Clans
def get_clan_members(clan_tag):
    logger.info(f"Отримання списку учасників клану з тегом {clan_tag}")
    url = f"https://api.clashofclans.com/v1/clans/%23{clan_tag}/members"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        members = data.get("items", [])
        logger.info(f"Отримано список учасників клану: {len(members)} учасників")
        return members
    except requests.exceptions.RequestException as e:
        logger.error(f"Помилка запиту до API: {e}")
        return []
    except (ValueError, KeyError):
        logger.error("Неочікуваний формат відповіді API")
        return []

# Завантаження існуючої бази даних
if os.path.exists("database.json"):
    with open("database.json", "r") as f:
        db = json.load(f)
    logger.info("Існуюча база даних завантажена")
else:
    db = {}
    logger.info("Створено нову базу даних")

# Отримання нових даних учасників
members = get_clan_members(CLAN_TAG)

# Оновлення бази даних новими учасниками
for member in members:
    tag = member["tag"]
    name = member["name"]
    if tag not in db:
        user_data = {
            "tag": tag,
            "name": name,
            "telegram_id": None,
            "registered": False,
            "password": None
        }
        db[tag] = user_data
        logger.info(f"Додано нового користувача {name} ({tag}) до бази даних")

# Зберігання оновленої бази даних у файл
with open("database.json", "w") as f:
    json.dump(db, f, indent=4)
logger.info("База даних JSON успішно оновлена")


bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    logger.info(f"Користувач {message.chat.id} почав роботу з ботом")
    telegram_id = str(message.chat.id)
    registered_user = next((user for user in db.values() if str(user["telegram_id"]) == telegram_id), None)
    if registered_user:
        logger.info(f"Користувач {message.chat.id} вже зареєстрований")
        name = registered_user["name"]
        msg = f"З поверненням, {name}!"
        bot.reply_to(message, msg)
    else:
        msg = "Вітаю! Введіть свій тег учасника клану <b>(#\u200BXXXXXXX)</b>:"
        bot.reply_to(message, msg, parse_mode='HTML')
        bot.register_next_step_handler(message, handle_tag)


# Обробник отримання тегу учасника клану
def handle_tag(message):
    logger.info(f"Користувач {message.chat.id} ввів тег учасника")
    tag = message.text.upper()
    if tag in db:
        name = db[tag]["name"]
        db[tag]["telegram_id"] = message.chat.id
        msg = f"Привіт, {name}! Введіть ваш пароль для реєстрації:"
        bot.reply_to(message, msg)
        bot.register_next_step_handler(message, handle_password)
    else:
        logger.warning(f"Тег {tag} не знайдено в базі даних")
        msg = "Тег не знайдено в клані. Спробуйте ще раз."
        bot.reply_to(message, msg)
        bot.register_next_step_handler(message, handle_tag)


# Обробник реєстрації пароля
def handle_password(message):
    logger.info(f"Користувач {message.chat.id} намагається зареєструватися")
    tag = None
    for user_tag, user_data in db.items():
        if user_data["telegram_id"] == message.chat.id:
            tag = user_tag
            break
    if tag:
        db[tag]["password"] = message.text
        db[tag]["registered"] = True
        with open("database.json", "w") as f:
            json.dump(db, f)
        msg = f"Реєстрація успішна, {db[tag]['name']}!"
        bot.reply_to(message, msg)
        logger.info(f"Користувач {message.chat.id} успішно зареєстрований")
    else:
        logger.warning(f"Не вдалося знайти користувача з ID {message.chat.id} в базі даних")
        msg = "Щось пішло не так, спробуйте ще раз команду /start"
        bot.reply_to(message, msg)


# Обробник авторизації
@bot.message_handler(func=lambda message: any(str(message.chat.id) == str(user["telegram_id"]) for user in db.values()))
def handle_auth(message):
    logger.info(f"Користувач {message.chat.id} намагається авторизуватися")
    for user in db.values():
        if str(message.chat.id) == str(user["telegram_id"]):
            if user["registered"]:
                name = user["name"]
                msg = f"Привіт, {name}! Ви вже зареєстровані."
                bot.reply_to(message, msg)
                logger.info(f"Користувач {message.chat.id} успішно авторизований")
            else:
                msg = "Ви ще не завершили реєстрацію. Введіть команду /start"
                bot.reply_to(message, msg)
                logger.warning(f"Користувач {message.chat.id} не зареєстрований")
            break


# Запуск бота
logger.info("Запуск бота...")
bot.polling()
