import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from datetime import datetime, timedelta

API_TOKEN = '7863880912:AAGeVZrF23r41XW5lgrgOMiHyR_m76rJVAA'

logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Создание таблицы users, если она не существует
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, 
    full_name TEXT,
    phone TEXT
    )
    ''')
    # Удаление старой таблицы visits, если она существует
    cursor.execute('DROP TABLE IF EXISTS visits')
    # Создание новой таблицы visits с обновлённой структурой
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    visit_category TEXT,
    target_name TEXT,
    spec_or_position TEXT,
    organization TEXT,
    location_text TEXT,  -- Новый столбец для региона и района
    visit_topic TEXT,
    visit_result TEXT,
    latitude REAL,
    longitude REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

init_db()  # Инициализация базы данных с новой структурой

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AuthStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_name = State()
    waiting_for_phone = State()

class VisitRegistrationStates(StatesGroup):
    choosing_category = State()
    waiting_for_name = State()
    waiting_for_spec_or_position = State()
    waiting_for_organization = State()
    waiting_for_location_text = State()
    waiting_for_topic = State()
    waiting_for_result = State()
    waiting_for_location = State()

class SettingsStates(StatesGroup):
    choosing_option = State()
    waiting_for_new_full_name = State()
    waiting_for_new_phone = State()

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
    [KeyboardButton(text="📝 Зарегистрировать визит")],
    [KeyboardButton(text="📊 Сформировать отчет")],
    [KeyboardButton(text="📢 Получить рекламный материал")],
    [KeyboardButton(text="⚙️ Настройка данных")],
    [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

location_keyboard = ReplyKeyboardMarkup(
    keyboard=[
    [KeyboardButton(text="📍 Отправить локацию", request_location=True)],
    [KeyboardButton(text="🔙 Вернуться в главное меню")]
    ],
    resize_keyboard=True
)

# Регистрация и авторизация
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await message.answer("Введите код:")
    await state.set_state(AuthStates.waiting_for_code)

@dp.message(AuthStates.waiting_for_code)
async def code_handler(message: types.Message, state: FSMContext):
    if message.text == "12051993":
        await message.answer("Код верный. Введите, пожалуйста, ваше ФИО:")
        await state.set_state(AuthStates.waiting_for_name)
    else:
        await message.answer("Неверный код. Попробуйте ещё раз:")

@dp.message(AuthStates.waiting_for_name)
async def name_handler(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Отправьте номер телефона:")
    await state.set_state(AuthStates.waiting_for_phone)

@dp.message(AuthStates.waiting_for_phone)
async def phone_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    full_name = user_data.get("full_name")
    phone = message.text
    user_id = message.from_user.id
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO users (user_id, full_name, phone)
    VALUES (?, ?, ?)
    ''', (user_id, full_name, phone))
    conn.commit()
    conn.close()
    await message.answer("Вы успешно авторизовались! Выберите действие:", reply_markup=main_menu_keyboard)
    await state.clear()

# Обработка визитов
@dp.message(F.text == "📝 Зарегистрировать визит")
async def register_visit_handler(message: types.Message, state: FSMContext):
    visit_keyboard = ReplyKeyboardMarkup(
    keyboard=[
    [KeyboardButton(text="👨‍⚕️ Врач")],
    [KeyboardButton(text="🏥 Аптека")],
    [KeyboardButton(text="📦 Дистрибьютор")],
    [KeyboardButton(text="🔙 Вернуться в главное меню")]
    ],
    resize_keyboard=True
    )
    await message.answer("Выберите категорию визита:", reply_markup=visit_keyboard)
    await state.set_state(VisitRegistrationStates.choosing_category)

@dp.message(VisitRegistrationStates.choosing_category)
async def process_category_selection(message: types.Message, state: FSMContext):
    if message.text not in ["👨‍⚕️ Врач", "🏥 Аптека", "📦 Дистрибьютор"]:
        await message.answer("Пожалуйста, выберите категорию из предложенных:")
        return
    await state.update_data(visit_category=message.text)
    if message.text == "👨‍⚕️ Врач":
        await message.answer("Введите ФИО врача:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(VisitRegistrationStates.waiting_for_name)
    else:
        await message.answer("Введите должность сотрудника:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(VisitRegistrationStates.waiting_for_spec_or_position)

@dp.message(VisitRegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(target_name=message.text)
    await message.answer("Введите специальность врача:")
    await state.set_state(VisitRegistrationStates.waiting_for_spec_or_position)

@dp.message(VisitRegistrationStates.waiting_for_spec_or_position)
async def process_spec_or_position(message: types.Message, state: FSMContext):
    await state.update_data(spec_or_position=message.text)
    await message.answer("Введите организацию:")
    await state.set_state(VisitRegistrationStates.waiting_for_organization)

@dp.message(VisitRegistrationStates.waiting_for_organization)
async def process_organization(message: types.Message, state: FSMContext):
    await state.update_data(organization=message.text)
    await message.answer("Введите регион и район (например: Ташкент, Юнусабадский район):")
    await state.set_state(VisitRegistrationStates.waiting_for_location_text)

@dp.message(VisitRegistrationStates.waiting_for_location_text)
async def process_location_text(message: types.Message, state: FSMContext):
    await state.update_data(location_text=message.text)
    await message.answer("Введите тему визита:")
    await state.set_state(VisitRegistrationStates.waiting_for_topic)

@dp.message(VisitRegistrationStates.waiting_for_topic)
async def process_topic(message: types.Message, state: FSMContext):
    await state.update_data(visit_topic=message.text)
    await message.answer("Опишите результат визита:")
    await state.set_state(VisitRegistrationStates.waiting_for_result)

@dp.message(VisitRegistrationStates.waiting_for_result)
async def process_result(message: types.Message, state: FSMContext):
    await state.update_data(visit_result=message.text)
    await message.answer("Отправьте геолокацию:", reply_markup=location_keyboard)
    await state.set_state(VisitRegistrationStates.waiting_for_location)

@dp.message(VisitRegistrationStates.waiting_for_location, F.location)
async def process_location(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
    INSERT INTO visits (
    user_id, visit_category, target_name, spec_or_position, 
    organization, location_text, visit_topic, visit_result, latitude, longitude
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
    message.from_user.id,
    user_data.get("visit_category"),
    user_data.get("target_name", None),  # Только для врачей
    user_data.get("spec_or_position"),
    user_data.get("organization"),
    user_data.get("location_text"),
    user_data.get("visit_topic"),
    user_data.get("visit_result"),
    message.location.latitude,
    message.location.longitude
    ))
        conn.commit()
        await message.answer("✅ Визит успешно зарегистрирован!", reply_markup=main_menu_keyboard)
    except Exception as e:
        logging.error(f"Database error: {e}")
        await message.answer("❌ Ошибка при сохранении данных", reply_markup=main_menu_keyboard)
    finally:
        conn.close()
        await state.clear()

# Обработчик для кнопки "📊 Сформировать отчет"
@dp.message(F.text == "📊 Сформировать отчет")
async def report_menu_handler(message: types.Message):
    report_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="За сегодня")],
            [KeyboardButton(text="За неделю")],
            [KeyboardButton(text="За месяц")],
            [KeyboardButton(text="🔙 Вернуться в главное меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите период для формирования отчета:", reply_markup=report_keyboard)

@dp.message(F.text == "За сегодня")
async def report_today_handler(message: types.Message):
    user_id = message.from_user.id
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now()

    # Получаем данные из базы данных за сегодня
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT visit_category, target_name, organization, spec_or_position, visit_result, latitude, longitude 
        FROM visits 
        WHERE user_id = ? AND timestamp BETWEEN ? AND ?
    ''', (user_id, today_start, today_end))
    visits = cursor.fetchall()
    conn.close()

    # Формируем отчет
    report_text = "*Отчет за сегодня:*\n"
    doctors_data = []
    pharmacy_distributor_data = []

    for visit in visits:
        category, target_name, organization, spec_or_position, visit_result, latitude, longitude = visit
        location = f"📍 Широта: {latitude}, Долгота: {longitude}" if latitude and longitude else "📍 Локация не указана"
        visit_info = (
            f"   🏢 Организация: {organization}\n"
            f"   👨‍💼 Специальность/Должность: {spec_or_position}\n"
            f"   ✅ Результат визита: {visit_result}\n"
            f"   {location}\n"
        )
        if category == "👨‍⚕️ Врач":
            doctors_data.append(f"👨‍⚕️ *ФИО врача:* {target_name}\n{visit_info}")
        elif category in ["🏥 Аптека", "📦 Дистрибьютор"]:
            pharmacy_distributor_data.append(f"🏥/📦 *Организация:* {organization}\n{visit_info}")

    # Формируем текст для врачей
    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "👨‍⚕️ *Врачи*\n"
    if doctors_data:
        report_text += "\n".join(doctors_data)
    else:
        report_text += "❌ Нет данных о визитах к врачам.\n"

    # Формируем текст для аптек/дистрибьюторов
    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "🏥/📦 *Аптеки/Дистрибьюторы*\n"
    if pharmacy_distributor_data:
        report_text += "\n".join(pharmacy_distributor_data)
    else:
        report_text += "❌ Нет данных о визитах к аптекам/дистрибьюторам.\n"

    # Добавляем % выполнения плана
    total_doctors = len(doctors_data)
    total_pharmacy_distributor = len(pharmacy_distributor_data)

    min_doctor_plan = 8
    max_doctor_plan = 12
    min_pharmacy_distributor_plan = 6
    max_pharmacy_distributor_plan = 10

    doctor_min_percent = (total_doctors / min_doctor_plan) * 100 if total_doctors <= min_doctor_plan else 100
    doctor_max_percent = (total_doctors / max_doctor_plan) * 100 if total_doctors <= max_doctor_plan else 100

    pharmacy_distributor_min_percent = (total_pharmacy_distributor / min_pharmacy_distributor_plan) * 100 if total_pharmacy_distributor <= min_pharmacy_distributor_plan else 100
    pharmacy_distributor_max_percent = (total_pharmacy_distributor / max_pharmacy_distributor_plan) * 100 if total_pharmacy_distributor <= max_pharmacy_distributor_plan else 100

    total_visits = total_doctors + total_pharmacy_distributor
    total_min_plan = min_doctor_plan + min_pharmacy_distributor_plan
    total_max_plan = max_doctor_plan + max_pharmacy_distributor_plan

    total_min_percent = (total_visits / total_min_plan) * 100 if total_visits <= total_min_plan else 100
    total_max_percent = (total_visits / total_max_plan) * 100 if total_visits <= total_max_plan else 100

    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "*Процент выполнения плана:*\n"
    report_text += (
        f"👨‍⚕️ Врачи:\n"
        f"   Минимального: {total_doctors}/{min_doctor_plan} - *{doctor_min_percent:.2f}%*\n"
        f"   Максимального: {total_doctors}/{max_doctor_plan} - *{doctor_max_percent:.2f}%*\n\n"
        f"🏥/📦 Аптеки/Дистрибьюторы:\n"
        f"   Минимального: {total_pharmacy_distributor}/{min_pharmacy_distributor_plan} - *{pharmacy_distributor_min_percent:.2f}%*\n"
        f"   Максимального: {total_pharmacy_distributor}/{max_pharmacy_distributor_plan} - *{pharmacy_distributor_max_percent:.2f}%*\n\n"
        f"📈 Общий процент выполнения плана:\n"
        f"   Минимального: {total_visits}/{total_min_plan} - *{total_min_percent:.2f}%*\n"
        f"   Максимального: {total_visits}/{total_max_plan} - *{total_max_percent:.2f}%*\n"
    )

    await message.answer(report_text, reply_markup=main_menu_keyboard, parse_mode="Markdown")

@dp.message(F.text == "За неделю")
async def report_week_handler(message: types.Message):
    user_id = message.from_user.id
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Начало недели (понедельник)
    end_of_week = today

    # Получаем данные из базы данных за неделю
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT visit_category, target_name, organization, spec_or_position, visit_result, latitude, longitude 
        FROM visits 
        WHERE user_id = ? AND timestamp BETWEEN ? AND ?
    ''', (user_id, start_of_week, end_of_week))
    visits = cursor.fetchall()
    conn.close()

    # Формируем отчет
    report_text = "*Отчет за неделю:*\n"
    doctors_data = []
    pharmacy_distributor_data = []

    for visit in visits:
        category, target_name, organization, spec_or_position, visit_result, latitude, longitude = visit
        location = f"📍 Широта: {latitude}, Долгота: {longitude}" if latitude and longitude else "📍 Локация не указана"
        visit_info = (
            f"   🏢 Организация: {organization}\n"
            f"   👨‍💼 Специальность/Должность: {spec_or_position}\n"
            f"   ✅ Результат визита: {visit_result}\n"
            f"   {location}\n"
        )
        if category == "👨‍⚕️ Врач":
            doctors_data.append(f"👨‍⚕️ *ФИО врача:* {target_name}\n{visit_info}")
        elif category in ["🏥 Аптека", "📦 Дистрибьютор"]:
            pharmacy_distributor_data.append(f"🏥/📦 *Организация:* {organization}\n{visit_info}")

    # Формируем текст для врачей
    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "👨‍⚕️ *Врачи*\n"
    if doctors_data:
        report_text += "\n".join(doctors_data)
    else:
        report_text += "❌ Нет данных о визитах к врачам.\n"

    # Формируем текст для аптек/дистрибьюторов
    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "🏥/📦 *Аптеки/Дистрибьюторы*\n"
    if pharmacy_distributor_data:
        report_text += "\n".join(pharmacy_distributor_data)
    else:
        report_text += "❌ Нет данных о визитах к аптекам/дистрибьюторам.\n"

    # Добавляем % выполнения плана
    total_doctors = len(doctors_data)
    total_pharmacy_distributor = len(pharmacy_distributor_data)

    min_doctor_plan = 40
    max_doctor_plan = 60
    min_pharmacy_distributor_plan = 30
    max_pharmacy_distributor_plan = 50

    doctor_min_percent = (total_doctors / min_doctor_plan) * 100 if total_doctors <= min_doctor_plan else 100
    doctor_max_percent = (total_doctors / max_doctor_plan) * 100 if total_doctors <= max_doctor_plan else 100

    pharmacy_distributor_min_percent = (total_pharmacy_distributor / min_pharmacy_distributor_plan) * 100 if total_pharmacy_distributor <= min_pharmacy_distributor_plan else 100
    pharmacy_distributor_max_percent = (total_pharmacy_distributor / max_pharmacy_distributor_plan) * 100 if total_pharmacy_distributor <= max_pharmacy_distributor_plan else 100

    total_visits = total_doctors + total_pharmacy_distributor
    total_min_plan = min_doctor_plan + min_pharmacy_distributor_plan
    total_max_plan = max_doctor_plan + max_pharmacy_distributor_plan

    total_min_percent = (total_visits / total_min_plan) * 100 if total_visits <= total_min_plan else 100
    total_max_percent = (total_visits / total_max_plan) * 100 if total_visits <= total_max_plan else 100

    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "*Процент выполнения плана:*\n"
    report_text += (
        f"👨‍⚕️ Врачи:\n"
        f"   Минимального: {total_doctors}/{min_doctor_plan} - *{doctor_min_percent:.2f}%*\n"
        f"   Максимального: {total_doctors}/{max_doctor_plan} - *{doctor_max_percent:.2f}%*\n\n"
        f"🏥/📦 Аптеки/Дистрибьюторы:\n"
        f"   Минимального: {total_pharmacy_distributor}/{min_pharmacy_distributor_plan} - *{pharmacy_distributor_min_percent:.2f}%*\n"
        f"   Максимального: {total_pharmacy_distributor}/{max_pharmacy_distributor_plan} - *{pharmacy_distributor_max_percent:.2f}%*\n\n"
        f"📈 Общий процент выполнения плана:\n"
        f"   Минимального: {total_visits}/{total_min_plan} - *{total_min_percent:.2f}%*\n"
        f"   Максимального: {total_visits}/{total_max_plan} - *{total_max_percent:.2f}%*\n"
    )

    await message.answer(report_text, reply_markup=main_menu_keyboard, parse_mode="Markdown")

@dp.message(F.text == "За месяц")
async def report_month_handler(message: types.Message):
    user_id = message.from_user.id
    today = datetime.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = today

    # Получаем данные из базы данных за месяц
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT visit_category, target_name, organization, spec_or_position, visit_result, latitude, longitude 
        FROM visits 
        WHERE user_id = ? AND timestamp BETWEEN ? AND ?
    ''', (user_id, start_of_month, end_of_month))
    visits = cursor.fetchall()
    conn.close()

    # Формируем отчет
    report_text = "*Отчет за месяц:*\n"
    doctors_data = []
    pharmacy_distributor_data = []

    for visit in visits:
        category, target_name, organization, spec_or_position, visit_result, latitude, longitude = visit
        location = f"📍 Широта: {latitude}, Долгота: {longitude}" if latitude and longitude else "📍 Локация не указана"
        visit_info = (
            f"   🏢 Организация: {organization}\n"
            f"   👨‍💼 Специальность/Должность: {spec_or_position}\n"
            f"   ✅ Результат визита: {visit_result}\n"
            f"   {location}\n"
        )
        if category == "👨‍⚕️ Врач":
            doctors_data.append(f"👨‍⚕️ *ФИО врача:* {target_name}\n{visit_info}")
        elif category in ["🏥 Аптека", "📦 Дистрибьютор"]:
            pharmacy_distributor_data.append(f"🏥/📦 *Организация:* {organization}\n{visit_info}")

    # Формируем текст для врачей
    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "👨‍⚕️ *Врачи*\n"
    if doctors_data:
        report_text += "\n".join(doctors_data)
    else:
        report_text += "❌ Нет данных о визитах к врачам.\n"

    # Формируем текст для аптек/дистрибьюторов
    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "🏥/📦 *Аптеки/Дистрибьюторы*\n"
    if pharmacy_distributor_data:
        report_text += "\n".join(pharmacy_distributor_data)
    else:
        report_text += "❌ Нет данных о визитах к аптекам/дистрибьюторам.\n"

    # Добавляем % выполнения плана
    total_doctors = len(doctors_data)
    total_pharmacy_distributor = len(pharmacy_distributor_data)

    min_doctor_plan = 160
    max_doctor_plan = 240
    min_pharmacy_distributor_plan = 120
    max_pharmacy_distributor_plan = 200

    doctor_min_percent = (total_doctors / min_doctor_plan) * 100 if total_doctors <= min_doctor_plan else 100
    doctor_max_percent = (total_doctors / max_doctor_plan) * 100 if total_doctors <= max_doctor_plan else 100

    pharmacy_distributor_min_percent = (total_pharmacy_distributor / min_pharmacy_distributor_plan) * 100 if total_pharmacy_distributor <= min_pharmacy_distributor_plan else 100
    pharmacy_distributor_max_percent = (total_pharmacy_distributor / max_pharmacy_distributor_plan) * 100 if total_pharmacy_distributor <= max_pharmacy_distributor_plan else 100

    total_visits = total_doctors + total_pharmacy_distributor
    total_min_plan = min_doctor_plan + min_pharmacy_distributor_plan
    total_max_plan = max_doctor_plan + max_pharmacy_distributor_plan

    total_min_percent = (total_visits / total_min_plan) * 100 if total_visits <= total_min_plan else 100
    total_max_percent = (total_visits / total_max_plan) * 100 if total_visits <= total_max_plan else 100

    report_text += "\n*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*\n"
    report_text += "*Процент выполнения плана:*\n"
    report_text += (
        f"👨‍⚕️ Врачи:\n"
        f"   Минимального: {total_doctors}/{min_doctor_plan} - *{doctor_min_percent:.2f}%*\n"
        f"   Максимального: {total_doctors}/{max_doctor_plan} - *{doctor_max_percent:.2f}%*\n\n"
        f"🏥/📦 Аптеки/Дистрибьюторы:\n"
        f"   Минимального: {total_pharmacy_distributor}/{min_pharmacy_distributor_plan} - *{pharmacy_distributor_min_percent:.2f}%*\n"
        f"   Максимального: {total_pharmacy_distributor}/{max_pharmacy_distributor_plan} - *{pharmacy_distributor_max_percent:.2f}%*\n\n"
        f"📈 Общий процент выполнения плана:\n"
        f"   Минимального: {total_visits}/{total_min_plan} - *{total_min_percent:.2f}%*\n"
        f"   Максимального: {total_visits}/{total_max_plan} - *{total_max_percent:.2f}%*\n"
    )

    await message.answer(report_text, reply_markup=main_menu_keyboard, parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())