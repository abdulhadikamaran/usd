<div align="center">
  <h1>💱 Erbil USD/IQD Exchange Rate Platform</h1>
  <p><b>The fastest, most accurate, real-time Dollar to Iraqi Dinar tracker for the Erbil market.</b></p>
  
  [![Live Demo](https://img.shields.io/badge/Live%20Demo-usd--ih41.onrender.com-success?style=for-the-badge&logo=vercel)](https://usd-ih41.onrender.com/)
  <br/>
</div>

## 🌟 Overview

The Erbil USD/IQD Exchange Rate Platform is a complete, production-ready system consisting of a highly intelligent background engine, a robust API, and a stunning Progressive Web App (PWA). 

It continuously monitors the primary Erbil market Telegram channels in real-time. By leveraging a custom NLP-style parser, it instantly extracts the official market rates, bypasses the noise, and pushes updates straight to user devices with near-zero latency using WebSockets.

---

## ✨ Key Features & Marketing Highlights

- ⚡ **Extreme Real-Time (WebSockets)** — Don't fall behind the market. As soon as a message drops on Telegram, the system parses it and pushes the update to all connected web clients instantly via WebSockets.
- 🧠 **Dual-Dialect Smart Parser** — The market changes formats, but we don't break. Automatically detects and accurately understands both wholesale (`پێنجی / سوور`) and retail (`کڕین / فرۆشتن`) price dialects, snapping directly to the most accurate official price.
- 📱 **Beautiful Native-Like PWA** — Built with raw Tailwind CSS and Vanilla JS for a frictionless, ultra-fast UI. Installable on iOS/Android, featuring offline support, a premium glassmorphism design, and a real-time smart currency converter.
- 📊 **Deep Historical Analytics** — Every price fluctuation is permanently archived into a high-performance PostgreSQL database. Dive into 1D, 7D, 30D, and 90D interactive SVG charts natively rendered on the frontend.
- 🛡️ **Self-Healing & Anomaly Guard** — Protects against typos and fake data. Automatically rejects prices deviating wildly from the moving average and auto-reconnects on network drops.

---

## 🏗️ Architecture Stack

**Backend Engine**
- `FastAPI` — Blazing fast Python web framework
- `Telethon` — Asynchronous Telegram client
- `PostgreSQL` + `asyncpg` — Scalable, concurrent data storage
- `WebSockets` — Real-time event broadcasting

**Frontend Client**
- `Vanilla JS` + `Tailwind CSS v3`
- `Service Workers` — Stale-while-revalidate caching and offline mode
- Custom zero-dependency SVG charted analytics

---

## 🌐 Live Application
Experience the platform live: **[https://usd-ih41.onrender.com/](https://usd-ih41.onrender.com/)**

---

## 🚀 Quick Start (Local Development)

### 1. Clone & Install

```bash
git clone <repo-url>
cd usd
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example template and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION_STRING=your_session_string
TELEGRAM_CHANNEL=@iraqborsa
DATABASE_URL=postgresql://user:pass@host/dbname
```

### 3. Generate Telegram Session (If needed)

```bash
python extract_session.py
```
*Follow the terminal prompts. It will spit out a gigantic string. Save this as `TELEGRAM_SESSION_STRING` in your `.env`!*

### 4. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On startup, the system will execute any pending DB migrations, connect to the Telegram socket, begin the scheduler loop, and serve the API.

---

## 📡 API Endpoints

The backend exposes a clean REST API interface alongside the WebSocket. Check out `http://localhost:8000/docs` for the interactive Swagger UI.

### `GET /api/rate/latest`
Returns the most recent Erbil exchange rate.

### `GET /api/rate/history?days=x`
Returns aggregated historical data ready for charting. Supports 1, 7, 30, and 90 days.

### `GET /api/health`
System status, connection pool health, and record count.

---

## 🚀 Deployment

This application is fully optimized for platform-as-a-service providers like **Render.com**. 
1. Connect your GitHub repo to a Render Web Service.
2. Set the build command to `pip install -r requirements.txt`.
3. Set the start command to `uvicorn app.main:app --host 0.0.0.0 --port 10000`.
4. Inject your `.env` variables into the environment settings. 

---

<div align="center">
  <p>Built for the modern market edge. 📈</p>
</div>
