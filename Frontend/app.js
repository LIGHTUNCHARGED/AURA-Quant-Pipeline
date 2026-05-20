const API_BASE = "https://aura-quant-pipeline.onrender.com";
let pollInterval = null; // Holds the timer for background polling

const state = {
    rows: [],
    sortKey: "Alpha_Weight_%",
    sortDirection: "desc",
    query: ""
};

document.addEventListener("DOMContentLoaded", () => {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: "0px 0px -50px 0px" });

    document.querySelectorAll('.info-card, .theory-topic, .section-heading, .cta-band').forEach((el, index) => {
        el.classList.add('animate-on-scroll');


        if (el.classList.contains('info-card')) {
            el.classList.add(`delay-${(index % 5) + 1}`);
        }

        observer.observe(el);
    });

    if (document.body.dataset.page !== "scanner") {
        return;
    }

    bindScannerControls();

    const params = new URLSearchParams(window.location.search);
    if (params.get("scan") === "live") {
        fetchData();
    }
});

function bindScannerControls() {
    const refreshBtn = document.getElementById("refresh-btn");
    const exportBtn = document.getElementById("export-btn");
    const searchInput = document.getElementById("ticker-search");
    const headers = document.querySelectorAll("#screener-table th[data-sort]");

    refreshBtn?.addEventListener("click", fetchData);
    exportBtn?.addEventListener("click", exportToCSV);
    searchInput?.addEventListener("input", event => {
        state.query = event.target.value.trim().toLowerCase();
        renderRows();
    });

    headers.forEach(header => {
        header.addEventListener("click", () => {
            const nextKey = header.dataset.sort;
            if (state.sortKey === nextKey) {
                state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
            } else {
                state.sortKey = nextKey;
                state.sortDirection = nextKey === "Ticker" ? "asc" : "desc";
            }
            renderRows();
        });
    });

    // Fetch initial status on load
    fetch(`${API_BASE}/status`)
        .then(res => res.json())
        .then(statusData => {
            const timeEl = document.getElementById("last-updated-time");
            if (timeEl && statusData.last_updated) timeEl.textContent = statusData.last_updated;
        })
        .catch(err => console.error("Initial status check failed:", err));
}

// 1.The Trigger
async function fetchData() {
    const refreshBtn = document.getElementById("refresh-btn");
    const tableBody = document.getElementById("screener-body");

    setStatus("loading", '<span class="spinner" aria-hidden="true"></span>Checking cache and engine status...');
    if (refreshBtn) {
        refreshBtn.disabled = true;
    }
    if (tableBody) {
        tableBody.innerHTML = '<tr class="empty-row"><td colspan="8">Connecting to backend pipeline...</td></tr>';
    }

    try {
        const response = await fetch(`${API_BASE}/trigger-scan`, { method: "POST" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.status === "cached") {
            // CACHE HIT: Skip waiting and load instantly
            setStatus("loading", `<span class="spinner" aria-hidden="true"></span>${data.message} Loading...`);

            // Render the timestamp received from the cache data
            const timeEl = document.getElementById("last-updated-time");
            if (timeEl && data.last_updated) timeEl.textContent = data.last_updated;

            await fetchFinalResults();
        } else {
            // CACHE MISS: Start polling the status every 5 seconds
            setStatus("loading", `<span class="spinner" aria-hidden="true"></span>${data.message}`);

            // Clear any existing intervals just in case
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(checkScanStatus, 5000);
        }
    } catch (error) {
        console.error("Trigger API error:", error);
        state.rows = [];
        setStatus("error", "Could not connect to the Quant API. Start the FastAPI backend on port 8000 and run the scan again.");
        renderRows("The API is not reachable yet.");
        if (refreshBtn) refreshBtn.disabled = false;
    }
}

// 2. The Poller
async function checkScanStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (!response.ok) return;

        const statusData = await response.json();

        // Update the timestamp card on the fly if it is available
        const timeEl = document.getElementById("last-updated-time");
        if (timeEl && statusData.last_updated) {
            timeEl.textContent = statusData.last_updated;
        }

        if (statusData.is_scanning) {
            setStatus("loading", `<span class="spinner" aria-hidden="true"></span>${statusData.message}`);
        } else {
            clearInterval(pollInterval);
            pollInterval = null;
            await fetchFinalResults();
        }
    } catch (error) {
        console.error("Status check error:", error);
    }
}

// 3. The Fetcher
async function fetchFinalResults() {
    const statusEl = document.getElementById("status-message");
    const refreshBtn = document.getElementById("refresh-btn");

    try {
        const response = await fetch(`${API_BASE}/screener`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const payload = await response.json();
        const rows = Array.isArray(payload.data) ? payload.data : [];
        state.rows = rows;

        const exportBtn = document.getElementById("export-btn");
        if (exportBtn) exportBtn.disabled = rows.length === 0;

        if (payload.status === "no_trades" || rows.length === 0) {
            setStatus("warning", "Scan complete. No stocks passed the strict quantitative filters today.");
            renderRows();
            return;
        }

        setStatus("success", `${rows.length} stock(s) passed every filter. Results are sorted by allocation weight.`);
        renderRows();
    } catch (error) {
        console.error("Final fetch error:", error);
        state.rows = [];
        setStatus("error", "Error loading the final scan results from the API.");
        renderRows("Failed to load pipeline data.");
    } finally {
        if (refreshBtn) {
            refreshBtn.disabled = false;
        }
        if (statusEl) {
            statusEl.setAttribute("aria-live", "polite");
        }
    }
}

function renderRows(emptyMessage = "No matching tickers found.") {
    const tableBody = document.getElementById("screener-body");
    if (!tableBody) {
        return;
    }

    const visibleRows = getVisibleRows();
    if (visibleRows.length === 0) {
        tableBody.innerHTML = `<tr class="empty-row"><td colspan="8">${emptyMessage}</td></tr>`;
        return;
    }

    tableBody.innerHTML = visibleRows.map((stock, index) => `
        <tr style="animation-delay: ${index * 35}ms"> <td class="ticker">${escapeHtml(stock.Ticker)}</td>
            <td class="neutral">${formatCurrency(stock.Close_Price)}</td>
            <td class="${numberClass(stock.Alpha)}">${formatNumber(stock.Alpha, 5)}</td>
            <td class="neutral">${formatNumber(stock.Beta, 2)}</td>
            <td class="${numberClass(stock.Log_RS)}">${formatNumber(stock.Log_RS, 4)}</td>
            <td class="highlight">${formatPercent(stock["Alpha_Weight_%"])}</td>
            <td class="highlight">${formatPercent(stock["Beta_Weight_%"])}</td>
            <td class="stop-loss">${formatCurrency(stock.Stop_Loss)}</td>
        </tr>
    `).join("");
}

function getVisibleRows() {
    const filteredRows = state.rows.filter(stock => {
        if (!state.query) {
            return true;
        }
        return String(stock.Ticker || "").toLowerCase().includes(state.query);
    });

    return filteredRows.sort((a, b) => {
        const aValue = a[state.sortKey];
        const bValue = b[state.sortKey];
        const direction = state.sortDirection === "asc" ? 1 : -1;

        if (state.sortKey === "Ticker") {
            return String(aValue || "").localeCompare(String(bValue || "")) * direction;
        }

        return (toNumber(aValue) - toNumber(bValue)) * direction;
    });
}

function setStatus(type, message) {
    const statusEl = document.getElementById("status-message");
    if (!statusEl) {
        return;
    }
    statusEl.className = `status-box ${type}`;
    statusEl.innerHTML = message;
}

function toNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

function formatNumber(value, digits) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(digits) : "-";
}

function formatCurrency(value) {
    const number = Number(value);
    return Number.isFinite(number) ? `Rs. ${number.toFixed(2)}` : "-";
}

function formatPercent(value) {
    const number = Number(value);
    return Number.isFinite(number) ? `${number.toFixed(2)}%` : "-";
}

function numberClass(value) {
    return Number(value) >= 0 ? "positive" : "negative";
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function exportToCSV() {
    const visibleRows = getVisibleRows();
    if (visibleRows.length === 0) return;

    const headers = [
        "Ticker",
        "Close Price",
        "Alpha",
        "Beta",
        "Log RS",
        "Alpha Weight %",
        "Beta Weight %",
        "ATR Stop Loss"
    ];

    const csvRows = [
        headers.join(","),
        ...visibleRows.map(stock => {
            return [
                stock.Ticker,
                toNumber(stock.Close_Price).toFixed(2),
                toNumber(stock.Alpha).toFixed(5),
                toNumber(stock.Beta).toFixed(2),
                toNumber(stock.Log_RS).toFixed(4),
                toNumber(stock["Alpha_Weight_%"]).toFixed(2),
                toNumber(stock["Beta_Weight_%"]).toFixed(2),
                toNumber(stock.Stop_Loss).toFixed(2)
            ].join(",");
        })
    ];

    const csvString = csvRows.join("\n");
    const blob = new Blob([csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const downloadLink = document.createElement("a");
    downloadLink.setAttribute("href", url);

    const dateStr = new Date().toISOString().split("T")[0];
    downloadLink.setAttribute("download", `Quant_Scan_${dateStr}.csv`);

    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    URL.revokeObjectURL(url);
}
