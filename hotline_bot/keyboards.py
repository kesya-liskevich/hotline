from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from hotline_bot.program import CATEGORIES, DISCIPLINES, CATEGORY_KIDS


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Регистрация на соревнования", callback_data="competition:start")],
            [InlineKeyboardButton(text="Мои регистрации", callback_data="registrations")],
            [InlineKeyboardButton(text="Запись на мастер-класс/лекцию (скоро)", callback_data="soon")],
            [InlineKeyboardButton(text="Программа и расписание", callback_data="program")],
        ]
    )


def disciplines_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"discipline:{name}")]
            for name in DISCIPLINES
        ]
    )


def categories_keyboard() -> InlineKeyboardMarkup:
    categories = [name for name in CATEGORIES if name != CATEGORY_KIDS]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"category:{name}")]
            for name in categories
        ]
    )


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить заявку", callback_data="registration:confirm")],
            [InlineKeyboardButton(text="Изменить данные", callback_data="edit:menu")],
        ]
    )


def rules_ack_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Окей", callback_data="rules:ok")],
        ]
    )


def edit_keyboard(is_minor: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="ФИО", callback_data="edit:full_name")],
        [InlineKeyboardButton(text="Телефон", callback_data="edit:phone")],
        [InlineKeyboardButton(text="Город", callback_data="edit:city")],
        [InlineKeyboardButton(text="Возраст", callback_data="edit:age")],
        [InlineKeyboardButton(text="Дисциплина", callback_data="edit:discipline")],
        [InlineKeyboardButton(text="Стаж катания", callback_data="edit:experience")],
        [InlineKeyboardButton(text="Спонсоры", callback_data="edit:sponsors")],
    ]
    if is_minor:
        rows.insert(4, [InlineKeyboardButton(text="Подписанный документ", callback_data="edit:consent")])
    else:
        rows.insert(4, [InlineKeyboardButton(text="Паспорт", callback_data="edit:passport")])
        rows.insert(5, [InlineKeyboardButton(text="Подписанное согласие", callback_data="edit:consent")])
        rows.insert(7, [InlineKeyboardButton(text="Категория", callback_data="edit:category")])
    rows.append([InlineKeyboardButton(text="Назад к заявке", callback_data="edit:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def registrations_keyboard(registration_ids: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Отменить {reg_id[:8]}", callback_data=f"registration:cancel:{reg_id}")]
        for reg_id in registration_ids
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
