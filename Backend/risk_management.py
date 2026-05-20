import pandas as pd
import numpy as np


def calculate_atr_stop(high_series, low_series, close_series, target_ticker, window=14, k=2.0):
    """
    Calculates the Average True Range (ATR) and the dynamic trailing stop loss.
    Stop = EntryPrice - (k * ATR)
    """
    print(f"Calculating {window}-day ATR Stop Loss for {target_ticker} (k={k})...")

    # 1. Calculate the three True Range components
    tr1 = high_series - low_series
    tr2 = (high_series - close_series.shift(1)).abs()
    tr3 = (low_series - close_series.shift(1)).abs()

    # 2. Find the maximum of the three to get the True Range (TR)
    # pd.concat merges them column-wise, and .max(axis=1) finds the highest value per day
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # 3. Calculate ATR (Using Wilder's Smoothing for accuracy)
    atr = tr.ewm(alpha=1 / window, adjust=False).mean()

    # 4. Calculate the Stop Loss Level
    # In a live system, you use your actual fill price.
    # For backtesting/signals, we calculate it relative to the current Close price.
    stop_loss_level = close_series - (k * atr)

    # Combine into a DataFrame for analysis
    atr_df = pd.DataFrame({
        f'{target_ticker}_Close': close_series,
        f'{target_ticker}_ATR': atr,
        f'{target_ticker}_Stop_Level': stop_loss_level
    })

    return atr_df.dropna()


if __name__ == "__main__":
    import yfinance as yf

    # 1. Quick Data Fetch (Extracting High, Low, Close)
    target_stock = 'RELIANCE.NS'
    print("Fetching High/Low/Close data for ATR test...")
    data = yf.download([target_stock], start='2024-01-01', end='2026-05-20', progress=False)

    high_prices = data['High'][target_stock]
    low_prices = data['Low'][target_stock]
    close_prices = data['Close'][target_stock]

    # 2. Calculate ATR Stop Loss (Using a k=2 multiplier)
    risk_metrics = calculate_atr_stop(
        high_series=high_prices,
        low_series=low_prices,
        close_series=close_prices,
        target_ticker=target_stock,
        window=14,
        k=2.0
    )

    print(f"\n--- Dynamic ATR Stop Loss for {target_stock} ---")
    print(risk_metrics.tail())