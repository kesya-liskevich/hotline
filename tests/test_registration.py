import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from hotline_bot.google_services import _registration_from_sheet_row, _workshop_registration_from_sheet_row
from hotline_bot.handlers import (
    PASSPORT_SKIP_NOTICE,
    _cancel_buttons,
    _is_workshop_closed,
    _safe_callback_answer,
    _workshop_attendance_response_text,
    _workshop_by_number,
    _workshops_menu_text,
)
from hotline_bot.keyboards import (
    kevin_group_attendance_keyboard,
    passport_skip_keyboard,
    workshop_attendance_keyboard,
)
from hotline_bot.models import KevinTrainingRegistration, Registration, RegistrationStatus, WorkshopRegistration
from hotline_bot.program import CATEGORY_MEN_PRO, DISCIPLINE_BOTH, WORKSHOPS, program_text
from hotline_bot.storage import RegistrationRepository
from scripts.broadcast_monday_workshop import active_recipients
from scripts.broadcast_presession import unique_recipients
from scripts.prepare_kevin_lee_groups import grouped_participants


class CallbackAnswerTest(unittest.IsolatedAsyncioTestCase):
    async def test_callback_network_error_does_not_escape(self) -> None:
        callback = AsyncMock()
        callback.answer.side_effect = RuntimeError("network unavailable")

        await _safe_callback_answer(callback)

        callback.answer.assert_awaited_once_with(text=None, show_alert=False)


class PresessionBroadcastTest(unittest.TestCase):
    def test_recipients_are_unique_across_all_registration_sheets(self) -> None:
        rows = {
            "competitions": [["competition-1", "123", "first"]],
            "workshops": [
                ["workshop-1", "123", "first"],
                ["workshop-2", "456", "second"],
            ],
            "kevin_lee": [],
            "kevin_lee_lottery": [["kevin-1", "789", "third"]],
            "kevin_lee_paid": [["kevin-2", "456", "second"]],
        }

        recipients = unique_recipients(rows)

        self.assertEqual([item.telegram_id for item in recipients], [123, 456, 789])


class KevinLeeGroupsTest(unittest.TestCase):
    def test_grouping_deduplicates_people_but_preserves_shared_account(self) -> None:
        rows = [
            ["one", "262939864", "dshumkin", "Шумкин Дмитрий Михайлович"],
            ["two", "262939864", "dshumkin", "Шумкин Дмитрий Михайлович"],
            ["three", "262939864", "dshumkin", "Шумкина Мария Дмитриевна"],
        ]

        pro, beginners, missing = grouped_participants(rows)

        self.assertEqual(len(pro), 1)
        self.assertEqual(len(beginners), 1)
        self.assertEqual(pro[0].telegram_id, beginners[0].telegram_id)
        self.assertNotIn("Шумкин Дмитрий Михайлович", missing)
        self.assertNotIn("Шумкина Мария Дмитриевна", missing)

    def test_beginner_attendance_buttons_have_expected_callbacks(self) -> None:
        keyboard = kevin_group_attendance_keyboard("beginner")
        buttons = keyboard.inline_keyboard[0]

        self.assertEqual(buttons[0].text, "Приду")
        self.assertEqual(
            buttons[0].callback_data,
            "kevin:attendance:beginner:yes",
        )
        self.assertEqual(buttons[1].text, "Не смогу прийти")
        self.assertEqual(
            buttons[1].callback_data,
            "kevin:attendance:beginner:no",
        )


def make_registration() -> Registration:
    registration = Registration(
        telegram_id=123,
        telegram_username="skater",
        full_name="Иван Иванов Иванович",
        phone="+79990000000",
        city="Санкт-Петербург",
        age_or_birthdate="29.01.2009",
        passport_file_url="https://drive/passport",
        consent_file_url="https://drive/consent",
        discipline=DISCIPLINE_BOTH,
        category=CATEGORY_MEN_PRO,
        experience="5 лет",
        sponsors="нет",
    )
    registration.mark_submitted()
    return registration


class RegistrationTest(unittest.TestCase):
    def test_registration_row_contains_competition_data(self) -> None:
        registration = make_registration()

        row = registration.as_row()

        self.assertEqual(row[0], registration.registration_id)
        self.assertEqual(row[6], "competition")
        self.assertEqual(row[7], "Street + Park")
        self.assertEqual(row[8], "PRO: мужчины")
        self.assertEqual(row[14], "submitted")

    def test_repository_saves_and_cancels_registration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = RegistrationRepository(str(Path(tmpdir) / "hotline.sqlite3"))
            registration = make_registration()

            repo.save(registration)
            saved = repo.get(registration.registration_id)

            self.assertIsNotNone(saved)
            assert saved is not None
            self.assertEqual(saved.status, RegistrationStatus.SUBMITTED)
            self.assertEqual(saved.full_name, "Иван Иванов Иванович")

            saved.mark_cancelled()
            repo.save(saved)
            cancelled = repo.get(registration.registration_id)

            self.assertIsNotNone(cancelled)
            assert cancelled is not None
            self.assertEqual(cancelled.status, RegistrationStatus.CANCELLED)

    def test_stats_groups_by_category_and_discipline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = RegistrationRepository(str(Path(tmpdir) / "hotline.sqlite3"))
            repo.save(make_registration())

            stats = repo.stats_text()

            self.assertIn("Подтвержденных заявок: 1", stats)
            self.assertIn("PRO: мужчины: 1", stats)
            self.assertIn("Street + Park: 1", stats)

    def test_repository_saves_workshop_registration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = RegistrationRepository(str(Path(tmpdir) / "hotline.sqlite3"))
            registration = WorkshopRegistration(
                telegram_id=123,
                telegram_username="skater",
                workshop_id="mon_fsk_aggressive",
                workshop_title="Как подготовить своё катание от FSK к агрессивным роликам",
                workshop_date="8 июня, понедельник, 18:00",
                full_name="Иван Иванов",
                phone="+79990000000",
                skating_type="ФСК",
            )

            repo.save_workshop(registration)
            saved = repo.list_workshops_by_user(123)

            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].workshop_id, "mon_fsk_aggressive")
            self.assertEqual(saved[0].skating_type, "ФСК")

    def test_kevin_training_row_contains_contact_data(self) -> None:
        registration = KevinTrainingRegistration(
            telegram_id=123,
            telegram_username="skater",
            full_name="Иван Иванов",
            phone="+79990000000",
            age="18",
            participation_type="paid",
        )

        row = registration.as_row()

        self.assertEqual(row[1], "123")
        self.assertEqual(row[3], "Иван Иванов")
        self.assertEqual(row[4], "+79990000000")
        self.assertEqual(row[5], "18")
        self.assertEqual(row[6], "kevin_lee_training")
        self.assertEqual(row[7], "paid")
        self.assertEqual(row[8], "submitted")

    def test_repository_saves_kevin_training_registration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = RegistrationRepository(str(Path(tmpdir) / "hotline.sqlite3"))
            registration = KevinTrainingRegistration(
                telegram_id=123,
                telegram_username="skater",
                full_name="Иван Иванов",
                phone="+79990000000",
                age="18",
                participation_type="lottery",
            )

            repo.save_kevin_training(registration)
            saved = repo.list_kevin_trainings_by_user(123)

            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].full_name, "Иван Иванов")
            self.assertEqual(saved[0].phone, "+79990000000")
            self.assertEqual(saved[0].age, "18")
            self.assertEqual(saved[0].participation_type, "lottery")

    def test_repository_cancels_only_selected_workshop_registration(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = RegistrationRepository(str(Path(tmpdir) / "hotline.sqlite3"))
            first = WorkshopRegistration(
                telegram_id=123,
                workshop_id="tue_ofp",
                workshop_title="ОФП и подготовка тела к катанию",
                workshop_date="9 июня, вторник, 18:00",
                full_name="Иван Иванов",
                phone="+79990000000",
            )
            second = WorkshopRegistration(
                telegram_id=123,
                workshop_id="sat_rollbay",
                workshop_title="Обслуживание роликов: устройство, настройка и уход",
                workshop_date="13 июня, суббота, 13:00",
                full_name="Иван Иванов",
                phone="+79990000000",
            )

            repo.save_workshop(first)
            repo.save_workshop(second)
            first.mark_cancelled()
            repo.save_workshop(first)
            saved = repo.list_workshops_by_user(123)

            statuses = {item.registration_id: item.status for item in saved}
            self.assertEqual(statuses[first.registration_id], RegistrationStatus.CANCELLED)
            self.assertEqual(statuses[second.registration_id], RegistrationStatus.SUBMITTED)

    def test_cancel_buttons_use_readable_labels(self) -> None:
        competition = make_registration()
        workshop = WorkshopRegistration(
            telegram_id=123,
            workshop_id="tue_ofp",
            workshop_title="ОФП и подготовка тела к катанию",
            workshop_date="9 июня, вторник, 18:00",
            full_name="Иван Иванов",
            phone="+79990000000",
        )

        buttons = _cancel_buttons([competition], [workshop])

        labels = [label for label, _callback_data in buttons]
        callbacks = [_callback_data for _label, _callback_data in buttons]
        self.assertIn("Отменить соревнования: Street + Park", labels)
        self.assertTrue(any(label.startswith("Отменить МК: 9 июня") for label in labels))
        self.assertIn(f"competition:cancel:{competition.registration_id}", callbacks)
        self.assertIn(f"workshop:cancel:{workshop.registration_id}", callbacks)

    def test_registration_can_be_restored_from_sheet_row(self) -> None:
        row = make_registration().as_row()

        restored = _registration_from_sheet_row(row)

        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.telegram_id, 123)
        self.assertEqual(restored.status, RegistrationStatus.SUBMITTED)
        self.assertEqual(restored.discipline, "Street + Park")

    def test_workshop_can_be_restored_from_sheet_row(self) -> None:
        row = WorkshopRegistration(
            telegram_id=123,
            telegram_username="skater",
            workshop_id="sat_rollbay",
            workshop_title="Обслуживание роликов: устройство, настройка и уход",
            workshop_date="13 июня, суббота, 13:00",
            full_name="Иван Иванов",
            phone="+79990000000",
        ).as_row()

        restored = _workshop_registration_from_sheet_row(row)

        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.telegram_id, 123)
        self.assertEqual(restored.workshop_id, "sat_rollbay")
        self.assertEqual(restored.status, RegistrationStatus.SUBMITTED)

    def test_workshop_can_be_selected_by_number(self) -> None:
        self.assertEqual(_workshop_by_number("1"), WORKSHOPS[0])
        self.assertEqual(_workshop_by_number(str(len(WORKSHOPS))), WORKSHOPS[-1])
        self.assertIsNone(_workshop_by_number("0"))
        self.assertIsNone(_workshop_by_number("abc"))

    def test_fifth_workshop_is_closed(self) -> None:
        workshop = _workshop_by_number("5")

        self.assertIsNotNone(workshop)
        assert workshop is not None
        self.assertTrue(_is_workshop_closed(workshop))
        self.assertIn(
            "5. 12 июня, пятница, 18:00 — Практический воркшоп для тренеров по роликам "
            "(регистрация закрыта, места закончились)",
            _workshops_menu_text(),
        )

    def test_second_workshop_is_closed(self) -> None:
        workshop = _workshop_by_number("2")

        self.assertIsNotNone(workshop)
        assert workshop is not None
        self.assertTrue(_is_workshop_closed(workshop))
        self.assertIn(
            "2. 9 июня, вторник, 18:00 — ОФП и подготовка тела к катанию "
            "(регистрация закрыта, места закончились)",
            _workshops_menu_text(),
        )

    def test_third_workshop_is_closed(self) -> None:
        workshop = _workshop_by_number("3")

        self.assertIsNotNone(workshop)
        assert workshop is not None
        self.assertTrue(_is_workshop_closed(workshop))
        self.assertIn(
            "3. 10 июня, среда, 18:00 — Ракурс решает: как увидеть своё катание со стороны "
            "(регистрация закрыта, места закончились)",
            _workshops_menu_text(),
        )

    def test_workshop_broadcast_uses_only_active_unique_recipients(self) -> None:
        active = WorkshopRegistration(
            telegram_id=123,
            telegram_username="kesyaliskevich",
            workshop_id="mon_fsk_aggressive",
            status=RegistrationStatus.SUBMITTED,
        )
        duplicate = WorkshopRegistration(
            telegram_id=123,
            telegram_username="kesyaliskevich",
            workshop_id="mon_fsk_aggressive",
            status=RegistrationStatus.SUBMITTED,
        )
        cancelled = WorkshopRegistration(
            telegram_id=456,
            telegram_username="Because_why_not",
            workshop_id="mon_fsk_aggressive",
            status=RegistrationStatus.CANCELLED,
        )

        recipients = active_recipients(
            [active, duplicate, cancelled],
            {"kesyaliskevich", "Because_why_not"},
        )

        self.assertEqual([item.telegram_id for item in recipients], [123])

    def test_passport_step_can_be_skipped(self) -> None:
        keyboard = passport_skip_keyboard()
        button = keyboard.inline_keyboard[0][0]

        self.assertEqual(button.text, "Пропустить пункт")
        self.assertEqual(button.callback_data, "document:skip:passport")
        self.assertIn("регистрацию можно завершить без загрузки паспорта", PASSPORT_SKIP_NOTICE)
        self.assertIn("подтверждения личности участника", PASSPORT_SKIP_NOTICE)

    def test_workshop_attendance_buttons_have_expected_callbacks(self) -> None:
        keyboard = workshop_attendance_keyboard("tue_ofp")
        buttons = keyboard.inline_keyboard[0]

        self.assertEqual(buttons[0].text, "приду")
        self.assertEqual(buttons[0].callback_data, "workshop:attendance:tue_ofp:yes")
        self.assertEqual(buttons[1].text, "не смогу прийти")
        self.assertEqual(buttons[1].callback_data, "workshop:attendance:tue_ofp:no")
        self.assertEqual(
            _workshop_attendance_response_text("yes"),
            "Супер, ждём вас на тренировке!",
        )
        self.assertEqual(
            _workshop_attendance_response_text("no"),
            "Окей, ваша запись на тренировку отменена.",
        )

    def test_program_text_has_current_festival_schedule(self) -> None:
        text = program_text()

        self.assertIn("📅 8 июня, понедельник", text)
        self.assertIn("Большая открытая тренировка", text)
        self.assertIn("Прессейшн & Cash for Tricks", text)
        self.assertIn("День 1 соревнований", text)
        self.assertIn("STREET — квалификации: женщины, мужчины PRO", text)
        self.assertIn("PARK — контест: дети, женщины, мужчины AM/PRO", text)
        self.assertIn("Автозаводская, 31Б", text)
        self.assertNotIn("Дети до 18 лет", text)
        self.assertNotIn("Air", text)


if __name__ == "__main__":
    unittest.main()
