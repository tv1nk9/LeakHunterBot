import os
import json
import asyncio
import httpx

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.send_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.base_dir = os.path.dirname(__file__)
        self.users_file = os.path.join(self.base_dir, "..", "db", "users.json")
        self.leaks_file = os.path.join(self.base_dir, "..", "db", "leaks.json")
        self.check_interval = 20

    async def send_message(self, chat_id: int, text: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.send_url, data={"chat_id": chat_id, "text": text})
        return resp.status_code == 200

    async def monitor_leaks_loop(self):
        print("Start")
        
        while True:
            try:
                users = json.loads(open(self.users_file, encoding="utf-8").read())
                leaks = json.loads(open(self.leaks_file, encoding="utf-8").read())
            except FileNotFoundError:
                print("File not found")
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
                            f"Детали: {leak.get('leak_info','нет данных')}"
                        )
                        ok = await self.send_message(chat_id, msg)
                        if ok:
                            leak["notified"] = True
                            updated = True

            if updated:
                with open(self.leaks_file, "w", encoding="utf-8") as f:
                    json.dump(leaks, f, ensure_ascii=False, indent=2)

            await asyncio.sleep(self.check_interval)