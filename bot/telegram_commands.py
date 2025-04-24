import os
import json
import asyncio
import httpx

class TelegramBot:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.get_updates_url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        self.send_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.base_dir = os.path.dirname(__file__)
        self.users_file = os.path.join(self.base_dir, "..", "db", "users.json")
        self.poll_interval = 1
        self.timeout = 20

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
                    await self.send_message(chat_id, "👋 Привет! Пришли мне свой email для подписки на утечки.")
                elif "@" in text and "." in text:
                    users = self.load_users()
                    users[text] = chat_id
                    self.save_users(users)
                    await self.send_message(chat_id, f"✅ {text} добавлен в подписку.")
                else:
                    await self.send_message(chat_id, "❗️ Не понял?. Пришли просто email.")

            await asyncio.sleep(self.poll_interval)