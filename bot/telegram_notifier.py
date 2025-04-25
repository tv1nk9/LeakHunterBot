import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

class TelegramNotifier:
    def __init__(self):
        load_dotenv()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.send_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.db_service_url = os.getenv("DB_SERVICE_URL")  # URL микросервиса для работы с БД
        self.check_interval = 3600  # Интервал проверки утечек в секундах (1 час)

    async def send_message(self, chat_id: int, text: str) -> bool:
        """Отправляет сообщение пользователю в Telegram."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.send_url, data={"chat_id": chat_id, "text": text})
        return resp.status_code == 200

    async def get_users(self) -> dict:
        """Получает список пользователей из БД."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.db_service_url}/users")
            if response.status_code == 200:
                return response.json()  # Ожидается, что API вернет словарь {email: chat_id}
            return {}
    
    async def get_leaks(self) -> list:
        """Получает список утечек из БД."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.db_service_url}/leaks")
            if response.status_code == 200:
                return response.json()  # Ожидается, что API вернет список утечек
            return []

    async def update_leak(self, leak_id: int, notified: bool):
        """Обновляет статус уведомления для утечки."""
        async with httpx.AsyncClient() as client:
            await client.patch(f"{self.db_service_url}/leaks/{leak_id}", json={"notified": notified})

    async def monitor_leaks_loop(self):
        """Основной цикл мониторинга утечек."""
        print("Start monitoring leaks")
        
        while True:
            try:
                users = await self.get_users()
                leaks = await self.get_leaks()
            except Exception as e:
                print(f"Error fetching data: {e}")
                await asyncio.sleep(self.check_interval)
                continue

            updated = False
            for leak in leaks:
                if not leak.get("notified", False):
                    chat_id = users.get(leak["email"])
                    if chat_id:
                        msg = (
                            f"⚠️ Утечка!\n"
                            f"Email: {leak['email']}\n"
                            f"Источник: {leak['source']}\n"
                            f"Детали: {leak.get('leak_info', 'нет данных')}"
                        )
                        ok = await self.send_message(chat_id, msg)
                        if ok:
                            await self.update_leak(leak["id"], True)
                            updated = True

            if updated:
                print("Уведомления отправлены и утечки обновлены.")

            await asyncio.sleep(self.check_interval)