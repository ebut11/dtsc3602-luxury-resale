import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class ResaleFeatures(BaseEstimator, TransformerMixin):
    """Prepare the original listing inputs for the resale model."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        data = pd.DataFrame(X).copy()

        required = [
            "brand",
            "item_type",
            "condition",
            "age_band",
            "estimated_retail_price",
        ]

        missing = [column for column in required if column not in data.columns]
        if missing:
            raise ValueError(f"Missing input columns: {missing}")

        data["age_band"] = data["age_band"].fillna("Unknown")

        retail = pd.to_numeric(
            data["estimated_retail_price"], errors="coerce"
        )

        if (retail.isna() | ~np.isfinite(retail) | (retail <= 0)).any():
            raise ValueError("Estimated retail price must be a positive number.")

        data["log_retail"] = np.log(retail)

        return data[
            ["brand", "item_type", "condition", "age_band", "log_retail"]
        ]
