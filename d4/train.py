from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from d4.transformers import ResaleFeatures


ROOT = Path(__file__).resolve().parents[1]
TRAIN_FILE = ROOT / "data" / "clean" / "train.csv"
MODEL_FILE = ROOT / "d4" / "resale_pipeline.joblib"

INPUTS = [
    "brand",
    "item_type",
    "condition",
    "age_band",
    "estimated_retail_price",
]
TARGET = "asking_price_ratio"


def main():
    data = pd.read_csv(TRAIN_FILE)

    # D3 trained on listings with a recorded target.
    training = data.loc[data[TARGET].notna()].copy()

    if training.empty:
        raise ValueError("No training rows have an asking price percentage.")

    if not np.isfinite(training[TARGET].to_numpy(dtype=float)).all():
        raise ValueError("Training targets must be finite numbers.")

    print(f"Total rows: {len(data):,}")
    print(f"Rows with an asking price percentage: {len(training):,}")

    # Use the same encoder settings and ridge model as D3.
    encoder = ColumnTransformer([
        (
            "categories",
            OneHotEncoder(
                handle_unknown="infrequent_if_exist",
                min_frequency=5,
                sparse_output=False,
            ),
            ["brand", "item_type", "condition", "age_band"],
        ),
        ("retail", "passthrough", ["log_retail"]),
    ])

    pipeline = Pipeline([
        ("prepare", ResaleFeatures()),
        ("encode", encoder),
        ("model", Ridge(alpha=1.0)),
    ])

    pipeline.fit(training[INPUTS], training[TARGET])
    joblib.dump(pipeline, MODEL_FILE)

    # Check that loading the saved file preserves predictions.
    example = training[INPUTS].head(5)
    loaded = joblib.load(MODEL_FILE)

    np.testing.assert_allclose(
        pipeline.predict(example),
        loaded.predict(example),
        rtol=0,
        atol=1e-10,
    )

    print(f"Saved model: {MODEL_FILE}")
    print("Saved-model prediction check passed.")


if __name__ == "__main__":
    main()
