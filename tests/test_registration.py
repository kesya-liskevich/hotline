import tempfile
import unittest
from pathlib import Path

from hotline_bot.models import Registration, RegistrationStatus
from hotline_bot.program import CATEGORY_MEN_PRO, DISCIPLINE_BOTH, program_text
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

    def test_program_text_has_only_street_and_park(self) -> None:
        text = program_text()

        self.assertIn("Street и Park", text)
        self.assertIn("Дети до 16 лет", text)
        self.assertNotIn("Дети до 18 лет", text)
        self.assertNotIn("Air", text)


if __name__ == "__main__":
    unittest.main()
