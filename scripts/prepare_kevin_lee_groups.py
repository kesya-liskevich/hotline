from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from hotline_bot.kevin_groups import grouped_participants


def main() -> None:
    settings = get_settings()
    sheets = GoogleClients(
        settings.google_service_account_file,
        settings.google_sheets_spreadsheet_id,
        settings.google_drive_root_folder_id,
        settings.google_drive_oauth_client_file,
        settings.google_drive_oauth_token_file,
    ).sheets()
    rows = sheets._read_rows("kevin_lee_lottery!A2:K")
    pro, beginners, missing = grouped_participants(rows)

    print(f"Pro participants: {len(pro)}; unique Telegram IDs: {len({item.telegram_id for item in pro})}")
    for item in pro:
        print(f"- {item.full_name}: {item.telegram_id}")
    print(
        f"Beginner participants: {len(beginners)}; "
        f"unique Telegram IDs: {len({item.telegram_id for item in beginners})}"
    )
    for item in beginners:
        print(f"- {item.full_name}: {item.telegram_id}")
    shared_ids = sorted(
        {item.telegram_id for item in pro} & {item.telegram_id for item in beginners}
    )
    print(f"Shared Telegram IDs between groups: {shared_ids}")
    print(f"Missing names: {missing}")
    print("Dry run only. This script does not send messages.")


if __name__ == "__main__":
    main()
