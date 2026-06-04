from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

from hotline_bot.models import KevinTrainingRegistration, Registration, RegistrationStatus, WorkshopRegistration


HEADERS = [
    "registration_id",
    "telegram_id",
    "telegram_username",
    "full_name",
    "phone",
    "city",
    "event_type",
    "discipline",
    "category",
    "age_or_birthdate",
    "experience",
    "sponsors",
    "passport_file_url",
    "consent_file_url",
    "status",
    "needs_review",
    "review_note",
    "created_at",
    "updated_at",
]

WORKSHOP_HEADERS = [
    "registration_id",
    "telegram_id",
    "telegram_username",
    "full_name",
    "phone",
    "event_type",
    "workshop_id",
    "workshop_title",
    "workshop_date",
    "skating_type",
    "status",
    "created_at",
    "updated_at",
]

KEVIN_TRAINING_HEADERS = [
    "registration_id",
    "telegram_id",
    "telegram_username",
    "full_name",
    "phone",
    "age",
    "event_type",
    "participation_type",
    "status",
    "created_at",
    "updated_at",
]


class RegistrationRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registrations (
                    registration_id TEXT PRIMARY KEY,
                    telegram_id INTEGER NOT NULL,
                    telegram_username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    city TEXT NOT NULL,
                    age_or_birthdate TEXT NOT NULL,
                    passport_file_url TEXT NOT NULL,
                    consent_file_url TEXT NOT NULL,
                    discipline TEXT NOT NULL,
                    category TEXT NOT NULL,
                    experience TEXT NOT NULL,
                    sponsors TEXT NOT NULL,
                    status TEXT NOT NULL,
                    needs_review INTEGER NOT NULL,
                    review_note TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workshop_registrations (
                    registration_id TEXT PRIMARY KEY,
                    telegram_id INTEGER NOT NULL,
                    telegram_username TEXT,
                    workshop_id TEXT NOT NULL,
                    workshop_title TEXT NOT NULL,
                    workshop_date TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    skating_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kevin_training_registrations (
                    registration_id TEXT PRIMARY KEY,
                    telegram_id INTEGER NOT NULL,
                    telegram_username TEXT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    age TEXT NOT NULL DEFAULT '',
                    participation_type TEXT NOT NULL DEFAULT 'lottery',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "kevin_training_registrations", "age", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(
                conn,
                "kevin_training_registrations",
                "participation_type",
                "TEXT NOT NULL DEFAULT 'lottery'",
            )

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        definition: str,
    ) -> None:
        columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def save(self, registration: Registration) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO registrations (
                    registration_id, telegram_id, telegram_username, full_name,
                    phone, city, age_or_birthdate, passport_file_url,
                    consent_file_url, discipline, category, experience, sponsors,
                    status, needs_review, review_note, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(registration_id) DO UPDATE SET
                    telegram_username = excluded.telegram_username,
                    full_name = excluded.full_name,
                    phone = excluded.phone,
                    city = excluded.city,
                    age_or_birthdate = excluded.age_or_birthdate,
                    passport_file_url = excluded.passport_file_url,
                    consent_file_url = excluded.consent_file_url,
                    discipline = excluded.discipline,
                    category = excluded.category,
                    experience = excluded.experience,
                    sponsors = excluded.sponsors,
                    status = excluded.status,
                    needs_review = excluded.needs_review,
                    review_note = excluded.review_note,
                    updated_at = excluded.updated_at
                """,
                (
                    registration.registration_id,
                    registration.telegram_id,
                    registration.telegram_username,
                    registration.full_name,
                    registration.phone,
                    registration.city,
                    registration.age_or_birthdate,
                    registration.passport_file_url,
                    registration.consent_file_url,
                    registration.discipline,
                    registration.category,
                    registration.experience,
                    registration.sponsors,
                    registration.status.value,
                    int(registration.needs_review),
                    registration.review_note,
                    registration.created_at,
                    registration.updated_at,
                ),
            )

    def list_by_user(self, telegram_id: int) -> list[Registration]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM registrations
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                """,
                (telegram_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def save_workshop(self, registration: WorkshopRegistration) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workshop_registrations (
                    registration_id, telegram_id, telegram_username, workshop_id,
                    workshop_title, workshop_date, full_name, phone, skating_type,
                    status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(registration_id) DO UPDATE SET
                    telegram_username = excluded.telegram_username,
                    workshop_id = excluded.workshop_id,
                    workshop_title = excluded.workshop_title,
                    workshop_date = excluded.workshop_date,
                    full_name = excluded.full_name,
                    phone = excluded.phone,
                    skating_type = excluded.skating_type,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    registration.registration_id,
                    registration.telegram_id,
                    registration.telegram_username,
                    registration.workshop_id,
                    registration.workshop_title,
                    registration.workshop_date,
                    registration.full_name,
                    registration.phone,
                    registration.skating_type,
                    registration.status.value,
                    registration.created_at,
                    registration.updated_at,
                ),
            )

    def save_kevin_training(self, registration: KevinTrainingRegistration) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kevin_training_registrations (
                    registration_id, telegram_id, telegram_username, full_name,
                    phone, age, participation_type, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(registration_id) DO UPDATE SET
                    telegram_username = excluded.telegram_username,
                    full_name = excluded.full_name,
                    phone = excluded.phone,
                    age = excluded.age,
                    participation_type = excluded.participation_type,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    registration.registration_id,
                    registration.telegram_id,
                    registration.telegram_username,
                    registration.full_name,
                    registration.phone,
                    registration.age,
                    registration.participation_type,
                    registration.status.value,
                    registration.created_at,
                    registration.updated_at,
                ),
            )

    def list_kevin_trainings_by_user(self, telegram_id: int) -> list[KevinTrainingRegistration]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM kevin_training_registrations
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                """,
                (telegram_id,),
            ).fetchall()
        return [self._kevin_training_from_row(row) for row in rows]

    def list_workshops_by_user(self, telegram_id: int) -> list[WorkshopRegistration]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM workshop_registrations
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                """,
                (telegram_id,),
            ).fetchall()
        return [self._workshop_from_row(row) for row in rows]

    def get_workshop(self, registration_id: str) -> WorkshopRegistration | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workshop_registrations WHERE registration_id = ?",
                (registration_id,),
            ).fetchone()
        return self._workshop_from_row(row) if row else None

    def get(self, registration_id: str) -> Registration | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM registrations WHERE registration_id = ?",
                (registration_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def all_submitted(self) -> list[Registration]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM registrations WHERE status = ? ORDER BY created_at",
                (RegistrationStatus.SUBMITTED.value,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def stats_text(self) -> str:
        registrations = self.all_submitted()
        if not registrations:
            return "Пока нет подтвержденных заявок."
        by_category = Counter(item.category for item in registrations)
        by_discipline = Counter(item.discipline for item in registrations)
        lines = [f"Подтвержденных заявок: {len(registrations)}", "\nПо категориям:"]
        lines.extend(f"- {name}: {count}" for name, count in by_category.items())
        lines.append("\nПо дисциплинам:")
        lines.extend(f"- {name}: {count}" for name, count in by_discipline.items())
        return "\n".join(lines)

    def _from_row(self, row: sqlite3.Row) -> Registration:
        return Registration(
            registration_id=row["registration_id"],
            telegram_id=row["telegram_id"],
            telegram_username=row["telegram_username"],
            full_name=row["full_name"],
            phone=row["phone"],
            city=row["city"],
            age_or_birthdate=row["age_or_birthdate"],
            passport_file_url=row["passport_file_url"],
            consent_file_url=row["consent_file_url"],
            discipline=row["discipline"],
            category=row["category"],
            experience=row["experience"],
            sponsors=row["sponsors"],
            status=RegistrationStatus(row["status"]),
            needs_review=bool(row["needs_review"]),
            review_note=row["review_note"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _workshop_from_row(self, row: sqlite3.Row) -> WorkshopRegistration:
        return WorkshopRegistration(
            registration_id=row["registration_id"],
            telegram_id=row["telegram_id"],
            telegram_username=row["telegram_username"],
            workshop_id=row["workshop_id"],
            workshop_title=row["workshop_title"],
            workshop_date=row["workshop_date"],
            full_name=row["full_name"],
            phone=row["phone"],
            skating_type=row["skating_type"],
            status=RegistrationStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _kevin_training_from_row(self, row: sqlite3.Row) -> KevinTrainingRegistration:
        return KevinTrainingRegistration(
            registration_id=row["registration_id"],
            telegram_id=row["telegram_id"],
            telegram_username=row["telegram_username"],
            full_name=row["full_name"],
            phone=row["phone"],
            age=row["age"],
            participation_type=row["participation_type"],
            status=RegistrationStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
