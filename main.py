import asyncio
from fastapi import FastAPI

from bot.telegram_commands import TelegramBot
from bot.telegram_notifier import TelegramNotifier

app = FastAPI(title="Telegram Bot API")

bot = TelegramBot()
bot_notifier = TelegramNotifier()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(bot.polling_commands())
    asyncio.create_task(bot_notifier.monitor_leaks_loop())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
