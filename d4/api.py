"""FastAPI service for the fitted asking-price-ratio pipeline.

Run locally from the repository root:  uv run uvicorn d4.api:app --reload
Env var MODEL_PATH overrides the bundle location (used to test the 503 path).

The bundle is loaded once per server process at startup; nothing is retrained while serving.
If it can't be loaded (missing file, bad pickle, scikit-learn version mismatch), the app
still starts, /health reports it, and /predict and /pipeline/info return 503.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
import sklearn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from d4.transformers import ResaleFeatures  # noqa: F401  (needed to unpickle the bundle)


MODEL_FILE = Path(__file__).with_name("resale_pipeline.joblib")

Brand = Literal[
    "Balenciaga", "Breitling", "Burberry", "Chanel", "David Yurman", "Dolce & Gabbana",
    "Gucci", "Louis Vuitton", "Omega", "Saint Laurent", "Tiffany & Co.",
]
ItemType = Literal["Accessory", "Handbag", "Jewelry", "Shoes", "Watch"]
Condition = Literal["Fair", "Good", "Very Good", "Great", "Excellent", "Pristine"]
AgeBand = Literal["5 or less", "6-10", "11-20", "Over 20"]


class ListingInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "brand": "Gucci",
                "item_type": "Handbag",
                "condition": "Very Good",
                "age_band": None,
                "estimated_retail_price": 2000,
            }
        },
    )

    brand: Brand
    item_type: ItemType
    condition: Condition
    age_band: AgeBand | None = Field(
        None, description="Years since production; null if unknown (only LV/Chanel codes are decodable)"
    )
    estimated_retail_price: float = Field(gt=0, le=500_000, allow_inf_nan=False,
                                          description="Current retail price in USD")


class PredictionOutput(BaseModel):
    predicted_percentage: float
    predicted_asking_price: float
    capped: bool = Field(description="True if the raw model output was outside the range seen in training")
    warnings: list[str]


def load_bundle(app: FastAPI):
    path = Path(os.environ.get("MODEL_PATH", MODEL_FILE))
    app.state.pipeline, app.state.metadata, app.state.load_error = None, None, None
    try:
        bundle = joblib.load(path)
        metadata = bundle["metadata"]
        if metadata["sklearn_version"] != sklearn.__version__:
            raise RuntimeError(
                f"scikit-learn mismatch: artifact {metadata['sklearn_version']}, server {sklearn.__version__}"
            )
        app.state.pipeline, app.state.metadata = bundle["pipeline"], metadata
    except Exception as exc:  # any load failure -> 503 on model routes, not a crash
        app.state.load_error = f"{type(exc).__name__}: {exc}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_bundle(app)
    yield


app = FastAPI(
    title="Luxury Resale Prediction API",
    description="Predicts a Rebag listing's asking price as a percentage of estimated retail price "
                "for SouthPark Mall brands. Predictions are asking prices, not sale prices. DTSC 3602 Group 12.",
    version="1.1.0",
    lifespan=lifespan,
)

# The D5 website calls this API from the browser, which requires CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def require_model():
    if app.state.pipeline is None:
        raise HTTPException(status_code=503, detail=f"Model artifact unavailable ({app.state.load_error})")
    return app.state.pipeline, app.state.metadata


@app.get("/")
def root():
    return {"service": "luxury-resale-d4", "endpoints": ["/health", "/pipeline/info", "/predict", "/docs"]}


@app.get("/health")
def health():
    loaded = app.state.pipeline is not None
    return {"status": "ready" if loaded else "degraded", "model_loaded": loaded, "error": app.state.load_error}


@app.get("/pipeline/info")
def pipeline_info():
    pipeline, metadata = require_model()
    return {**metadata, "server_sklearn_version": sklearn.__version__}


@app.post("/predict", response_model=PredictionOutput)
def predict(listing: ListingInput):
    pipeline, metadata = require_model()
    inputs = pd.DataFrame([listing.model_dump()])
    raw = float(pipeline.predict(inputs)[0])

    low, high = metadata["prediction_cap"]
    percentage = min(max(raw, low), high)
    capped = percentage != raw

    learned = metadata["learned_by_transformer"]
    warnings = []
    if capped:
        warnings.append(f"Raw prediction {raw:.1f}% was outside the training range and was capped at {percentage:.1f}%.")
    if listing.brand not in learned["brand_levels"]:
        warnings.append(f"Few {listing.brand} listings in the training data; it is grouped with other rare brands.")
    if listing.item_type != "Handbag":
        warnings.append("93% of training listings are handbags, so this prediction is less reliable.")
    lo_price, hi_price = learned["retail_bounds"]
    if not lo_price <= listing.estimated_retail_price <= hi_price:
        warnings.append(f"Retail price is outside the training range (${lo_price:,.0f}-${hi_price:,.0f}).")

    percentage = round(percentage, 2)  # price below uses the shown percentage, so the two always agree
    return PredictionOutput(
        predicted_percentage=percentage,
        predicted_asking_price=round(listing.estimated_retail_price * percentage / 100, 2),
        capped=capped,
        warnings=warnings,
    )
