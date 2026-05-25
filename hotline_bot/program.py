from __future__ import annotations

from dataclasses import dataclass


DISCIPLINE_STREET = "Street"
DISCIPLINE_PARK = "Park"
DISCIPLINE_BOTH = "Street + Park"

CATEGORY_KIDS = "Дети до 16 лет"
CATEGORY_WOMEN = "Женщины"
CATEGORY_MEN_AM = "AM: мужчины"
CATEGORY_MEN_PRO = "PRO: мужчины"


@dataclass(frozen=True)
class FestivalDay:
    date: str
    title: str
    description: str


PROGRAM_DAYS: tuple[FestivalDay, ...] = (
    FestivalDay(
        "8-10 июня",
        "Мастер-классы и открытые тренировки",
        "Городские скейт-парки. Запись откроется позже.",
    ),
    FestivalDay(
        "11 июня",
        "Пресейшн и Best Trick",
        "Вечерняя сессия катания под мостом Бетанкура. Запись откроется позже.",
    ),
    FestivalDay(
        "12 июня",
        "Детские соревнования",
        "Дети до 16 лет, девочки и мальчики вместе. Дисциплины Street и Park.",
    ),
    FestivalDay(
        "13 июня",
        "Street",
        "Женщины без деления на AM/PRO. Мужчины: AM и PRO.",
    ),
    FestivalDay(
        "14 июня",
        "Park",
        "Женщины без деления на AM/PRO. Мужчины: AM и PRO.",
    ),
)

DISCIPLINES = (DISCIPLINE_STREET, DISCIPLINE_PARK, DISCIPLINE_BOTH)
CATEGORIES = (CATEGORY_KIDS, CATEGORY_WOMEN, CATEGORY_MEN_AM, CATEGORY_MEN_PRO)


def program_text() -> str:
    lines = ["Программа и расписание фестиваля:"]
    for day in PROGRAM_DAYS:
        lines.append(f"\n{day.date}: {day.title}\n{day.description}")
    return "\n".join(lines)


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
