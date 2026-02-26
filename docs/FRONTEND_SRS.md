# نرخی دۆلار — Frontend SRS
## Software Requirements Specification v1.0

**Document Version:** 1.0 Final  
**Date:** 2026-02-26  
**Project:** Erbil USD/IQD Market Rate PWA  
**App Name:** نرخی دۆلار  

---

## 1. Overview

### 1.1 Purpose
A mobile-first Progressive Web App (PWA) that displays the live Erbil USD/IQD
market exchange rate, provides an instant currency converter, and shows
historical rate analytics through interactive charts.

### 1.2 Target Users
- Erbil residents and business owners who deal in USD/IQD daily
- Kurdish and English speakers
- Primarily mobile users (Android/iOS)

### 1.3 Core Value Proposition
Open the app → see the dollar rate in under 1 second. Convert currencies
instantly. Works offline. No login required.

---

## 2. Technology Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Structure | HTML5 | Semantic, accessible |
| Styling | Vanilla CSS | No build tools, CSS variables for theming |
| Logic | Vanilla JavaScript (ES Modules) | No framework, fast, small bundle |
| Charts | Chart.js (CDN) | Lightweight, responsive, line chart support |
| PWA | Service Worker + Web App Manifest | Offline support, installable |
| Data Cache | localStorage | Rate data persistence |
| Hosting | PythonAnywhere (served by FastAPI) | Single deployment, free tier |
| Fonts | Google Fonts — Inter | Clean, modern, excellent number rendering |

### 2.1 No Build Tools
The frontend is pure static files. No npm, no webpack, no bundler.
Files are served directly by FastAPI's `StaticFiles` middleware.

---

## 3. Hosting & Serving Architecture

### 3.1 Single Deployment
The frontend lives inside the existing `usd/` backend project:

```
usd/
├── app/                    # Backend (existing)
├── static/                 # Frontend (NEW)
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── app.js          # Main application logic
│   │   ├── converter.js    # Currency converter module
│   │   ├── chart.js        # Chart rendering module
│   │   ├── cache.js        # Offline cache manager
│   │   └── i18n.js         # Language (Kurdish/English)
│   ├── sw.js               # Service Worker (root of static/)
│   ├── manifest.json       # PWA manifest
│   └── icons/              # App icons (multiple sizes)
│       ├── icon-192.png
│       └── icon-512.png
```

### 3.2 FastAPI Integration
FastAPI serves the static files:
- `GET /` → serves `static/index.html`
- `GET /static/*` → serves CSS, JS, icons
- `GET /api/*` → existing API endpoints (unchanged)

Everything runs under one URL: `yourusername.pythonanywhere.com`

---

## 4. Features Specification

---

### 4.1 Feature: Live Rate Display

**Priority:** Critical  
**Location:** Top of page (hero section)

#### 4.1.1 What is shown
| Element | Description | Example |
|---------|-------------|---------|
| Average rate | Large bold number, primary focus | `153,275` |
| Label | "IQD per $100" below the number | `IQD بۆ $100` |
| City label | "Erbil Market Rate" | `نرخی بازاڕی هەولێر` |
| Direction arrow | Green ▲ if rate went up, Red ▼ if down vs previous | `▲ +250` |
| Timestamp | Relative time since last update | `٥ خولەک لەمەوپێش` / `5 mins ago` |

#### 4.1.2 Behavior
- On app load: display cached rate instantly (< 100ms)
- In background: check if cache is > 1 hour old
  - If yes AND online: fetch fresh rate from `/api/rate/latest`
  - If yes AND offline: show stale rate + warning banner
  - If no: use cached rate, don't fetch
- Direction arrow compares current rate to the previous rate in cache
- Timestamp updates every minute via `setInterval`

#### 4.1.3 Warning Banner (Offline)
When using stale data (cache > 1 hour and offline):
```
⚠️ ئۆفلاین — نرخی ٣ کاتژمێر لەمەوپێش
⚠️ Offline — rate from 3 hours ago
```
- Yellow/amber bar, subtle, non-blocking
- Disappears automatically when fresh data is fetched

---

### 4.2 Feature: Currency Converter

**Priority:** Critical  
**Location:** Below the rate card

#### 4.2.1 Layout
```
┌─────────────────────────────┐
│  💵  USD                    │
│  ┌───────────────────────┐  │
│  │ [input field]          │  │
│  └───────────────────────┘  │
│           ⇅ swap            │
│  🇮🇶  IQD                    │
│  ┌───────────────────────┐  │
│  │ [calculated result]    │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

#### 4.2.2 Behavior
- **Real-time calculation** on every keystroke (`input` event)
- No "Convert" button — result updates as you type
- Formula: `IQD = USD × (average_rate / 100)`
- Reverse: `USD = IQD / (average_rate / 100)`
- **Swap button**: toggles which field is the input vs output
  - Smooth 180° rotation animation on the swap icon
- Number formatting: commas for thousands (e.g., `1,532,750`)
- Input validation: only positive numbers allowed
- Default state: USD input = `100`, IQD shows the current rate

#### 4.2.3 Offline Behavior
- Converter uses the locally cached rate
- Works 100% offline — no API call needed per conversion
- The rate it uses is displayed: "Based on rate: 153,275 IQD/$100"

---

### 4.3 Feature: Today's Hourly Chart

**Priority:** High  
**Location:** Below the converter

#### 4.3.1 What is shown
- A **line chart** showing today's rate movement, plotted hourly
- X-axis: hours of the day (e.g., 10:00, 11:00, 12:00, ...)
- Y-axis: average IQD rate
- Single line (average rate only, no Penzi/Sur breakdown)

#### 4.3.2 Data Source
- Fetches from: `GET /api/rate/history?days=1`
- Groups the returned records by hour
- For each hour: takes the **last recorded rate** as that hour's value

#### 4.3.3 Adaptive Market Hours
Market hours are NOT hardcoded. The chart adapts to the data:
- If the first data point today is at 9:17 AM → chart starts at 9:00
- If the last data point today is at 5:42 PM → chart ends at 6:00
- If no data exists today → show message: "No data yet today"
- The chart only plots hours where data actually exists
- Between data gaps: draw a flat line at the last known rate

#### 4.3.4 Night / No-Data State
When no new data is coming in (market closed):
- The chart shows the last available rate as a flat line
- A subtle text label: "Market closed — last rate: 153,275"
- In Kurdish: "بازاڕ داخراوە — دوایین نرخ: ١٥٣,٢٧٥"

---

### 4.4 Feature: History Dashboard

**Priority:** High  
**Location:** Below today's chart, tabbed interface

#### 4.4.1 Time Range Tabs
Three tab buttons at the top of the section:

| Tab | Label (KU) | Label (EN) | Data |
|-----|-----------|-----------|------|
| 7D | ٧ ڕۆژ | 7 Days | Daily averages, last 7 days |
| 30D | ٣٠ ڕۆژ | 30 Days | Daily averages, last 30 days |
| 90D | ٩٠ ڕۆژ | 90 Days | Daily averages, last 90 days |

Active tab is visually highlighted. Default: 7D.

#### 4.4.2 Chart Behavior
- **Line chart** for all three views
- X-axis: dates
- Y-axis: average IQD rate
- Smooth, curved line (tension: 0.3 in Chart.js)
- On tap/hover a data point: tooltip shows exact rate and date

#### 4.4.3 7-Day View — Hourly Drill-Down
The 7-day view has an extra feature:
- **Tapping a day on the chart** expands an hourly breakdown below
- Shows a mini hourly chart for that specific day
- Same adaptive behavior as Today's chart (no hardcoded hours)
- Tap another day → switches to that day's hourly view
- Tap the same day again → collapses the hourly view

#### 4.4.4 Data Source
- 7D: `GET /api/rate/history?days=7`
- 30D: `GET /api/rate/history?days=30`
- 90D: `GET /api/rate/history?days=90`

#### 4.4.5 Data Processing (Client-Side)
The API returns individual rate records. The frontend processes them:
1. Group records by date (YYYY-MM-DD)
2. For daily view: calculate the **average of all rates** for that day
3. For hourly drill-down: group by hour within a day

---

### 4.5 Feature: Bilingual Support (Kurdish / English)

**Priority:** High

#### 4.5.1 Languages
| Code | Language | Script | Direction |
|------|----------|--------|-----------|
| `ku` | Kurdish (Sorani) | Arabic script | RTL (right-to-left) |
| `en` | English | Latin script | LTR (left-to-right) |

#### 4.5.2 Behavior
- **Default language:** Kurdish (`ku`)
- Language toggle: a small button in the top-right corner
  - Shows "EN" when Kurdish is active (switch to English)
  - Shows "کو" when English is active (switch to Kurdish)
- Switching language:
  - All text labels update instantly (no page reload)
  - Layout direction flips (RTL ↔ LTR) via `dir` attribute on `<html>`
  - Number formatting changes: Western digits in EN, Arabic-Indic optional in KU
  - Preference saved to `localStorage` and restored on next visit

#### 4.5.3 Translated Elements
All visible text is translatable. Key strings include:

| Key | Kurdish (ku) | English (en) |
|-----|-------------|-------------|
| `app_name` | نرخی دۆلار | Dollar Rate |
| `rate_label` | نرخی بازاڕی هەولێر | Erbil Market Rate |
| `per_100` | IQD بۆ $100 | IQD per $100 |
| `updated_ago` | ٥ خولەک لەمەوپێش | 5 mins ago |
| `converter` | گۆڕینی دراو | Currency Converter |
| `today` | ئەمڕۆ | Today |
| `days_7` | ٧ ڕۆژ | 7 Days |
| `days_30` | ٣٠ ڕۆژ | 30 Days |
| `days_90` | ٩٠ ڕۆژ | 90 Days |
| `offline` | ئۆفلاین | Offline |
| `market_closed` | بازاڕ داخراوە | Market Closed |
| `no_data` | هیچ داتایەک نییە | No data available |
| `install_app` | دابەزاندن | Install App |

---

### 4.6 Feature: Auto Dark/Light Theme

**Priority:** Medium

#### 4.6.1 Behavior
- Uses CSS `prefers-color-scheme` media query
- If phone/browser is set to dark mode → app shows dark theme
- If phone/browser is set to light mode → app shows light theme
- No manual toggle — fully automatic

#### 4.6.2 Color Palettes

**Dark Theme:**
| Element | Color | Hex |
|---------|-------|-----|
| Background | Deep navy | `#0f1923` |
| Card background | Dark glass | `rgba(255,255,255,0.05)` |
| Card border | Subtle glow | `rgba(255,255,255,0.1)` |
| Primary text | White | `#f0f0f0` |
| Secondary text | Muted gray | `#8899aa` |
| Accent (rate) | Gold | `#f0b429` |
| Up indicator | Green | `#10b981` |
| Down indicator | Red | `#ef4444` |
| Chart line | Accent gold | `#f0b429` |

**Light Theme:**
| Element | Color | Hex |
|---------|-------|-----|
| Background | Off-white | `#f8f9fa` |
| Card background | White | `#ffffff` |
| Card border | Light gray | `#e2e8f0` |
| Primary text | Dark | `#1a202c` |
| Secondary text | Gray | `#718096` |
| Accent (rate) | Deep blue | `#2563eb` |
| Up indicator | Green | `#059669` |
| Down indicator | Red | `#dc2626` |
| Chart line | Deep blue | `#2563eb` |

---

### 4.7 Feature: Offline Support (PWA)

**Priority:** Critical

#### 4.7.1 Service Worker Strategy

| Resource Type | Cache Strategy | Details |
|--------------|---------------|---------|
| HTML, CSS, JS | **Cache-First** | Cached on first visit, served from cache always. Updated in background |
| Google Fonts | **Cache-First** | Cached on first load |
| Chart.js CDN | **Cache-First** | Cached on first load |
| API responses | **Stale-While-Revalidate** | Serve cached, fetch fresh in background |
| App icons | **Cache-First** | Cached on install |

#### 4.7.2 Rate Data Cache (localStorage)

```json
{
  "latest_rate": {
    "average": 153275,
    "penzi": 153300,
    "sur": 153250,
    "last_updated": "2026-02-26T15:30:00+03:00",
    "previous_average": 153025
  },
  "cached_at": 1708952400000,
  "language": "ku",
  "history_7d": [...],
  "history_7d_cached_at": 1708952400000
}
```

#### 4.7.3 Cache Refresh Logic

```
App opens:
  1. Instantly show cached rate (< 100ms render)
  2. Check: is cached_at > 1 hour ago?
     → NO:  Done. Use cached data.
     → YES: Try fetch from /api/rate/latest
       → SUCCESS: Update cache + display + save previous_average
       → FAIL (offline): Show warning banner, keep using stale cache
```

#### 4.7.4 Background Refresh
- While app is open: `setInterval` every 60 minutes → re-fetch rate
- On tab focus (Page Visibility API): if cache is stale → re-fetch
- History charts: cached per tab (7d, 30d, 90d), refreshed when tab is tapped AND cache is > 1 hour old

#### 4.7.5 PWA Manifest (`manifest.json`)

```json
{
  "name": "نرخی دۆلار — Erbil Dollar Rate",
  "short_name": "نرخی دۆلار",
  "description": "Live Erbil USD/IQD exchange rate with offline support",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0f1923",
  "theme_color": "#f0b429",
  "lang": "ku",
  "dir": "rtl",
  "icons": [
    { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

---

## 5. UI Layout Specification

### 5.1 Mobile-First Single Page

The entire app is ONE scrollable page with this vertical stack:

```
┌──────────────────────────────────┐
│  ⚙︎ Header: App name + 🌐 Lang   │
├──────────────────────────────────┤
│                                  │
│     💰 LIVE RATE CARD            │
│     153,275 IQD                  │
│     per $100  ▲ +250             │
│     Updated 5 mins ago           │
│                                  │
├──────────────────────────────────┤
│                                  │
│     🔁 CONVERTER                 │
│     USD: [100      ]             │
│          ⇅ swap                  │
│     IQD: [153,275  ]             │
│                                  │
├──────────────────────────────────┤
│                                  │
│     📊 TODAY'S CHART             │
│     [hourly line chart]          │
│                                  │
├──────────────────────────────────┤
│                                  │
│     📈 HISTORY                   │
│     [7D] [30D] [90D]            │
│     [daily line chart]           │
│     [hourly drill-down if 7D]    │
│                                  │
├──────────────────────────────────┤
│  Footer: "Data from @iraqborsa"  │
└──────────────────────────────────┘
```

### 5.2 Responsive Breakpoints

| Width | Target | Layout |
|-------|--------|--------|
| < 480px | Small phones | Full width cards, stacked |
| 480–768px | Large phones / small tablets | Same layout, slightly more padding |
| > 768px | Tablets / desktop | Max-width container (480px), centered |

The app is designed for phones. On larger screens, it stays phone-width
and centers itself — it does NOT expand to fill a desktop monitor.

---

## 6. Animations & Micro-Interactions

| Element | Animation | Duration |
|---------|-----------|----------|
| Rate number on update | Count-up animation (old → new value) | 600ms ease-out |
| Direction arrow | Fade-in + slight bounce | 300ms |
| Swap button | 180° rotation | 300ms ease |
| Tab switch | Slide + fade transition on chart | 200ms |
| Warning banner | Slide down from top | 300ms |
| Chart data points | Progressive reveal (left to right) | 800ms |
| Language switch | Smooth text swap (no page reload) | 150ms |

---

## 7. Error States

| Scenario | Display |
|----------|---------|
| First visit, no internet | Full screen: "Connect to internet to get started" with retry button |
| API error (server down) | Use cached data + amber banner: "Server unreachable" |
| No data in database yet | "Data not available yet — check back soon" |
| History has no data for period | "No records for this period" with empty chart placeholder |

---

## 8. Data Flow Summary

```
                    ┌─────────────────┐
                    │  localStorage   │
                    │  (rate cache)   │
                    └──────┬──────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌─────────────┐  ┌──────────┐  ┌─────────────┐
   │ Rate Display │  │Converter │  │   Charts    │
   │ (hero card) │  │(instant) │  │ (Chart.js)  │
   └─────────────┘  └──────────┘  └─────────────┘
          ▲                                ▲
          │                                │
   ┌──────┴───────────────────────────────┴──┐
   │           cache.js (manager)             │
   │  - Check staleness (> 1 hour?)          │
   │  - Fetch from /api/rate/latest          │
   │  - Fetch from /api/rate/history?days=N  │
   │  - Save to localStorage                │
   └─────────────────────────────────────────┘
          ▲
          │ (HTTP fetch, only when online + cache stale)
          ▼
   ┌─────────────────┐
   │  FastAPI Backend │
   │  /api/rate/*     │
   └─────────────────┘
```

---

## 9. Backend Changes Required

### 9.1 Static File Serving
Add to `app/main.py`:
- Mount `static/` directory via FastAPI's `StaticFiles`
- Update root route to serve `index.html` instead of redirect to `/docs`
- Swagger docs available at `/docs` (unchanged)

### 9.2 New API Endpoint (Optional Enhancement)
To support the hourly drill-down on the 7-day view, the existing
`/api/rate/history` endpoint already returns all records with timestamps.
The client-side JavaScript handles grouping by date and hour.
No new backend endpoints are needed.

### 9.3 CORS
Already configured as `allow_origins=["*"]` — no changes needed.

---

## 10. App Logo Specification

**Name:** نرخی دۆلار  
**Style:** Modern, flat, incorporates:
- Kurdish flag colors (red, white, green, sun)
- Dollar symbol ($)
- Clean enough to work as a small PWA icon (192×192px)

**Usage:**
- PWA icon on home screen
- Header of the app
- Splash screen on launch

---

## 11. Implementation Phases

### Phase G: Static Shell
1. Create `static/` directory structure
2. Build `index.html` with semantic layout
3. Build `style.css` with dark/light theme + RTL/LTR support
4. Generate app logo and icons

### Phase H: Core Features
5. Build `app.js` — main controller
6. Build `converter.js` — real-time converter
7. Build `cache.js` — localStorage manager with 1-hour staleness
8. Build `i18n.js` — Kurdish/English translation system
9. Wire up rate display with cached data

### Phase I: Charts
10. Integrate Chart.js (CDN)
11. Build `chart.js` — today's hourly chart
12. Build history tabs (7D/30D/90D)
13. Build 7-day hourly drill-down
14. Adaptive market hours (no hardcoded times)

### Phase J: PWA & Polish
15. Build `sw.js` — service worker with cache strategies
16. Build `manifest.json` — PWA manifest
17. Generate icons (192px, 512px)
18. Update `app/main.py` to serve static files
19. Final testing: offline, install, convert, charts
20. Deploy to PythonAnywhere

---

## 12. Acceptance Criteria

| # | Criteria | How to verify |
|---|---------|---------------|
| 1 | App loads in < 1 second on second visit | Chrome DevTools → Performance |
| 2 | Rate visible immediately on open | Visual check |
| 3 | Converter updates as you type | Type "50" → IQD shows instantly |
| 4 | Swap button works | Click swap → inputs reverse |
| 5 | Today's chart shows hourly data | Visual check during market hours |
| 6 | Chart adapts to actual data hours | No hardcoded 10AM–4PM |
| 7 | 7D/30D/90D tabs switch chart | Click each tab |
| 8 | 7D hourly drill-down works | Tap a day → hourly chart appears |
| 9 | Kurdish↔English toggle works | Toggle → all text changes, RTL flips |
| 10 | Dark/light theme follows system | Change phone setting → app follows |
| 11 | Works offline after first visit | Airplane mode → app loads + converts |
| 12 | Stale data shows warning banner | Offline for 2 hours → banner appears |
| 13 | Installable as PWA | "Add to Home Screen" prompt works |
| 14 | Opens full-screen (no browser bar) | Launch from home screen icon |
