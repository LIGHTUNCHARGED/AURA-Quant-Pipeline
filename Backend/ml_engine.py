import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib


def prepare_ml_data(historical_df):
    """
    Transforms raw OHLCV and indicator data into ML features and targets.
    """
    df = historical_df.copy()

    # 1. Define the Target: 5-Day Forward Return
    # Shift the close price backwards to get the future price
    df['Future_5d_Close'] = df['Close'].shift(-5)
    df['Forward_Return'] = (df['Future_5d_Close'] - df['Close']) / df['Close']

    # Binary Classification: 1 if positive return, 0 if negative/flat
    df['Target'] = np.where(df['Forward_Return'] > 0, 1, 0)

    # 2. Feature Engineering (Ensure these exist from your indicators.py)
    # Adding a normalized volatility feature (ATR / Close Price)
    df['Vol_Ratio'] = df['ATR'] / df['Close']

    features = ['Alpha', 'Beta', 'Log_RS', 'RSI', 'Vol_Ratio']

    # Drop rows with NaN values (due to rolling windows and future shifting)
    ml_df = df.dropna(subset=features + ['Target'])

    return ml_df[features], ml_df['Target']


def train_and_save_model(X, y, filename="logistic_model.pkl"):
    """
    Trains the Logistic Regression model and saves the scaler and model weights.
    """
    print("Training ML Classifier...")

    # Split data chronologically (don't shuffle time-series data)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Standardize the features (Mean=0, Variance=1) - Critical for Logistic Regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Initialize and train the model
    model = LogisticRegression(class_weight='balanced', random_state=42)
    model.fit(X_train_scaled, y_train)

    # Evaluate basic accuracy on the test set
    accuracy = model.score(X_test_scaled, y_test)
    print(f"Model Training Complete. Test Accuracy: {accuracy:.2f}")

    # Save the model and the scaler together
    pipeline = {'model': model, 'scaler': scaler}
    joblib.dump(pipeline, filename)
    print(f"Saved model pipeline to {filename}")


def predict_probabilities(current_data, filename="logistic_model.pkl"):
    """
    Loads the trained model to predict the win probability of live candidates.
    """
    pipeline = joblib.load(filename)
    model = pipeline['model']
    scaler = pipeline['scaler']

    features = ['Alpha', 'Beta', 'Log_RS', 'RSI', 'Vol_Ratio']
    X_live = current_data[features]

    X_live_scaled = scaler.transform(X_live)

    # predict_proba returns an array like [Prob_0, Prob_1]. We want Prob_1.
    probabilities = model.predict_proba(X_live_scaled)[:, 1]

    return probabilities