from __future__ import annotations

from dataclasses import dataclass


PRO_NAMES = {
    "Боброва Дарья Алексеевна",
    "Галишев Даниил Александрович",
    "Грачев Даниил Викторович",
    "Ерошевская Анастасия Дмитриевна",
    "Завгородний Матвей Алексеевич",
    "Карпов Степан Александрович",
    "Маясов Илья Евгеньевич",
    "Поляков Илья Андреевич",
    "Раков Виктор Михайлович",
    "Раковчен Андрей Вячеславович",
    "Сафонова Вера Игоревна",
    "Свиридов Максим Иванович",
    "Степанова Любовь Александровна",
    "Харченко Даниил Витальевич",
    "Шумкин Дмитрий Михайлович",
}

BEGINNER_NAMES = {
    "Антонов Георгий Петрович",
    "Бедретдинов Хасан Динарович",
    "Крупеева Анна Владимировна",
    "Михайлов Владимир Евгеньевич",
    "Петрова Злата Александровна",
    "Сурков Сергей Александрович",
    "Шумкина Мария Дмитриевна",
}


@dataclass(frozen=True)
class KevinParticipant:
    telegram_id: int
    telegram_username: str | None
    full_name: str


def grouped_participants(
    rows: list[list[str]],
) -> tuple[list[KevinParticipant], list[KevinParticipant], list[str]]:
    participants: dict[tuple[int, str], KevinParticipant] = {}
    for row in rows:
        try:
            telegram_id = int(row[1])
            full_name = row[3].strip()
        except (IndexError, TypeError, ValueError):
            continue
        username = row[2].strip() if len(row) > 2 else ""
        participant = KevinParticipant(
            telegram_id=telegram_id,
            telegram_username=username or None,
            full_name=full_name,
        )
        participants[(telegram_id, full_name)] = participant

    pro = sorted(
        (item for item in participants.values() if item.full_name in PRO_NAMES),
        key=lambda item: item.full_name,
    )
    beginners = sorted(
        (item for item in participants.values() if item.full_name in BEGINNER_NAMES),
        key=lambda item: item.full_name,
    )
    matched_names = {item.full_name for item in [*pro, *beginners]}
    missing = sorted((PRO_NAMES | BEGINNER_NAMES) - matched_names)
    return pro, beginners, missing
