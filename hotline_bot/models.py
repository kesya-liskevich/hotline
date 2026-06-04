from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from hotline_bot.program import review_reason


class RegistrationStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"


@dataclass
class Registration:
    telegram_id: int
    telegram_username: str | None = None
    registration_id: str = field(default_factory=lambda: uuid4().hex)
    full_name: str = ""
    phone: str = ""
    city: str = ""
    age_or_birthdate: str = ""
    passport_file_url: str = ""
    consent_file_url: str = ""
    discipline: str = ""
    category: str = ""
    experience: str = ""
    sponsors: str = ""
    status: RegistrationStatus = RegistrationStatus.DRAFT
    needs_review: bool = False
    review_note: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def mark_submitted(self) -> None:
        reason = review_reason(self.discipline, self.category)
        self.needs_review = reason is not None
        self.review_note = reason or ""
        self.status = RegistrationStatus.SUBMITTED
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_cancelled(self) -> None:
        self.status = RegistrationStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def as_row(self) -> list[str]:
        return [
            self.registration_id,
            str(self.telegram_id),
            self.telegram_username or "",
            self.full_name,
            self.phone,
            self.city,
            "competition",
            self.discipline,
            self.category,
            self.age_or_birthdate,
            self.experience,
            self.sponsors,
            self.passport_file_url,
            self.consent_file_url,
            self.status.value,
            "yes" if self.needs_review else "no",
            self.review_note,
            self.created_at,
            self.updated_at,
        ]

    def summary(self) -> str:
        review = "\n\nНужна ручная проверка: да" if self.needs_review else ""
        return (
            "Проверьте заявку:\n\n"
            f"ФИО: {self.full_name}\n"
            f"Телефон: {self.phone}\n"
            f"Город: {self.city}\n"
            f"Дата рождения: {self.age_or_birthdate}\n"
            f"Дисциплина: {self.discipline}\n"
            f"Категория: {self.category}\n"
            f"Стаж катания: {self.experience}\n"
            f"Спонсоры: {self.sponsors or 'нет / не указаны'}"
            f"{review}"
        )


@dataclass
class WorkshopRegistration:
    telegram_id: int
    telegram_username: str | None = None
    registration_id: str = field(default_factory=lambda: uuid4().hex)
    workshop_id: str = ""
    workshop_title: str = ""
    workshop_date: str = ""
    full_name: str = ""
    phone: str = ""
    skating_type: str = ""
    status: RegistrationStatus = RegistrationStatus.SUBMITTED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def mark_cancelled(self) -> None:
        self.status = RegistrationStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def as_row(self) -> list[str]:
        return [
            self.registration_id,
            str(self.telegram_id),
            self.telegram_username or "",
            self.full_name,
            self.phone,
            "workshop",
            self.workshop_id,
            self.workshop_title,
            self.workshop_date,
            self.skating_type,
            self.status.value,
            self.created_at,
            self.updated_at,
        ]

    def summary(self) -> str:
        skating = f"\nФСК или агрессив: {self.skating_type}" if self.skating_type else ""
        return (
            "Запись на мастер-класс:\n\n"
            f"{self.workshop_title}\n"
            f"{self.workshop_date}\n\n"
            f"ФИО: {self.full_name}\n"
            f"Телефон: {self.phone}"
            f"{skating}"
        )


@dataclass
class KevinTrainingRegistration:
    telegram_id: int
    telegram_username: str | None = None
    registration_id: str = field(default_factory=lambda: uuid4().hex)
    full_name: str = ""
    phone: str = ""
    age: str = ""
    status: RegistrationStatus = RegistrationStatus.SUBMITTED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_row(self) -> list[str]:
        return [
            self.registration_id,
            str(self.telegram_id),
            self.telegram_username or "",
            self.full_name,
            self.phone,
            self.age,
            "kevin_lee_training",
            self.status.value,
            self.created_at,
            self.updated_at,
        ]
