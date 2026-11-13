"""Background sync with Fitness First (Netpulse) on a jittered schedule."""

import asyncio
import logging
import random
from datetime import datetime, timedelta

from . import db
from .config import Settings
from .fitnessfirst import AuthExpired, LoginFailed, LoginRejected, Netpulse, NetpulseConfig

log = logging.getLogger("gym.sync")

# Set when Fitness First rejects FF_USERNAME / FF_PASSWORD. No more logins in
# this process after that (repeated bad logins can lock the account); editing
# .env and recreating the container starts a new process and clears it.
_login_rejected: str | None = None


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _client(settings: Settings, cfg: NetpulseConfig) -> Netpulse:
    return Netpulse(cfg, settings.zone, settings.ff_username, settings.ff_password,
                    on_change=lambda c: c.save(settings.credentials_path))


async def sync_once(settings: Settings, force_backfill: bool = False) -> dict:
    """Fetch, store, and record the outcome in the meta table. Never raises."""
    global _login_rejected
    cfg = NetpulseConfig.load(settings.credentials_path)
    if cfg is None and settings.ff_username and settings.ff_password:
        cfg = NetpulseConfig.bootstrap()
        cfg.save(settings.credentials_path)
        log.info("no stored session: bootstrapping, will log in as the configured user")
    with db.connect(settings.db_path) as conn:
        status = db.get_meta(conn, "sync") or {}
    status["last_attempt"] = now_iso()
    status.pop("token_expires", None)

    if cfg is None:
        status.update(state="not_configured", error="Set FF_USERNAME / FF_PASSWORD in .env (or gym import-curl).")
    elif _login_rejected:
        status.update(state="login_rejected", error=_login_rejected)
    else:
        try:
            now = datetime.now(settings.zone)
            async with _client(settings, cfg) as np:
                status["can_login"] = np.can_login
                if force_backfill or not status.get("backfill_done"):
                    log.info("backfill: walking back through the check-in history")
                    visits = await np.backfill(
                        now, settings.backfill_floor_year, settings.backfill_empty_months,
                        progress=lambda y, m, n: log.info("backfill %04d-%02d: %d check-ins", y, m, n),
                    )
                    status["backfill_done"] = now_iso()
                else:
                    visits = await np.recent(now)
            with db.connect(settings.db_path) as conn:
                changed = db.upsert_visits(conn, visits, "app")
            status.update(state="ok", error=None, last_ok=now_iso(), last_count=len(visits), last_changed=changed)
            log.info("sync ok: %d check-ins fetched, %d new or updated", len(visits), changed)
        except LoginRejected as e:
            _login_rejected = str(e)
            status.update(state="login_rejected", error=str(e))
            log.error("sync: %s. No more login attempts until the container is recreated.", e)
        except (AuthExpired, LoginFailed) as e:
            status.update(state="auth_expired", error=str(e))
            log.warning("sync: %s", e)
        except Exception as e:  # network, JSON, schema change ...
            status.update(state="error", error=f"{type(e).__name__}: {e}"[:300])
            log.exception("sync failed")

    with db.connect(settings.db_path) as conn:
        db.set_meta(conn, "sync", status)
    return status


def slots(settings: Settings, day: datetime) -> list[datetime]:
    """The day's planned sync times, evenly spread from first to last hour."""
    n = max(1, settings.sync_per_day)
    first, last = settings.sync_first_hour, settings.sync_last_hour
    step = (last - first) / (n - 1) if n > 1 else 0
    midnight = day.replace(hour=0, minute=0, second=0, microsecond=0)
    return [midnight + timedelta(hours=first + i * step) for i in range(n)]


def next_delay(settings: Settings, now: datetime | None = None) -> float:
    """Seconds until the next planned slot (after the jitter), at least a minute."""
    now = now or datetime.now(settings.zone)
    jitter = settings.sync_jitter_minutes
    for day in (now, now + timedelta(days=1)):
        for slot in slots(settings, day):
            at = slot + timedelta(minutes=random.uniform(-jitter, jitter))
            if at > now + timedelta(minutes=1):
                return (at - now).total_seconds()
    return 3600.0


async def sync_loop(settings: Settings) -> None:
    await asyncio.sleep(random.uniform(5, 20))
    while True:
        status = await sync_once(settings)
        delay = next_delay(settings)
        nxt = datetime.now().astimezone() + timedelta(seconds=delay)
        with db.connect(settings.db_path) as conn:
            st = db.get_meta(conn, "sync") or {}
            st["next_at"] = nxt.isoformat(timespec="seconds")
            db.set_meta(conn, "sync", st)
        log.info("next sync in %.0f min", delay / 60)
        await asyncio.sleep(delay)
