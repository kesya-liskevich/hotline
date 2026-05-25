# Hotline Registration Bot

Telegram-бот для первой волны регистрации на соревнования фестиваля роллерблейдинга «Горячая линия».

## Что уже есть

- `/start` с приветствием и тремя кнопками:
  - регистрация на соревнования;
  - запись на мастер-класс/лекцию, пока «скоро»;
  - программа и расписание.
- Пошаговая анкета соревнований:
  - ФИО, телефон в формате `+79625021991`, город, дата рождения в формате `29.01.1997`;
  - фото паспорта;
  - фото подписанного согласия;
  - дисциплина: `Street`, `Park`, `Street + Park`;
  - категория: `Дети до 16 лет`, `Женщины`, `AM: мужчины`, `PRO: мужчины`;
  - стаж катания и спонсоры.
- SQLite как локальная база.
- Google Sheets для отчетности.
- Google Drive для файлов участников.
- Админ-команды: `/stats`, `/export`, `/broadcast_competition`.
- `/id` показывает личный Telegram ID для настройки `ADMIN_IDS`.

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m hotline_bot.main
```

Для локального теста можно заполнить только `BOT_TOKEN`. Если Google-переменные пустые, бот не будет падать: файлы останутся как Telegram `file_id`, а `/export` напишет, что Google Sheets не настроен.

## Переменные окружения

- `BOT_TOKEN` — токен Telegram-бота.
- `ADMIN_IDS` — Telegram ID админов через запятую.
- `DATABASE_PATH` — путь к SQLite-файлу.
- `GOOGLE_SERVICE_ACCOUNT_FILE` — JSON сервисного аккаунта Google.
- `GOOGLE_SHEETS_SPREADSHEET_ID` — ID таблицы.
- `GOOGLE_DRIVE_ROOT_FOLDER_ID` — ID папки Drive для документов.
- `GOOGLE_DRIVE_OAUTH_CLIENT_FILE` — OAuth client JSON для загрузки файлов в Drive от имени пользователя.
- `GOOGLE_DRIVE_OAUTH_TOKEN_FILE` — локальный token-файл после `scripts/auth_google_drive.py`.
- `CONSENT_DOCUMENT_FILE_ID` — устаревшая настройка, сейчас согласие отправляется ссылкой на Google Doc.

Google-таблица должна быть доступна сервисному аккаунту. Бот сам создаст листы `registrations_all`, `competitions` и `summary`, если их нет.

## Docker

```bash
docker build -t hotline-registration-bot .
docker run --env-file .env -v "$PWD:/app" hotline-registration-bot
```

## Проверка

```bash
python3 -m unittest discover -s tests
python3 -m compileall hotline_bot tests
```
