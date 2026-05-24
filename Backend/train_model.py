import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from pathlib import Path

from data_loader import fetch_and_preprocess
from indicators import calculate_rs, calculate_beta, calculate_alpha
from filters import calculate_rsi_filter
from risk_management import calculate_atr_stop
from ml_engine import train_and_save_model

BASE_DIR = Path(__file__).resolve().parent


def get_training_stocks():
    """Returns a curated list of liquid NSE stocks for model training."""
    return [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
        'HINDUNILVR.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'ITC.NS',
        'LT.NS', 'AXISBANK.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS', 'MARUTI.NS',
        'SUNPHARMA.NS', 'TITAN.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS', 'WIPRO.NS',
        'HCLTECH.NS', 'M&M.NS', 'TATAMOTORS.NS', 'TATASTEEL.NS', 'NTPC.NS',
        'POWERGRID.NS', 'ONGC.NS', 'JSWSTEEL.NS', 'ADANIENT.NS', 'ADANIPORTS.NS',
        'TECHM.NS', 'INDUSINDBK.NS', 'DIVISLAB.NS', 'DRREDDY.NS', 'CIPLA.NS',
        'BPCL.NS', 'COALINDIA.NS', 'GRASIM.NS', 'HEROMOTOCO.NS', 'EICHERMOT.NS',
        'BAJAJFINSV.NS', 'HDFCLIFE.NS', 'SBILIFE.NS', 'BRITANNIA.NS', 'APOLLOHOSP.NS',
        'TATACONSUM.NS', 'HINDALCO.NS', 'UPL.NS', 'SHREECEM.NS', 'PIDILITIND.NS',
    ]


def build_training_data(tickers, benchmark='^NSEI', start_date='2022-01-01', end_date=None):
    """
    Fetches historical data and computes indicators for each stock,
    returning a combined DataFrame with all ML features.
    """
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')

    print(f"=== BUILDING TRAINING DATA ===")
    print(f"Universe: {len(tickers)} stocks | Period: {start_date} to {end_date}")

    # Download all data at once
    print("Downloading historical data...")
    full_data = yf.download(
        tickers + [benchmark],
        start=start_date,
        end=end_date,
        group_by='ticker',
        threads=True,
        ignore_tz=True,
        progress=True
    )

    prices, volumes, log_returns = fetch_and_preprocess(full_data, benchmark)

    all_stock_data = []

    for stock in tickers:
        try:
            print(f"Processing {stock}...")

            # Skip if insufficient data
            if stock not in log_returns.columns or log_returns[stock].dropna().shape[0] < 120:
                print(f"  -> Insufficient data for {stock}. Skipping.")
                continue

            # Compute indicators
            rs_df = calculate_rs(log_returns, stock, benchmark)
            log_rs_series = rs_df[f'{stock}_Log_RS']

            beta_df = calculate_beta(log_returns, stock)
            beta_series = beta_df[f'{stock}_Beta']

            alpha_df = calculate_alpha(log_returns, beta_series, stock)

            price_series = prices[stock]

            rsi_df = calculate_rsi_filter(price_series, stock)

            # Get High/Low/Close for ATR
            if len(tickers) > 1:
                high_series = full_data[stock]['High']
                low_series = full_data[stock]['Low']
                close_series = full_data[stock]['Close']
            else:
                high_series = full_data['High']
                low_series = full_data['Low']
                close_series = full_data['Close']

            atr_df = calculate_atr_stop(
                high_series=high_series,
                low_series=low_series,
                close_series=close_series,
                target_ticker=stock
            )

            # Build per-stock DataFrame
            stock_df = pd.DataFrame({
                'Close': close_series,
                'ATR': atr_df[f'{stock}_ATR'],
                'Alpha': alpha_df[f'{stock}_Alpha'],
                'Beta': beta_series,
                'Log_RS': log_rs_series,
                'RSI': rsi_df[f'{stock}_RSI'],
            })

            # Compute 5-day forward return target per-stock (must be done before concatenation)
            stock_df['Future_5d_Close'] = stock_df['Close'].shift(-5)
            stock_df['Forward_Return'] = (stock_df['Future_5d_Close'] - stock_df['Close']) / stock_df['Close']
            stock_df['Target'] = np.where(stock_df['Forward_Return'] > 0, 1, 0)

            # Drop rows with NaN from rolling windows or forward shift
            stock_df = stock_df.dropna(subset=['Close', 'ATR', 'Alpha', 'Beta', 'Log_RS', 'RSI', 'Target'])

            if stock_df.shape[0] < 30:
                print(f"  -> Too few valid rows for {stock}. Skipping.")
                continue

            all_stock_data.append(stock_df)
            print(f"  -> {stock_df.shape[0]} samples collected.")

        except Exception as e:
            print(f"  -> Error processing {stock}: {e}")

    if not all_stock_data:
        raise ValueError("No valid training data could be constructed.")

    combined_df = pd.concat(all_stock_data, ignore_index=True)
    print(f"\nTotal training samples: {combined_df.shape[0]}")
    return combined_df


if __name__ == "__main__":
    # 1. Get training universe
    tickers = get_training_stocks()

    # 2. Build training data (2+ years of history for robust feature/target computation)
    training_df = build_training_data(tickers, start_date='2022-01-01')

    # 3. Extract features and pre-computed targets
    features = ['Alpha', 'Beta', 'Log_RS', 'RSI']
    training_df['Vol_Ratio'] = training_df['ATR'] / training_df['Close']
    features_with_vol = features + ['Vol_Ratio']

    X = training_df[features_with_vol]
    y = training_df['Target']

    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Target distribution:\n{y.value_counts(normalize=True)}")

    # 4. Train and save the model
    train_and_save_model(X, y, filename=BASE_DIR / "logistic_model.pkl")
    print("\n=== TRAINING COMPLETE ===")
