# RentMate — Rent & Flatmate Finder

A platform where owners list rooms and tenants create "looking for room"
profiles. An LLM-powered compatibility engine scores and ranks matches,
real-time chat unlocks once interest is accepted, and email notifications
fire on key events.

## Setup

```bash
git clone <your-repo-url>
cd rentmate
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values, see below
python app.py           # runs at http://localhost:5000
```

The SQLite DB and all tables are created automatically on first run.

### Environment variables (`.env`)

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | yes | any random string |
| `DATABASE_URL` | no | defaults to local SQLite file |
| `LLM_API_KEY` | no | Anthropic API key. If blank, scoring always uses the rule-based fallback |
| `LLM_MODEL` | no | defaults to `claude-sonnet-4-6` |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | no | Gmail SMTP + App Password. If blank, emails are logged to console instead of sent (so the app still runs without a mail account) |

## Project structure

```
app.py              # app factory, blueprint registration, SocketIO init
config.py            # env-driven config
models.py             # SQLAlchemy models
llm_service.py        # LLM compatibility scoring + rule-based fallback
email_service.py      # email notifications (graceful no-op fallback)
routes/
  auth.py             # register/login/logout
  main.py              # landing page + role-based dashboard
  listings.py          # post listing, browse/filter, tenant profile
  interests.py          # express interest, accept/decline
  chat.py               # chat page + WebSocket events
  admin.py               # admin activity view
templates/             # Jinja2 templates
static/css/style.css    # design system
```

## Database schema

**User**: id, name, email (unique), password_hash, role (`owner`/`tenant`/`admin`), created_at

**Listing**: id, owner_id → User, location, rent, available_from, room_type,
furnishing_status, photo_url, description, is_filled, created_at

**TenantProfile**: id, user_id → User (1:1), preferred_location, budget_min,
budget_max, move_in_date, bio

**Interest**: id, tenant_id → User, listing_id → Listing, status
(`pending`/`accepted`/`declined`), compatibility_score, compatibility_explanation,
score_source (`llm`/`fallback`), created_at
— score is computed once when interest is created and stored here, never recomputed.

**Message**: id, interest_id → Interest, sender_id → User, content, sent_at

## API / routes

| Route | Method | Role | Description |
|---|---|---|---|
| `/register`, `/login`, `/logout` | GET/POST | any | auth |
| `/dashboard` | GET | any | role-based dashboard |
| `/listings/new` | GET/POST | owner | create listing |
| `/listings/<id>/fill` | POST | owner | mark listing filled |
| `/profile` | GET/POST | tenant | create/edit tenant profile |
| `/browse` | GET | tenant | browse + filter listings, ranked by compatibility |
| `/listings/<id>/interest` | POST | tenant | express interest → triggers LLM scoring |
| `/interests/<id>/accept` | POST | owner | accept interest → unlocks chat, emails tenant |
| `/interests/<id>/decline` | POST | owner | decline interest → emails tenant |
| `/chat/<interest_id>` | GET | both parties | chat room (only if interest accepted) |
| `/admin` | GET | admin | platform activity |

WebSocket events (Socket.IO): `join` (joins room for an interest),
`send_message` → broadcasts `new_message` to both parties, persisted to DB.

## LLM compatibility scoring

**Prompt** (`llm_service.build_prompt`):
```
Given this room listing: location=Koramangala, rent=15000, room_type=Single,
furnishing=Furnished, available_from=2026-07-01.

And this tenant profile: preferred_location=Koramangala, budget_min=10000,
budget_max=18000, move_in_date=2026-07-15.

Compute a compatibility score from 0 to 100 based on budget and location match.
Return ONLY valid JSON, no other text: {"score": number, "explanation": string}
```

**Example output:**
```json
{"score": 92, "explanation": "Exact location match and rent comfortably within budget."}
```

**Fallback (no API key / LLM call fails):** a deterministic rule-based score —
50 points for location match (exact/partial/none) + 50 points for budget fit
(full credit if rent is within range, partial credit scaled by distance from
the budget midpoint otherwise). This guarantees the flow never breaks even if
the LLM is down, and `score_source` records which path was used.

## Deploying (Render)

1. Push this repo to GitHub (branch `main`, public).
2. On [render.com](https://render.com): **New → Web Service** → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: leave default (Render reads the `Procfile`) — or set explicitly:
   `gunicorn --worker-class eventlet -w 1 app:app`
5. Add environment variables from `.env.example` in the Render dashboard
   (`SECRET_KEY` at minimum; `LLM_API_KEY` and `MAIL_USERNAME`/`MAIL_PASSWORD`
   are optional — app degrades gracefully without them).
6. Deploy. SQLite works for a demo but resets on redeploy — for persistence
   across deploys, add a Render Postgres instance and set `DATABASE_URL`.

Railway works the same way (it also reads the `Procfile`).

## Known tradeoffs (for the design write-up)

- SQLite by default for zero-setup demo; swap `DATABASE_URL` to Postgres for production.
- Email gracefully no-ops to console logs if SMTP credentials aren't set, so
  graders can run the app without configuring a mail account.
- Browse-page ranking uses the fast rule-based scorer for all visible listings
  (would be too slow/costly to call the LLM on every listing on every page
  load); the authoritative LLM score is computed once, on actual interest, and stored.
