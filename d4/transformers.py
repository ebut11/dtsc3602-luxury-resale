import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

REQUIRED = ["brand", "item_type", "condition", "age_band", "estimated_retail_price"]
OUTPUT = ["brand", "item_type", "condition", "age_band", "log_retail"]


class ResaleFeatures(BaseEstimator, TransformerMixin):
    """Prepare the original listing inputs for the resale model.

    Learned in fit() (from the training rows only):
      * brand_levels_ / item_type_levels_ - categories with at least `min_count`
        training rows. Rarer values are pooled into "Other", so a brand with only
        1-3 listings shares one estimated effect instead of getting its own noisy one.
      * retail_bounds_ - the 1st-99th percentile of estimated retail price. Prices
        outside it are clipped before the log, so the linear model can't extrapolate
        to impossible ratios (e.g. a $5,000,000 retail price giving -72%).

    transform() also fills a missing age band with "Unknown" and takes log(retail).
    """

    def __init__(self, min_count=10, clip_quantiles=(0.01, 0.99)):
        self.min_count = min_count
        self.clip_quantiles = clip_quantiles

    def fit(self, X, y=None):
        data = self._check(X)
        brands = data["brand"].value_counts()
        types = data["item_type"].value_counts()
        self.brand_levels_ = sorted(brands[brands >= self.min_count].index)
        self.item_type_levels_ = sorted(types[types >= self.min_count].index)
        lo, hi = data["estimated_retail_price"].quantile(list(self.clip_quantiles))
        self.retail_bounds_ = (float(lo), float(hi))
        return self

    def transform(self, X):
        data = self._check(X)
        data["brand"] = data["brand"].where(data["brand"].isin(self.brand_levels_), "Other")
        data["item_type"] = data["item_type"].where(data["item_type"].isin(self.item_type_levels_), "Other")
        data["age_band"] = data["age_band"].fillna("Unknown")
        retail = data["estimated_retail_price"].clip(*self.retail_bounds_)
        data["log_retail"] = np.log(retail)
        return data[OUTPUT]

    def get_feature_names_out(self, input_features=None):
        return np.array(OUTPUT, dtype=object)

    @staticmethod
    def _check(X):
        data = pd.DataFrame(X).copy()
        missing = [column for column in REQUIRED if column not in data.columns]
        if missing:
            raise ValueError(f"Missing input columns: {missing}")
        retail = pd.to_numeric(data["estimated_retail_price"], errors="coerce")
        if (retail.isna() | ~np.isfinite(retail) | (retail <= 0)).any():
            raise ValueError("Estimated retail price must be a positive number.")
        data["estimated_retail_price"] = retail
        return data
