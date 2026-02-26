/**
 * cache.js — localStorage rate cache with 1-hour staleness
 */

const CACHE_KEY = "usd_rate_cache";
const STALE_MS = 60 * 60 * 1000; // 1 hour

export function getCachedRate() {
    try {
        const raw = localStorage.getItem(CACHE_KEY);
        if (!raw) return null;
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

export function setCachedRate(data) {
    try {
        const cache = {
            ...data,
            cached_at: Date.now(),
        };
        localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
    } catch {
        // localStorage full or unavailable
    }
}

export function isCacheStale() {
    const cache = getCachedRate();
    if (!cache || !cache.cached_at) return true;
    return Date.now() - cache.cached_at > STALE_MS;
}

export function getCacheAge() {
    const cache = getCachedRate();
    if (!cache || !cache.cached_at) return null;
    return Date.now() - cache.cached_at;
}

// History cache (per tab: 7, 30, 90)
export function getCachedHistory(days) {
    try {
        const raw = localStorage.getItem(`usd_history_${days}`);
        if (!raw) return null;
        const data = JSON.parse(raw);
        if (Date.now() - data.cached_at > STALE_MS) return null;
        return data.rates;
    } catch {
        return null;
    }
}

export function setCachedHistory(days, rates) {
    try {
        localStorage.setItem(
            `usd_history_${days}`,
            JSON.stringify({ rates, cached_at: Date.now() })
        );
    } catch { }
}
