/**
 * converter.js — Real-time USD ↔ IQD converter
 * Pure client-side math using cached rate. No API calls per keystroke.
 */

let currentRate = 0; // average IQD per $100
let isSwapped = false; // false = USD→IQD, true = IQD→USD

export function setRate(avg) {
    currentRate = avg;
}

export function getRate() {
    return currentRate;
}

export function init(rate) {
    currentRate = rate;

    const usdInput = document.getElementById("usd-input");
    const iqdInput = document.getElementById("iqd-input");
    const swapBtn = document.getElementById("swap-btn");

    if (!usdInput || !iqdInput) return;

    // Set initial values
    usdInput.value = "100";
    updateConversion();

    // Real-time on every keystroke
    usdInput.addEventListener("input", () => {
        if (!isSwapped) updateConversion();
    });

    iqdInput.addEventListener("input", () => {
        if (isSwapped) updateReverseConversion();
    });

    // Swap button
    if (swapBtn) {
        swapBtn.addEventListener("click", () => {
            isSwapped = !isSwapped;
            const icon = swapBtn.querySelector(".material-symbols-outlined");
            if (icon) {
                icon.style.transition = "transform 0.3s ease";
                icon.style.transform = isSwapped ? "rotate(180deg)" : "rotate(0deg)";
            }

            // Swap input editability
            if (isSwapped) {
                usdInput.readOnly = true;
                iqdInput.readOnly = false;
                iqdInput.type = "number";
                iqdInput.classList.remove("pointer-events-none");
                usdInput.classList.add("pointer-events-none");
                // Convert current IQD back to USD
                updateReverseConversion();
            } else {
                usdInput.readOnly = false;
                iqdInput.readOnly = true;
                iqdInput.type = "text";
                iqdInput.classList.add("pointer-events-none");
                usdInput.classList.remove("pointer-events-none");
                updateConversion();
            }
        });
    }
}

function updateConversion() {
    const usdInput = document.getElementById("usd-input");
    const iqdInput = document.getElementById("iqd-input");
    if (!usdInput || !iqdInput || !currentRate) return;

    const usd = parseFloat(usdInput.value) || 0;
    const iqd = usd * (currentRate / 100);
    iqdInput.value = formatNumber(Math.round(iqd));
}

function updateReverseConversion() {
    const usdInput = document.getElementById("usd-input");
    const iqdInput = document.getElementById("iqd-input");
    if (!usdInput || !iqdInput || !currentRate) return;

    const iqd = parseFloat(iqdInput.value) || 0;
    const usd = iqd / (currentRate / 100);
    usdInput.value = usd.toFixed(2);
}

export function formatNumber(num) {
    return num.toLocaleString("en-US");
}
