/**
 * app.js — Main application controller
 * Initializes all modules, fetches data, manages page navigation
 */

import { t, getLang, setLang, toggleLang } from "./i18n.js";
import {
    getCachedRate,
    setCachedRate,
    isCacheStale,
    getCacheAge,
} from "./cache.js";
import { init as initConverter, setRate, formatNumber } from "./converter.js";
import {
    renderTodayChart,
    renderHistoryChart,
    initHistoryTabs,
} from "./chart.js";

const API_BASE = "/api";

// ── State ────────────────────────────────────────────────────────────

let currentPage = "home"; // 'home' or 'analytics'

// ── Boot ─────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
    // Apply saved language
    const lang = getLang();
    setLang(lang);

    // Show cached rate instantly
    const cached = getCachedRate();
    if (cached) {
        displayRate(cached);
        initConverter(cached.average);
    }

    // Setup navigation
    setupNavigation();
    setupLangToggle();

    // Fetch fresh data if stale
    if (isCacheStale()) {
        await fetchAndDisplayRate();
    }

    // Render charts if on analytics page
    // (deferred until user navigates there)

    // Background refresh every 60min
    setInterval(async () => {
        if (isCacheStale()) {
            await fetchAndDisplayRate();
        }
    }, 60 * 60 * 1000);

    // Refresh on tab focus if stale
    document.addEventListener("visibilitychange", async () => {
        if (!document.hidden && isCacheStale()) {
            await fetchAndDisplayRate();
        }
    });

    // Apply translations
    applyTranslations();
});

// ── API Fetch ────────────────────────────────────────────────────────

async function fetchAndDisplayRate() {
    try {
        const res = await fetch(`${API_BASE}/rate/latest`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // Calculate diff from previous
        const prev = getCachedRate();
        const rateData = {
            average: data.average,
            penzi: data.penzi,
            sur: data.sur,
            last_updated: data.last_updated,
            previous_average: prev ? prev.average : data.average,
        };

        setCachedRate(rateData);
        displayRate(rateData);
        setRate(data.average);
        initConverter(data.average);
        hideOfflineBanner();
    } catch (err) {
        console.warn("Failed to fetch rate:", err);
        showOfflineBanner();
    }
}

// ── Display ──────────────────────────────────────────────────────────

function displayRate(data) {
    const rateEl = document.getElementById("main-rate");
    const perEl = document.getElementById("rate-per-100");
    const diffEl = document.getElementById("rate-diff");
    const diffIcon = document.getElementById("rate-diff-icon");
    const updatedEl = document.getElementById("rate-updated");

    if (rateEl) {
        rateEl.textContent = formatNumber(data.average);
    }

    if (perEl) {
        perEl.textContent = t("per_100");
    }

    // Direction indicator
    if (diffEl && data.previous_average) {
        const diff = data.average - data.previous_average;
        const sign = diff >= 0 ? "+" : "";
        diffEl.textContent = `${sign}${formatNumber(diff)}`;

        // Remove old color classes
        const parent = diffEl.closest("[data-diff-container]");
        if (parent) {
            parent.classList.remove(
                "text-green-500",
                "bg-green-500/10",
                "border-green-500/20",
                "text-red-500",
                "bg-red-500/10",
                "border-red-500/20"
            );
            if (diff >= 0) {
                parent.classList.add("text-green-500", "bg-green-500/10", "border-green-500/20");
            } else {
                parent.classList.add("text-red-500", "bg-red-500/10", "border-red-500/20");
            }
        }

        if (diffIcon) {
            diffIcon.textContent = diff >= 0 ? "trending_up" : "trending_down";
        }
    }

    // Updated time
    if (updatedEl && data.last_updated) {
        const updated = new Date(data.last_updated);
        const mins = Math.floor((Date.now() - updated.getTime()) / 60000);
        if (mins < 1) {
            updatedEl.textContent = t("updated_just");
        } else {
            updatedEl.textContent = t("updated_ago").replace("{n}", mins);
        }
    }
}

// ── Navigation ───────────────────────────────────────────────────────

function setupNavigation() {
    const navHome = document.getElementById("nav-home");
    const navAnalytics = document.getElementById("nav-analytics");

    const homePage = document.getElementById("page-home");
    const analyticsPage = document.getElementById("page-analytics");

    if (navHome) {
        navHome.addEventListener("click", (e) => {
            e.preventDefault();
            showPage("home");
        });
    }

    if (navAnalytics) {
        navAnalytics.addEventListener("click", (e) => {
            e.preventDefault();
            showPage("analytics");
        });
    }

    // Back button on analytics
    const backBtn = document.getElementById("analytics-back");
    if (backBtn) {
        backBtn.addEventListener("click", () => showPage("home"));
    }
}

function showPage(page) {
    currentPage = page;
    const homePage = document.getElementById("page-home");
    const analyticsPage = document.getElementById("page-analytics");
    const navHome = document.getElementById("nav-home");
    const navAnalytics = document.getElementById("nav-analytics");

    if (page === "home") {
        homePage?.classList.remove("hidden");
        analyticsPage?.classList.add("hidden");
        // Update nav active states
        setNavActive(navHome, true);
        setNavActive(navAnalytics, false);
    } else {
        homePage?.classList.add("hidden");
        analyticsPage?.classList.remove("hidden");
        setNavActive(navHome, false);
        setNavActive(navAnalytics, true);
        // Load charts
        renderTodayChart();
        renderHistoryChart(7);
        initHistoryTabs();
    }
}

function setNavActive(el, active) {
    if (!el) return;
    const icon = el.querySelector(".material-symbols-outlined");
    const label = el.querySelector(":scope > span:last-child");

    if (active) {
        el.classList.remove("text-slate-400", "dark:text-slate-500");
        el.classList.add("text-primary");
        if (icon) icon.style.fontVariationSettings = "'FILL' 1";
    } else {
        el.classList.remove("text-primary");
        el.classList.add("text-slate-400", "dark:text-slate-500");
        if (icon) icon.style.fontVariationSettings = "'FILL' 0";
    }
}

// ── Language Toggle ──────────────────────────────────────────────────

function setupLangToggle() {
    const btn = document.getElementById("lang-toggle");
    if (!btn) return;

    btn.addEventListener("click", () => {
        toggleLang();
        applyTranslations();
    });
}

function applyTranslations() {
    // Update all elements with data-i18n attribute
    document.querySelectorAll("[data-i18n]").forEach((el) => {
        el.textContent = t(el.dataset.i18n);
    });

    // Update lang toggle flag icon
    const langFlag = document.getElementById("lang-flag");
    if (langFlag) {
        // Show the flag of the language you'll switch TO
        // Kurdish active → show US flag (tap to switch to English)
        // English active → show Kurdish flag (tap to switch to Kurdish)
        langFlag.className = getLang() === "ku" ? "flag-us" : "flag-kurd";
    }

    // Re-display rate with new translations
    const cached = getCachedRate();
    if (cached) displayRate(cached);
}

// ── Offline Banner ───────────────────────────────────────────────────

function showOfflineBanner() {
    let banner = document.getElementById("offline-banner");
    if (!banner) {
        banner = document.createElement("div");
        banner.id = "offline-banner";
        banner.className =
            "fixed top-0 left-0 right-0 z-[100] bg-amber-500/90 text-black text-center text-sm py-2 px-4 font-medium backdrop-blur-md transition-transform";
        document.body.prepend(banner);
    }

    const age = getCacheAge();
    let timeStr = "";
    if (age) {
        const hrs = Math.floor(age / 3600000);
        const mins = Math.floor((age % 3600000) / 60000);
        timeStr = hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
    }

    banner.textContent = t("offline_banner").replace("{time}", timeStr);
    banner.style.transform = "translateY(0)";
}

function hideOfflineBanner() {
    const banner = document.getElementById("offline-banner");
    if (banner) {
        banner.style.transform = "translateY(-100%)";
        setTimeout(() => banner.remove(), 300);
    }
}

// ── Service Worker Registration ──────────────────────────────────────

if ("serviceWorker" in navigator) {
    navigator.serviceWorker
        .register("/static/sw.js")
        .then(() => console.log("SW registered"))
        .catch((err) => console.warn("SW failed:", err));
}
