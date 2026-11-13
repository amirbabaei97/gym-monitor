from datetime import date
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("/data")
    static_dir: Path = Path(__file__).resolve().parent.parent / "static"
    tz: str = "Europe/Berlin"

    site_title: str = "Gym Wall of Shame"
    weekly_goal: int = 3

    # Privacy: the page is public. Off by default: whether I'm in the gym
    # right now, and which studio I go to.
    show_live: bool = False
    show_studios: bool = False

    # Sync schedule: SYNC_PER_DAY runs spread evenly from SYNC_FIRST_HOUR to
    # SYNC_LAST_HOUR (local time), each moved by up to ±SYNC_JITTER_MINUTES.
    sync_per_day: int = 5
    sync_first_hour: float = 8
    sync_last_hour: float = 22
    sync_jitter_minutes: int = 20
    sync_enabled: bool = True

    # Check-ins before this date (YYYY-MM-DD) stay in the database but are left
    # out of the page, e.g. stray early check-ins from before the app counted
    # reliably. Empty = show everything.
    data_start: str = ""

    # Fitness First (Netpulse) account, used only to renew the session via the
    # captured login request. Kept in .env (mode 600) on the server.
    ff_username: str = ""
    ff_password: str = ""

    # One-time history backfill: walk back month by month until this many
    # empty months in a row, but not before this year.
    backfill_empty_months: int = 18
    backfill_floor_year: int = 2012

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    @property
    def data_start_date(self) -> date | None:
        return date.fromisoformat(self.data_start) if self.data_start.strip() else None

    @property
    def db_path(self) -> Path:
        return self.data_dir / "gym.db"

    @property
    def credentials_path(self) -> Path:
        return self.data_dir / "netpulse.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
