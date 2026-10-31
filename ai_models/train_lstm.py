# ai_models/train_lstm.py

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler  # pyright: ignore[reportMissingModuleSource]
from tensorflow.keras.models import Sequential  # pyright: ignore[reportMissingModuleSource]
from tensorflow.keras.layers import LSTM, Dense, Dropout  # pyright: ignore[reportMissingModuleSource]
import pickle
import os

# ── 1. Load your sales data ──────────────────────────────
# Replace this with real data from your DB later
# Format: date, total_sales
data = {
    'date': pd.date_range(start='2024-01-01', periods=365, freq='D'),
    'sales': np.random.randint(5000, 50000, size=365)  # dummy data
}
df = pd.DataFrame(data)
df = df.set_index('date')

# ── 2. Normalize data ────────────────────────────────────
scaler = MinMaxScaler(feature_range=(0, 1))
scaled = scaler.fit_transform(df[['sales']])

# ── 3. Create sequences (30 days → predict next day) ─────
SEQ_LEN = 30

def create_sequences(data, seq_len):
    X, y = [], []
    for i in range(seq_len, len(data)):
        X.append(data[i-seq_len:i, 0])
        y.append(data[i, 0])
    return np.array(X), np.array(y)

X, y = create_sequences(scaled, SEQ_LEN)
X = X.reshape((X.shape[0], X.shape[1], 1))  # LSTM needs 3D input

# ── 4. Split train/test ──────────────────────────────────
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# ── 5. Build LSTM model ──────────────────────────────────
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(SEQ_LEN, 1)),
    Dropout(0.2),
    LSTM(32, return_sequences=False),
    Dropout(0.2),
    Dense(16),
    Dense(1)
])

model.compile(optimizer='adam', loss='mse')
model.summary()

# ── 6. Train ─────────────────────────────────────────────
model.fit(
    X_train, y_train,
    epochs=50,
    batch_size=32,
    validation_data=(X_test, y_test),
    verbose=1
)

# ── 7. Save model and scaler ─────────────────────────────
os.makedirs('ai_models/saved_models', exist_ok=True)
model.save('ai_models/saved_models/lstm_model.h5')

with open('ai_models/saved_models/scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

print("✅ LSTM model saved!")