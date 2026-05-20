# AURA-Quant-Pipeline 📊🏦
### Automated Relative Strength, Alpha-Beta Estimation & Risk Sizing Engine

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-Vanilla%20JS%20%2F%20CSS-orange.svg)](https://developer.mozilla.org/en-US/)

An automated end-to-end quantitative trading pipeline designed to identify, rank, and dynamically allocate capital to equities showing structurally significant momentum. The engine streams tick data across the Nifty universe, separates market tailwinds from stock-specific skill using rolling OLS regressions, filters statistical noise via Z-scores, and calculates execution risk metrics in a decoupled web architecture.

---

## 🏢 System Architecture

The pipeline decouples resource-heavy mathematical computations from the client network layer to bypass web timeout limits when processing large equity universes.

```text
[ Raw Market Ingestion (yfinance) ] 
               │
               ▼
[ Quantitative Math Engine (main.py) ] ──(Generates Snapshots)──► [ latest_scan.json ]
               │                                                          ▲
               ▼                                                          │ (Direct I/O File Read)
[ Asynchronous Background Worker ]                                        │
               │                                                          │
   (Pings Status / Trigger)                                               │
               │                                                          │
               ▼                                                          │
[ FastAPI Production Gateway (api.py) ] ◄─────────────────────────────────┘
               ▲
               │ (Non-blocking Async Polling)
               ▼
[ Vanilla CSS/JS Dashboard (UI) ] ──► [ Client CSV Export Engine ]
```
## 🧪 Core Quantitative Methodology

### 1. Data Ingestion & Additive Continuity
Raw Open-High-Low-Close-Volume (OHLCV) datasets are ingested sequentially. To eliminate compounding scale asymmetry inherent in standard arithmetic percentage changes, returns are transformed into logarithmic time-series:

$$
r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)
$$

### 2. Idiosyncratic Alpha vs. Beta Systematic Separation
To ensure the model captures genuine momentum rather than broader market buoyancy, the script evaluates a rolling linear regression model of the asset against the benchmark index ($^N\text{SEI}$):

$$
R_{\text{stock}} = \alpha + \beta R_{\text{Nifty}} + \epsilon
$$

* **Beta ($\beta$):** Represents systematic risk sensitivity (covariance of asset and market divided by market variance).
* **Alpha ($\alpha$):** Represents true, isolated manager/asset outperformance independent of index behavior.

### 3. Statistical Significance Gating
Relative Strength (Log RS) is tracked as a linear difference of cumulative logarithmic distributions. To pass the core filter, an asset's Log RS must deviate from its historical rolling mean ($\mu$) by a minimum standard deviation threshold ($\sigma$), eliminating short-term noise:

$$
Z = \frac{\text{RS} - \mu_{\text{RS}}}{\sigma_{\text{RS}}} > 1.5\sigma
$$

### 4. Risk-Adjusted Allocation Sizing
Surviving candidates are passed to a portfolio optimization engine. Capital allocation is scaled proportionally to its generated Alpha density, while being heavily penalized by systematic market risk exposure (Beta variance profile).

### 5. Dynamic Trailing Drawdown Controls
Risk management is asset-agnostic and volatility-adaptive. Instead of static percentage stops, a multi-period Average True Range (ATR) algorithm estimates active intraday expansion boundaries, mapping trailing stop losses to the equity's natural noise floor:

$$
\text{True Range (TR)} = \max\left[(H - L), |H - C_{\text{prev}}|, |L - C_{\text{prev}}|\right]
$$

$$
\text{Stop Level} = \text{Close} - (2 \times \text{ATR}_{14})
$$

---

## 🛠️ Tech Stack & Optimization Engineering
* **Backend Mathematical Engine:** Python 3.13, Pandas, NumPy, yfinance.
* **Server Architecture:** FastAPI running asynchronous background workers (`BackgroundTasks`) via Uvicorn.
* **Web Caching:** High-speed Time-to-Live (TTL) server-side cache window set to 30 minutes ($1800$ seconds) via dynamic file descriptor modification detection (`os.path.getmtime`).
* **Frontend Dashboard:** Vanilla HTML5, Vanilla JavaScript, CSS custom variables (Dark Slate Fintech Theme).
* **Data Serialization & Portability:** Native Client-side CSV parser processing data chunks straight into dynamic system Blob structures for direct download.

---

## 🚀 Installation & Local Deployment

### 1. Backend Initialization
Ensure your directory contains a verified list of active exchange assets inside `Symbols_NSE.txt`.

```bash
# Clone the repository
git clone [https://github.com/your-username/AURA-Quant-Pipeline.git](https://github.com/your-username/AURA-Quant-Pipeline.git)
cd AURA-Quant-Pipeline/Backend

# Install required dependencies
pip install -r requirements.txt

# Launch the FastAPI production server
uvicorn api:app --reload
