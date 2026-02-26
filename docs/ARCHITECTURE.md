# Architecture Plan
## Erbil USD/IQD Market Rate Backend

| Field                | Value                                      |
|----------------------|--------------------------------------------|
| **Document Version** | 1.0 — Draft                                |
| **Date**             | 2026-02-26                                 |
| **Status**           | ⏳ Awaiting Client Decisions               |
| **Depends On**       | SRS v2.0 Final                             |

---

## Table of Contents

1. [Architecture Decisions — Questions for Client](#1-architecture-decisions--questions-for-client)
2. [Project Structure](#2-project-structure)
3. [Module Specifications](#3-module-specifications)
4. [Data Flow & Sequence Diagrams](#4-data-flow--sequence-diagrams)
5. [Database Architecture](#5-database-architecture)
6. [Parser Engine Architecture](#6-parser-engine-architecture)
7. [API Architecture](#7-api-architecture)
8. [Background Scheduler Architecture](#8-background-scheduler-architecture)
9. [Configuration Architecture](#9-configuration-architecture)
10. [Error Handling Architecture](#10-error-handling-architecture)
11. [Implementation Order](#11-implementation-order)

---

## 1. Architecture Decisions — Questions for Client

> ⚠️ **The following decisions need your input before I finalize the architecture.
> Each question has my recommendation marked with ⭐.**

---

### ❓ Q1: First-Time Telethon Authentication

Telethon requires a **one-time interactive session** the first time it runs. Telegram will send an OTP code to your phone, and you must type it into the terminal. After that, a `.session` file is created and reused automatically.

**How should we handle this?**

| Option | Description |
|--------|-------------|
| **A ⭐** | Create a separate `scripts/auth.py` script you run once manually: `python scripts/auth.py`. It authenticates, creates the `.session` file, and exits. The main app then reuses that session file silently. |
| **B** | Handle it inside the main app on first startup — the app will pause and ask for the OTP in the terminal. |

**My recommendation: Option A** — cleaner separation. The main app never blocks for user input.

---

### ❓ Q2: First Run — Backfill Historical Data?

When the app starts for the very first time, the database is empty. Should it:

| Option | Description |
|--------|-------------|
| **A ⭐** | Fetch the **last 50 messages** from the channel on first run, parse all valid ones, and backfill the database with historical rates. This gives you data immediately. |
| **B** | Start fresh — only process messages that arrive **after** the app starts. First valid rate may take up to 5 minutes (or longer if the channel hasn't posted recently). |

**My recommendation: Option A** — you get a populated database instantly.

---

### ❓ Q3: Timezone for Timestamps

The channel operates in **Iraq time (UTC+3)**. What timezone should the `created_at` field use?

| Option | Description |
|--------|-------------|
| **A ⭐** | Store as **UTC** in the database, return as **UTC** (`Z` suffix) in API responses. This is the industry standard and avoids DST issues. |
| **B** | Store and return as **Iraq time (UTC+3)**. Easier to read directly but non-standard. |

**My recommendation: Option A** — UTC is the international standard for APIs.

---

### ❓ Q4: Health Check Endpoint

Should the API include a health check endpoint?

| Option | Description |
|--------|-------------|
| **A ⭐** | Add `GET /api/health` returning `{"status": "ok", "last_fetch": "...", "rates_count": N}`. Useful for monitoring and deployment platforms. |
| **B** | No health check — only the 3 endpoints defined in the SRS. |

**My recommendation: Option A** — very useful for deployment platforms (Railway, Render, etc.) and debugging.

---

### ❓ Q5: Historical Rates Endpoint

The SRS mentions storing historical data for analytics, but Phase 1 only defines a "latest rate" endpoint. Should we add a basic history endpoint now?

| Option | Description |
|--------|-------------|
| **A ⭐** | Add `GET /api/rate/history?days=7` returning the last N days of rates. Minimal effort since the data is already stored. |
| **B** | Skip it — Phase 1 is latest + conversions only. Add history in Phase 2. |

**My recommendation: Option A** — the data is there, exposing it costs almost nothing.

---

### ❓ Q6: Who Consumes the API?

This affects CORS (Cross-Origin Resource Sharing) configuration:

| Option | Description |
|--------|-------------|
| **A** | Only **server-to-server** calls (other backends, scripts, Postman). No CORS needed. |
| **B ⭐** | Potentially a **frontend web app** in the future (Phase 2). Enable CORS with `allow_origins=["*"]` now to be ready. |
| **C** | A specific domain only. Enable CORS for that domain. |

**My recommendation: Option B** — enable open CORS now, tighten later if needed.

---

### ❓ Q7: Rate Caching

The latest rate could be cached in memory to avoid hitting SQLite on every API call:

| Option | Description |
|--------|-------------|
| **A ⭐** | Cache the latest rate in memory. Update it when a new rate is stored. API reads from memory (instant), not disk. |
| **B** | Always query SQLite. Still fast for SQLite, but slightly slower. |

**My recommendation: Option A** — negligible complexity, noticeable performance gain.

---

## 2. Project Structure

```
usd/
│
├── app/
│   ├── __init__.py                # Package marker
│   ├── main.py                    # FastAPI app creation, lifespan, startup/shutdown
│   ├── config.py                  # Settings class (loads .env), all constants
│   ├── database.py                # SQLite: schema init, insert, query functions
│   ├── models.py                  # Pydantic models for API responses
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py             # All API route handlers
│   │
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── fetcher.py            # Telethon client wrapper, message fetching
│   │   └── parser.py             # Multi-layer parser engine
│   │
│   └── scheduler/
│       ├── __init__.py
│       └── jobs.py               # Background task: fetch → parse → store loop
│
├── scripts/
│   └── auth.py                   # One-time Telethon session authentication
│
├── data/                          # SQLite DB lives here (gitignored)
│   └── .gitkeep
│
├── docs/
│   ├── SRS.md                    # Requirements specification
│   └── ARCHITECTURE.md           # This document
│
├── .env                          # Credentials (gitignored)
├── .env.example                  # Credential template
├── .gitignore
├── requirements.txt              # Python dependencies
└── README.md                     # Project overview & setup guide
```

**Total files: 18** — lean, focused, no over-engineering.

---

## 3. Module Specifications

### 3.1 `app/config.py` — Configuration & Constants

**Responsibility:** Single source of truth for all configurable values.

```
class Settings:
    # From .env
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_PHONE: str
    TELEGRAM_CHANNEL: str

    # Constants
    FETCH_INTERVAL_SECONDS: int = 300          # 5 minutes
    DB_PATH: str = "data/rates.db"
    SESSION_NAME: str = "erbil_rate_session"

    # Parser Keywords (easy to update)
    CITY_KEYWORDS: list = ["هەولێر"]
    PENZI_KEYWORDS: list = ["پێنجی"]
    SUR_KEYWORDS: list = ["سوور"]
    EXCLUDE_KEYWORDS: list = ["ذهب", "زێر", "الذهب"]

    # Validation
    MIN_VALID_PRICE: int = 100_000
    MAX_VALID_PRICE: int = 200_000
    MAX_ANOMALY_DEVIATION: int = 10_000

    # Backfill
    INITIAL_FETCH_COUNT: int = 50
```

**Design Rationale:**
- All keywords in one place → if the channel changes terminology, update ONE file.
- Validation ranges are constants → easy to adjust without touching parser logic.

---

### 3.2 `app/database.py` — Database Layer

**Responsibility:** All SQLite interactions. No SQL leaks into other modules.

```
Functions:
├── init_db()                    # Create tables + indexes if not exist
├── insert_rate(penzi, sur, avg, msg_id)   # INSERT new rate record
├── get_latest_rate()            # SELECT most recent record
├── get_last_message_id()        # For fetch deduplication
├── get_rate_history(days)       # SELECT records within last N days
└── get_rates_count()            # COUNT for health check
```

**Connection Strategy:**
- Use `aiosqlite` for async compatibility with FastAPI.
- Single connection with WAL (Write-Ahead Logging) mode for concurrent reads.
- Connection opened at app startup, closed at shutdown (via FastAPI lifespan).

**Schema initialization** runs on every startup — `CREATE TABLE IF NOT EXISTS` is idempotent.

---

### 3.3 `app/models.py` — Pydantic Response Models

**Responsibility:** Type-safe API response serialization.

```
Models:
├── RateResponse                 # city, penzi, sur, average, last_updated
├── UsdToIqdResponse             # usd, iqd, rate_per_100
├── IqdToUsdResponse             # iqd, usd, rate_per_100
├── HistoryResponse              # list of RateResponse records
├── HealthResponse               # status, last_fetch, rates_count
└── ErrorResponse                # error message string
```

---

### 3.4 `app/api/routes.py` — API Route Handlers

**Responsibility:** Thin handlers that validate input and delegate to database.

```
Routes:
├── GET /api/rate/latest         → get_latest_rate() → RateResponse
├── GET /api/convert/usd-to-iqd  → get_latest_rate() → calculate → UsdToIqdResponse
├── GET /api/convert/iqd-to-usd  → get_latest_rate() → calculate → IqdToUsdResponse
├── GET /api/rate/history        → get_rate_history() → HistoryResponse
└── GET /api/health              → get system status → HealthResponse
```

**Design Principle:** Routes contain **zero** business logic. They:
1. Validate query parameters
2. Call database functions
3. Apply formulas (for conversions)
4. Return Pydantic models

---

### 3.5 `app/telegram/fetcher.py` — Telegram Client

**Responsibility:** Manages Telethon connection and raw message fetching.

```
Class: TelegramFetcher
├── __init__(settings)           # Store config
├── connect()                    # Start Telethon client, load session
├── disconnect()                 # Graceful shutdown
├── fetch_new_messages()         # Get messages after last processed ID
│   └── Returns: list[Message]   # Raw Telethon message objects
└── fetch_initial_messages(n)    # For backfill: get last N messages
```

**Key Design Decisions:**
- The fetcher does NOT parse — it only fetches raw data.
- Session file = `{SESSION_NAME}.session` stored in project root (gitignored).
- Uses `client.get_messages()` with `min_id` parameter for incremental fetching.

---

### 3.6 `app/telegram/parser.py` — Parser Engine

**Responsibility:** The brain of the system. Filters, extracts, validates.

```
Class: MessageParser
├── __init__(settings)           # Load keywords and thresholds
├── parse_message(text)          # Full pipeline: filter → extract → validate
│   └── Returns: ParseResult | None
├── _is_excluded(text)           # Check for gold/official keywords
├── _extract_erbil_prices(text)  # Line-by-line extraction
│   ├── _try_primary_regex(line) # Layer 1: exact format match
│   └── _try_relaxed_regex(line) # Layer 2: flexible number extraction
├── _validate_price(price)       # Range check: 100k-200k
└── _check_anomaly(avg, prev)    # Deviation check: ±10k

Data class: ParseResult
├── penzi_price: int
├── sur_price: int
├── average_price: int
└── message_id: str
```

**Parser Pipeline (per message):**

```
Input: raw message text
  │
  ▼
Step 1: EXCLUDE CHECK
  Is the message about gold? (ذهب, زێر, الذهب)
  → YES: return None (skip entire message)
  → NO: continue
  │
  ▼
Step 2: SPLIT INTO LINES
  Split message by newlines
  │
  ▼
Step 3: LINE-BY-LINE SCAN
  For each line:
  │
  ├─ Does line contain هەولێر? → NO: skip line
  │
  ├─ Does line contain پێنجی or سوور? → NO: skip line
  │
  ├─ Try Layer 1 regex: \$?100\$?[=\s]*([0-9,]+)
  │   → Match? Extract number, strip commas, convert to int
  │   → No match? Try Layer 2 regex: any 6-digit number
  │
  ├─ Validate: 100,000 ≤ price ≤ 200,000?
  │   → NO: skip line
  │
  └─ Categorize: پێنجی → penzi_price, سوور → sur_price
  │
  ▼
Step 4: COMPLETENESS CHECK
  Do we have exactly 1 penzi + 1 sur?
  → NO: return None (skip message)
  → YES: continue
  │
  ▼
Step 5: COMPUTE AVERAGE
  average = round((penzi + sur) / 2)
  │
  ▼
Step 6: ANOMALY CHECK
  |average - last_stored_average| ≤ 10,000?
  → NO: log warning, return None (skip)
  → YES: return ParseResult
```

---

### 3.7 `app/scheduler/jobs.py` — Background Job

**Responsibility:** Orchestrates the fetch → parse → store pipeline.

```
Function: run_fetch_cycle(fetcher, parser, db)
  │
  ├── 1. Call fetcher.fetch_new_messages()
  ├── 2. Sort messages by date (most recent first)
  ├── 3. For each message:
  │      ├── Call parser.parse_message(text)
  │      ├── If valid result:
  │      │     ├── Call db.insert_rate(result)
  │      │     ├── Update in-memory cache
  │      │     └── BREAK (use only most recent valid message)
  │      └── If None: continue to next message
  ├── 4. Update last processed message ID
  └── 5. Log cycle summary

Function: start_scheduler(fetcher, parser, db)
  │
  └── Infinite async loop:
        ├── await run_fetch_cycle(...)
        ├── Log next run time
        └── await asyncio.sleep(300)
```

---

### 3.8 `app/main.py` — Application Entry Point

**Responsibility:** Wires everything together.

```
Lifespan:
├── STARTUP:
│   ├── Load Settings from .env
│   ├── Init database (create tables)
│   ├── Connect Telethon client
│   ├── If first run: backfill from last 50 messages
│   ├── Load latest rate into memory cache
│   └── Start background scheduler task
│
├── RUNNING:
│   └── FastAPI serves requests + scheduler runs in background
│
└── SHUTDOWN:
    ├── Cancel scheduler task
    ├── Disconnect Telethon client
    └── Close database connection
```

---

## 4. Data Flow & Sequence Diagrams

### 4.1 Normal Fetch Cycle (Every 5 Minutes)

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Scheduler│     │ Fetcher  │     │ Parser   │     │ Database │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │  fetch_new()   │                │                │
     │───────────────►│                │                │
     │                │──── Telethon ──►│ @dolaraka12   │
     │                │◄── messages ────│               │
     │  [messages]    │                │                │
     │◄───────────────│                │                │
     │                │                │                │
     │  parse(msg)    │                │                │
     │────────────────────────────────►│                │
     │                │                │── filter       │
     │                │                │── extract      │
     │                │                │── validate     │
     │  ParseResult   │                │                │
     │◄────────────────────────────────│                │
     │                │                │                │
     │  insert_rate(result)            │                │
     │─────────────────────────────────────────────────►│
     │                │                │    INSERT      │
     │  OK            │                │                │
     │◄─────────────────────────────────────────────────│
     │                │                │                │
     │  sleep(300s)   │                │                │
     │──────┐         │                │                │
     │      │         │                │                │
     │◄─────┘         │                │                │
```

### 4.2 API Request Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │ Routes   │     │ Database │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     │ GET /api/rate  │                │
     │  /latest       │                │
     │───────────────►│                │
     │                │ get_latest()   │
     │                │───────────────►│
     │                │  Rate record   │
     │                │◄───────────────│
     │  200 OK        │                │
     │  {json body}   │                │
     │◄───────────────│                │
```

---

## 5. Database Architecture

### 5.1 Schema

```sql
CREATE TABLE IF NOT EXISTS exchange_rates (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    erbil_penzi       INTEGER NOT NULL,
    erbil_sur         INTEGER NOT NULL,
    erbil_average     INTEGER NOT NULL,
    source_message_id TEXT    NOT NULL UNIQUE,
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_created_at
    ON exchange_rates(created_at DESC);
```

### 5.2 Query Patterns

| Query                    | SQL                                                            | Frequency     |
|--------------------------|----------------------------------------------------------------|---------------|
| Get latest rate          | `SELECT * FROM exchange_rates ORDER BY created_at DESC LIMIT 1`| Per API call  |
| Insert new rate          | `INSERT INTO exchange_rates (penzi, sur, avg, msg_id) VALUES (?,?,?,?)` | Per valid parse |
| Get last message ID      | `SELECT source_message_id FROM exchange_rates ORDER BY id DESC LIMIT 1` | Per fetch cycle |
| Get history (N days)     | `SELECT * FROM exchange_rates WHERE created_at >= datetime('now', '-N days') ORDER BY created_at DESC` | On demand |
| Count records            | `SELECT COUNT(*) FROM exchange_rates`                          | Health check  |

### 5.3 SQLite Configuration

```
PRAGMA journal_mode = WAL;          -- Allows concurrent reads during writes
PRAGMA busy_timeout = 5000;         -- Wait 5s if DB is locked
PRAGMA foreign_keys = ON;           -- Enforce constraints
```

---

## 6. Parser Engine Architecture

### 6.1 Regex Patterns

**Layer 1 — Primary (matches observed format exactly):**

```
Pattern: \*?\$?100\$?\s*=\s*([0-9]{1,3}(?:,[0-9]{3})*)\s+هەولێر\s+(پێنجی|سوور)\*?
```

Breakdown:
| Part | Matches | Example |
|------|---------|---------|
| `\*?` | Optional bold marker | `*` |
| `\$?100\$?` | `$100` or `100$` or `100` | `$100` |
| `\s*=\s*` | Equals sign with optional spaces | `=` |
| `([0-9]{1,3}(?:,[0-9]{3})*)` | Price with optional commas | `153,300` |
| `\s+هەولێر\s+` | Erbil city keyword | `هەولێر` |
| `(پێنجی\|سوور)` | Rate type | `پێنجی` |
| `\*?` | Optional closing bold marker | `*` |

**Layer 2 — Relaxed (fallback if format changes):**

```
Pattern: ([1][0-9]{2}[,.]?[0-9]{3})
```

Applied only to lines that contain BOTH `هەولێر` AND (`پێنجی` or `سوور`).
Extracts any number between 100,000–199,999.

### 6.2 Price Normalization

```
Raw input     → Normalized
"153,300"     → 153300
"153.300"     → 153300
"153300"      → 153300
"153 300"     → 153300
```

---

## 7. API Architecture

### 7.1 Route Definitions

```python
# Router prefix: /api

GET  /api/rate/latest              → latest_rate()
GET  /api/convert/usd-to-iqd      → convert_usd_to_iqd(amount: float)
GET  /api/convert/iqd-to-usd      → convert_iqd_to_usd(amount: float)
GET  /api/rate/history             → rate_history(days: int = 7)
GET  /api/health                   → health_check()
```

### 7.2 Response Structure

All responses follow a consistent JSON structure:

**Success responses** return the data directly:
```json
{
  "city": "Erbil",
  "penzi": 153300,
  ...
}
```

**Error responses** use a standard format:
```json
{
  "error": "Descriptive error message.",
  "code": "NO_DATA"
}
```

### 7.3 HTTP Status Codes

| Status | When Used |
|--------|-----------|
| `200 OK` | Successful request with data. |
| `400 Bad Request` | Missing or invalid query parameter (`amount`). |
| `503 Service Unavailable` | No rate data stored yet (DB is empty). |

### 7.4 CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Open for Phase 1
    allow_methods=["GET"],     # Read-only API
    allow_headers=["*"],
)
```

---

## 8. Background Scheduler Architecture

### 8.1 Lifecycle

```
App Startup
    │
    ├── First run? (no data in DB)
    │     ├── YES: Backfill last 50 messages
    │     └── NO: Continue normally
    │
    └── Start asyncio.create_task(scheduler_loop)
            │
            └── Loop forever:
                  ├── try:
                  │     ├── fetch_new_messages()
                  │     ├── parse and validate
                  │     ├── store if valid
                  │     └── update cache
                  ├── except Exception:
                  │     └── log error (never crash)
                  └── await asyncio.sleep(300)
```

### 8.2 Concurrency Model

```
┌──────────────────────────────────────────┐
│              asyncio Event Loop          │
│                                          │
│   ┌────────────────┐  ┌──────────────┐   │
│   │ FastAPI Server │  │  Scheduler   │   │
│   │ (handles HTTP) │  │  (5-min loop)│   │
│   └────────────────┘  └──────────────┘   │
│         ▲                    ▲            │
│         │                    │            │
│         └── shared ──────────┘            │
│              DB connection                │
│              Memory cache                 │
└──────────────────────────────────────────┘
```

Both the API and the scheduler run in the **same asyncio event loop** inside one process. This means:
- No inter-process communication needed.
- Shared in-memory cache is trivial (just a Python variable).
- `aiosqlite` handles async DB access without blocking the event loop.

---

## 9. Configuration Architecture

### 9.1 Environment Variables (`.env`)

```
TELEGRAM_API_ID=39340358
TELEGRAM_API_HASH=6c12ddaade336dbfbb261a7816cd6dc6
TELEGRAM_PHONE=+9647518798141
TELEGRAM_CHANNEL=@dolaraka12
```

### 9.2 Application Constants (`config.py`)

All magic numbers and keywords live here. **Nothing is hard-coded elsewhere.**

| Constant                  | Default   | Purpose                               |
|---------------------------|-----------|---------------------------------------|
| `FETCH_INTERVAL_SECONDS`  | `300`     | How often to check Telegram (5 min).  |
| `DB_PATH`                 | `data/rates.db` | SQLite file location.            |
| `SESSION_NAME`            | `erbil_rate_session` | Telethon session file name.  |
| `CITY_KEYWORDS`           | `["هەولێر"]` | Erbil identifiers.               |
| `PENZI_KEYWORDS`          | `["پێنجی"]` | Penzi type identifiers.           |
| `SUR_KEYWORDS`            | `["سوور"]` | Sur type identifiers.              |
| `EXCLUDE_KEYWORDS`        | `["ذهب", "زێر", "الذهب"]` | Gold exclusion terms. |
| `MIN_VALID_PRICE`         | `100,000` | Minimum valid IQD rate.               |
| `MAX_VALID_PRICE`         | `200,000` | Maximum valid IQD rate.               |
| `MAX_ANOMALY_DEVIATION`   | `10,000`  | Max allowed deviation from last rate. |
| `INITIAL_FETCH_COUNT`     | `50`      | Messages to fetch on first run.       |

---

## 10. Error Handling Architecture

### 10.1 Error Categories & Handling

```
┌─────────────────────────────────────────────────────────┐
│                    Error Hierarchy                       │
│                                                         │
│  CRITICAL (needs manual intervention)                   │
│  ├── Telethon session expired                           │
│  └── Database file corrupted                            │
│                                                         │
│  RECOVERABLE (auto-retry next cycle)                    │
│  ├── Telegram API timeout                               │
│  ├── Network unreachable                                │
│  ├── Database write lock                                │
│  └── Rate limited by Telegram                           │
│                                                         │
│  EXPECTED (log and continue)                            │
│  ├── No new messages in channel                         │
│  ├── Message failed parsing (invalid format)            │
│  ├── Message failed validation (out of range)           │
│  ├── Anomaly detected (±10k deviation)                  │
│  └── Duplicate message ID (already stored)              │
└─────────────────────────────────────────────────────────┘
```

### 10.2 Logging Format

```
[2026-02-26 14:05:00] [INFO]  Fetch cycle started
[2026-02-26 14:05:01] [INFO]  Fetched 3 new messages
[2026-02-26 14:05:01] [INFO]  Message 12345: Excluded (contains "ذهب")
[2026-02-26 14:05:01] [INFO]  Message 12346: Parsed OK → penzi=153300, sur=153200, avg=153250
[2026-02-26 14:05:01] [INFO]  Stored rate: avg=153250 (message 12346)
[2026-02-26 14:05:01] [INFO]  Fetch cycle complete. Next run at 14:10:00
```

```
[2026-02-26 14:10:00] [WARNING] Message 12350: Anomaly detected. avg=180000, prev=153250, diff=26750
[2026-02-26 14:10:00] [WARNING] Raw message: "*$100=180,000 هەولێر پێنجی* ..."
```

```
[2026-02-26 14:15:00] [ERROR]  Telegram fetch failed: ConnectionError. Will retry in 300s.
```

---

## 11. Implementation Order

Development proceeds in 6 phases, each building on the previous:

### Phase A: Foundation (config + database)
```
1. app/config.py          — Settings class, load .env, define constants
2. app/database.py        — Schema creation, insert, query functions
3. app/models.py          — Pydantic response models
```
**Testable:** Can create DB, insert dummy data, query it.

### Phase B: Parser Engine
```
4. app/telegram/parser.py — Multi-layer parser with all regex patterns
```
**Testable:** Feed sample messages, verify extraction results.

### Phase C: Telegram Fetcher
```
5. scripts/auth.py        — One-time authentication script
6. app/telegram/fetcher.py — Telethon client wrapper
```
**Testable:** Authenticate, fetch real messages from @dolaraka12.

### Phase D: API Layer
```
7. app/api/routes.py      — All 5 endpoints
8. app/main.py            — FastAPI app (without scheduler for now)
```
**Testable:** Start server, hit endpoints with Postman/browser.

### Phase E: Scheduler Integration
```
9. app/scheduler/jobs.py  — Background loop
10. Update app/main.py    — Wire scheduler into lifespan
```
**Testable:** Full system running end-to-end.

### Phase F: Polish
```
11. requirements.txt      — Lock dependencies
12. README.md             — Setup guide, API docs
```

---

### Dependency Graph

```
                config.py
               /    |    \
              /     |     \
        database  models  parser.py
            |       |        |
            └───┬───┘        │
                │             │
           routes.py     fetcher.py
                │             │
                └──────┬──────┘
                       │
                    jobs.py
                       │
                    main.py
```

---

*End of Architecture Plan — Awaiting client decisions on Q1–Q7*
