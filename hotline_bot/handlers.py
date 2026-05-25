from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from hotline_bot.config import Settings
from hotline_bot.google_services import DriveClient, SheetsClient
from hotline_bot.keyboards import (
    categories_keyboard,
    confirmation_keyboard,
    disciplines_keyboard,
    edit_keyboard,
    main_menu,
    registrations_keyboard,
    rules_ack_keyboard,
)
from hotline_bot.models import Registration, RegistrationStatus
from hotline_bot.program import CATEGORY_KIDS, category_help_text, discipline_help_text, program_text
from hotline_bot.storage import RegistrationRepository


WELCOME_TEXT = (
    "Привет, вы на «Горячей линии» роллерблейдинга! Это бот для регистрации.\n\n"
    "Здесь можно:\n"
    "— зарегистрироваться на соревнования (форма открыта);\n"
    "— записаться на мастер-классы/лекции/кино (форма скоро откроется);\n"
    "— узнать программу и расписание фестиваля.\n\n"
    "Выбирай действие ниже:"
)
WELCOME_IMAGE_PATH = Path(__file__).resolve().parent.parent / "assets" / "welcome.png"


class CompetitionForm(StatesGroup):
    full_name = State()
    phone = State()
    city = State()
    age = State()
    passport = State()
    consent = State()
    discipline = State()
    category = State()
    experience = State()
    sponsors = State()
    rules = State()
    confirm = State()


EDIT_PROMPTS = {
    "full_name": ("Введите ФИО полностью: имя, фамилия, отчество", CompetitionForm.full_name),
    "phone": ("Введите телефон в формате +7XXXXXXXXXX", CompetitionForm.phone),
    "city": ("Введите город", CompetitionForm.city),
    "age": ("Введите дату рождения в формате dd.MM.yyyy (например, 14.06.2026)", CompetitionForm.age),
    "passport": ("Отправьте фото или файл паспорта: страницы 2-3", CompetitionForm.passport),
    "consent": ("Отправьте фото или файл подписанного документа", CompetitionForm.consent),
    "discipline": (discipline_help_text(), CompetitionForm.discipline),
    "category": (category_help_text(), CompetitionForm.category),
    "experience": ("Введите стаж катания", CompetitionForm.experience),
    "sponsors": ("Есть ли у вас спонсоры? Если есть, укажите. Если нет, напишите «нет»", CompetitionForm.sponsors),
}

CONSENT_UPLOAD_TEXT = (
    "Пожалуйста, заполните <a href=\"https://docs.google.com/document/d/1-F_VbnVcj9v6UYjV_RftOtXfmV8xJTyYUbGnPiqEIws/edit?usp=sharing\">Согласие об отказе претензий</a> и отправьте в чат его фото. "
    "Убедитесь, что текст читаем и в кадр попали все поля документа"
)
RULES_TEXT = (
    "Обязательно ознакомьтесь с <a href=\"https://streetsportacademy.ru/rules_ssa\">правилами</a> "
    "и <a href=\"https://streetsportacademy.ru/offer_ssa\">публичной офертой скейт-парка</a> "
    "Street Sport Academy.\n\n"
    "Если вы посещаете парк впервые, необходимо заполнить "
    "<a href=\"https://streetsportacademy.ru/home/skatepark_street_sport_academy/#rules\">расписку</a>.\n"
    "Обращаем внимание, детям до 18 лет необходимо заранее получить расписку от родителей "
    "или законного представителя."
)
MINOR_UNDER_14_CONSENT_TEXT = (
    "Пожалуйста, заполните <a href=\"https://docs.google.com/document/d/10I1iilxi5bSJNJlmgJWQ4OEHFz-UL8CrqeuDfS9Z0z0/edit?usp=sharing\">Согласие об отказе претензий</a> и отправьте в чат его фото. "
    "Убедитесь, что текст читаем и в кадр попали все поля документа"
)
FESTIVAL_AGE_DATE = date(2026, 6, 12)


def build_router(
    repo: RegistrationRepository,
    sheets: SheetsClient,
    drive: DriveClient,
    settings: Settings,
) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await _send_welcome(message)

    @router.message(Command("id"))
    async def show_id(message: Message) -> None:
        await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

    @router.callback_query(F.data == "menu")
    async def menu(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await _send_welcome(callback.message)
        await callback.answer()

    @router.callback_query(F.data == "soon")
    async def soon(callback: CallbackQuery) -> None:
        await callback.message.answer(
            "Форма записи на мастер-классы, лекции и кино скоро откроется. "
            "Сейчас доступна регистрация на соревнования."
        )
        await callback.answer()

    @router.callback_query(F.data == "program")
    async def program(callback: CallbackQuery) -> None:
        await callback.message.answer(program_text(), reply_markup=main_menu())
        await callback.answer()

    @router.callback_query(F.data == "competition:start")
    async def competition_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        registration = Registration(
            telegram_id=callback.from_user.id,
            telegram_username=callback.from_user.username,
        )
        await state.update_data(
            telegram_id=callback.from_user.id,
            telegram_username=callback.from_user.username,
            registration_id=registration.registration_id,
        )
        await callback.message.answer("Введите ФИО полностью: имя, фамилия, отчество")
        await state.set_state(CompetitionForm.full_name)
        await callback.answer()

    @router.message(CompetitionForm.full_name)
    async def full_name(message: Message, state: FSMContext) -> None:
        await state.update_data(full_name=message.text.strip())
        if await _finish_edit_if_needed(message, state):
            return
        await message.answer("Введите телефон в формате +7XXXXXXXXXX")
        await state.set_state(CompetitionForm.phone)

    @router.message(CompetitionForm.phone)
    async def phone(message: Message, state: FSMContext) -> None:
        phone_value = (message.text or "").strip()
        if not _is_valid_phone(phone_value):
            await message.answer("Введите телефон в формате +7XXXXXXXXXX")
            return
        await state.update_data(phone=phone_value)
        if await _finish_edit_if_needed(message, state):
            return
        await message.answer("Введите город")
        await state.set_state(CompetitionForm.city)

    @router.message(CompetitionForm.city)
    async def city(message: Message, state: FSMContext) -> None:
        await state.update_data(city=message.text.strip())
        if await _finish_edit_if_needed(message, state):
            return
        await message.answer("Введите дату рождения в формате dd.MM.yyyy (например, 14.06.2026)")
        await state.set_state(CompetitionForm.age)

    @router.message(CompetitionForm.age)
    async def age(message: Message, state: FSMContext) -> None:
        birthdate = _parse_birthdate(message.text or "")
        if birthdate is None:
            await message.answer("Введите дату рождения в формате dd.MM.yyyy (например, 14.06.2026)")
            return
        age_value = _age_on(birthdate, FESTIVAL_AGE_DATE)
        data = await state.get_data()
        is_editing_age = data.get("editing_field") == "age"
        await state.update_data(
            age_or_birthdate=birthdate.strftime("%d.%m.%Y"),
            birthdate=birthdate.strftime("%d.%m.%Y"),
            age=age_value,
        )
        if is_editing_age:
            await _handle_age_edit(message, state, settings, age_value)
            return
        if age_value < 16:
            await state.update_data(passport_file_url="")
            await _ask_minor_consent(message, settings, age_value)
            await state.set_state(CompetitionForm.consent)
            return
        await message.answer("Отправьте фото или файл паспорта: страницы 2-3")
        await state.set_state(CompetitionForm.passport)

    @router.message(CompetitionForm.passport, F.photo | F.document)
    async def passport_file(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        draft = _draft_from_state(data)
        file_id, filename = _message_file(message, "passport.jpg")
        url = await drive.upload_telegram_file(
            message.bot,
            file_id,
            draft,
            filename,
        )
        await state.update_data(
            passport_file_url=url,
            passport_media_group_id=message.media_group_id,
            passport_media_count=1,
        )
        data = await state.get_data()
        if data.get("editing_field") == "adult_documents":
            await _ask_consent_for_age(message, settings, _state_age(data))
            await state.update_data(editing_field="adult_consent")
            await state.set_state(CompetitionForm.consent)
            return
        if await _finish_edit_if_needed(message, state):
            return
        await _ask_consent_for_age(message, settings, _state_age(data))
        await state.set_state(CompetitionForm.consent)

    @router.message(CompetitionForm.passport)
    async def passport_not_file(message: Message) -> None:
        await message.answer("Пожалуйста, отправьте фото или файл паспорта")

    @router.message(CompetitionForm.consent, F.photo | F.document)
    async def consent_file(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        if (
            message.media_group_id
            and data.get("passport_media_group_id")
            and message.media_group_id == data.get("passport_media_group_id")
        ):
            await _save_extra_passport_file(message, state, drive)
            return
        draft = _draft_from_state(data)
        file_id, filename = _message_file(message, "signed_document.jpg")
        url = await drive.upload_telegram_file(
            message.bot,
            file_id,
            draft,
            filename,
        )
        await state.update_data(
            consent_file_url=url,
            consent_media_group_id=message.media_group_id,
            consent_media_count=1,
        )
        data = await state.get_data()
        if data.get("editing_field") == "adult_consent":
            await state.update_data(editing_field="category")
            await message.answer(category_help_text(), reply_markup=categories_keyboard())
            await state.set_state(CompetitionForm.category)
            return
        if await _finish_edit_if_needed(message, state):
            return
        await message.answer(discipline_help_text(), reply_markup=disciplines_keyboard())
        await state.set_state(CompetitionForm.discipline)

    @router.message(CompetitionForm.consent)
    async def consent_not_file(message: Message) -> None:
        await message.answer("Пожалуйста, отправьте фото или файл подписанного документа")

    @router.message(F.photo | F.document)
    async def extra_group_file(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        if (
            message.media_group_id
            and data.get("consent_media_group_id")
            and message.media_group_id == data.get("consent_media_group_id")
        ):
            await _save_extra_consent_file(message, state, drive)
            return
        if (
            message.media_group_id
            and data.get("passport_media_group_id")
            and message.media_group_id == data.get("passport_media_group_id")
        ):
            await _save_extra_passport_file(message, state, drive)

    @router.callback_query(CompetitionForm.discipline, F.data.startswith("discipline:"))
    async def discipline(callback: CallbackQuery, state: FSMContext) -> None:
        value = callback.data.split(":", 1)[1]
        await state.update_data(discipline=value)
        if await _finish_edit_if_needed(callback.message, state):
            await callback.answer()
            return
        if _is_minor(await state.get_data()):
            await state.update_data(category=CATEGORY_KIDS)
            await callback.message.answer("Введите стаж катания")
            await state.set_state(CompetitionForm.experience)
            await callback.answer()
            return
        await callback.message.answer(category_help_text(), reply_markup=categories_keyboard())
        await state.set_state(CompetitionForm.category)
        await callback.answer()

    @router.callback_query(CompetitionForm.category, F.data.startswith("category:"))
    async def category(callback: CallbackQuery, state: FSMContext) -> None:
        value = callback.data.split(":", 1)[1]
        if value == CATEGORY_KIDS and not _is_minor(await state.get_data()):
            await callback.answer("Эта категория доступна только участникам до 16 лет", show_alert=True)
            return
        await state.update_data(category=value)
        if await _finish_edit_if_needed(callback.message, state):
            await callback.answer()
            return
        await callback.message.answer("Введите стаж катания")
        await state.set_state(CompetitionForm.experience)
        await callback.answer()

    @router.message(CompetitionForm.experience)
    async def experience(message: Message, state: FSMContext) -> None:
        await state.update_data(experience=message.text.strip())
        if await _finish_edit_if_needed(message, state):
            return
        await message.answer("Есть ли у вас спонсоры? Если есть, укажите. Если нет, напишите «нет».")
        await state.set_state(CompetitionForm.sponsors)

    @router.message(CompetitionForm.sponsors)
    async def sponsors(message: Message, state: FSMContext) -> None:
        await state.update_data(sponsors=message.text.strip())
        await message.answer(RULES_TEXT, reply_markup=rules_ack_keyboard(), parse_mode="HTML")
        await state.set_state(CompetitionForm.rules)

    @router.callback_query(CompetitionForm.rules, F.data == "rules:ok")
    async def rules_ok(callback: CallbackQuery, state: FSMContext) -> None:
        await state.update_data(rules_acknowledged=True)
        await _send_draft_summary(callback.message, state)
        await callback.answer()

    @router.callback_query(CompetitionForm.confirm, F.data == "edit:menu")
    async def edit_menu(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await callback.message.answer(
            "Что хотите изменить?",
            reply_markup=edit_keyboard(_is_minor(data)),
        )
        await callback.answer()

    @router.callback_query(CompetitionForm.confirm, F.data == "edit:back")
    async def edit_back(callback: CallbackQuery, state: FSMContext) -> None:
        await _send_draft_summary(callback.message, state)
        await callback.answer()

    @router.callback_query(CompetitionForm.confirm, F.data.startswith("edit:"))
    async def edit_field(callback: CallbackQuery, state: FSMContext) -> None:
        field = callback.data.split(":", 1)[1]
        prompt_state = EDIT_PROMPTS.get(field)
        if not prompt_state:
            await callback.answer("Неизвестное поле", show_alert=True)
            return
        prompt, next_state = prompt_state
        await state.update_data(editing_field=field)
        if field == "discipline":
            await callback.message.answer(prompt, reply_markup=disciplines_keyboard())
        elif field == "category":
            await callback.message.answer(prompt, reply_markup=categories_keyboard())
        elif field == "consent":
            data = await state.get_data()
            await _ask_consent_for_age(callback.message, settings, _state_age(data))
        else:
            await callback.message.answer(prompt)
        await state.set_state(next_state)
        await callback.answer()

    @router.callback_query(CompetitionForm.confirm, F.data == "registration:confirm")
    async def confirm(callback: CallbackQuery, state: FSMContext) -> None:
        registration = _draft_from_state(await state.get_data())
        registration.mark_submitted()
        repo.save(registration)
        sheets.append_registration(registration)
        await state.clear()
        await callback.message.answer(
            "Спасибо за регистрацию! Вы в списке участников «Горячей линии» 📞\n\n"
            "Следите за актуальными новостями в соцсетях:\n"
            '<a href="https://t.me/hotlineblading">телеграм</a>\n'
            '<a href="https://www.instagram.com/hotlineblading?igsh=dmw4cmYzM3l1bThn">инстаграм</a>',
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
        await callback.answer()

    @router.message(Command("registrations"))
    async def my_registrations(message: Message) -> None:
        await _send_registrations(message, repo)

    @router.callback_query(F.data == "registrations")
    async def my_registrations_callback(callback: CallbackQuery) -> None:
        await _send_registrations(callback.message, repo, callback.from_user.id)
        await callback.answer()

    @router.callback_query(F.data.startswith("registration:cancel:"))
    async def cancel_registration(callback: CallbackQuery) -> None:
        registration_id = callback.data.rsplit(":", 1)[1]
        registration = repo.get(registration_id)
        if not registration or registration.telegram_id != callback.from_user.id:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
        registration.mark_cancelled()
        repo.save(registration)
        sheets.update_registration(registration)
        await callback.message.answer("Заявка отменена.", reply_markup=main_menu())
        await callback.answer()

    @router.message(Command("stats"))
    async def stats(message: Message) -> None:
        if not _is_admin(message.from_user.id, settings):
            return
        await message.answer(repo.stats_text())

    @router.message(Command("export"))
    async def export(message: Message) -> None:
        if not _is_admin(message.from_user.id, settings):
            return
        await message.answer(sheets.spreadsheet_url())

    @router.message(Command("broadcast_competition"))
    async def broadcast(message: Message) -> None:
        if not _is_admin(message.from_user.id, settings):
            return
        text = message.text.partition(" ")[2].strip()
        if not text:
            await message.answer("Использование: /broadcast_competition текст рассылки")
            return
        sent = 0
        for registration in repo.all_submitted():
            try:
                await message.bot.send_message(registration.telegram_id, text)
                sent += 1
            except Exception:
                continue
        await message.answer(f"Отправлено сообщений: {sent}")

    return router


async def _send_welcome(message: Message) -> None:
    if WELCOME_IMAGE_PATH.exists():
        await message.answer_photo(
            FSInputFile(WELCOME_IMAGE_PATH),
            caption=WELCOME_TEXT,
            reply_markup=main_menu(),
        )
        return
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


async def _ask_adult_consent(message: Message, settings: Settings) -> None:
    await message.answer(CONSENT_UPLOAD_TEXT, parse_mode="HTML")


async def _ask_consent_for_age(
    message: Message,
    settings: Settings,
    age_value: int | None,
) -> None:
    if age_value is not None and age_value < 18:
        await _ask_minor_consent(message, settings, age_value)
        return
    await _ask_adult_consent(message, settings)


async def _ask_minor_consent(message: Message, settings: Settings, age_value: int) -> None:
    if age_value < 14:
        text = (
            f"{MINOR_UNDER_14_CONSENT_TEXT}\n\n"
            "До 14 лет документ заполняет только мама, папа или ответственное лицо имеющее "
            "доверенность, которая удостоверена нотариусом. Для заполнения заявления необходим "
            "паспорт законного представителя и свидетельство о рождении ребенка."
        )
        await message.answer(text, parse_mode="HTML")
        return

    text = (
        f"{MINOR_UNDER_14_CONSENT_TEXT}\n\n"
        "С 14 лет заявление заполняет не только законный представитель, но и сам "
        "несовершеннолетний, которому будут оказаны услуги. Для заполнения понадобится "
        "паспорт ребенка и законного представителя."
    )
    await message.answer(text, parse_mode="HTML")


async def _send_registrations(
    message: Message,
    repo: RegistrationRepository,
    telegram_id: int | None = None,
) -> None:
    user_id = telegram_id or message.from_user.id
    registrations = [
        item for item in repo.list_by_user(user_id)
        if item.status != RegistrationStatus.CANCELLED
    ]
    if not registrations:
        await message.answer("У вас пока нет активных заявок.", reply_markup=main_menu())
        return
    text = "\n\n".join(item.summary() for item in registrations)
    await message.answer(
        text,
        reply_markup=registrations_keyboard([item.registration_id for item in registrations]),
    )


def _draft_from_state(data: dict) -> Registration:
    registration_id = data.get("registration_id") or Registration(
        telegram_id=data["telegram_id"],
        telegram_username=data.get("telegram_username"),
    ).registration_id
    return Registration(
        registration_id=registration_id,
        telegram_id=data["telegram_id"],
        telegram_username=data.get("telegram_username"),
        full_name=data.get("full_name", ""),
        phone=data.get("phone", ""),
        city=data.get("city", ""),
        age_or_birthdate=data.get("age_or_birthdate", ""),
        passport_file_url=data.get("passport_file_url", ""),
        consent_file_url=data.get("consent_file_url", ""),
        discipline=data.get("discipline", ""),
        category=data.get("category", ""),
        experience=data.get("experience", ""),
        sponsors=data.get("sponsors", ""),
    )


async def _finish_edit_if_needed(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    if not data.get("editing_field"):
        return False
    await state.update_data(editing_field=None)
    await _send_draft_summary(message, state)
    return True


async def _handle_age_edit(
    message: Message,
    state: FSMContext,
    settings: Settings,
    age_value: int,
) -> None:
    await state.update_data(editing_field=None)
    if age_value < 16:
        await state.update_data(
            category=CATEGORY_KIDS,
            passport_file_url="",
            consent_file_url="",
            passport_media_group_id=None,
            passport_media_count=0,
        )
        await _ask_minor_consent(message, settings, age_value)
        await state.update_data(editing_field="consent")
        await state.set_state(CompetitionForm.consent)
        return

    await state.update_data(
        category="",
        passport_file_url="",
        consent_file_url="",
        passport_media_group_id=None,
        passport_media_count=0,
    )
    await message.answer("Возраст изменен. Отправьте фото или файл паспорта: страницы 2-3")
    await state.update_data(editing_field="adult_documents")
    await state.set_state(CompetitionForm.passport)


async def _save_extra_passport_file(
    message: Message,
    state: FSMContext,
    drive: DriveClient,
) -> None:
    data = await state.get_data()
    draft = _draft_from_state(data)
    count = int(data.get("passport_media_count", 1)) + 1
    file_id, filename = _message_file(message, f"passport_{count}.jpg")
    url = await drive.upload_telegram_file(message.bot, file_id, draft, filename)
    existing = data.get("passport_file_url", "")
    combined = f"{existing}\n{url}" if existing else url
    await state.update_data(passport_file_url=combined, passport_media_count=count)


async def _save_extra_consent_file(
    message: Message,
    state: FSMContext,
    drive: DriveClient,
) -> None:
    data = await state.get_data()
    draft = _draft_from_state(data)
    count = int(data.get("consent_media_count", 1)) + 1
    file_id, filename = _message_file(message, f"signed_document_{count}.jpg")
    url = await drive.upload_telegram_file(message.bot, file_id, draft, filename)
    existing = data.get("consent_file_url", "")
    combined = f"{existing}\n{url}" if existing else url
    await state.update_data(consent_file_url=combined, consent_media_count=count)


async def _send_draft_summary(message: Message, state: FSMContext) -> None:
    registration = _draft_from_state(await state.get_data())
    registration.mark_submitted()
    warning = ""
    if registration.needs_review:
        warning = "\n\nВозможное несоответствие расписанию будет проверено организаторами."
    await message.answer(registration.summary() + warning, reply_markup=confirmation_keyboard())
    await state.set_state(CompetitionForm.confirm)


def _parse_birthdate(value: str) -> date | None:
    cleaned = value.strip()
    try:
        parsed = datetime.strptime(cleaned, "%d.%m.%Y").date()
    except ValueError:
        return None
    if parsed > FESTIVAL_AGE_DATE:
        return None
    age_value = _age_on(parsed, FESTIVAL_AGE_DATE)
    if age_value < 0 or age_value > 100:
        return None
    return parsed


def _age_on(birthdate: date, target_date: date) -> int:
    age_value = target_date.year - birthdate.year
    if (target_date.month, target_date.day) < (birthdate.month, birthdate.day):
        age_value -= 1
    return age_value


def _is_valid_phone(value: str) -> bool:
    return re.fullmatch(r"\+7\d{10}", value.strip()) is not None


def _state_age(data: dict) -> int | None:
    if isinstance(data.get("age"), int):
        return data["age"]
    birthdate = _parse_birthdate(str(data.get("birthdate") or data.get("age_or_birthdate", "")))
    if birthdate is None:
        return None
    return _age_on(birthdate, FESTIVAL_AGE_DATE)


def _is_minor(data: dict) -> bool:
    age_value = _state_age(data)
    return age_value is not None and age_value < 16


def _message_file(message: Message, photo_filename: str) -> tuple[str, str]:
    if message.photo:
        return message.photo[-1].file_id, photo_filename
    if message.document:
        return (
            message.document.file_id,
            message.document.file_name or photo_filename.replace(".jpg", ".bin"),
        )
    raise ValueError("Message does not contain a photo or document")


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_id_set
