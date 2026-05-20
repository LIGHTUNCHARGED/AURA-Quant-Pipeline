import pandas as pd


def calculate_allocations(filtered_stocks_df):
    """
    Takes a DataFrame of stocks that have passed all filters (Z-score, RSI, etc.)
    and calculates their ideal portfolio weights based on Alpha and Beta.

    Expected columns in filtered_stocks_df: 'Ticker', 'Alpha', 'Beta', 'Log_RS'
    """
    print("Calculating Alpha-Weighted and Beta-Adjusted portfolio allocations...")

    df = filtered_stocks_df.copy()

    # 1. ALPHA-WEIGHTED PORTFOLIO
    # We clip Alpha at 0 because we only want to allocate long capital to positive Alpha.
    positive_alpha = df['Alpha'].clip(lower=0)

    # Formula: w_i = alpha_i / sum(alpha)
    df['Alpha_Weight'] = positive_alpha / positive_alpha.sum()

    # 2. BETA-ADJUSTED WEIGHTING
    # Formula: W_i = RS_i / Beta_i
    # We clip Beta at 0.1 to prevent division by zero or negative weights in long-only portfolios.
    safe_beta = df['Beta'].clip(lower=0.1)
    beta_adjusted_score = df['Log_RS'] / safe_beta

    # Normalize the beta-adjusted scores so they sum up to 1 (100% of the portfolio)
    # We only allocate to positive RS scores
    positive_beta_score = beta_adjusted_score.clip(lower=0)
    df['Beta_Weight'] = positive_beta_score / positive_beta_score.sum()

    # Clean up formatting for readability (convert to percentages)
    df['Alpha_Weight_%'] = (df['Alpha_Weight'] * 100).round(2)
    df['Beta_Weight_%'] = (df['Beta_Weight'] * 100).round(2)

    return df[['Ticker', 'Alpha', 'Beta', 'Log_RS', 'Alpha_Weight_%', 'Beta_Weight_%']]


if __name__ == "__main__":

    mock_filtered_data = {
        'Ticker': ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ZOMATO.NS'],
        'Alpha': [0.002, 0.001, -0.0005, 0.008],  # Daily alpha values
        'Beta': [1.1, 0.8, 1.2, 2.5],  # Market sensitivity
        'Log_RS': [0.05, 0.02, -0.01, 0.15]  # Relative Strength
    }

    filtered_stocks_df = pd.DataFrame(mock_filtered_data)

    # Calculate Allocations
    allocation_metrics = calculate_allocations(filtered_stocks_df)

    print("\n--- Portfolio Allocation ---")
    print(allocation_metrics)