"""Command line tools, run inside the container:

    docker compose exec web gym login                         # check FF_USERNAME / FF_PASSWORD from .env
    docker compose exec web gym sync                          # sync now (the first run backfills everything)
    # fallbacks if the app changes:
    docker compose exec -T web gym import-curl < curl.txt    # captured check-ins request
    docker compose exec -T web gym import-login < login.txt  # captured login, password -> {{PASSWORD}}
    docker compose exec -T web gym import-csv < checkins.csv  # old v1 CSV export
    docker compose exec web gym status
"""

import argparse
import asyncio
import csv
import json
import random
import sys
from datetime import datetime, timedelta

from . import db
from .config import get_settings
from .fitnessfirst import Netpulse, NetpulseConfig, login_template, parse_curl
from .sync import now_iso, sync_once


def _read(path: str) -> str:
    return sys.stdin.read() if path == "-" else open(path).read()


def cmd_import_curl(args) -> int:
    """Store the captured check-ins request, keeping a login that was imported before."""
    settings = get_settings()
    cap = parse_curl(_read(args.file))
    cfg = NetpulseConfig.from_history_request(cap)
    old = NetpulseConfig.load(settings.credentials_path)
    if old:
        cfg.login = old.login
        cfg.cookie = cfg.cookie or old.cookie
    cfg.saved_at = now_iso()
    cfg.save(settings.credentials_path)
    print(f"Netpulse:  {cfg.base}, exerciser {cfg.exerciser_id[:8]}…")
    print(f"Headers:   {', '.join(sorted(cfg.headers))}")  # names only, never values
    print(f"Session:   {'cookie captured' if cap.cookie else 'none in the request'}; "
          f"login {'configured' if cfg.login else 'not configured'}")
    print("Saved. Syncing now (a first run walks back through the whole history, a few minutes) ...")
    return cmd_sync(args)


def cmd_import_login(args) -> int:
    """Store the captured login request. The password in it must be replaced by {{PASSWORD}}."""
    settings = get_settings()
    cfg = NetpulseConfig.load(settings.credentials_path)
    if cfg is None:
        print("Import the check-ins request first (gym import-curl).")
        return 1
    cap = parse_curl(_read(args.file))
    cfg.login = login_template(cap, cfg.base)
    cfg.saved_at = now_iso()
    cfg.save(settings.credentials_path)
    print(f"Login request saved: {cap.method} {cap.url.split('?')[0]}")
    if not settings.ff_password:
        print("FF_PASSWORD is not set in .env, so it can't be tested yet.")
        return 0
    if "{{USERNAME}}" in cap.body and not settings.ff_username:
        print("The body uses {{USERNAME}} but FF_USERNAME is not set in .env.")
        return 1

    async def test():
        async with Netpulse(cfg, settings.zone, settings.ff_username, settings.ff_password,
                            on_change=lambda c: c.save(settings.credentials_path)) as np:
            await np.login()

    asyncio.run(test())
    print("Login works: got a fresh session.")
    return 0


def cmd_login(args) -> int:
    """Log in with FF_USERNAME / FF_PASSWORD once, to check them. Prints no secrets."""
    settings = get_settings()
    if not (settings.ff_username and settings.ff_password):
        print("Set FF_USERNAME and FF_PASSWORD in .env, then recreate the container.")
        return 1
    cfg = NetpulseConfig.load(settings.credentials_path) or NetpulseConfig.bootstrap()

    async def run():
        async with Netpulse(cfg, settings.zone, settings.ff_username, settings.ff_password,
                            on_change=lambda c: c.save(settings.credentials_path)) as np:
            await np.login()

    asyncio.run(run())
    cfg.saved_at = now_iso()
    cfg.save(settings.credentials_path)
    print(f"Login OK: exerciser {cfg.exerciser_id[:8]}…, fresh session stored.")
    return 0


def cmd_import_csv(args) -> int:
    """v1 format: Studio,Start Time,End Time,Duration with local 'YYYY-MM-DD HH:MM:SS' times."""
    settings = get_settings()
    zone = settings.zone
    f = sys.stdin if args.file == "-" else open(args.file, newline="")
    visits = []
    for row in csv.DictReader(f):
        start = datetime.strptime(row["Start Time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=zone)
        end = row.get("End Time")
        end = datetime.strptime(end, "%Y-%m-%d %H:%M:%S").replace(tzinfo=zone) if end else None
        visits.append(db.Visit(start, end, row.get("Studio") or None))
    with db.connect(settings.db_path) as conn:
        changed = db.upsert_visits(conn, visits, "csv")
    print(f"{len(visits)} rows read, {changed} new or updated.")
    return 0


def cmd_seed_demo(args) -> int:
    """Fill the database with ~2 years of made-up visits (local development only)."""
    settings = get_settings()
    zone = settings.zone
    rng = random.Random(42)
    day = datetime.now(zone).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=730)
    end = datetime.now(zone)
    visits = []
    motivation = 0.55
    while day < end:
        motivation = min(0.85, max(0.1, motivation + rng.uniform(-0.08, 0.08)))
        p = motivation * (0.55 if day.weekday() >= 5 else 0.45)
        if day.month in (8, 12):
            p *= 0.5  # holidays
        if rng.random() < p:
            hour = rng.choice([7, 7, 8, 12, 17, 18, 18, 19, 19, 20]) if day.weekday() < 5 else rng.choice([10, 11, 12, 14, 16])
            start = day.replace(hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59))
            if start + timedelta(hours=3) < end:  # check-ins only, like Fitness First reports them
                visits.append(db.Visit(start, None, rng.choice(["Frankfurt - Industriehof", "Frankfurt - Industriehof", "Frankfurt - Opernplatz"])))
        day += timedelta(days=1)
    with db.connect(settings.db_path) as conn:
        changed = db.upsert_visits(conn, visits, "demo")
        db.set_meta(conn, "sync", {"state": "ok", "last_ok": now_iso()})
    print(f"{changed} demo visits written to {settings.db_path}")
    return 0


def cmd_sync(args) -> int:
    status = asyncio.run(sync_once(get_settings(), force_backfill=getattr(args, "backfill", False)))
    print(json.dumps(status, indent=2))
    return 0 if status.get("state") == "ok" else 1


def cmd_status(args) -> int:
    settings = get_settings()
    with db.connect(settings.db_path) as conn:
        status = db.get_meta(conn, "sync") or {}
        n, first, last = conn.execute("SELECT COUNT(*), MIN(checkin), MAX(checkin) FROM sessions").fetchone()
    cfg = NetpulseConfig.load(settings.credentials_path)
    print(f"Visits stored: {n} ({first or '-'} .. {last or '-'})")
    print(f"Netpulse:      {'session stored ' + (cfg.saved_at or '') if cfg else 'nothing stored yet'}"
          f"{', captured login override' if cfg and cfg.login else ''}")
    print(f"Login:         {'FF_USERNAME + FF_PASSWORD set' if settings.ff_username and settings.ff_password else 'FF_USERNAME / FF_PASSWORD missing'}")
    print(json.dumps(status, indent=2))
    return 0


def main() -> None:
    p = argparse.ArgumentParser(prog="gym")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("import-curl", help="store the captured check-ins request (curl from Proxyman) and sync")
    s.add_argument("file", nargs="?", default="-")
    s.set_defaults(fn=cmd_import_curl, backfill=False)
    s = sub.add_parser("import-login", help="store the captured login request (password replaced by {{PASSWORD}})")
    s.add_argument("file", nargs="?", default="-")
    s.set_defaults(fn=cmd_import_login)
    s = sub.add_parser("import-csv", help="import a v1 checkins.csv")
    s.add_argument("file", nargs="?", default="-")
    s.set_defaults(fn=cmd_import_csv)
    sub.add_parser("login", help="check FF_USERNAME / FF_PASSWORD by logging in once").set_defaults(fn=cmd_login)
    sub.add_parser("seed-demo", help="write made-up visits (dev only)").set_defaults(fn=cmd_seed_demo)
    s = sub.add_parser("sync", help="sync with Fitness First now")
    s.add_argument("--backfill", action="store_true", help="walk back through the whole history again")
    s.set_defaults(fn=cmd_sync)
    sub.add_parser("status", help="show sync status").set_defaults(fn=cmd_status)
    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
