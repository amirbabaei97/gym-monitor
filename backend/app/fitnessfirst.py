"""Fitness First check-ins via Netpulse, the platform behind the Fitness First app.

There is no public API. Everything here mirrors what the iOS app does, as
captured with Proxyman on 2026-11-13:

    GET https://fitnessfirst.netpulse.com/np/exercisers/<uuid>/check-ins/history
        ?startDate=2026-10-01T00:00:00&endDate=2026-10-31T23:59:59
    Cookie: JSESSIONID=...           (session, Max-Age 3 h)
    X-NP-API-Version / X-NP-APP-Version / X-NP-User-Agent / User-Agent

    -> {"checkIns": [{"gymLocationName": "...", "checkInDate": "2026-10-31T17:05:10",
                      "timezone": "Europe/Berlin", "duration": null, ...}]}

Only check-in times are returned (no check-out). The app asks for one month
at a time, and so do we.

Login (from a HAR of the app, 2026-11-13) is a single form post:

    POST https://fitnessfirst.netpulse.com/np/exerciser/login
    Content-Type: application/x-www-form-urlencoded
    username=<e-mail>&password=<password>
    -> 200 {"uuid": "<exerciser uuid>", ...} + Set-Cookie: JSESSIONID=...; Max-Age=10800
    -> 401 {"message": "Username or password does not match"}

So with FF_USERNAME / FF_PASSWORD set, nothing has to be captured: the client
logs in, learns its exerciser uuid and renews the session whenever it's refused.
`gym import-curl` / `gym import-login` remain as fallbacks if the app changes.
"""

import asyncio
import json
import os
import random
import re
import shlex
from calendar import monthrange
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

from .db import Visit

DEFAULT_BASE = "https://fitnessfirst.netpulse.com"


def default_headers(device_uid: str) -> dict[str, str]:
    """What the iOS app (3.1, build 329) sends. The device id is our own, not the phone's."""
    return {
        "Accept": "application/json,text/plain",
        "Accept-Language": "en-DE;q=1.0",
        "X-NP-API-Version": "1.5",
        "X-NP-APP-Version": "3.1",
        "X-NP-User-Agent": (
            f"clientType=MOBILE_DEVICE; devicePlatform=IOS; deviceUid={device_uid}; "
            "applicationName=Fitness First; applicationVersion=3.1; applicationVersionCode=329;"
        ),
        "User-Agent": "FitnessFirst/3.1 (com.netpulse.fitnessfirst; build:329; iOS 27.2.0) Alamofire/5.9.1",
    }


def clean_headers(headers: dict[str, str]) -> dict[str, str]:
    """h11 refuses values with leading/trailing whitespace; the app itself sends 'X-NP-User-Agent: …; '."""
    return {k.strip(): v.strip() for k, v in headers.items()}


HISTORY_RE = re.compile(r"^(https://[^/]+)/np/exercisers/([^/?#]+)/check-ins/history")
JSESSION_RE = re.compile(r"JSESSIONID=([^;\s]+)")

# Headers that must not be replayed verbatim (httpx sets them itself).
DROP_HEADERS = {"host", "content-length", "accept-encoding", "connection", "transfer-encoding", "cookie"}


class AuthExpired(Exception):
    """Session refused (401/403) and no working login to renew it."""


class LoginFailed(Exception):
    """Login didn't work for a reason that may go away (server error, no cookie)."""


class LoginRejected(LoginFailed):
    """Wrong username or password. Retrying would only risk locking the account."""


# --- capturing ------------------------------------------------------------------

@dataclass
class Captured:
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    cookie: str | None = None  # JSESSIONID value, if the request carried one
    body: str | None = None


def parse_curl(command: str) -> Captured:
    """Parse `curl ...` as copied from Proxyman, Charles or browser dev tools."""
    command = command.replace("\\\r\n", " ").replace("\\\n", " ").strip()
    args = shlex.split(command)
    if not args or args[0] != "curl":
        raise ValueError("expected a command starting with 'curl'")

    url, method, body, cookie = None, None, None, None
    headers: dict[str, str] = {}
    i = 1
    while i < len(args):
        a = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else None
        if a in ("-H", "--header") and nxt is not None:
            name, _, value = nxt.partition(":")
            name, value = name.strip(), value.strip()
            if name.lower() == "cookie":
                m = JSESSION_RE.search(value)
                cookie = m.group(1) if m else cookie
            elif name.lower() not in DROP_HEADERS:
                headers[name] = value
            i += 2
        elif a in ("-X", "--request") and nxt is not None:
            method = nxt.upper()
            i += 2
        elif a in ("-b", "--cookie") and nxt is not None:
            m = JSESSION_RE.search(nxt)
            cookie = m.group(1) if m else cookie
            i += 2
        elif a in ("-A", "--user-agent") and nxt is not None:
            headers["User-Agent"] = nxt
            i += 2
        elif a in ("-d", "--data", "--data-raw", "--data-binary", "--data-ascii", "--data-urlencode") and nxt is not None:
            body = nxt if body is None else f"{body}&{nxt}"
            i += 2
        elif a == "--url" and nxt is not None:
            url = nxt
            i += 2
        elif a.startswith("-"):
            i += 1  # --compressed, -k, -i, -s, ... take no value
        else:
            url = a
            i += 1

    if not url or not url.startswith("https://"):
        raise ValueError("no https:// URL found in the curl command")
    return Captured(url=url, method=method or ("POST" if body else "GET"), headers=headers, cookie=cookie, body=body)


# --- stored configuration -----------------------------------------------------------

@dataclass
class NetpulseConfig:
    base: str                       # https://fitnessfirst.netpulse.com
    exerciser_id: str
    headers: dict[str, str]         # the app's own headers (no cookie)
    cookie: str | None = None       # current JSESSIONID
    login: dict | None = None       # captured login request with {{PASSWORD}} placeholder
    saved_at: str | None = None

    @classmethod
    def bootstrap(cls, base: str = DEFAULT_BASE) -> "NetpulseConfig":
        """A fresh config for logging in with FF_USERNAME / FF_PASSWORD; the exerciser id comes from the login."""
        import uuid
        return cls(base=base, exerciser_id="", headers=default_headers(str(uuid.uuid4()).upper()))

    @classmethod
    def from_history_request(cls, cap: Captured) -> "NetpulseConfig":
        m = HISTORY_RE.match(cap.url)
        if not m:
            raise ValueError("that isn't the check-ins request: expected …/np/exercisers/<id>/check-ins/history")
        return cls(base=m.group(1), exerciser_id=m.group(2), headers=cap.headers, cookie=cap.cookie)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(asdict(self), f, indent=2)
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "NetpulseConfig | None":
        try:
            return cls(**json.loads(path.read_text()))
        except FileNotFoundError:
            return None


def login_template(cap: Captured, base: str) -> dict:
    if not cap.url.startswith(base + "/"):
        raise ValueError(f"login request goes to {urlsplit(cap.url).netloc}, not {urlsplit(base).netloc}")
    if not cap.body or "{{PASSWORD}}" not in cap.body:
        raise ValueError("replace the password in the captured login body with {{PASSWORD}} first")
    return {"method": cap.method, "url": cap.url, "headers": cap.headers, "body": cap.body}


def _fill(template: str, username: str, password: str, content_type: str) -> str:
    if "json" in content_type:
        enc = lambda v: json.dumps(v)[1:-1]
    elif "x-www-form-urlencoded" in content_type:
        from urllib.parse import quote_plus as enc
    else:
        enc = lambda v: v
    return template.replace("{{USERNAME}}", enc(username)).replace("{{PASSWORD}}", enc(password))


# --- parsing ---------------------------------------------------------------------------

def parse_time(value, zone: ZoneInfo) -> datetime | None:
    """ISO strings with or without offset (naive = `zone`), Java '…[Zone]' suffixes, epoch millis."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        ts = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(zone)
    s = str(value).split("[", 1)[0].strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zone)
    return dt.replace(microsecond=0)


def _pick(entry: dict, *names):
    lowered = {k.lower(): v for k, v in entry.items()}
    for name in names:
        if "." in name:
            outer, inner = name.split(".", 1)
            sub = lowered.get(outer.lower())
            if isinstance(sub, dict) and (found := _pick(sub, inner)) is not None:
                return found
        elif lowered.get(name.lower()) is not None:
            return lowered[name.lower()]
    return None


def _entries(payload) -> list[dict]:
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    if isinstance(payload, dict):
        for key in payload:
            if key.lower() in ("checkins", "data", "items", "content", "results", "visits"):
                return _entries(payload[key])
    raise ValueError(f"unexpected response shape: {type(payload).__name__} {list(payload)[:8] if isinstance(payload, dict) else ''}")


def parse_visits(payload, zone: ZoneInfo) -> list[Visit]:
    visits = []
    for e in _entries(payload):
        tz = _pick(e, "timezone", "timeZone")
        try:
            ez = ZoneInfo(tz) if isinstance(tz, str) and tz else zone
        except (KeyError, ValueError):
            ez = zone
        checkin = parse_time(_pick(e, "checkInDate", "checkinTime", "checkInTime", "checkin", "startTime", "start"), ez)
        if checkin is None:
            continue
        checkout = parse_time(_pick(e, "checkOutDate", "checkoutTime", "checkOutTime", "checkout", "endTime", "end"), ez)
        studio = _pick(e, "gymLocationName", "studioName", "clubName", "studio.name", "location.name")
        visits.append(Visit(checkin.astimezone(zone), checkout.astimezone(zone) if checkout else None,
                            studio if isinstance(studio, str) else None))
    return visits


# --- client ----------------------------------------------------------------------------

def month_window(year: int, month: int) -> tuple[str, str]:
    last = monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01T00:00:00", f"{year:04d}-{month:02d}-{last:02d}T23:59:59"


def previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


class Netpulse:
    """One session against Netpulse. Renews the JSESSIONID by logging in when it's refused."""

    def __init__(self, cfg: NetpulseConfig, zone: ZoneInfo, username: str = "", password: str = "",
                 on_change=None):
        self.cfg, self.zone = cfg, zone
        self.username, self.password = username, password
        self.on_change = on_change or (lambda cfg: None)
        self.client = httpx.AsyncClient(timeout=30, follow_redirects=False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.client.aclose()

    @property
    def can_login(self) -> bool:
        return bool(self.password and (self.username or self.cfg.login))

    def _remember_cookie(self, resp: httpx.Response) -> None:
        self.client.cookies.clear()  # the session cookie is managed by hand, never by httpx's jar
        for raw in resp.headers.get_list("set-cookie"):
            if (m := JSESSION_RE.search(raw)) and m.group(1) != self.cfg.cookie:
                self.cfg.cookie = m.group(1)
                self.on_change(self.cfg)

    async def login(self) -> None:
        if not self.can_login:
            raise AuthExpired("session expired and no login configured (FF_USERNAME / FF_PASSWORD in .env)")
        if t := self.cfg.login:  # captured override (gym import-login)
            ctype = next((v for k, v in t["headers"].items() if k.lower() == "content-type"), "")
            body = _fill(t["body"], self.username, self.password, ctype.lower())
            resp = await self.client.request(t["method"], t["url"], headers=clean_headers(t["headers"]), content=body)
        else:
            resp = await self.client.post(
                f"{self.cfg.base}/np/exerciser/login",
                headers={**clean_headers(self.cfg.headers), "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
                data={"password": self.password, "username": self.username},
            )
        if resp.status_code in (400, 401, 403):
            raise LoginRejected(f"Fitness First rejected the login (HTTP {resp.status_code}): check FF_USERNAME / FF_PASSWORD")
        if resp.status_code >= 400:
            raise LoginFailed(f"login answered HTTP {resp.status_code}")
        before = self.cfg.cookie
        self._remember_cookie(resp)
        if self.cfg.cookie == before:
            raise LoginFailed("login answered without a new session cookie")
        try:
            data = resp.json()
            new_id = _pick(data, "uuid", "exerciserUuid", "exerciserId") if isinstance(data, dict) else None
            if isinstance(new_id, str) and new_id and new_id != self.cfg.exerciser_id:
                self.cfg.exerciser_id = new_id
                self.on_change(self.cfg)
        except ValueError:
            pass

    async def history(self, start: str, end: str) -> list[Visit]:
        if not self.cfg.exerciser_id or not self.cfg.cookie:
            await self.login()
        for attempt in (1, 2):
            url = f"{self.cfg.base}/np/exercisers/{self.cfg.exerciser_id}/check-ins/history"
            headers = clean_headers(self.cfg.headers)
            if self.cfg.cookie:
                headers["Cookie"] = f"JSESSIONID={self.cfg.cookie}"
            resp = await self.client.get(url, params={"startDate": start, "endDate": end}, headers=headers)
            self._remember_cookie(resp)
            if resp.status_code in (401, 403) and attempt == 1:
                await self.login()
                continue
            if resp.status_code in (401, 403):
                raise AuthExpired(f"Netpulse answered {resp.status_code} even after logging in")
            resp.raise_for_status()
            return parse_visits(resp.json(), self.zone)
        raise AssertionError("unreachable")

    async def recent(self, now: datetime) -> list[Visit]:
        """This month and last month (catches late-synced check-ins around the month change)."""
        y, m = now.year, now.month
        py, pm = previous_month(y, m)
        visits = await self.history(*month_window(py, pm))
        await asyncio.sleep(random.uniform(1, 3))
        return visits + await self.history(*month_window(y, m))

    async def backfill(self, now: datetime, floor_year: int, stop_after_empty: int, progress=None) -> list[Visit]:
        """Walk back month by month until `stop_after_empty` empty months in a row (or `floor_year`)."""
        y, m = now.year, now.month
        visits, empty = [], 0
        while y >= floor_year and empty < stop_after_empty:
            got = await self.history(*month_window(y, m))
            visits += got
            empty = 0 if got else empty + 1
            if progress:
                progress(y, m, len(got))
            y, m = previous_month(y, m)
            await asyncio.sleep(random.uniform(1.5, 4))
        return visits
