from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field


MODEL_FILE = Path(__file__).with_name("resale_pipeline.joblib")


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

    brand: str = Field(min_length=1)
    item_type: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    age_band: str | None = None
    estimated_retail_price: float = Field(gt=0, allow_inf_nan=False)


class PredictionOutput(BaseModel):
    predicted_percentage: float
    predicted_asking_price: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipeline = joblib.load(MODEL_FILE)
    yield


app = FastAPI(
    title="Luxury Resale Prediction API",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ready"}


@app.post("/predict", response_model=PredictionOutput)
def predict(listing: ListingInput):
    inputs = pd.DataFrame([listing.model_dump()])
    percentage = float(app.state.pipeline.predict(inputs)[0])

    return PredictionOutput(
        predicted_percentage=percentage,
        predicted_asking_price=round(
            listing.estimated_retail_price * percentage / 100,
            2,
        ),
    )
