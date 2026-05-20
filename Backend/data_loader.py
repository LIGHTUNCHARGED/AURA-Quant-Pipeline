import yfinance as yf
import pandas as pd
import numpy as np


def fetch_tickers_from_txt(file_path: str = 'Symbols_NSE.txt') -> list:
    """
    Parses the NSE symbols text file, cleans out non-standard equities
    (like block deals and mutual funds), and formats them for Yahoo Finance.
    """
    clean_tickers = []

    with open(file_path, 'r', encoding='utf-8') as file:
        next(file, None)

        for line in file:
            # Split by the first whitespace/tab to isolate the symbol
            parts = line.strip().split(maxsplit=1)
            if not parts:
                continue

            raw_symbol = parts[0]

            # FILTERING LOGIC:
            # Skip mutual funds (often start with 0P) and
            # skip NSE internal series tags like .BL, .ST, -SM, .RE
            if '.' in raw_symbol or '-' in raw_symbol or raw_symbol.startswith('0P'):
                continue

            # Append .NS so Yahoo Finance knows to look at the National Stock Exchange
            yf_ticker = f"{raw_symbol}.NS"
            clean_tickers.append(yf_ticker)

    # Return a unique, sorted list
    return sorted(list(set(clean_tickers)))


def fetch_and_preprocess(full_data, benchmark='^NSEI'):
    """
    Takes the bulk downloaded market data and calculates log returns.
    """
    print("Preprocessing bulk data...")

    # 1. DATA COLLECTION
    if isinstance(full_data.columns, pd.MultiIndex):
        if 'Close' in full_data.columns.levels[0]:
            # Grouped by feature (Default yfinance behavior)
            prices = full_data['Close']
            volumes = full_data['Volume']
        else:
            # Grouped by ticker (group_by='ticker')
            prices = full_data.xs('Close', level=1, axis=1)
            volumes = full_data.xs('Volume', level=1, axis=1)
    else:
        # Fallback for single ticker downloads
        prices = full_data[['Close']]
        volumes = full_data[['Volume']]

    # We only need volume for the individual stocks, not necessarily the index
    if benchmark in volumes.columns:
        volumes = volumes.drop(columns=[benchmark], errors='ignore')

    # 2. PREPROCESSING: Log Returns
    log_returns = np.log(prices / prices.shift(1))
    log_returns = log_returns.dropna(how='all')
    prices = prices.dropna(how='all')

    return prices, volumes, log_returns


# Testing example stocks
if __name__ == "__main__":

    sample_stocks = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']
    benchmark = '^NSEI'

    print("Running localized test download...")
    test_data = yf.download(
        sample_stocks + [benchmark],
        start='2024-01-01',
        end='2024-05-20',
        group_by='ticker',
        progress=False
    )

    prices, volumes, log_returns = fetch_and_preprocess(test_data, benchmark)
    print("\n--- Log Returns (First 5 Rows) ---")
    print(log_returns.head())