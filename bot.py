import telebot
from telebot import types
import requests
import json
import sqlite3
import threading
import logging

logging.basicConfig(level=logging.ERROR)
bot = telebot.TeleBot('7979937153:AAHCnz14491woEq7ds6atdnUDbWesXUO7_Y')

# Добавление клавиатуры
keyboard = types.ReplyKeyboardMarkup(row_width=3,resize_keyboard=True)
bt = types.KeyboardButton('Прогноз погоды')
bt2 = types.KeyboardButton('Настройки')
keyboard.add(bt, bt2)
keyboard_inline_one = types.InlineKeyboardMarkup()
keyboard_inline_two = types.InlineKeyboardMarkup()
button = types.InlineKeyboardButton(text='Город по умолчанию', callback_data='get_weather')
button4 = types.InlineKeyboardButton(text='Другой город', callback_data='get_weather_city')
button2 = types.InlineKeyboardButton(text='Показать город по умолчанию', callback_data='default_city')
button3 = types.InlineKeyboardButton(text='Изменить город по умолчанию', callback_data='update_default_city')
keyboard_inline_one.add(button, button4)
keyboard_inline_two.add(button2, button3)

# Словарь для хранения городов пользователя

user_cities = {}
default_city = None

# объект блокировки
db_lock = threading.Lock()


@bot.message_handler(commands=['start'])
def start(message):
    # Получение информации о пользователе
    user = message.from_user
    bot.reply_to(message, f'Добро пожаловать, {user.first_name}!\n', reply_markup=keyboard)
    connect = sqlite3.connect('user.db')
    cursor = connect.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users_id(
    id INTEGER PRIMARY KEY,
    city varchar(30))""")

    # Проверяем пользователя по БД

    people_id = message.chat.id
    cursor.execute(f"SELECT id FROM users_id WHERE id = {people_id}")
    data = cursor.fetchone()

    if data is None:
        #add users
        user_id = message.chat.id
        city_table = 'не указан'
        cursor.execute("INSERT into users_id VALUES(?,?);", (user_id, city_table))
        connect.commit()
        connect.close
    else:
        bot.send_message(message.chat.id, f'Ваш пользователь аутентифицирован в боте.\nС возвращением {user.first_name}')


@bot.message_handler(func=lambda message: message.text.lower() == 'настройки')
def show_settings(message):
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard_inline_two)


# ВЫВОД ГОРОДА ПО УМОЛЧАНИЮ

@bot.callback_query_handler(func=lambda call: call.data == 'default_city')
def show_default_city(call):
    connect = sqlite3.connect('user.db')
    cursor = connect.cursor()
    chat_id = call.message.chat.id
    user_id = [call.from_user.id]
    default_city = cursor.execute(f"SELECT city FROM users_id WHERE id = ?", user_id)
    result = cursor.fetchone()  # Извлечение данных из курсора
    if result:
        default_city = result[0]  # Извлечение города из кортежа результата
        bot.send_message(chat_id, text=f'Ваш город по умолчанию: {default_city}')
    else:
        bot.send_message(chat_id, text='Город по умолчанию не установлен')

# ИЗМЕНЕНИЕ ГОРОДА ПО УМОЛЧАНИЮ

@bot.callback_query_handler(func=lambda call: call.data == 'update_default_city')
def update_default_city(call):
    connect = sqlite3.connect('user.db')
    cursor = connect.cursor()
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    bot.send_message(chat_id, "Введите новый город по умолчанию:")

    # Регистрация следующего шага для получения нового города
    bot.register_next_step_handler(call.message, lambda message: set_default_city(message, user_id, cursor, connect))

def set_default_city(message, user_id, cursor, connect):
    new_default_city = message.text.strip()

    # Захват блокировки
    with db_lock:
        cursor.execute("UPDATE users_id SET city = ? WHERE id = ?", (new_default_city, user_id))
        connect.commit()

    # Закрытие соединения
    connect.close()

    bot.send_message(message.chat.id, f'Город по умолчанию обновлен: {new_default_city}')


# ВЫВОД ИНЛАЙН КЛАВЫ НА ОПРЕДЕЛИНЕ ПО КАКОМУ УКАЗЫВАТЬ ГОРОД
@bot.message_handler(func=lambda message: message.text.lower() == 'прогноз погоды')
def show_weather(message):
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard_inline_one)

#

@bot.callback_query_handler(func=lambda call: call.data == 'get_weather')
def show_weather_default(call):
    connect = sqlite3.connect('user.db')
    cursor = connect.cursor()
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    cursor.execute("SELECT city FROM users_id WHERE id = ?", (user_id,))
    city = cursor.fetchone()[0]  # Извлечение данных из курсора
    try:
        if city:
            url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&lang=ru&appid=79d1ca96933b0328e1c7e3e7a26cb347'
            weather_data = requests.get(url).json()  # Получение данных о погоде
            weather_data_structure = json.dumps(weather_data, indent=2, ensure_ascii=False)
            bot.send_message(call.message.chat.id, 'Общая информация по погоде:')

            # Обработка запроса и превращение в объект

            weather_data = requests.get(url).json()

            weather_data_structure = json.dumps(weather_data, indent=2)

            # print(weather_data_structure)

            # Обработка переменных по структуре weather_data

            temperature = round(weather_data['main']['temp'])

            temperature_feels_like = round(weather_data['main']['feels_like'])

            temperature_min = round(weather_data['main']['temp_min'])
            temperature_max = round(weather_data['main']['temp_max'])

            speed_wind = weather_data['wind']['speed']

            bot.send_message(chat_id, f'Сейчас в {city} {temperature}°C\nОщущается как {temperature_feels_like}°C\n'
                                      f'Скорость ветра {speed_wind} м/c\n'
                                      f'Максимальная температура сегодня составит {temperature_max}°C \n'
                                      f'Минимальная температура составит {temperature_min}°C')
        connect.close()
    except Exception as e:
        logging.error('Произошла ошибка')
        bot.send_message(chat_id, 'Произошла ошибка. Убедитесь в достоверности данных')




@bot.callback_query_handler(func=lambda call: call.data == 'get_weather_city')
def callback_query(call):
    chat_id = call.message.chat.id

    # Запрос к пользователю для ввода города
    bot.send_message(chat_id, "Введите город:")

    # Получение города из сообщения и сохранение в словаре user_cities
    @bot.message_handler(func=lambda message: True)
    def get_city(message):
        try:
            user_cities[chat_id] = message.text
            city = message.text
            if city:
                url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&lang=ru&appid=79d1ca96933b0328e1c7e3e7a26cb347'
                weather_data = requests.get(url).json()  # Получение данных о погоде
                weather_data_structure = json.dumps(weather_data, indent=2, ensure_ascii=False)
                bot.send_message(chat_id, 'Общая информация по погоде:')

                # Обработка запроса и превращение в объект
                weather_data = requests.get(url).json()
                weather_data_structure = json.dumps(weather_data, indent=2)

                # Обработка переменных по структуре weather_data
                temperature = round(weather_data['main']['temp'])
                temperature_feels_like = round(weather_data['main']['feels_like'])
                temperature_min = round(weather_data['main']['temp_min'])
                temperature_max = round(weather_data['main']['temp_max'])
                speed_wind = weather_data['wind']['speed']

                bot.send_message(chat_id, f'Сейчас в {city} {temperature}°C\nОщущается как {temperature_feels_like}°C\n'
                                          f'Скорость ветра {speed_wind} м/c\n'
                                          f'Максимальная температура сегодня составит {temperature_max}°C \n'
                                          f'Минимальная температура составит {temperature_min}°C')

            # Зарегистрировать обработчик сообщений
            bot.register_next_step_handler(call.message, get_city)

            def send_weather_periodically():
                for chat_id, city in user_cities.items():
                    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&lang=ru&appid=79d1ca96933b0328e1c7e3e7a26cb347'
                    weather_data = requests.get(url).json()  # Получение данных о погоде
                    temperature = round(weather_data['main']['temp'])
                    bot.send_message(chat_id, f'Сейчас в {city} {temperature}°C')
        except Exception as e:
            logging.error('Произошла ошибка')
            bot.send_message(message.chat.id, 'Произошла ошибка. Убедитесь в достоверности данных')
@bot.polling(none_stop=True)
def handle_errors(message):
    logging.error(f'Произошла ошибка: {message}')


bot.polling()
