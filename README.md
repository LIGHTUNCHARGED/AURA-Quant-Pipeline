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
'''

