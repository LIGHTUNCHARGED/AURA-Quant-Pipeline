import pandas as pd
import numpy as np
from data_loader import fetch_and_preprocess


def calculate_rs(log_returns, target_ticker, benchmark='^NSEI'):
    """
    Calculates both Log Relative Strength and Standard Relative Strength.
    """
    print(f"Calculating RS for {target_ticker} against {benchmark}...")

    cum_log_return_stock = log_returns[target_ticker].cumsum()
    cum_log_return_benchmark = log_returns[benchmark].cumsum()

    log_rs = cum_log_return_stock - cum_log_return_benchmark
    standard_rs = np.exp(log_rs)

    rs_df = pd.DataFrame({
        f'{target_ticker}_Log_RS': log_rs,
        f'{target_ticker}_Standard_RS': standard_rs
    })

    return rs_df


def calculate_rarsi(log_returns, log_rs, target_ticker, window=20):
    """
    Calculates Risk-Adjusted Relative Strength (RARSI).
    RARSI = Log(RS) / Volatility
    """
    print(f"Calculating RARSI for {target_ticker} (Rolling {window}-day volatility)...")

    # 1. Calculate Rolling Volatility
    # (Standard deviation of daily log returns over the specified window)
    rolling_volatility = log_returns[target_ticker].rolling(window=window).std()

    # 2. Calculate RARSI
    rarsi = log_rs / rolling_volatility

    # Combine into a DataFrame for analysis
    rarsi_df = pd.DataFrame({
        f'{target_ticker}_Log_RS': log_rs,
        f'{target_ticker}_Volatility': rolling_volatility,
        f'{target_ticker}_RARSI': rarsi
    })

    # Drop the initial NaN rows created by the rolling window requirement
    return rarsi_df.dropna()


def calculate_weighted_rs(log_returns, target_ticker, benchmark='^NSEI', span=20):
    """
    Calculates Weighted Relative Strength (WRS) using exponential decay.
    Formula: Sum of w_i * [log(1+Rs) - log(1+Rm)] where w_i = lambda^(n-i)
    """
    print(f"Calculating Weighted RS for {target_ticker} (Span={span} days)...")

    # 1. Calculate the daily difference in log returns
    # This represents: [log(1+Rs) - log(1+Rm)] for each day
    daily_log_rs = log_returns[target_ticker] - log_returns[benchmark]

    # 2. Apply the Exponential Decay (lambda weighting)
    # A 'span' of 20 roughly corresponds to a lambda of 0.904.
    # and interpretable, representing the recency-weighted average daily outperformance.
    wrs = daily_log_rs.ewm(span=span, adjust=False).mean()

    # Combine into a DataFrame for analysis
    wrs_df = pd.DataFrame({
        f'{target_ticker}_Daily_Outperformance': daily_log_rs,
        f'{target_ticker}_WRS': wrs
    })

    return wrs_df.dropna()


def calculate_beta(log_returns, target_ticker, benchmark='^NSEI', window=60):
    """
    Calculates the rolling Beta of a stock relative to the benchmark.
    Formula: Beta = Cov(Rs, Rm) / Var(Rm)
    """
    print(f"Calculating Beta for {target_ticker} (Rolling {window}-day window)...")

    # 1. Calculate Rolling Covariance between the stock and the benchmark
    rolling_covariance = log_returns[target_ticker].rolling(window=window).cov(log_returns[benchmark])

    # 2. Calculate Rolling Variance of the benchmark
    rolling_variance = log_returns[benchmark].rolling(window=window).var()

    # 3. Calculate Beta
    rolling_beta = rolling_covariance / rolling_variance

    # Combine into a DataFrame for analysis
    beta_df = pd.DataFrame({
        f'{target_ticker}_Beta': rolling_beta
    })

    return beta_df.dropna()


def calculate_alpha(log_returns, rolling_beta_series, target_ticker, benchmark='^NSEI', window=60):
    """
    Calculates the rolling Regression Alpha of a stock.
    Formula: Alpha = Mean(Rs) - Beta * Mean(Rm) over the rolling window.
    """
    print(f"Calculating Alpha for {target_ticker} (Rolling {window}-day window)...")

    # 1. Calculate the rolling average daily return for the stock
    rolling_mean_stock = log_returns[target_ticker].rolling(window=window).mean()

    # 2. Calculate the rolling average daily return for the benchmark
    rolling_mean_benchmark = log_returns[benchmark].rolling(window=window).mean()

    # 3. Calculate Rolling Alpha (The y-intercept of the regression line)
    rolling_alpha = rolling_mean_stock - (rolling_beta_series * rolling_mean_benchmark)

    # Combine into a DataFrame for analysis
    alpha_df = pd.DataFrame({
        f'{target_ticker}_Alpha': rolling_alpha
    })

    return alpha_df.dropna()


def calculate_volume_filter(volume_series, target_ticker, window=20):
    """
    Calculates the rolling average volume and applies a boolean filter
    for the condition: Volume > 2 * AverageVolume.
    """
    print(f"Calculating Volume breakout filter for {target_ticker} ({window}-day average)...")

    # 1. Calculate the rolling average volume
    avg_volume = volume_series.rolling(window=window).mean()

    # 2. Apply the Strategy Filter condition
    # Evaluates to True only if today's volume is more than double the average
    volume_passed = volume_series > (2 * avg_volume)

    # Combine into a DataFrame for analysis
    volume_df = pd.DataFrame({
        f'{target_ticker}_Volume': volume_series,
        f'{target_ticker}_Avg_Volume': avg_volume,
        f'{target_ticker}_Volume_Passed': volume_passed
    })

    return volume_df.dropna()

# 2. EXECUTE THE PIPELINE (For testing purposes only)
if __name__ == "__main__":
    from data_loader import fetch_and_preprocess

    # 1. Get Data
    sample_stocks = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']
    prices, volumes, log_returns = fetch_and_preprocess(sample_stocks)

    target_stock = 'RELIANCE.NS'

    # ... (Your Z-Score, RSI, and EMA test code can stay here) ...

    # 2. Calculate Volume Filter
    # Extract the raw volume series for the target stock
    volume_series = volumes[target_stock]

    volume_metrics = calculate_volume_filter(volume_series, target_stock, window=20)

    print(f"\n--- Volume Confirmation Filter for {target_stock} ---")
    # Print the tail to see if there have been any recent volume breakouts
    print(volume_metrics.tail())