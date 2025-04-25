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
        self.base_dir = os.path.dirname(__file__)
        self.users_file = os.path.join(self.base_dir, "..", "db", "users.json")
        self.poll_interval = 1
        self.timeout = 20
        self.wait_to_add_email = set()
        self.waiting_for_unsubscribe_email = set()  # Множество для отслеживания пользователей, ожидающих ввода email
    
    async def send_message(self, chat_id: int, text: str):
        async with httpx.AsyncClient() as client:
            await client.post(self.send_url, data={"chat_id": chat_id, "text": text})

    def load_users(self):
        try:
            return json.loads(open(self.users_file, encoding="utf-8").read())
        except FileNotFoundError:
            return {}

    def save_users(self, users):
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

    def delete_user(self, email: str):
        """Удаляет пользователя из JSON-файла."""
        users = self.load_users()
        if email in users:
            del users[email]
            self.save_users(users)
            return True
        return False

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
                    self.wait_to_add_email.add(chat_id)  # Добавляем пользователя в активные
                    await self.send_message(chat_id, "👋 Привет! Пришли мне свой email для подписки на утечки.")
                
                elif text.startswith("/subscribe"):
                    self.wait_to_add_email.add(chat_id)
                    await self.send_message(chat_id, "❗️ Напиши email, который нужно добавить в подписку.")

                elif "@" in text and "." in text:
                    if chat_id in self.wait_to_add_email:  # Проверяем, отправил ли пользователь /start или /subscribe
                        if text in self.waiting_for_unsubscribe_email:  # Проверяем, не ожидает ли пользователь отписку
                            self.waiting_for_unsubscribe_email.discard(chat_id)  # Удаляем пользователя из ожидания отписки
                        users = self.load_users()
                        users[text] = chat_id
                        self.save_users(users)
                        await self.send_message(chat_id, f"✅ {text} добавлен в подписку. Чтобы отписаться, напиши /unsubscribe.")
                        self.wait_to_add_email.discard(chat_id)  # Удаляем пользователя из активных
                    elif chat_id in self.waiting_for_unsubscribe_email:  # Проверяем, ожидает ли пользователь ввода email для отписки
                        users = self.load_users()
                        if text in users:
                            self.delete_user(text)
                            await self.send_message(chat_id, f"✅ Email {text} успешно удален из подписки.")
                        else:
                            await self.send_message(chat_id, f"❗️ Email {text} не найден в базе.")
                        self.waiting_for_unsubscribe_email.discard(chat_id)  # Удаляем пользователя из списка ожидания
                    else:
                        await self.send_message(chat_id, "❗️ Сначала выбери действие. Список комнад: /help")

                elif text.startswith("/unsubscribe"):
                    if chat_id in self.wait_to_add_email:
                        self.wait_to_add_email.discard(chat_id)
                    self.waiting_for_unsubscribe_email.add(chat_id)  # Добавляем пользователя в список ожидания
                    await self.send_message(chat_id, "❗️ Напиши email, который нужно удалить из подписки.")
                
                elif text.startswith("/help"):
                    await self.send_message(chat_id, "Чтобы подписаться на утечки, напиши /subscribe.\nЧтобы отписаться, напиши /unsubscribe.")
                
                else:
                    await self.send_message(chat_id, "❗️ Не понял. Напиши /help для получения списка команд.")

            await asyncio.sleep(self.poll_interval)