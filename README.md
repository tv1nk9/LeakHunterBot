# Telegram Bot Microservice

Этот проект представляет собой Telegram-бота, который работает как микросервис. Бот позволяет пользователям подписываться на уведомления об утечках данных и получать уведомления через Telegram. Бот взаимодействует с базой данных через API другого микросервиса.

## Зависимости

Перед запуском убедитесь, что у вас установлены следующие зависимости:

- Python 3.8 или выше
- Установленные библиотеки из `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

## Настройка

1. **Создайте файл `.env` в корне проекта**:
   Укажите в нем следующие переменные:
   ```properties
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   DB_SERVICE_URL=http://localhost:8001  # URL микросервиса для работы с базой данных
   ```

2. **Запустите микросервис для работы с базой данных**:
   Убедитесь, что у вас есть API, предоставляющий следующие эндпоинты:
   - `GET /users` — возвращает список всех пользователей в формате `{email: chat_id}`.
   - `GET /users/{email}` — проверяет существование пользователя и возвращает его данные.
   - `POST /users` — добавляет нового пользователя. Ожидается тело запроса:
     ```json
     {
       "email": "user@example.com",
       "chat_id": 123456789
     }
     ```
   - `DELETE /users/{email}` — удаляет пользователя по email.
   - `GET /leaks` — возвращает список всех утечек.
   - `PATCH /leaks/{id}` — обновляет статус уведомления для утечки. Ожидается тело запроса:
     ```json
     {
       "notified": true
     }

#### Структура данных пользователей (`users_db`)
```json
{
  "user@example.com": 123456789
}
```

#### Структура данных утечек (`leaks_db`)
```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "source": "example.com",
    "leak_info": "Пароль скомпрометирован",
    "notified": false
  }
]
```

3. **Запустите Telegram Bot**:
   Убедитесь, что микросервис базы данных запущен, и выполните команду:
   ```bash
   uvicorn main:app --reload
   ```

## Описание работы

### Telegram Bot
- **Подписка**:
  - Пользователь отправляет команду `/start`, чтобы начать взаимодействие.
  - Пользователь отправляет свой email для подписки.
  - Бот отправляет запрос к API микросервиса для добавления пользователя в базу данных.

- **Отписка**:
  - Пользователь отправляет команду `/unsubscribe`.
  - Бот ожидает ввода email от пользователя.
  - После получения email бот отправляет запрос к API микросервиса для удаления пользователя из базы данных.

- **Справка**:
  - Команда `/help` выводит список доступных команд.

### Telegram Notifier
- Периодически проверяет наличие новых утечек через API микросервиса.
- Отправляет уведомления пользователям, если их email присутствует в утечке.
- После успешной отправки уведомления обновляет статус утечки через API.