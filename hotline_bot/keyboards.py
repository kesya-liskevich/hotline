from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from hotline_bot.program import CATEGORIES, DISCIPLINES, CATEGORY_KIDS


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Регистрация на соревнования", callback_data="competition:start")],
            [InlineKeyboardButton(text="Мои регистрации", callback_data="registrations")],
            [InlineKeyboardButton(text="Запись на мастер-класс/лекцию", callback_data="workshop:start")],
            [InlineKeyboardButton(text="Тренировка с Kevin Lee", callback_data="kevin:start")],
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


def registrations_keyboard(cancel_buttons: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=text, callback_data=callback_data)]
        for text, callback_data in cancel_buttons
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def workshops_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="В меню", callback_data="menu")],
        ]
    )


def kevin_training_options_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Розыгрыш", callback_data="kevin:option:lottery")],
            [InlineKeyboardButton(text="🎟 Платная тренировка", callback_data="kevin:option:paid")],
            [InlineKeyboardButton(text="В меню", callback_data="menu")],
        ]
    )


def skating_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ФСК", callback_data="workshop:skating:ФСК")],
            [InlineKeyboardButton(text="Агрессив", callback_data="workshop:skating:Агрессив")],
        ]
    )
