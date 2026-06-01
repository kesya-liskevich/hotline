import tempfile
import unittest
from pathlib import Path

from hotline_bot.google_services import _registration_from_sheet_row, _workshop_registration_from_sheet_row
from hotline_bot.handlers import _workshop_by_number
from hotline_bot.models import Registration, RegistrationStatus, WorkshopRegistration
from hotline_bot.program import CATEGORY_MEN_PRO, DISCIPLINE_BOTH, WORKSHOPS, program_text
from hotline_bot.storage import RegistrationRepository


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

    def test_program_text_has_current_festival_schedule(self) -> None:
        text = program_text()

        self.assertIn("ПРОГРАММА ФЕСТИВАЛЯ «ГОРЯЧАЯ ЛИНИЯ»", text)
        self.assertIn("8 июня, понедельник, 18:00", text)
        self.assertIn("12 июня, пятница — Квалификации", text)
        self.assertIn("14 июня, воскресенье — Финалы Park", text)
        self.assertIn("Eazy Money", text)
        self.assertNotIn("Дети до 18 лет", text)
        self.assertNotIn("Air", text)


if __name__ == "__main__":
    unittest.main()
