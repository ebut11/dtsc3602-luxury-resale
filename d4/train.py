"""Fit the D3 selected model as one scikit-learn Pipeline and save it with metadata.

Run from the repository root:  uv run python -m d4.train
Writes d4/resale_pipeline.joblib = {"pipeline": fitted Pipeline, "metadata": {...}}
Uses data/clean/train.csv only; the reserved test set stays untouched until D6.
"""
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from d4.transformers import ResaleFeatures


ROOT = Path(__file__).resolve().parents[1]
TRAIN_FILE = ROOT / "data" / "clean" / "train.csv"
MODEL_FILE = ROOT / "d4" / "resale_pipeline.joblib"
METADATA_FILE = ROOT / "d4" / "metadata.json"

INPUTS = [
    "brand",
    "item_type",
    "condition",
    "age_band",
    "estimated_retail_price",
]
TARGET = "asking_price_ratio"
SEED = 3602


def build_pipeline():
    # Same encoder settings and ridge model as D3.
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

    return Pipeline([
        ("prepare", ResaleFeatures()),
        ("encode", encoder),
        ("model", Ridge(alpha=1.0)),
    ])


def grouped_cv(training):
    """5-fold CV grouped by bag model, same design as D3. Reports MAE vs the brand-median baseline."""
    folds = GroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    y = training[TARGET]
    model_mae, baseline_mae = [], []
    for train_idx, valid_idx in folds.split(training, groups=training["model_group"]):
        tr, va = training.iloc[train_idx], training.iloc[valid_idx]
        pred = build_pipeline().fit(tr[INPUTS], tr[TARGET]).predict(va[INPUTS])
        medians = tr.groupby("brand")[TARGET].median()
        base = va["brand"].map(medians).fillna(tr[TARGET].median())
        model_mae.append(np.mean(np.abs(va[TARGET] - pred)))
        baseline_mae.append(np.mean(np.abs(va[TARGET] - base)))
    return {
        "method": f"5-fold GroupKFold by model_group, shuffle seed {SEED}",
        "model_mae": round(float(np.mean(model_mae)), 2),
        "model_mae_fold_sd": round(float(np.std(model_mae, ddof=1)), 2),
        "baseline_mae": round(float(np.mean(baseline_mae)), 2),
        "target_mean": round(float(y.mean()), 2),
    }


def main():
    data = pd.read_csv(TRAIN_FILE, encoding="utf-8-sig")

    # D3 trained on listings with a recorded target.
    training = data.loc[data[TARGET].notna()].reset_index(drop=True)

    if training.empty:
        raise ValueError("No training rows have an asking price percentage.")

    if not np.isfinite(training[TARGET].to_numpy(dtype=float)).all():
        raise ValueError("Training targets must be finite numbers.")

    print(f"Total rows: {len(data):,}")
    print(f"Rows with an asking price percentage: {len(training):,}")

    cv = grouped_cv(training)
    print(f"Grouped CV MAE: model {cv['model_mae']} (fold SD {cv['model_mae_fold_sd']}), "
          f"brand-median baseline {cv['baseline_mae']}")

    pipeline = build_pipeline()
    pipeline.fit(training[INPUTS], training[TARGET])
    prepare = pipeline.named_steps["prepare"]

    metadata = {
        "model_name": "luxury-asking-ratio-ridge",
        "model_version": "1.1.0",
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "steps": [name for name, _ in pipeline.steps],
        "raw_features": INPUTS,
        "target": "asking_price_ratio: Rebag asking price / estimated retail price x 100",
        "target_note": "Advertised asking price on Rebag partner listings, not a sale price.",
        "training_rows": int(len(training)),
        "training_file": "data/clean/train.csv (rows with a target); test.csv untouched until D6",
        "estimator": "Ridge(alpha=1.0) on one-hot brand/item_type/condition/age_band + log retail price",
        "learned_by_transformer": {
            "brand_levels": prepare.brand_levels_,
            "item_type_levels": prepare.item_type_levels_,
            "retail_bounds": [round(b, 2) for b in prepare.retail_bounds_],
        },
        "prediction_cap": [0.0, float(training[TARGET].max())],
        "cv": cv,
    }

    joblib.dump({"pipeline": pipeline, "metadata": metadata}, MODEL_FILE)
    METADATA_FILE.write_text(json.dumps(metadata, indent=2))

    # Check that loading the saved file preserves predictions.
    example = training[INPUTS].head(5)
    loaded = joblib.load(MODEL_FILE)["pipeline"]

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
