import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

TRUE = {"1", "true", "yes", "on"}


def parse_ref(ref: str) -> str | int:
    ref = ref.strip()
    if ref.lstrip("-").isdigit():
        return int(ref)
    return ref.removeprefix("https://").removeprefix("http://").removeprefix("t.me/").split("/")[0]


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Не задана переменная {name}, см. .env.example")
    return value


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    sources: list[str | int]
    target: str | int
    data_dir: Path
    save_media: bool
    max_media_mb: float
    media_keep_days: int
    backfill: int
    check_interval_min: int
    check_days: int
    report_unknown: bool
    tz_offset: float
    signature: str

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        get = os.getenv
        return cls(
            api_id=int(_required("API_ID")),
            api_hash=_required("API_HASH"),
            sources=[parse_ref(ref) for ref in _required("SOURCE_CHANNELS").split(",") if ref.strip()],
            target=parse_ref(_required("TARGET_CHANNEL")),
            data_dir=Path(get("DATA_DIR", "data")).resolve(),
            save_media=get("SAVE_MEDIA", "true").lower() in TRUE,
            max_media_mb=float(get("MAX_MEDIA_MB", "20")),
            media_keep_days=int(get("MEDIA_KEEP_DAYS", "7")),
            backfill=int(get("BACKFILL_LIMIT", "50")),
            check_interval_min=int(get("CHECK_INTERVAL_MIN", "30")),
            check_days=int(get("CHECK_DAYS", "3")),
            report_unknown=get("REPORT_UNKNOWN", "false").lower() in TRUE,
            tz_offset=float(get("TZ_OFFSET", "3")),
            signature=get("SIGNATURE", "это автоматическое сообщение бота"),
        )

    def format_time(self, moment: datetime) -> str:
        tz = timezone(timedelta(hours=self.tz_offset))
        label = "МСК" if self.tz_offset == 3 else f"UTC{self.tz_offset:+g}"
        return f"{moment.astimezone(tz):%d.%m.%Y %H:%M:%S} {label}"
