# 💱 Erbil USD/IQD Market Rate API

A self-hosted backend that **automatically** tracks the Erbil USD/IQD exchange rate by monitoring a public Telegram channel, extracting market prices, and exposing them through a clean REST API.

---

## ✨ Features

- 🔄 **Auto-fetching** — Pulls exchange rates from Telegram every 5 minutes
- 🏙️ **Erbil-specific** — Extracts only Erbil Penzi & Sur market rates
- 📊 **Historical data** — Stores all rates in SQLite with full history
- 🔁 **USD ↔ IQD conversion** — Built-in currency converter endpoints
- 🛡️ **Anomaly detection** — Rejects suspicious rate jumps (±10,000 IQD)
- 📝 **Swagger UI** — Auto-generated interactive API docs at `/docs`
- ⚡ **In-memory cache** — Instant API responses without DB queries
- 🧠 **Smart parser** — Multi-layer regex with fallback patterns

---

## 🏗️ Architecture

```
Telegram Channel (@iraqborsa)
        │
        ▼
┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Telegram Fetcher │────▶│  Parser Engine │────▶│  SQLite DB    │
│  (Telethon)       │     │  (Multi-layer) │     │  (aiosqlite)  │
└──────────────────┘     └──────────────┘     └──────┬───────┘
                                                      │
                              ┌────────────────────────┘
                              ▼
                    ┌──────────────────┐
                    │   FastAPI Server   │
                    │   /api/rate/latest │
                    │   /api/convert/... │
                    │   /api/health      │
                    └──────────────────┘
```

---

## 📋 Prerequisites

- **Python 3.11+**
- **Telegram API credentials** from [my.telegram.org](https://my.telegram.org)
- A phone number registered with Telegram

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd usd
pip install -r requirements.txt
```

### 2. Configure

Copy the example and fill in your Telegram credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+964xxxxxxxxxx
TELEGRAM_CHANNEL=@iraqborsa
```

### 3. Authenticate with Telegram (one-time)

```bash
python scripts/auth.py
```

Telegram will send an OTP to your phone — enter it when prompted. This creates a `.session` file that the app reuses silently.

### 4. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On startup, the server will:
1. Initialize the database
2. Connect to Telegram
3. Backfill the last 50 messages (if DB is empty)
4. Start the 5-minute fetch loop
5. Serve the API

Visit **http://localhost:8000/docs** for interactive Swagger UI.

---

## 📡 API Endpoints

### `GET /api/rate/latest`

Returns the most recent Erbil exchange rate.

```json
{
  "city": "Erbil",
  "penzi": 153300,
  "sur": 153250,
  "average": 153275,
  "last_updated": "2026-02-26T03:17:21+03:00"
}
```

### `GET /api/convert/usd-to-iqd?amount=100`

Converts USD to IQD using the latest average rate.

```json
{
  "usd": 100.0,
  "iqd": 153275.0,
  "rate_per_100": 153275
}
```

### `GET /api/convert/iqd-to-usd?amount=1000000`

Converts IQD to USD using the latest average rate.

```json
{
  "iqd": 1000000.0,
  "usd": 652.74,
  "rate_per_100": 153275
}
```

### `GET /api/rate/history?days=7`

Returns historical rates from the last N days (1–365).

```json
{
  "city": "Erbil",
  "count": 35,
  "rates": [
    {
      "city": "Erbil",
      "penzi": 153300,
      "sur": 153250,
      "average": 153275,
      "last_updated": "2026-02-26T03:17:21+03:00"
    }
  ]
}
```

### `GET /api/health`

Returns service status.

```json
{
  "status": "ok",
  "last_fetch": "2026-02-26T03:17:21+03:00",
  "rates_count": 35
}
```

---

## 📁 Project Structure

```
usd/
├── app/
│   ├── __init__.py
│   ├── config.py           # Settings, keywords, thresholds
│   ├── database.py         # Async SQLite layer (aiosqlite)
│   ├── models.py           # Pydantic response models
│   ├── main.py             # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py       # All REST endpoint handlers
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── fetcher.py      # Telethon client wrapper
│   │   └── parser.py       # Multi-layer message parser
│   └── scheduler/
│       ├── __init__.py
│       └── jobs.py          # Background fetch loop
├── scripts/
│   └── auth.py             # One-time Telegram authentication
├── data/
│   └── rates.db            # SQLite database (auto-created)
├── docs/
│   ├── SRS.md              # Software Requirements Spec
│   └── ARCHITECTURE.md     # Architecture Plan
├── .env                    # Telegram credentials (git-ignored)
├── .env.example            # Credential template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔧 Configuration

All settings are in `app/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `FETCH_INTERVAL_SECONDS` | `300` | Fetch cycle interval (5 min) |
| `INITIAL_FETCH_COUNT` | `50` | Messages to backfill on first run |
| `MIN_VALID_PRICE` | `100,000` | Minimum valid IQD per $100 |
| `MAX_VALID_PRICE` | `200,000` | Maximum valid IQD per $100 |
| `MAX_ANOMALY_DEVIATION` | `10,000` | Max allowed rate jump |
| `TIMEZONE` | `Asia/Baghdad` | Timestamp timezone (UTC+3) |

---

## 🛡️ Parser Strategy

The parser uses a **4-layer defense** to ensure data quality:

| Layer | Purpose |
|-------|---------|
| **Layer 1** | Primary regex: matches `$100=153,300` format exactly |
| **Layer 2** | Relaxed regex: catches format variations (no commas, `100$=`) |
| **Layer 3** | Anomaly guard: rejects rates deviating >10k from the last stored rate |
| **Layer 4** | Full logging: every parse attempt is logged for debugging |

Only lines containing **هەولێر** (Erbil) + **پێنجی** (Penzi) or **سوور** (Sur) are processed. Gold prices, other cities, and promotional messages are automatically filtered out.

---

## 📄 License

MIT

---

## 🤝 Credits

- Exchange rate data sourced from public Telegram channel [`@iraqborsa`](https://t.me/iraqborsa)
- Built with [FastAPI](https://fastapi.tiangolo.com/), [Telethon](https://docs.telethon.dev/), and [aiosqlite](https://github.com/omnilib/aiosqlite)
