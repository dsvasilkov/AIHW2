import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")
