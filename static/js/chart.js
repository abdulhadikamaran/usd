/**
 * chart.js — Chart rendering for today's hourly and history tabs
 * Uses inline SVG (matching the design files) for lightweight rendering
 */

import { getCachedHistory, setCachedHistory } from "./cache.js";
import { t } from "./i18n.js";

const API_BASE = "/api";

// ── Today's hourly chart ─────────────────────────────────────────────

export async function renderTodayChart() {
    const container = document.getElementById("today-chart");
    const labelContainer = document.getElementById("today-labels");
    const rateDisplay = document.getElementById("today-rate");
    const changeDisplay = document.getElementById("today-change");

    if (!container) return;

    try {
        const res = await fetch(`${API_BASE}/rate/history?days=1`);
        if (!res.ok) throw new Error("API error");
        const data = await res.json();

        if (!data.rates || data.rates.length === 0) {
            container.innerHTML = `<p class="text-center text-slate-400 py-8">${t("no_data")}</p>`;
            return;
        }

        // Group by hour
        const hourly = groupByHour(data.rates);
        const hours = Object.keys(hourly).sort();

        if (hours.length === 0) {
            container.innerHTML = `<p class="text-center text-slate-400 py-8">${t("no_data")}</p>`;
            return;
        }

        const values = hours.map((h) => hourly[h]);
        const min = Math.min(...values);
        const max = Math.max(...values);
        const range = max - min || 1;

        // Update rate display
        const latest = values[values.length - 1];
        const first = values[0];
        const diff = latest - first;

        if (rateDisplay) rateDisplay.textContent = latest.toLocaleString();
        if (changeDisplay) {
            const pct = ((diff / first) * 100).toFixed(2);
            const sign = diff >= 0 ? "+" : "";
            changeDisplay.textContent = `${sign}${pct}%`;
            changeDisplay.className = changeDisplay.className.replace(
                /text-(green|red)-500/g,
                ""
            );
            changeDisplay.classList.add(diff >= 0 ? "text-green-500" : "text-red-500");
            // Update background
            changeDisplay.className = changeDisplay.className.replace(
                /bg-(green|red)-500\/10/g,
                ""
            );
            changeDisplay.classList.add(
                diff >= 0 ? "bg-green-500/10" : "bg-red-500/10"
            );
        }

        // Build SVG path
        const width = 300;
        const height = 120;
        const padding = 10;
        const points = values.map((v, i) => {
            const x = values.length === 1 ? width / 2 : (i / (values.length - 1)) * width;
            const y = padding + ((max - v) / range) * (height - 2 * padding);
            return { x, y };
        });

        const pathD = buildSmoothPath(points);
        const fillD = `${pathD} V${height} H0 Z`;
        const lastP = points[points.length - 1];

        const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        const color = isDark ? "#f0b429" : "#2563eb";
        const gradId = "gradientToday";

        container.innerHTML = `
      <svg class="w-full h-full overflow-visible" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.2"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <path d="${fillD}" fill="url(#${gradId})"/>
        <path d="${pathD}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="${lastP.x}" cy="${lastP.y}" r="4" fill="${color}" stroke="${isDark ? "#1a242e" : "#ffffff"}" stroke-width="2"/>
      </svg>
    `;

        // Labels
        if (labelContainer) {
            const labelHours =
                hours.length <= 6
                    ? hours
                    : hours.filter(
                        (_, i) => i === 0 || i === hours.length - 1 || i % Math.ceil(hours.length / 4) === 0
                    );
            labelContainer.innerHTML = labelHours
                .map((h) => `<span>${h}:00</span>`)
                .join("");
        }
    } catch (err) {
        console.warn("Today chart error:", err);
        if (container)
            container.innerHTML = `<p class="text-center text-slate-400 py-8">${t("no_data")}</p>`;
    }
}

// ── History chart ────────────────────────────────────────────────────

let currentHistoryDays = 7;

export async function renderHistoryChart(days = 7) {
    currentHistoryDays = days;
    const container = document.getElementById("history-chart");
    const labelContainer = document.getElementById("history-labels");
    const highEl = document.getElementById("history-high");
    const lowEl = document.getElementById("history-low");

    if (!container) return;

    try {
        // Try cache first
        let rates = getCachedHistory(days);

        if (!rates) {
            const res = await fetch(`${API_BASE}/rate/history?days=${days}`);
            if (!res.ok) throw new Error("API error");
            const data = await res.json();
            rates = data.rates || [];
            setCachedHistory(days, rates);
        }

        if (rates.length === 0) {
            container.innerHTML = `<p class="text-center text-slate-400 py-8">${t("no_data")}</p>`;
            return;
        }

        // Group by day
        const daily = groupByDay(rates);
        const days_keys = Object.keys(daily).sort();
        const values = days_keys.map((d) => daily[d]);

        const min = Math.min(...values);
        const max = Math.max(...values);
        const range = max - min || 1;

        if (highEl) highEl.textContent = max.toLocaleString();
        if (lowEl) lowEl.textContent = min.toLocaleString();

        // Build SVG
        const width = 300;
        const height = 150;
        const padding = 10;

        const points = values.map((v, i) => {
            const x = values.length === 1 ? width / 2 : (i / (values.length - 1)) * width;
            const y = padding + ((max - v) / range) * (height - 2 * padding);
            return { x, y };
        });

        const pathD = buildSmoothPath(points);
        const lastP = points[points.length - 1];

        const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        const color = isDark ? "#f0b429" : "#2563eb";

        // Grid lines
        const gridLines = [0.25, 0.5, 0.75].map(
            (f) =>
                `<line x1="0" y1="${f * height}" x2="${width}" y2="${f * height}" stroke="${isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)"}" stroke-dasharray="4,4"/>`
        ).join("");

        // Data point circles
        const circles = points
            .map(
                (p, i) =>
                    `<circle cx="${p.x}" cy="${p.y}" r="${i === points.length - 1 ? 5 : 3}" fill="${i === points.length - 1 ? color : (isDark ? "#1a242e" : "#ffffff")}" stroke="${color}" stroke-width="2"/>`
            )
            .join("");

        container.innerHTML = `
      <svg class="w-full h-full overflow-visible" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
        ${gridLines}
        <path d="${pathD}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round"/>
        ${circles}
      </svg>
    `;

        // Day labels
        if (labelContainer) {
            const dayNames = [t("sun"), t("mon"), t("tue"), t("wed"), t("thu"), t("fri"), t("sat")];
            let labels;
            if (days <= 7) {
                labels = days_keys.map((d) => {
                    const date = new Date(d);
                    return dayNames[date.getDay()];
                });
            } else {
                // Show date labels for 30D/90D
                const step = Math.ceil(days_keys.length / 6);
                labels = days_keys
                    .filter((_, i) => i % step === 0 || i === days_keys.length - 1)
                    .map((d) => {
                        const date = new Date(d);
                        return `${date.getMonth() + 1}/${date.getDate()}`;
                    });
            }
            labelContainer.innerHTML = labels.map((l) => `<span>${l}</span>`).join("");
        }
    } catch (err) {
        console.warn("History chart error:", err);
        if (container)
            container.innerHTML = `<p class="text-center text-slate-400 py-8">${t("no_data")}</p>`;
    }
}

export function initHistoryTabs() {
    const tabs = document.querySelectorAll("[data-history-tab]");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const days = parseInt(tab.dataset.historyTab);
            // Update active style
            tabs.forEach((t) => {
                t.classList.remove(
                    "bg-white",
                    "dark:bg-primary",
                    "text-slate-900",
                    "dark:text-background-dark",
                    "shadow-sm"
                );
                t.classList.add("text-slate-500", "dark:text-text-muted");
            });
            tab.classList.add(
                "bg-white",
                "dark:bg-primary",
                "text-slate-900",
                "dark:text-background-dark",
                "shadow-sm"
            );
            tab.classList.remove("text-slate-500", "dark:text-text-muted");
            renderHistoryChart(days);
        });
    });
}

// ── Helpers ──────────────────────────────────────────────────────────

function groupByHour(rates) {
    const hourly = {};
    // rates are newest-first, reverse to process oldest first
    for (const r of [...rates].reverse()) {
        const date = new Date(r.last_updated);
        const h = date.getHours();
        hourly[h] = r.average; // last value per hour wins
    }
    return hourly;
}

function groupByDay(rates) {
    const daily = {};
    const counts = {};
    for (const r of rates) {
        const d = r.last_updated.split("T")[0];
        if (!daily[d]) {
            daily[d] = 0;
            counts[d] = 0;
        }
        daily[d] += r.average;
        counts[d]++;
    }
    // Average per day
    for (const d in daily) {
        daily[d] = Math.round(daily[d] / counts[d]);
    }
    return daily;
}

function buildSmoothPath(points) {
    if (points.length === 0) return "";
    if (points.length === 1) return `M${points[0].x},${points[0].y}`;

    let d = `M${points[0].x},${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1];
        const curr = points[i];
        const cpx = (prev.x + curr.x) / 2;
        d += ` C${cpx},${prev.y} ${cpx},${curr.y} ${curr.x},${curr.y}`;
    }
    return d;
}
