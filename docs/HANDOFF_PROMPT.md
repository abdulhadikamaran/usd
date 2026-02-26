# HANDOFF PROMPT — Copy everything below this line to the other AI

---

## WHO YOU ARE
You are continuing work on an existing backend project. The backend is DONE and working. Your job is to build the FRONTEND only. Do NOT modify any backend Python files unless I ask you to.

---

## PROJECT OVERVIEW

**Project:** Erbil USD/IQD Market Rate App  
**App Name:** نرخی دۆلار (Dollar Rate)  
**What it does:** Automatically fetches USD/IQD exchange rates from a Telegram channel, stores them in SQLite, and serves them via a REST API. You are building the mobile-first PWA frontend that displays this data.

**Location:** `c:\Users\Lenovo\OneDrive\Desktop\projects\usd\`

---

## BACKEND API (ALREADY WORKING — DO NOT MODIFY)

The backend is a FastAPI app running at `http://localhost:8000`. These are the 5 endpoints you will consume:

### 1. GET /api/rate/latest
Returns the most recent exchange rate.
```json
{
  "city": "Erbil",
  "penzi": 153300,
  "sur": 153250,
  "average": 153275,
  "last_updated": "2026-02-26T03:17:21.385874+03:00"
}
```
- `average` = the main number to display (IQD per $100 USD)
- `penzi` and `sur` = two market types (you only show the average)
- `last_updated` = Iraq timezone (UTC+3)

### 2. GET /api/convert/usd-to-iqd?amount=100
```json
{
  "usd": 100.0,
  "iqd": 153275.0,
  "rate_per_100": 153275
}
```

### 3. GET /api/convert/iqd-to-usd?amount=1000000
```json
{
  "iqd": 1000000.0,
  "usd": 652.74,
  "rate_per_100": 153275
}
```

### 4. GET /api/rate/history?days=7
Returns all rate records from the last N days (supports days=1, 7, 30, 90).
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
      "last_updated": "2026-02-26T15:30:21+03:00"
    },
    {
      "city": "Erbil",
      "penzi": 153250,
      "sur": 153200,
      "average": 153225,
      "last_updated": "2026-02-26T14:15:10+03:00"
    }
  ]
}
```
- Records are ordered newest first
- Multiple records per day (each time the rate is fetched)
- You group these by date and hour on the client side

### 5. GET /api/health
```json
{
  "status": "ok",
  "last_fetch": "2026-02-26T03:17:21+03:00",
  "rates_count": 35
}
```

---

## WHAT YOU ARE BUILDING: FRONTEND PWA

### Tech Stack (STRICT — do not change)
- **HTML5** — single `index.html`
- **Vanilla CSS** — one `style.css`, CSS variables for theming
- **Vanilla JavaScript (ES Modules)** — no React, no Vue, no framework
- **Chart.js via CDN** — for line charts
- **Google Fonts (Inter)** — typography
- **Service Worker** — for offline caching
- **No npm, no build tools, no bundler**

### File Structure to Create
```
usd/static/
├── index.html          # Single page app
├── css/
│   └── style.css       # All styles (dark/light + RTL/LTR)
├── js/
│   ├── app.js          # Main controller, initializes everything
│   ├── converter.js    # Currency converter logic
│   ├── chart.js        # Chart rendering (Chart.js)
│   ├── cache.js        # localStorage cache manager
│   └── i18n.js         # Kurdish/English translations
├── sw.js               # Service Worker
├── manifest.json       # PWA manifest
└── icons/
    ├── icon-192.png    # App icon (already generated, I will provide)
    └── icon-512.png    # App icon large
```

---

## THE APP: ONE SCROLLABLE PAGE WITH 4 SECTIONS

### Section 1: Header
- App name "نرخی دۆلار" on the left
- Language toggle button ("EN" / "کو") on the right
- Minimal, clean

### Section 2: Live Rate Card (HERO)
- Large, bold number showing the average rate: `153,275`
- Below it: "IQD per $100" (or Kurdish: `IQD بۆ $100`)
- Direction indicator: green ▲ +250 (if rate went up) or red ▼ -100 (if down)
- Relative timestamp: "Updated 5 mins ago"
- This is the FIRST thing users see. Make it BIG and clear.

### Section 3: Currency Converter
- Two input fields in a card:
  - Top: USD input (default: 100)
  - Bottom: IQD result (calculated)
- Circular swap ⇅ button between them to flip direction
- **Real-time**: result updates on EVERY keystroke (use `input` event)
- **Formula**: `IQD = USD × (average / 100)` and reverse
- **No API call per keystroke** — use the cached rate for math
- Number formatting with commas (e.g., 1,532,750)

### Section 4: Today's Hourly Chart
- Line chart (Chart.js) showing today's rate by hour
- X-axis: hours (adapts to when data exists, NOT hardcoded)
- Y-axis: IQD rate
- Data source: `GET /api/rate/history?days=1`
- Group records by hour, take last record per hour
- If no data today: show "No data yet today"
- Gold line (#f0b429) on dark theme, blue (#2563eb) on light

### Section 5: History Dashboard
- Three tab buttons: **7D** | **30D** | **90D**
- Line chart showing daily average rates for selected period
- Data: fetch `/api/rate/history?days=7` (or 30, 90)
- Client groups records by date, calculates daily average
- **7D special feature**: tapping a day shows an hourly breakdown below the chart
- Smooth curved lines (Chart.js tension: 0.3)

### Footer
- Small text: "Data from @iraqborsa"

---

## CRITICAL FEATURES

### Bilingual: Kurdish (RTL) + English (LTR)
- Default language: Kurdish
- Toggle button switches ALL text instantly (no page reload)
- When Kurdish: `<html dir="rtl" lang="ku">`
- When English: `<html dir="ltr" lang="en">`
- Save preference in localStorage

**All translatable strings:**
| Key | Kurdish | English |
|-----|---------|---------|
| app_name | نرخی دۆلار | Dollar Rate |
| rate_label | نرخی بازاڕی هەولێر | Erbil Market Rate |
| per_100 | IQD بۆ $100 | IQD per $100 |
| updated_ago | {n} خولەک لەمەوپێش | {n} mins ago |
| converter | گۆڕینی دراو | Currency Converter |
| today | ئەمڕۆ | Today |
| days_7 | ٧ ڕۆژ | 7 Days |
| days_30 | ٣٠ ڕۆژ | 30 Days |
| days_90 | ٩٠ ڕۆژ | 90 Days |
| offline_banner | ئۆفلاین — نرخی {time} لەمەوپێش | Offline — rate from {time} ago |
| market_closed | بازاڕ داخراوە | Market Closed |
| no_data | هیچ داتایەک نییە | No data available |

### Auto Dark/Light Theme
- Use CSS `prefers-color-scheme` media query
- No manual toggle — follows system setting

**Dark theme colors:**
- Background: `#0f1923`
- Cards: `rgba(255,255,255,0.05)` with `backdrop-filter: blur(10px)`
- Text: `#f0f0f0`
- Accent/chart: gold `#f0b429`
- Up: `#10b981`, Down: `#ef4444`

**Light theme colors:**
- Background: `#f8f9fa`
- Cards: `#ffffff` with subtle shadow
- Text: `#1a202c`
- Accent/chart: blue `#2563eb`
- Up: `#059669`, Down: `#dc2626`

### Offline Support (PWA)
1. **Service Worker** caches HTML, CSS, JS, fonts on first visit → app loads offline
2. **localStorage** caches rate data:
   ```json
   {
     "latest_rate": { "average": 153275, "last_updated": "...", "previous_average": 153025 },
     "cached_at": 1708952400000,
     "language": "ku"
   }
   ```
3. **Cache logic**:
   - App opens → show cached rate instantly
   - If cache is > 1 hour old AND online → fetch fresh rate
   - If cache is > 1 hour old AND offline → show stale rate + yellow warning banner
   - Converter ALWAYS works offline (it's just math)
4. **manifest.json** with `"display": "standalone"` so it opens like a native app

### Animations
- Rate number: count-up animation when value changes (600ms)
- Swap button: 180° rotation (300ms)
- Tab switch: smooth chart transition (200ms)
- Chart: progressive reveal left-to-right (800ms)

---

## BACKEND CHANGE NEEDED (ONLY THIS)

Update `app/main.py` to serve the static files. Add:
```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at root
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("static/index.html")
```

Replace the existing root route that redirects to /docs. Keep /docs available for API documentation.

---

## DESIGN AESTHETIC
- **Mobile-first** — designed for phones (390px width). On desktop, center with max-width 480px
- **Glassmorphism cards** — frosted glass effect with subtle borders
- **Premium fintech feel** — not a toy, not corporate. Think Revolut/Wise
- **Font: Inter** from Google Fonts
- **Responsive**: < 480px (phones), 480-768px (large phones), > 768px (center, don't expand)

---

## HOW TO TEST
1. Start the backend: `uvicorn app.main:app --host 127.0.0.1 --port 8000`
2. Open `http://localhost:8000` in browser (use Chrome mobile emulation)
3. The database already has 35 real exchange rate records

---

## IMPORTANT RULES
1. Do NOT use React, Vue, Tailwind, or any framework
2. Do NOT modify any Python files in `app/` except `app/main.py` (only to add static file serving)
3. Do NOT use npm or any build tools
4. ALL JavaScript must be vanilla ES modules
5. The app MUST work offline after first visit
6. The app MUST support RTL (Kurdish) and LTR (English)
7. Chart.js loaded via CDN: `https://cdn.jsdelivr.net/npm/chart.js`
