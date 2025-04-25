import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

class TelegramBot:
    def __init__(self):
        load_dotenv()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.get_updates_url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        self.send_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.db_service_url = os.getenv("DB_SERVICE_URL")  # URL микросервиса для работы с БД
        self.poll_interval = 1
        self.timeout = 20
        self.wait_to_add_email = set()
        self.waiting_for_unsubscribe_email = set()  # Множество для отслеживания пользователей, ожидающих ввода email
    
    async def send_message(self, chat_id: int, text: str):
        async with httpx.AsyncClient() as client:
            await client.post(self.send_url, data={"chat_id": chat_id, "text": text})

    async def add_user(self, email: str, chat_id: int):
        """Отправляет запрос на добавление пользователя в базу данных через API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.db_service_url}/users",
                json={"email": email, "chat_id": chat_id}
            )
            return response.status_code == 201

    async def delete_user(self, email: str):
        """Отправляет запрос на удаление пользователя из базы данных через API."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.db_service_url}/users/{email}")
            return response.status_code == 200

    async def email_exists(self, email: str) -> bool:
        """Проверяет, существует ли email в базе данных через API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.db_service_url}/users/{email}")
            return response.status_code == 200

    async def handle_start(self, chat_id: int):
        self.wait_to_add_email.add(chat_id)
        await self.send_message(chat_id, "👋 Привет! Пришли мне свой email для подписки на утечки.")

    async def handle_subscribe(self, chat_id: int):
        self.wait_to_add_email.add(chat_id)
        await self.send_message(chat_id, "❗️ Напиши email, который нужно добавить в подписку.")

    async def handle_email(self, chat_id: int, text: str):
        """
        Обрабатывает ввод email от пользователя.
        Если пользователь находится в режиме подписки, добавляет email в базу данных.
        Если пользователь находится в режиме отписки, удаляет email из базы данных.
        """
        if chat_id in self.wait_to_add_email:
            # Проверяем, существует ли email в базе
            if await self.email_exists(text):
                await self.send_message(chat_id, f"❗️ Email {text} уже существует в базе.")
            else:
                # Добавляем пользователя в базу данных
                success = await self.add_user(text, chat_id)
                if success:
                    await self.send_message(chat_id, f"✅ {text} добавлен в подписку. Чтобы отписаться, напиши /unsubscribe.")
                else:
                    await self.send_message(chat_id, f"❗️ Не удалось добавить {text} в подписку. Попробуйте позже.")
            self.wait_to_add_email.discard(chat_id)

        elif chat_id in self.waiting_for_unsubscribe_email:
            # Проверяем, существует ли email в базе
            if await self.email_exists(text):
                # Удаляем пользователя из базы данных
                success = await self.delete_user(text)
                if success:
                    await self.send_message(chat_id, f"✅ Email {text} успешно удален из подписки.")
                else:
                    await self.send_message(chat_id, f"❗️ Не удалось удалить {text} из подписки. Попробуйте позже.")
            else:
                await self.send_message(chat_id, f"❗️ Email {text} не найден в базе.")
            self.waiting_for_unsubscribe_email.discard(chat_id)

        else:
            # Если пользователь не выбрал действие
            await self.send_message(chat_id, "❗️ Сначала выбери действие. Список команд: /help")

    async def handle_unsubscribe(self, chat_id: int):
        self.waiting_for_unsubscribe_email.add(chat_id)
        await self.send_message(chat_id, "❗️ Напиши email, который нужно удалить из подписки.")

    async def handle_help(self, chat_id: int):
        await self.send_message(chat_id, "Чтобы подписаться на утечки, напиши /subscribe.\nЧтобы отписаться, напиши /unsubscribe.")

    async def polling_commands(self):
        offset = 0
        while True:
            params = {"timeout": self.timeout, "offset": offset}
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get(self.get_updates_url, params=params, timeout=self.timeout + 5)
                updates = r.json().get("result", [])
            except Exception:
                await asyncio.sleep(self.poll_interval)
                continue

            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if not msg or "text" not in msg:
                    continue

                chat_id = msg["chat"]["id"]
                text = msg["text"].strip()

                if text.startswith("/start"):
                    await self.handle_start(chat_id)
                elif text.startswith("/subscribe"):
                    await self.handle_subscribe(chat_id)
                elif "@" in text and "." in text:
                    await self.handle_email(chat_id, text)
                elif text.startswith("/unsubscribe"):
                    await self.handle_unsubscribe(chat_id)
                elif text.startswith("/help"):
                    await self.handle_help(chat_id)
                else:
                    await self.send_message(chat_id, "❗️ Не понял. Напиши /help для получения списка команд.")

            await asyncio.sleep(self.poll_interval)