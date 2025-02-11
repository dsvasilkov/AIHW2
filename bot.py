import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from handlers import setup_handlers
from middlewares import LoggingMiddleware


bot = Bot(token=TOKEN)
dp = Dispatcher()

dp.message.middleware(LoggingMiddleware())
setup_handlers(dp, bot)

async def main():
    print("Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



