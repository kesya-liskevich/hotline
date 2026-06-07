from __future__ import annotations

from dataclasses import dataclass

DISCIPLINE_STREET = "Street"
DISCIPLINE_PARK = "Park"
DISCIPLINE_BOTH = "Street + Park"

CATEGORY_KIDS = "Дети до 16 лет"
CATEGORY_WOMEN = "Женщины"
CATEGORY_MEN_AM = "AM: мужчины"
CATEGORY_MEN_PRO = "PRO: мужчины"

PROGRAM_TEXT = (
    "📅 8 июня, понедельник\n"
    "Большая открытая тренировка\n"
    "От FSK к агрессивному катанию\n"
    "📍 Скейт-парк на набережной Макарова\n"
    "🕕 18:00\n\n"
    "📅 9 июня, вторник\n"
    "ОФП и подготовка тела к катанию\n"
    "Егор Логинов\n"
    "📍 Скейт-парк на набережной Макарова\n"
    "🕕 18:00\n\n"
    "📅 10 июня, среда\n"
    "Ракурс решает: как увидеть своё катание со стороны\n"
    "Соня Кит\n"
    "📍 Скейт-парк «Смена»\n"
    "🕕 18:00\n\n"
    "📅 11 июня, четверг\n"
    "Прессейшн & Cash for Tricks\n"
    "📍 Скейт-парк под мостом Бетанкура\n"
    "🕕 18:00\n\n"
    "📅 12 июня, пятница\n"
    "День 1 соревнований\n"
    "• STREET & PARK — квалификации: дети, мужчины AM\n"
    "• Лекция «Профилактика травм в экстремальном спорте»\n"
    "• Воркшоп для тренеров от Kevin Lee\n"
    "📍 Street Sport Academy\n"
    "Автозаводская, 31Б\n\n"
    "📅 13 июня, суббота\n"
    "День 2 соревнований\n"
    "• STREET — квалификации: женщины, мужчины PRO\n"
    "• STREET — контест: дети, женщины, мужчины AM/PRO\n"
    "• Cash for Tricks\n"
    "• Воркшоп «Продвинутый роллер-фристайл»\n"
    "Григорий Фузеев\n"
    "📍 Street Sport Academy\n"
    "Автозаводская, 31Б\n\n"
    "📅 14 июня, воскресенье\n"
    "День 3 соревнований\n"
    "• PARK — квалификации: женщины, мужчины PRO\n"
    "• PARK — контест: дети, женщины, мужчины AM/PRO\n"
    "🏆 Награждение — 18:00\n"
    "📍 Street Sport Academy\n"
    "Автозаводская, 31Б"
)

DISCIPLINES = (DISCIPLINE_STREET, DISCIPLINE_PARK, DISCIPLINE_BOTH)
CATEGORIES = (CATEGORY_KIDS, CATEGORY_WOMEN, CATEGORY_MEN_AM, CATEGORY_MEN_PRO)


@dataclass(frozen=True)
class Workshop:
    workshop_id: str
    title: str
    date_text: str
    asks_skating_type: bool = False


WORKSHOPS: tuple[Workshop, ...] = (
    Workshop(
        "mon_fsk_aggressive",
        "Как подготовить своё катание от FSK к агрессивным роликам",
        "8 июня, понедельник, 18:00",
        True,
    ),
    Workshop(
        "tue_ofp",
        "ОФП и подготовка тела к катанию",
        "9 июня, вторник, 18:00",
    ),
    Workshop(
        "wed_video",
        "Ракурс решает: как увидеть своё катание со стороны",
        "10 июня, среда, 18:00",
        True,
    ),
    Workshop(
        "fri_rehab",
        "Профилактика травм в экстремальном спорте",
        "12 июня, пятница, 14:00",
    ),
    Workshop(
        "fri_trainers",
        "Практический воркшоп для тренеров по роликам",
        "12 июня, пятница, 18:00",
        True,
    ),
    Workshop(
        "sat_grisha_12",
        "Продвинутый роллер-фристайл в тренинг-зоне, группа 12:00",
        "13 июня, суббота, 12:00",
    ),
    Workshop(
        "sat_grisha_15",
        "Продвинутый роллер-фристайл в тренинг-зоне, группа 15:00",
        "13 июня, суббота, 15:00",
    ),
    Workshop(
        "sat_rollbay",
        "Обслуживание роликов: устройство, настройка и уход",
        "13 июня, суббота, 13:00",
    ),
)


def program_text() -> str:
    return PROGRAM_TEXT


def discipline_help_text() -> str:
    return "Выберите дисциплину"


def category_help_text() -> str:
    return (
        "Выберите категорию.\n\n"
        "Если вы уже побеждали в AM/PRO контестах, выбирайте категорию PRO."
    )


def review_reason(discipline: str, category: str) -> str | None:
    if category == CATEGORY_KIDS:
        return None
    if category == CATEGORY_WOMEN:
        return None
    if category in {CATEGORY_MEN_AM, CATEGORY_MEN_PRO}:
        return None
    return "Неизвестная категория"
