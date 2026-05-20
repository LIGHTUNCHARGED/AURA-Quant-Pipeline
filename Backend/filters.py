import pandas as pd


def calculate_z_score(rs_series, target_ticker, window=20):
    """
    Calculates the rolling Z-Score of the Relative Strength.
    Formula: Z = (RS - Rolling Mean) / Rolling Std Dev
    """
    print(f"Calculating Z-Score for {target_ticker} (Rolling {window}-day window)...")

    # 1. Calculate the rolling mean (μ) of the RS
    rolling_mean = rs_series.rolling(window=window).mean()

    # 2. Calculate the rolling standard deviation (σ) of the RS
    rolling_std = rs_series.rolling(window=window).std()

    # 3. Calculate the Z-Score
    # We add a tiny number (1e-8) to the denominator to prevent division by zero errors
    # if the standard deviation is completely flat for a period.
    z_score = (rs_series - rolling_mean) / (rolling_std + 1e-8)

    # Combine into a DataFrame for analysis
    z_score_df = pd.DataFrame({
        f'{target_ticker}_RS_Mean': rolling_mean,
        f'{target_ticker}_RS_Std': rolling_std,
        f'{target_ticker}_Z_Score': z_score
    })

    return z_score_df.dropna()


def calculate_rsi_filter(price_series, target_ticker, window=14):
    """
    Calculates the Relative Strength Index (RSI) using Wilder's Smoothing
    and applies a boolean filter for the target zone (45 < RSI < 70).
    """
    print(f"Calculating RSI and applying filter for {target_ticker} ({window}-day window)...")

    # 1. Calculate daily price changes
    delta = price_series.diff()

    # 2. Separate gains and losses using pandas .clip()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    # 3. Calculate Wilder's smoothed average gain and loss
    # alpha = 1/window is the exact mathematical equivalent to Wilder's Smoothing
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()

    # 4. Calculate RS and RSI
    # Adding 1e-8 to prevent division by zero on days with zero loss
    rs = avg_gain / (avg_loss + 1e-8)
    rsi = 100 - (100 / (1 + rs))

    # 5. Apply the Strategy Filter condition (45 < RSI < 70)
    # This creates a boolean (True/False) column indicating if the stock is a 'Buy' candidate
    rsi_passed = (rsi > 45) & (rsi < 70)

    # Combine into a DataFrame for analysis
    rsi_df = pd.DataFrame({
        f'{target_ticker}_RSI': rsi,
        f'{target_ticker}_RSI_Passed': rsi_passed
    })

    return rsi_df.dropna()


def calculate_ema_filter(price_series, target_ticker):
    """
    Calculates the 20, 50, and 200-day EMAs and applies a boolean filter
    for the condition: Price > 20EMA > 50EMA > 200EMA.
    """
    print(f"Calculating EMA trend filter for {target_ticker}...")

    # 1. Calculate the Exponential Moving Averages
    ema_20 = price_series.ewm(span=20, adjust=False).mean()
    ema_50 = price_series.ewm(span=50, adjust=False).mean()
    ema_200 = price_series.ewm(span=200, adjust=False).mean()

    # 2. Apply the Strategy Filter condition
    # This evaluates to True only if the entire trend stack is perfectly aligned
    ema_passed = (price_series > ema_20) & (ema_20 > ema_50) & (ema_50 > ema_200)

    # Combine into a DataFrame for analysis
    ema_df = pd.DataFrame({
        f'{target_ticker}_Price': price_series,
        f'{target_ticker}_20EMA': ema_20,
        f'{target_ticker}_50EMA': ema_50,
        f'{target_ticker}_200EMA': ema_200,
        f'{target_ticker}_EMA_Passed': ema_passed
    })

    return ema_df


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


if __name__ == "__main__":
    from data_loader import fetch_and_preprocess

    # 1. Get Data
    sample_stocks = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']
    prices, volumes, log_returns = fetch_and_preprocess(sample_stocks)

    target_stock = 'RELIANCE.NS'

    volume_series = volumes[target_stock]

    volume_metrics = calculate_volume_filter(volume_series, target_stock, window=20)

    print(f"\n--- Volume Confirmation Filter for {target_stock} ---")
    print(volume_metrics.tail())