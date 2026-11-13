# Gym Wall of Shame 💪

I kept skipping leg day, so every check-in at my gym is now public: days since the last visit, weekly goal and streaks, a year-long gym calendar, when I go and how long I stay.

Live at **https://gym.amir.rocks**.

## How it works

```
Fitness First app backend ──(5 syncs a day)──▶ FastAPI + SQLite ──▶ Svelte 5 dashboard
```

- **backend/**: FastAPI (Python 3.14, uv). It syncs check-ins on a jittered schedule into SQLite and serves `/api/dashboard` plus the built frontend. CLI: `gym`.
- **frontend/**: Svelte 5 + Vite 8 with hand-rolled SVG charts and self-hosted fonts. All stats are computed in the browser.
- **One container**: the multi-stage `Dockerfile` builds the frontend with Node and runs it with Python. No published port in production; Traefik routes to it.

## Connecting Fitness First

The Fitness First app runs on Netpulse (EGYM). There is no public API; the service talks to the same endpoints as the iOS app (found with Proxyman):

```
POST https://fitnessfirst.netpulse.com/np/exerciser/login            username=…&password=…  -> uuid + JSESSIONID (3 h)
GET  https://fitnessfirst.netpulse.com/np/exercisers/<uuid>/check-ins/history?startDate=…&endDate=…
```

The history returns check-in times and the studio only. There are no check-outs, so the dashboard shows durations only for older data that has them.

Setup:

1. Put `FF_USERNAME` (your Fitness First e-mail) and `FF_PASSWORD` into `.env`, then recreate the container (`docker compose up -d --force-recreate`).
2. Check the login (optional):
   ```bash
   docker compose exec web gym login
   ```
3. That's it. The first sync walks back month by month through your whole history. After that it fetches the current and last month five times a day, logging in again whenever the 3-hour session has run out. If Fitness First rejects the password, it stops trying (so the account doesn't get locked) until the container is recreated.

`gym status` shows the state. Fallbacks, in case the app changes: `gym import-curl < curl.txt` (a captured check-ins request) and `gym import-login < login.txt` (a captured login with the password replaced by `{{PASSWORD}}`). Old v1 data: `gym import-csv < checkins.csv`.

## Running it

```bash
cp .env.example .env                                       # optional settings
docker compose -f docker-compose.local.yml up --build      # http://localhost:8000
```

Production (`docker-compose.yml`) expects an external `traefik-public` network and a Traefik instance in front of it.

Development:

```bash
cd backend && uv sync && DATA_DIR=./data uv run gym seed-demo && DATA_DIR=./data SYNC_ENABLED=false uv run uvicorn app.main:app --reload
cd frontend && npm install && npm run dev                  # proxies /api to :8000
cd backend && uv run pytest
```

### Settings (`.env`)

| Variable | Default | |
|---|---|---|
| `DOMAIN` | `gym.amir.rocks` | Host rule for Traefik |
| `WEEKLY_GOAL` | `3` | Visits per week |
| `SHOW_LIVE` | `false` | Show "in the gym right now" while checked in |
| `SHOW_STUDIOS` | `false` | Show studio names |
| `SYNC_PER_DAY` | `5` | Syncs per day, spread evenly from `SYNC_FIRST_HOUR` (`8`) to `SYNC_LAST_HOUR` (`22`), each ±`SYNC_JITTER_MINUTES` (`20`) |
| `DATA_START` | empty | Hide check-ins before this date (`YYYY-MM-DD`), e.g. stray ones from before the app counted reliably |
| `TZ` | `Europe/Berlin` | |

## License

GPL-2.0. See `LICENSE`.
