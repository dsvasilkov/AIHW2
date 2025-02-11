from aiogram.fsm.state import State, StatesGroup

class Profile(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()
    food_logging = State()
    workout_logging = State()

