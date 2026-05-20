import pandas as pd
import yfinance as yf
from datetime import datetime

from data_loader import fetch_and_preprocess, fetch_tickers_from_txt
from indicators import calculate_rs, calculate_rarsi, calculate_weighted_rs, calculate_beta, calculate_alpha
from filters import calculate_z_score, calculate_rsi_filter, calculate_ema_filter, calculate_volume_filter
from portfolio import calculate_allocations
from risk_management import calculate_atr_stop


def run_quant_pipeline(tickers, benchmark='^NSEI', start_date='2024-01-01', end_date=None):

    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')

    print(f"=== INITIALIZING RS-BETA-ALPHA PIPELINE ===")
    print(f"Universe Size: {len(tickers)} | Date Range: {start_date} to {end_date}")

    # ---------------------------------------------------------
    # DATA COLLECTION & PREPROCESSING
    # ---------------------------------------------------------


    print("Fetching market data...")
    full_data = yf.download(
        tickers + [benchmark],  # Add benchmark to the bulk download
        start=start_date,
        end=end_date,
        group_by='ticker',
        threads=True,
        ignore_tz=True
    )


    prices, volumes, log_returns = fetch_and_preprocess(full_data, benchmark)

    master_screener = []

    # ---------------------------------------------------------
    # THE QUANTITATIVE ENGINE
    # ---------------------------------------------------------
    for stock in tickers:
        try:
            print(f"Processing {stock}...")

            rs_df = calculate_rs(log_returns, stock, benchmark)
            log_rs_series = rs_df[f'{stock}_Log_RS']

            rarsi_df = calculate_rarsi(log_returns, log_rs_series, stock)
            wrs_df = calculate_weighted_rs(log_returns, stock)

            beta_df = calculate_beta(log_returns, stock)
            beta_series = beta_df[f'{stock}_Beta']
            alpha_df = calculate_alpha(log_returns, beta_series, stock)

            z_score_df = calculate_z_score(log_rs_series, stock)

            price_series = prices[stock]
            volume_series = volumes[stock]

            rsi_df = calculate_rsi_filter(price_series, stock)
            ema_df = calculate_ema_filter(price_series, stock)
            vol_df = calculate_volume_filter(volume_series, stock)


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

            # --- SAFETY CHECK ---
            if atr_df.empty or rarsi_df.empty or z_score_df.empty:
                print(f"  -> Insufficient valid data for {stock}. Skipping.")
                continue

            latest_data = {
                'Ticker': stock,
                'Close_Price': price_series.dropna().iloc[-1],
                'Log_RS': log_rs_series.dropna().iloc[-1],
                'RARSI': rarsi_df[f'{stock}_RARSI'].dropna().iloc[-1],
                'Beta': beta_series.dropna().iloc[-1],
                'Alpha': alpha_df[f'{stock}_Alpha'].dropna().iloc[-1],
                'Z_Score': z_score_df[f'{stock}_Z_Score'].dropna().iloc[-1],
                'RSI_Passed': rsi_df[f'{stock}_RSI_Passed'].dropna().iloc[-1],
                'EMA_Passed': ema_df[f'{stock}_EMA_Passed'].dropna().iloc[-1],
                'Volume_Passed': vol_df[f'{stock}_Volume_Passed'].dropna().iloc[-1],
                'Stop_Loss': atr_df[f'{stock}_Stop_Level'].dropna().iloc[-1]
            }

            master_screener.append(latest_data)

        except Exception as e:
            print(f"Skipping {stock} due to error: {e}")

    screener_df = pd.DataFrame(master_screener)

    if screener_df.empty:
        print("\n=== PIPELINE ABORTED ===")
        print("Zero stocks were successfully processed. Check your data connection.")
        return

    # ---------------------------------------------------------
    # EXECUTE STRATEGY FILTERS
    # ---------------------------------------------------------
    print("\n=== APPLYING PIPELINE FILTERS ===")


    filtered_df = screener_df[
        (screener_df['Z_Score'] > 1.5) &
        (screener_df['RSI_Passed'] == True) &
        (screener_df['EMA_Passed'] == True) &
        (screener_df['Close_Price'] > 50.0)
        ].copy()

    # ---------------------------------------------------------
    # PORTFOLIO ALLOCATION
    # ---------------------------------------------------------
    if not filtered_df.empty:
        print(f"\n{len(filtered_df)} stocks passed the filters. Constructing Portfolio...")

        allocations = calculate_allocations(filtered_df)
        final_portfolio = pd.merge(
            allocations,
            filtered_df[['Ticker', 'Close_Price', 'Stop_Loss']],
            on='Ticker'
        )

        # --- NEW STEP: SAVE THE OUTPUT ---
        # Export the final portfolio to a local JSON file
        final_portfolio.to_json("latest_scan.json", orient="records")
        print("\n=== SUCCESS: Saved results to latest_scan.json ===")

        return final_portfolio

    else:
        print("\n=== NO TRADE ZONE ===")
        print("Zero stocks passed the quantitative filters today.")
        # Save an empty array so the API knows it ran but found nothing
        pd.DataFrame().to_json("latest_scan.json", orient="records")
        return pd.DataFrame()

if __name__ == "__main__":
    # 1. TEST MODE
    # target_universe = [
    #     'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ZOMATO.NS',
    #     'TATAMOTORS.NS', 'INFY.NS', 'BHARTIARTL.NS', 'ITC.NS', 'HALEOSLABS.NS'
    # ]

    # 2. PRODUCTION MODE (Active - Runs full market)
    target_universe = fetch_tickers_from_txt('Symbols_NSE.txt')

    run_quant_pipeline(target_universe)