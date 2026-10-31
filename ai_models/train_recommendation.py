# ai_models/train_recommendation.py

import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier  # type: ignore[reportMissingImports]
from sklearn.preprocessing import LabelEncoder  # type: ignore[reportMissingImports]
import pickle
import os

# ── 1. Dummy training data ───────────────────────────────
# Replace with real data from your DB
data = {
    'viewed_category':   ['shirts', 'pants', 'shoes', 'jackets', 'shirts', 'pants'],
    'session_duration':  [120,      200,      90,      300,       150,      180],
    'pages_visited':     [3,        5,        2,       8,         4,        6],
    'added_to_cart':     [1,        0,        1,       1,         0,        1],
    'recommended_item':  ['jacket', 'belt',   'socks', 'shirt',   'tie',    'shoes'],
}
df = pd.DataFrame(data)

# ── 2. Encode categories ─────────────────────────────────
le_cat  = LabelEncoder()
le_item = LabelEncoder()

df['viewed_category_enc'] = le_cat.fit_transform(df['viewed_category'])
df['recommended_item_enc'] = le_item.fit_transform(df['recommended_item'])

X = df[['viewed_category_enc', 'session_duration', 'pages_visited', 'added_to_cart']]
y = df['recommended_item_enc']

# ── 3. Train Decision Tree ───────────────────────────────
clf = DecisionTreeClassifier(max_depth=5, random_state=42)
clf.fit(X, y)

# ── 4. Save model and encoders ───────────────────────────
os.makedirs('ai_models/saved_models', exist_ok=True)

with open('ai_models/saved_models/recommendation_model.pkl', 'wb') as f:
    pickle.dump(clf, f)

with open('ai_models/saved_models/label_encoders.pkl', 'wb') as f:
    pickle.dump({'category': le_cat, 'item': le_item}, f)

print("✅ Recommendation model saved!")