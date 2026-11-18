# D4 — Fitted Pipeline and API

This API predicts an item's asking price as a percentage of its estimated retail price. It also returns the corresponding dollar amount.

## Model and training data

The pipeline uses ridge regression with alpha=1.0, selected in D3.

Inputs:
- Brand
- Item type
- Condition
- Age band, which can be missing
- Estimated retail price

Training uses data/clean/train.csv. Of 12,557 rows, 1,839 have a recorded asking price percentage and were used for training.

## Custom transformer

ResaleFeatures fills missing ages with "Unknown" and calculates the log of estimated retail price. It checks that retail prices are positive, finite numbers.

The pipeline then encodes the categories and applies ridge regression.

## Files

- transformers.py — custom transformer
- train.py — fits and saves the pipeline
- resale_pipeline.joblib — fitted pipeline
- api.py — FastAPI application
- requirements.txt — package versions
- modal_app.py — Modal deployment code

## Rebuild

Run these commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r d4/requirements.txt
python -m d4.train
```

## Run locally

```bash
python -m uvicorn d4.api:app --reload
```

Local documentation:
http://127.0.0.1:8000/docs

## Deploy

After authenticating with Modal:

```bash
python -m modal setup
python -m modal deploy d4/modal_app.py
```

## Live API

Base URL:
https://jaiamcgee--luxury-resale-d4-web.us-east.modal.run

Documentation:
https://jaiamcgee--luxury-resale-d4-web.us-east.modal.run/docs

Routes:
- GET /health
- POST /predict

## Verified example

On November 18, 2026, the saved model and deployed API were tested with:

```json
{
  "brand": "Gucci",
  "item_type": "Handbag",
  "condition": "Very Good",
  "age_band": null,
  "estimated_retail_price": 2000
}
```

Both returned approximately 56.906304% of retail.
The deployed API returned an asking price of $1,138.13.

The percentage outputs matched within 0.00000001 percentage points, and the dollar outputs matched to the cent.

## Interpretation

Predictions estimate listing asking prices. Actual sale prices may differ. D3 found larger errors for some smaller brand groups and items in fair condition.
