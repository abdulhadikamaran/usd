# Software Requirements Specification (SRS)
## Erbil USD/IQD Market Rate Backend — Phase 1

| Field                | Value                                      |
|----------------------|--------------------------------------------|
| **Document Version** | 2.0 — Final                                |
| **Date**             | 2026-02-26                                 |
| **Status**           | ✅ Approved — Ready for Development        |
| **Author**           | AI Requirements Analyst                    |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Stakeholders](#3-stakeholders)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Data Model](#6-data-model)
7. [API Specification](#7-api-specification)
8. [Background Job Specification](#8-background-job-specification)
9. [Failure Handling & Resilience](#9-failure-handling--resilience)
10. [Parser Reliability Strategy](#10-parser-reliability-strategy)
11. [Technology Stack](#11-technology-stack)
12. [System Architecture](#12-system-architecture)
13. [Phase 1 Deliverables](#13-phase-1-deliverables)
14. [Glossary](#14-glossary)

---

## 1. Introduction

### 1.1 Purpose

This document defines the complete software requirements for the **Erbil USD/IQD Market Rate Backend**, a Python-based system that automatically extracts the average USD-to-IQD market exchange rate for Erbil city from the public Telegram channel **@dolaraka12**, stores historical data in SQLite, and exposes RESTful API endpoints for rate retrieval and currency conversion.

### 1.2 Scope

**Phase 1** delivers a backend-only platform with:

- Automated Telegram data fetching via the **Telethon** client library.
- Intelligent, resilient message parsing for Erbil-specific exchange rates.
- Lightweight **SQLite** persistence with full history retention.
- **FastAPI** REST endpoints for rate queries and conversions.
- A scheduled background job running every 5 minutes.

**Explicitly excluded from Phase 1:**

| Exclusion                  | Planned Phase |
|----------------------------|---------------|
| Frontend / UI / website    | Phase 2+      |
| Push notifications         | Phase 2+      |
| Multi-city support         | Phase 2       |
| Cryptocurrency tracking    | Not planned   |
| Gold rate tracking         | Not planned   |

### 1.3 Definitions & Conventions

| Term                   | Meaning                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **Penzi (پێنجی)**     | Erbil market rate type — named after the 5,000 IQD denomination note.   |
| **Sur (سوور)**         | Erbil market rate type — "red", referring to the note color.            |
| **IQD**                | Iraqi Dinar.                                                            |
| **USD**                | United States Dollar.                                                   |
| **Rate per 100 USD**   | All extracted rates represent how many IQD are exchanged for 100 USD.   |
| **@dolaraka12**        | The source Telegram channel for exchange rate data.                     |

---

## 2. System Overview

The system operates as a **data pipeline** with three stages:

```
┌────────────────────────────┐
│  @dolaraka12 (Telegram)    │
│  Public Exchange Rate Feed │
└─────────────┬──────────────┘
              │ Telethon Client API (every 5 min)
              ▼
┌────────────────────────────┐
│  Fetcher                   │ Fetch new messages only
│  Parser                    │ Filter → Extract → Validate
│  Anomaly Guard             │ ±10,000 IQD deviation check
└─────────────┬──────────────┘
              │ Validated (penzi, sur, average)
              ▼
┌────────────────────────────┐
│  SQLite Database           │ Append-only history
│  Table: exchange_rates     │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│  FastAPI REST API          │
│  /api/rate/latest          │
│  /api/convert/usd-to-iqd   │
│  /api/convert/iqd-to-usd   │
└────────────────────────────┘
```

---

## 3. Stakeholders

| Role             | Description                                                           |
|------------------|-----------------------------------------------------------------------|
| Project Owner    | Client — sole owner and system administrator.                         |
| End Users        | Individuals and applications in Erbil consuming the API.              |
| System Admin     | Client — responsible for deployment and Telegram credentials.         |
| Data Source      | Public Telegram channel **@dolaraka12**.                              |

---

## 4. Functional Requirements

### FR-1: Telegram Data Fetching

| ID     | Requirement                                                                                             |
|--------|---------------------------------------------------------------------------------------------------------|
| FR-1.1 | The system SHALL connect to **@dolaraka12** using the **Telethon** library (Telegram Client API).       |
| FR-1.2 | The system SHALL fetch the latest messages from the channel every **5 minutes**.                         |
| FR-1.3 | The system SHALL track the last processed message ID to avoid re-processing previously seen messages.    |
| FR-1.4 | The system SHALL authenticate using the configured `api_id`, `api_hash`, and phone number session.      |
| FR-1.5 | The channel may have **multiple posters** (e.g., "Online", "Mumin"). The system SHALL process the **most recent valid message** regardless of the poster. |

### FR-2: Message Filtering

The channel publishes rates for multiple cities (Erbil, Sulaymaniyah, Duhok, Baghdad), gold prices, official bank rates, and promotional content. The parser must precisely isolate Erbil market rates.

#### FR-2.1 — Line-Level Targeting

| ID       | Requirement                                                                                           |
|----------|-------------------------------------------------------------------------------------------------------|
| FR-2.1.1 | The parser SHALL operate **line-by-line** within each message, not at the whole-message level.         |
| FR-2.1.2 | A line SHALL be considered a valid Erbil rate line if it contains **ALL** of: a price in the 100,000–200,000 range, the city identifier `هەولێر`, and one of the type identifiers (`پێنجی` or `سوور`). |

#### FR-2.2 — Inclusion Criteria

| ID       | Requirement                                                                                           |
|----------|-------------------------------------------------------------------------------------------------------|
| FR-2.2.1 | Target lines SHALL contain the Erbil city identifier: **`هەولێر`** (Kurdish for Hawler/Erbil).        |
| FR-2.2.2 | Target lines SHALL contain one of the rate type identifiers: **`پێنجی`** (Penzi) or **`سوور`** (Sur). |

#### FR-2.3 — Exclusion Criteria (Message-Level)

| ID       | Requirement                                                                                           |
|----------|-------------------------------------------------------------------------------------------------------|
| FR-2.3.1 | Messages primarily about gold SHALL be discarded. Detection keywords: `ذهب`, `زێر`, `الذهب`.         |
| FR-2.3.2 | The official central bank rate line (`السعر الرسمي`, `فەرمی`, `بانك مركزي`) SHALL be ignored. This line is naturally excluded because it does NOT contain `هەولێر` + `پێنجی`/`سوور`. |

#### FR-2.4 — Other Cities (Naturally Excluded)

| City          | Identifier   | Handling                                           |
|---------------|-------------|-----------------------------------------------------|
| Erbil         | `هەولێر`    | ✅ **Target** — extract Penzi and Sur prices.       |
| Sulaymaniyah  | `سلێمانی`   | ❌ Ignored — does not contain `هەولێر`.             |
| Duhok         | `دهوك`       | ❌ Ignored — does not contain `هەولێر`.             |
| Baghdad       | `بغداد`      | ❌ Ignored — does not contain `هەولێر`.             |

> **Design Note:** Because the parser requires `هەولێر` on the same line as the price, other cities are excluded naturally without needing a blocklist.

### FR-3: Price Extraction

#### FR-3.1 — Observed Message Format

From analysis of the live channel **@dolaraka12**, the confirmed format is:

```
*$100=153,300 هەولێر پێنجی*
*$100=153,250 هەولێر سوور*
```

| Element      | Format               | Notes                                           |
|--------------|----------------------|-------------------------------------------------|
| Bold markers | `*...*`              | Telegram markdown bold wrapping.                |
| Currency     | `$100=`              | Dollar sign **before** 100, followed by `=`.    |
| Price        | `153,300`            | Comma-separated 6-digit integer (IQD per $100). |
| City         | `هەولێر`             | Always on the same line as the price.           |
| Type         | `پێنجی` or `سوور`   | Always on the same line as the price.           |

#### FR-3.2 — Extraction Rules

| ID       | Requirement                                                                                           |
|----------|-------------------------------------------------------------------------------------------------------|
| FR-3.2.1 | The parser SHALL extract the numeric price from lines matching the pattern. The primary format is `$100=XXX,XXX` but the parser SHALL also handle: `100$=XXX,XXX` (dollar sign after), spaces around `=`, and absence of commas. |
| FR-3.2.2 | Extracted prices SHALL be validated to fall within **100,000 – 200,000 IQD** (inclusive). Values outside this range are discarded. |
| FR-3.2.3 | A valid extraction SHALL produce **exactly 2** Erbil prices — one Penzi and one Sur. Messages with fewer or more than 2 valid Erbil prices SHALL be discarded. |
| FR-3.2.4 | Bold markers (`*`) SHALL be stripped before parsing.                                                   |

### FR-4: Average Calculation

| ID     | Requirement                                                                                             |
|--------|---------------------------------------------------------------------------------------------------------|
| FR-4.1 | The system SHALL compute the average Erbil rate as: `average = (penzi_price + sur_price) / 2`.          |
| FR-4.2 | The result SHALL be stored as an **integer** (rounded to nearest whole number).                          |
| FR-4.3 | All three values (`penzi_price`, `sur_price`, `average_price`) SHALL be persisted together.             |

### FR-5: Data Storage

| ID     | Requirement                                                                                             |
|--------|---------------------------------------------------------------------------------------------------------|
| FR-5.1 | The system SHALL use **SQLite** as the persistence layer (file: `data/rates.db`).                       |
| FR-5.2 | The database SHALL contain a table `exchange_rates` with the schema defined in [Section 6](#6-data-model). |
| FR-5.3 | Records SHALL **never** be deleted or overwritten. Each valid extraction creates a new row (append-only). |
| FR-5.4 | If no new valid data is fetched in a cycle, the system SHALL retain the most recent valid record.        |

### FR-6: API Endpoints

| ID     | Requirement                                                                                             |
|--------|---------------------------------------------------------------------------------------------------------|
| FR-6.1 | `GET /api/rate/latest` — Returns the most recent exchange rate record.                                  |
| FR-6.2 | `GET /api/convert/usd-to-iqd?amount=<N>` — Converts USD to IQD: `IQD = amount × (average / 100)`.     |
| FR-6.3 | `GET /api/convert/iqd-to-usd?amount=<N>` — Converts IQD to USD: `USD = amount / (average / 100)`.     |
| FR-6.4 | All responses SHALL be **JSON** with appropriate HTTP status codes.                                     |
| FR-6.5 | If no rate data exists, endpoints SHALL return `503 Service Unavailable` with an informative message.   |
| FR-6.6 | If the `amount` parameter is missing or invalid, endpoints SHALL return `400 Bad Request`.              |

### FR-7: Message Deduplication

| ID     | Requirement                                                                                             |
|--------|---------------------------------------------------------------------------------------------------------|
| FR-7.1 | When multiple posters publish rates within the same fetch cycle, the system SHALL use the **most recently posted** valid message only. |
| FR-7.2 | The `source_message_id` field SHALL be stored to prevent re-processing the same Telegram message.       |

---

## 5. Non-Functional Requirements

### NFR-1: Performance

| ID      | Requirement                                                                      |
|---------|----------------------------------------------------------------------------------|
| NFR-1.1 | Telegram fetch + parse cycle SHALL complete in **< 2 seconds**.                  |
| NFR-1.2 | API response latency SHALL be **< 300 ms** (p95).                                |

### NFR-2: Reliability

| ID      | Requirement                                                                      |
|---------|----------------------------------------------------------------------------------|
| NFR-2.1 | The parser SHALL survive minor formatting changes (extra spaces, reordering, bold marker changes). |
| NFR-2.2 | When Telegram is unavailable, the API SHALL continue serving the last valid stored rate. |
| NFR-2.3 | The background job SHALL **not** crash the API server upon encountering errors.  |
| NFR-2.4 | The parser SHALL use a multi-strategy approach (see [Section 10](#10-parser-reliability-strategy)). |

### NFR-3: Security

| ID      | Requirement                                                                      |
|---------|----------------------------------------------------------------------------------|
| NFR-3.1 | Telegram credentials SHALL be stored in a `.env` file, excluded from version control via `.gitignore`. |
| NFR-3.2 | Telethon session files (`*.session`) SHALL be gitignored.                        |
| NFR-3.3 | The SQLite database file SHALL be gitignored.                                    |

### NFR-4: Maintainability

| ID      | Requirement                                                                      |
|---------|----------------------------------------------------------------------------------|
| NFR-4.1 | Parsing/filtering logic SHALL be **separated** from API route handlers into dedicated modules. |
| NFR-4.2 | Keywords (city names, rate types, exclusion terms) SHALL be stored in a **configuration/constants module**, not hard-coded across the codebase. |
| NFR-4.3 | The codebase SHALL follow standard Python project structure with clear module separation. |

### NFR-5: Logging & Observability

| ID      | Requirement                                                                      |
|---------|----------------------------------------------------------------------------------|
| NFR-5.1 | Every fetch cycle SHALL be logged: messages seen, messages processed, prices extracted, validation outcomes, and errors. |
| NFR-5.2 | Failed parses SHALL log the **full raw message text** for debugging.              |
| NFR-5.3 | Anomaly detections SHALL log extracted values AND the previous stored average.    |
| NFR-5.4 | Logs SHALL use Python's `logging` module with configurable log levels.            |

---

## 6. Data Model

### Table: `exchange_rates`

| Column              | Type       | Constraints                          | Description                        |
|---------------------|------------|--------------------------------------|------------------------------------|
| `id`                | `INTEGER`  | `PRIMARY KEY AUTOINCREMENT`          | Unique record identifier.          |
| `erbil_penzi`       | `INTEGER`  | `NOT NULL`                           | Penzi (پێنجی) price per 100 USD.  |
| `erbil_sur`         | `INTEGER`  | `NOT NULL`                           | Sur (سوور) price per 100 USD.     |
| `erbil_average`     | `INTEGER`  | `NOT NULL`                           | Calculated average of Penzi & Sur. |
| `source_message_id` | `TEXT`     | `NOT NULL UNIQUE`                    | Telegram message ID (dedup key).   |
| `created_at`        | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Timestamp of record creation.      |

### Indexes

| Index                        | Purpose                                    |
|------------------------------|--------------------------------------------|
| `PRIMARY KEY` on `id`        | Automatic — unique row identifier.         |
| `UNIQUE` on `source_message_id` | Prevents duplicate message storage.     |
| `INDEX` on `created_at DESC` | Efficient latest-rate queries.             |

---

## 7. API Specification

### 7.1 `GET /api/rate/latest`

Returns the most recently stored exchange rate.

**Success Response (200 OK):**

```json
{
  "city": "Erbil",
  "penzi": 153300,
  "sur": 153200,
  "average": 153250,
  "last_updated": "2026-02-26T14:05:00Z"
}
```

**No Data Response (503 Service Unavailable):**

```json
{
  "error": "No exchange rate data available yet."
}
```

### 7.2 `GET /api/convert/usd-to-iqd?amount=<N>`

Converts a USD amount to IQD using the latest average rate.

**Formula:** `IQD = amount × (average_rate / 100)`

**Example:** `GET /api/convert/usd-to-iqd?amount=50`

```json
{
  "usd": 50,
  "iqd": 76625.0,
  "rate_per_100": 153250
}
```

**Errors:**
- `400 Bad Request` — missing or invalid `amount`.
- `503 Service Unavailable` — no rate data stored yet.

### 7.3 `GET /api/convert/iqd-to-usd?amount=<N>`

Converts an IQD amount to USD using the latest average rate.

**Formula:** `USD = amount / (average_rate / 100)`

**Example:** `GET /api/convert/iqd-to-usd?amount=153250`

```json
{
  "iqd": 153250,
  "usd": 100.0,
  "rate_per_100": 153250
}
```

**Errors:**
- `400 Bad Request` — missing or invalid `amount`.
- `503 Service Unavailable` — no rate data stored yet.

---

## 8. Background Job Specification

### 8.1 Scheduling

- Executes **every 5 minutes** via `asyncio` loop or APScheduler.
- Runs **concurrently** with the FastAPI server in the same process.

### 8.2 Processing Pipeline (Per Cycle)

```
1.  Fetch new messages from @dolaraka12 (since last processed message ID)
2.  For each new message (most recent first):
    a.  Check for gold exclusion keywords (ذهب, زێر, الذهب) → SKIP entire message if found
    b.  Scan each line of the message:
        i.   Does the line contain "هەولێر"? → If NO, skip line
        ii.  Does the line contain "پێنجی" or "سوور"? → If NO, skip line
        iii. Extract numeric price from the line
        iv.  Validate price is between 100,000 – 200,000 → If NO, skip line
        v.   Store as penzi or sur based on which keyword matched
    c.  After scanning all lines: do we have exactly 1 penzi + 1 sur? → If NO, discard message
    d.  Compute average = (penzi + sur) / 2
    e.  Anomaly check: |new_average − last_stored_average| ≤ 10,000? → If NO, flag & skip
    f.  INSERT into database
    g.  STOP — use only the most recent valid message per cycle
3.  Update last-processed message ID
4.  Sleep until next cycle
```

### 8.3 Anomaly Detection

- If the newly computed average differs from the last stored average by **more than 10,000 IQD**, the record SHALL be **flagged and skipped**.
- The anomaly SHALL be logged with full context: raw message text, extracted values, previous average.
- This prevents corrupted, joke, or misformatted messages from polluting the database.

---

## 9. Failure Handling & Resilience

| Failure Scenario                  | System Behavior                                                        |
|-----------------------------------|------------------------------------------------------------------------|
| Telegram API unreachable          | Log error, retry on next 5-minute cycle. API serves last valid rate.   |
| Message parsing fails             | Log raw message + failure reason. Skip. Move to next message.          |
| No valid Erbil prices in message  | Log and skip. No database write.                                       |
| Anomalous rate detected (±10k)   | Log with full context, flag, skip. Do not store.                       |
| Database write fails              | Log error. Retry on next cycle.                                        |
| API called with no stored data    | Return `503 Service Unavailable` with informative JSON error.          |
| Session token expires             | Log error. Requires manual re-authentication (documented in ops guide).|
| Duplicate message ID              | `UNIQUE` constraint on `source_message_id` prevents duplicate inserts. |

---

## 10. Parser Reliability Strategy

The user requires the parser to remain functional even if the channel changes its message format. The following multi-layered approach ensures resilience:

### Layer 1 — Primary Regex (Current Format)

Matches the exact observed format:

```
*$100=XXX,XXX هەولێر پێنجی*
```

Pattern components:
- Optional `*` (bold markers)
- `$100=` or `100$=` (dollar sign before or after 100)
- Price: digits with optional commas (e.g., `153,300` or `153300`)
- City keyword: `هەولێر`
- Type keyword: `پێنجی` or `سوور`

### Layer 2 — Relaxed Regex (Format Variations)

If primary fails, attempt extraction with relaxed rules:
- No requirement for `$100=` prefix
- Search for any 6-digit number (100,000–200,000) on a line containing `هەولێر` + `پێنجی`/`سوور`
- Handle spaces, different separators, or restructured templates

### Layer 3 — Anomaly Guard

Even if extraction succeeds, the value is checked against the last stored rate:
- Deviation **≤ 10,000 IQD** → Accept
- Deviation **> 10,000 IQD** → Flag, log, skip

### Layer 4 — Full Logging

Every failed parse logs:
- The complete raw message text
- Which parsing layer was attempted
- The specific reason for failure

This enables rapid parser updates when format changes are detected.

---

## 11. Technology Stack

| Component           | Technology         | Justification                                              |
|---------------------|--------------------|------------------------------------------------------------|
| Language            | Python 3.10+       | Excellent Telegram library support, rapid development.     |
| Telegram Client     | Telethon           | Full Client API access (not limited Bot API).              |
| Database            | SQLite             | Zero-config, serverless, ideal for single-node deployment. |
| API Framework       | FastAPI            | Async-native, auto-generated docs, high performance.       |
| ASGI Server         | Uvicorn            | Production-grade ASGI server for FastAPI.                   |
| Task Scheduling     | asyncio            | Lightweight, no external dependencies.                     |
| Config Management   | python-dotenv      | Environment variable management for secrets.               |

---

## 12. System Architecture

### 12.1 Project Structure

```
usd/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app, lifespan, background task startup
│   ├── config.py              # Load .env, define constants & keywords
│   ├── database.py            # SQLite connection, queries, schema init
│   ├── models.py              # Pydantic response models
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # GET /api/rate/latest, /api/convert/*
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── fetcher.py         # Telethon client, message fetching
│   │   └── parser.py          # Multi-layer parser, filtering, validation
│   └── scheduler/
│       ├── __init__.py
│       └── jobs.py            # Background job orchestration (5-min loop)
├── data/
│   └── rates.db               # SQLite database (gitignored)
├── docs/
│   └── SRS.md                 # This document
├── .env                       # Telegram credentials (gitignored)
├── .env.example               # Template for required env vars
├── .gitignore
├── requirements.txt
└── README.md
```

### 12.2 Module Responsibility Map

| Module                   | Responsibility                                                          |
|--------------------------|-------------------------------------------------------------------------|
| `app/main.py`            | FastAPI app creation, lifespan events, background task startup.         |
| `app/config.py`          | Loads `.env`, defines all keywords, thresholds, and constants.          |
| `app/database.py`        | SQLite connection pool, schema creation, insert/query functions.        |
| `app/models.py`          | Pydantic models for API request validation and response serialization.  |
| `app/api/routes.py`      | Route handlers for all 3 API endpoints. Thin layer — delegates to DB.  |
| `app/telegram/fetcher.py`| Telethon session management, message fetching, last-ID tracking.        |
| `app/telegram/parser.py` | All parsing logic: filtering, regex extraction, validation, anomaly check. |
| `app/scheduler/jobs.py`  | Orchestrates the fetch → parse → store pipeline on a 5-minute loop.    |

### 12.3 Data Flow

```
@dolaraka12 (Telegram Channel)
    │
    │  Telethon Client API
    ▼
fetcher.py ─── Fetches new messages (tracks last message ID)
    │
    │  Raw message text
    ▼
parser.py ──── Layer 1: Primary regex ($100=XXX,XXX هەولێر پێنجی)
    │          Layer 2: Relaxed regex (any 100k-200k number + هەولێر)
    │          Layer 3: Anomaly guard (±10k from last rate)
    │          Layer 4: Full logging on failure
    │
    │  Validated (penzi, sur, average)
    ▼
database.py ── INSERT into exchange_rates (append-only)
    │
    ▼
routes.py ──── GET /api/rate/latest
               GET /api/convert/usd-to-iqd?amount=N
               GET /api/convert/iqd-to-usd?amount=N
```

---

## 13. Phase 1 Deliverables

| #  | Deliverable                                | Status        |
|----|--------------------------------------------|---------------|
| D1 | Environment configuration (`.env`, `.gitignore`) | ✅ Complete  |
| D2 | Software Requirements Specification        | ✅ Complete   |
| D3 | Telegram fetcher using Telethon            | 🔲 Pending    |
| D4 | Multi-layer parser engine for Erbil prices | 🔲 Pending    |
| D5 | SQLite database with schema & queries      | 🔲 Pending    |
| D6 | REST API: `GET /api/rate/latest`           | 🔲 Pending    |
| D7 | REST API: `GET /api/convert/usd-to-iqd`   | 🔲 Pending    |
| D8 | REST API: `GET /api/convert/iqd-to-usd`   | 🔲 Pending    |
| D9 | Background scheduler (5-min cycle)         | 🔲 Pending    |
| D10| Project README                             | 🔲 Pending    |

---

## 14. Glossary

| Term                | Definition                                                                     |
|---------------------|--------------------------------------------------------------------------------|
| **Telethon**        | A Python library for interacting with Telegram's full Client API.              |
| **FastAPI**         | A modern, high-performance Python web framework for building APIs.             |
| **SQLite**          | A lightweight, file-based relational database engine.                          |
| **Penzi (پێنجی)**  | Erbil market rate type — named after the 5,000 IQD denomination.               |
| **Sur (سوور)**      | Erbil market rate type — "red", referring to the note color.                   |
| **Anomaly Check**   | A safeguard rejecting rates deviating > 10,000 IQD from the previous value.    |
| **ASGI**            | Asynchronous Server Gateway Interface — the protocol FastAPI runs on.          |
| **@dolaraka12**     | Public Telegram channel — the sole data source for Phase 1.                    |
| **Append-Only**     | Database design where records are only inserted, never updated or deleted.     |

---

*End of Document — Version 2.0 Final*
