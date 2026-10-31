# ai_models/predict_sales.py

import numpy as np
import pickle
from tensorflow.keras.models import load_model

SEQ_LEN = 30

def load_lstm():
    model = load_model('ai_models/saved_models/lstm_model.h5')
    with open('ai_models/saved_models/scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)
    return model, scaler

def predict_next_30_days(recent_sales: list):
    """
    recent_sales: list of last 30 daily sales numbers
    returns: list of 30 predicted sales values
    """
    model, scaler = load_lstm()

    arr = np.array(recent_sales).reshape(-1, 1)
    scaled = scaler.transform(arr)

    predictions = []
    seq = list(scaled.flatten())

    for _ in range(30):
        X = np.array(seq[-SEQ_LEN:]).reshape(1, SEQ_LEN, 1)
        pred = model.predict(X, verbose=0)[0][0]
        predictions.append(pred)
        seq.append(pred)

    # Inverse transform back to real values
    preds_array = np.array(predictions).reshape(-1, 1)
    real_preds = scaler.inverse_transform(preds_array)

    return [round(float(v[0]), 2) for v in real_preds]