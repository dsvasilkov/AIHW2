from aiogram.enums import ParseMode
from aiogram.types import Message, BufferedInputFile
from states import Profile
import httpx
from aiogram.dispatcher.router import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import API_KEY
import matplotlib.pyplot as plt
import io
import seaborn as sns


router = Router()

users = {}
workout_calories = {
    "бег": 300,
    "ходьба": 150,
    "плавание": 250,
    "велосипед": 280,
    "йога": 180,
    "силовая тренировка": 350
}

def setup_handlers(dp, Bot):
    dp.include_router(router)
    global bot
    bot = Bot

def calculate_water_goal(weight, activity, temperature):
    base = weight * 30
    activity_water = (activity // 30) * 500
    weather_water = 500 if temperature > 25 else 0
    return base + activity_water + weather_water

def calculate_calorie_goal(weight, height, age, activity):
    base = 10 * weight + 6.25 * height - 5 * age
    activity_calories = (activity // 30) * 200
    return base + activity_calories

async def get_temperature(city):
    async with httpx.AsyncClient() as client:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = await client.get(url)

        if response.status_code == 200:
            return response.json()["main"]["temp"]
        else:
            raise Exception(f"Ошибка API: {response.json().get('message')}")


async def get_food_info(product_name):
    async with httpx.AsyncClient() as client:
        url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            if products:  # Проверяем, есть ли найденные продукты
                first_product = products[0]
                return {
                    'name': first_product.get('product_name', 'Неизвестно'),
                    'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
                }
            return None
        print(f"Ошибка: {response.status_code}")
        return None


@router.message(Command("start"))
async def start(message: Message):
    await message.answer("Добро пожаловать! Используйте /set_profile, чтобы настроить свой профиль.")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/set_profile - Настройка профиля\n"
        "/log_water - Логирование воды\n"
        "/log_food - Логирование еды\n"
        "/log_workout - Логирование тренировок\n"
        "/check_progress - Прогресс по воде и калориям\n"
        "/progress_chart - Графики с прогрессом по воде и калориям\n"
        "/recommend - Рекомендации"
    )


@router.message(Command("set_profile"))
async def set_profile(message: Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(Profile.weight)

@router.message(Profile.weight)
async def profile_weight(message: Message, state: FSMContext):
    try:
        weight = int(message.text)
        await state.update_data(weight=weight)
        await message.answer("Введите ваш рост (в см):")
        await state.set_state(Profile.height)
    except ValueError:
        await message.answer("Пожалуйста, введите рост.")

@router.message(Profile.height)
async def profile_height(message: Message, state: FSMContext):
    try:
        height = int(message.text)
        await state.update_data(height=height)
        await message.answer("Введите ваш возраст:")
        await state.set_state(Profile.age)
    except ValueError:
        await message.answer("Пожалуйста, введите возраст.")

@router.message(Profile.age)
async def profile_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await message.answer("Сколько минут активности у вас в день?")
        await state.set_state(Profile.activity)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")

@router.message(Profile.activity)
async def profile_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        await state.update_data(activity=activity)
        await message.answer("В каком городе вы находитесь?")
        await state.set_state(Profile.city)
    except ValueError:
        await message.answer("Пожалуйста, введите название города.")

@router.message(Profile.city)
async def profile_city(message: Message, state: FSMContext):
    data = await state.get_data()
    city = message.text
    weight = data['weight']
    height = data['height']
    age = data['age']
    activity = data['activity']

    try:
        temperature = await get_temperature(city)
    except:
        await message.answer("Пожалуйста, введите название города.")
        await state.set_state(Profile.city)
        return

    water_goal = calculate_water_goal(weight, activity, temperature)
    calorie_goal = calculate_calorie_goal(weight, height, age, activity)

    users[message.from_user.id] = {
        "weight": weight,
        "height": height,
        "age": age,
        "activity": activity,
        "city": city,
        "water_goal": water_goal,
        "calorie_goal": calorie_goal,
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0,
    }

    await message.answer(f"Профиль настроен!\nЦель по воде: {water_goal} мл\nЦель по калориям: {calorie_goal} ккал")
    await state.clear()

@router.message(Command("log_water"))
async def log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте свой профиль с помощью /set_profile.")
        return

    try:
        amount = int(message.text.split(maxsplit=1)[1])
        users[user_id]['logged_water'] += amount
        remaining = users[user_id]['water_goal'] - users[user_id]['logged_water']
        await message.answer(f"Выпито {amount} мл воды. Осталось: {max(remaining, 0)} мл.")
    except:
        await message.answer("Использование: /log_water <количество>")

@router.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте свой профиль с помощью /set_profile.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /log_food <название продукта>")
        return

    food = args[1]
    food_info = await get_food_info(food)

    if not food_info:
        await message.answer("Еда не найдена.")
        return

    await state.update_data(food_info=food_info)
    await message.answer(f"{food.capitalize()} - {food_info["calories"]} ккал на 100 г. Сколько грамм вы съели?")
    await state.set_state(Profile.food_logging)

@router.message(Profile.food_logging)
async def log_food_grams(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    food_info = data.get('food_info')

    if not food_info:
        return

    try:
        grams = int(message.text)
        calories = grams * food_info['calories'] / 100
        users[user_id]['logged_calories'] += calories
        await message.answer(f"Записано: {calories:.1f} ккал.")
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число.")


@router.message(Command("log_workout"))
async def log_workout(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Пожалуйста, сначала настройте профиль с помощью /set_profile.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Использование: /log_workout <тип тренировки> <время (мин)>")
        return

    workout_type = args[1].lower()
    try:
        duration = int(args[2])
    except ValueError:
        await message.answer("Пожалуйста, укажите корректное время тренировки в минутах.")
        return

    if workout_type not in workout_calories:
        await message.answer(f"Неизвестный тип тренировки. Доступные тренировки: {', '.join(workout_calories.keys())}")
        return

    base_calories = workout_calories[workout_type]
    burned_calories = (duration / 30) * base_calories

    extra_water = (duration // 30) * 200

    users[user_id]['burned_calories'] += burned_calories
    users[user_id]['logged_water'] += extra_water

    await message.answer(
        f"🏋️‍♂️ {workout_type.capitalize()} {duration} минут — {burned_calories:.1f} ккал. "
        f"Дополнительно: выпейте {extra_water} мл воды."
    )


@router.message(Command("check_progress"))
async def check_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте свой профиль с помощью /set_profile.")
        return

    user_data = users[user_id]
    water_progress = user_data['logged_water']
    water_goal = user_data['water_goal']
    calories = user_data['logged_calories']
    burned_calories = user_data['burned_calories']
    calorie_goal = user_data['calorie_goal']

    await message.answer(
        f"📊 Прогресс:\n"
        f"Вода:\n"
        f"- Выпито: {water_progress} мл из {water_goal} мл.\n"
        f"- Осталось: {water_goal - water_progress} мл.\n\n"
        f"Калории:\n"
        f"- Потреблено: {calories:.1f} ккал из {calorie_goal} ккал.\n"
        f"- Сожжено: {burned_calories:.1f} ккал.\n"
        f"- Баланс: {calories - burned_calories:.1f} ккал."
    )


@router.message(Command("progress_chart"))
async def progress_chart(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Пожалуйста, сначала настройте профиль с помощью /set_profile.")
        return

    user_data = users[user_id]

    water_goal = user_data['water_goal']
    water_logged = user_data['logged_water']
    calorie_goal = user_data['calorie_goal']
    calorie_logged = user_data['logged_calories'] - user_data['burned_calories']

    fig, ax = plt.subplots(1, 2, figsize=(10, 5))
    sns.set_style("whitegrid")

    sns.barplot(x=["Выпито", "Осталось"], y=[water_logged, max(water_goal - water_logged, 0)], ax=ax[0], palette=["green", "blue"])
    ax[0].set_title("Прогресс по воде (мл)")
    ax[0].set_ylabel("мл")

    sns.barplot(x=["Потреблено", "Осталось"], y=[calorie_logged, max(calorie_goal - calorie_logged, 0)], ax=ax[1], palette=["red", "orange"])
    ax[1].set_title("Прогресс по калориям (ккал)")
    ax[1].set_ylabel("ккал")

    # Сохраняем график в буфер
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Создаём объект InputFile для aiogram
    photo = BufferedInputFile(buf.getvalue(), filename="progress.png")

    # Отправляем изображение пользователю
    await bot.send_photo(chat_id=message.chat.id, photo=photo, caption="📊 Ваш прогресс по воде и калориям.")

    buf.close()


low_calorie_foods = [
    "🥗 Салат (15 ккал на 100г)",
    "🥒 Огурец (16 ккал на 100г)",
    "🍅 Помидор (18 ккал на 100г)",
    "🍏 Яблоко (52 ккал на 100г)"
]

workout_recommendations = [
    ("🚶 Прогулка", 150),
    ("🏃 Бег", 300),
    ("🚴‍♂️ Велосипед", 250),
    ("🏋️ Тренажёрный зал", 350)
]

@router.message(Command("recommend"))
async def recommend(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль через /set_profile.")
        return

    user_data = users[user_id]
    calorie_balance = user_data['calorie_goal'] - (user_data['logged_calories'] - user_data['burned_calories'])

    food_recommendation = "\n".join(low_calorie_foods)

    workout_recommendation = [w[0] for w in workout_recommendations if w[1] <= calorie_balance]
    workout_text = "\n".join(workout_recommendation) if workout_recommendation else "Попробуйте лёгкую прогулку."

    await message.answer(
        f"**Рекомендованные продукты с низкой калорийностью:**\n{food_recommendation}\n\n"
        f"**Рекомендованные тренировки:**\n{workout_text}",
        parse_mode=ParseMode.MARKDOWN
    )
