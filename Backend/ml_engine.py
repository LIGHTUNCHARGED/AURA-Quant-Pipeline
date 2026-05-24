import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import joblib

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = BASE_DIR / "logistic_model.pkl"
FEATURES = ['Alpha', 'Beta', 'Log_RS', 'RSI', 'Vol_Ratio']


def _resolve_model_path(filename=None):
    if filename is None:
        return DEFAULT_MODEL_PATH

    model_path = Path(filename)
    if model_path.is_absolute():
        return model_path
    if model_path.exists():
        return model_path
    return BASE_DIR / model_path


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

    # Drop rows with NaN values (due to rolling windows and future shifting)
    ml_df = df.dropna(subset=FEATURES + ['Target'])

    return ml_df[FEATURES], ml_df['Target']


def train_and_save_model(X, y, filename=None):
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
    model_path = _resolve_model_path(filename)
    pipeline = {'model': model, 'scaler': scaler, 'features': list(X.columns)}
    joblib.dump(pipeline, model_path)
    print(f"Saved model pipeline to {model_path}")


def predict_probabilities(current_data, filename=None):
    """
    Loads the trained model to predict the win probability of live candidates.
    """
    model_path = _resolve_model_path(filename)
    if not model_path.exists():
        raise FileNotFoundError(f"Trained model not found at {model_path}")

    pipeline = joblib.load(model_path)
    model = pipeline['model']
    scaler = pipeline['scaler']

    features = pipeline.get('features', FEATURES)
    missing_features = [feature for feature in features if feature not in current_data.columns]
    if missing_features:
        raise ValueError(f"Missing ML feature columns: {', '.join(missing_features)}")

    X_live = current_data[features].apply(pd.to_numeric, errors='coerce')
    X_live = X_live.replace([np.inf, -np.inf], np.nan)
    if X_live.isna().any().any():
        bad_columns = X_live.columns[X_live.isna().any()].tolist()
        raise ValueError(f"ML feature data contains non-numeric or missing values: {', '.join(bad_columns)}")

    X_live_scaled = scaler.transform(X_live)

    # predict_proba returns an array like [Prob_0, Prob_1]. We want Prob_1.
    probabilities = model.predict_proba(X_live_scaled)[:, 1]

    return probabilities
