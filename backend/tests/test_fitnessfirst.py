import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest

from app import db
from app.fitnessfirst import (
    AuthExpired, Netpulse, NetpulseConfig, login_template, month_window, parse_curl, parse_time, parse_visits,
)

BERLIN = ZoneInfo("Europe/Berlin")
BASE = "https://fitnessfirst.netpulse.com"
EID = "00000000-1111-2222-3333-444444444444"

HISTORY_CURL = (
    f"curl -H 'Host: fitnessfirst.netpulse.com' -H 'Accept: application/json,text/plain' "
    "-H 'Cookie: JSESSIONID=abc123; Max-Age=10800; Expires=Fri, 13 Nov 2026 09:41:59 GMT; Path=/; Secure; HttpOnly' "
    "-H 'X-NP-API-Version: 1.5' -H 'X-NP-APP-Version: 3.1' "
    "-H 'Accept-Encoding: br;q=1.0, gzip;q=0.9' -H 'User-Agent: FitnessFirst/3.1 (com.netpulse.fitnessfirst; build:329)' "
    f"--compressed '{BASE}/np/exercisers/{EID}/check-ins/history?endDate=2026-10-31T23%3A59%3A59&startDate=2026-10-01T00%3A00%3A00'"
)

PAYLOAD = {"checkIns": [
    {"gymLocationName": "Frankfurt - Opernplatz", "gymLocationAddress": "Hochstraße 44",
     "checkInDate": "2026-10-31T17:05:10", "timezone": "Europe/Berlin", "checkinId": None, "duration": None},
    {"gymLocationName": "Frankfurt - Industriehof", "checkInDate": "2026-07-30T18:37:17", "timezone": "Europe/Berlin"},
]}


def test_parse_netpulse_history():
    a, b = parse_visits(PAYLOAD, BERLIN)
    assert a.checkin == datetime(2026, 10, 31, 17, 5, 10, tzinfo=BERLIN)
    assert a.checkin.utcoffset() == timedelta(hours=1)  # CET
    assert b.checkin.utcoffset() == timedelta(hours=2)  # CEST
    assert a.checkout is None and a.studio == "Frankfurt - Opernplatz"


def test_parse_entry_timezone_wins():
    [v] = parse_visits({"checkIns": [{"checkInDate": "2026-10-31T17:00:00", "timezone": "Europe/London"}]}, BERLIN)
    assert v.checkin.astimezone(BERLIN).hour == 18


def test_parse_legacy_shapes():
    assert parse_time("2024-05-10T18:03:12.123+02:00[Europe/Berlin]", BERLIN) == datetime(2024, 5, 10, 18, 3, 12, tzinfo=BERLIN)
    [v] = parse_visits([{"studioName": "X", "checkinTime": "2024-05-10T18:00:00.000+02:00[Europe/Berlin]",
                         "checkoutTime": "2024-05-10T19:00:00.000+02:00[Europe/Berlin]"}], BERLIN)
    assert v.checkout - v.checkin == timedelta(hours=1)
    with pytest.raises(ValueError):
        parse_visits({"foo": 1}, BERLIN)


def test_history_curl_to_config():
    cfg = NetpulseConfig.from_history_request(parse_curl(HISTORY_CURL))
    assert (cfg.base, cfg.exerciser_id, cfg.cookie) == (BASE, EID, "abc123")
    assert set(cfg.headers) == {"Accept", "X-NP-API-Version", "X-NP-APP-Version", "User-Agent"}


def test_wrong_request_rejected():
    with pytest.raises(ValueError):
        NetpulseConfig.from_history_request(parse_curl(f"curl '{BASE}/np/exercisers/{EID}/latest-check-in'"))


def test_login_template_needs_placeholder():
    cap = parse_curl(f"curl -X POST '{BASE}/np/exerciser/login' -H 'Content-Type: application/x-www-form-urlencoded' "
                     "--data 'username=me%40x.de&password=secret'")
    with pytest.raises(ValueError):
        login_template(cap, BASE)


def test_month_window():
    assert month_window(2024, 2) == ("2024-02-01T00:00:00", "2024-02-29T23:59:59")


def _np(handler, login=True, password="pw"):
    cfg = NetpulseConfig(base=BASE, exerciser_id=EID, headers={"X-NP-API-Version": "1.5"}, cookie="old")
    if login:
        cfg.login = {"method": "POST", "url": f"{BASE}/np/exerciser/login",
                     "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                     "body": "username={{USERNAME}}&password={{PASSWORD}}"}
    saved = []
    np = Netpulse(cfg, BERLIN, "me@x.de", password, on_change=lambda c: saved.append(c.cookie))
    np.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return np, saved


async def test_relogin_on_403():
    seen = []

    def handler(req: httpx.Request):
        seen.append((req.method, req.url.path, req.headers.get("cookie"), req.content.decode()))
        if req.url.path.endswith("/login"):
            return httpx.Response(200, json={"uuid": EID}, headers={"set-cookie": "JSESSIONID=new; Path=/; HttpOnly"})
        if req.headers.get("cookie") == "JSESSIONID=new":
            return httpx.Response(200, json=PAYLOAD)
        return httpx.Response(403, json={"message": "Access is denied"})

    np, saved = _np(handler)
    async with np:
        visits = await np.history(*month_window(2026, 10))
    assert len(visits) == 2
    assert saved == ["new"]
    login = seen[1]
    assert login[3] == "username=me%40x.de&password=pw"
    assert seen[2][2] == "JSESSIONID=new"


async def test_no_login_raises_auth_expired():
    np, _ = _np(lambda req: httpx.Response(403, json={}), login=False, password="")
    async with np:
        with pytest.raises(AuthExpired):
            await np.history(*month_window(2026, 10))


async def test_backfill_stops_after_empty_months(monkeypatch):
    import app.fitnessfirst as ff

    async def nosleep(_):
        pass

    monkeypatch.setattr(ff.asyncio, "sleep", nosleep)
    months = []

    def handler(req: httpx.Request):
        start = req.url.params["startDate"][:7]
        months.append(start)
        if start in ("2026-11", "2026-09"):
            return httpx.Response(200, json={"checkIns": [{"checkInDate": f"{start}-02T18:00:00", "timezone": "Europe/Berlin"}]})
        return httpx.Response(200, json={"checkIns": []})

    np, _ = _np(handler)
    async with np:
        visits = await np.backfill(datetime(2026, 11, 13, tzinfo=BERLIN), 2012, 3)
    assert len(visits) == 2
    assert months == ["2026-11", "2026-10", "2026-09", "2026-08", "2026-07", "2026-06"]


def test_upsert_fills_checkout_later(tmp_path):
    start = datetime(2024, 5, 10, 18, 0, tzinfo=BERLIN)
    with db.connect(tmp_path / "t.db") as conn:
        assert db.upsert_visits(conn, [db.Visit(start, None, "A")], "app") == 1
        assert db.upsert_visits(conn, [db.Visit(start, None, "A")], "app") == 0
        assert db.upsert_visits(conn, [db.Visit(start, start + timedelta(hours=1), "A")], "app") == 1
        [v] = db.all_visits(conn)
        assert v.checkout == start + timedelta(hours=1)


async def test_builtin_login_bootstraps_exerciser_id():
    seen = []
    real = "5b1c2d3e-4f50-4617-8293-a4b5c6d7e8f9"

    def handler(req: httpx.Request):
        seen.append(req)
        if req.url.path == "/np/exerciser/login":
            return httpx.Response(200, json={"uuid": real, "homeClubName": "X"},
                                  headers={"set-cookie": "JSESSIONID=s1; Max-Age=10800; Path=/; Secure; HttpOnly"})
        assert req.headers["cookie"] == "JSESSIONID=s1"
        return httpx.Response(200, json=PAYLOAD)

    cfg = NetpulseConfig.bootstrap()
    np = Netpulse(cfg, BERLIN, "me@x.de", "p&ss=wörd", on_change=lambda c: None)
    np.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with np:
        visits = await np.history(*month_window(2026, 10))
    assert len(visits) == 2
    login, hist = seen
    assert login.method == "POST" and login.headers["content-type"].startswith("application/x-www-form-urlencoded")
    assert dict(httpx.QueryParams(login.content.decode())) == {"username": "me@x.de", "password": "p&ss=wörd"}
    assert login.headers["x-np-api-version"] == "1.5" and "deviceUid=" in login.headers["x-np-user-agent"]
    assert hist.url.path == f"/np/exercisers/{real}/check-ins/history"
    assert cfg.exerciser_id == real and cfg.cookie == "s1"


async def test_wrong_password_raises_login_rejected():
    from app.fitnessfirst import LoginRejected

    def handler(req: httpx.Request):
        return httpx.Response(401, json={"message": "Username or password does not match"},
                              headers={"set-cookie": "JSESSIONID=x; Path=/"})

    np = Netpulse(NetpulseConfig.bootstrap(), BERLIN, "me@x.de", "wrong")
    np.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with np:
        with pytest.raises(LoginRejected):
            await np.history(*month_window(2026, 10))


async def test_sync_stops_logging_in_after_rejection(tmp_path, monkeypatch):
    import app.sync as sync
    from app.config import Settings

    calls = []

    async def fake_history(self, start, end):
        calls.append(start)
        from app.fitnessfirst import LoginRejected
        raise LoginRejected("rejected")

    monkeypatch.setattr(sync.Netpulse, "history", fake_history)
    monkeypatch.setattr(sync, "_login_rejected", None)
    st = Settings(data_dir=tmp_path, ff_username="me@x.de", ff_password="wrong", _env_file=None)
    assert (await sync.sync_once(st))["state"] == "login_rejected"
    assert (await sync.sync_once(st))["state"] == "login_rejected"
    assert len(calls) == 1  # the second sync didn't try again
    assert NetpulseConfig.load(st.credentials_path).base == "https://fitnessfirst.netpulse.com"


async def test_headers_with_trailing_space_are_sent():
    """Regression: the app's X-NP-User-Agent ends in '; ', which h11 refuses. Uses the real transport stack."""
    import asyncio
    from app.fitnessfirst import default_headers

    got = {}

    async def serve(reader, writer):
        head = (await reader.readuntil(b"\r\n\r\n")).decode()
        got["head"] = head
        writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    cfg = NetpulseConfig(base=f"http://127.0.0.1:{port}", exerciser_id=EID, cookie="c",
                         headers={**default_headers("X"), "X-NP-User-Agent": "clientType=MOBILE_DEVICE; deviceUid=X; "})
    async with server, Netpulse(cfg, BERLIN) as np:
        with pytest.raises(AuthExpired):
            await np.history(*month_window(2026, 10))
    assert "deviceUid=X;\r\n" in got["head"]  # sent, with the trailing space stripped
    assert not default_headers("X")["X-NP-User-Agent"].endswith(" ")


def test_five_sync_slots_a_day(monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app import sync
    from app.config import Settings

    st = Settings(sync_per_day=5, sync_first_hour=8, sync_last_hour=22, sync_jitter_minutes=0)
    z = ZoneInfo("Europe/Berlin")
    day = datetime(2026, 11, 13, 12, 0, tzinfo=z)
    assert [s.strftime("%H:%M") for s in sync.slots(st, day)] == ["08:00", "11:30", "15:00", "18:30", "22:00"]
    assert sync.next_delay(st, day) == 3 * 3600  # 12:00 -> 15:00
    assert sync.next_delay(st, datetime(2026, 11, 13, 22, 30, tzinfo=z)) == 9.5 * 3600  # -> 08:00 next day
    st.sync_jitter_minutes = 20
    for _ in range(200):
        assert 2 * 3600 + 39 * 60 <= sync.next_delay(st, day) <= 3 * 3600 + 21 * 60


def test_data_start_hides_older_checkins(tmp_path, monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app import config, db, main

    z = ZoneInfo("Europe/Berlin")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATA_START", "2024-10-14")
    monkeypatch.setenv("SYNC_ENABLED", "false")
    config.get_settings.cache_clear()
    try:
        with db.connect(tmp_path / "gym.db") as conn:
            db.upsert_visits(conn, [
                db.Visit(datetime(2024, 3, 22, 20, 14, tzinfo=z), None, "A"),
                db.Visit(datetime(2024, 9, 3, 18, 32, tzinfo=z), None, "A"),
                db.Visit(datetime(2024, 10, 14, 17, 32, tzinfo=z), None, "A"),
            ], "test")
            assert len(db.all_visits(conn)) == 3  # kept in the database
        assert [s["start"][:10] for s in main.build_dashboard()["sessions"]] == ["2024-10-14"]
    finally:
        config.get_settings.cache_clear()
