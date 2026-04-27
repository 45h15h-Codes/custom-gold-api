# India Gold & Silver Rate API

A fast, lightweight, and reliable REST API built with FastAPI that provides real-time gold and silver rates in India (INR). The API fetches actual Indian market rates and provides international spot price calculations with import duties as a fallback.

## Features

- **Real-Time Data**: Primary data source is Goodreturns.in (IBJA market rates).
- **Clever Fallback**: Automatically falls back to calculating rates using Yahoo Finance international spot prices (`GC=F`) combined with USD to INR rates (`USDINR=X`) and an estimation of current Indian import duties (~15% total duties) if primary scraping fails.
- **Multiple Units**: Provides prices in Per Gram, Per 10 Grams, and Per Tola (11.6638 grams).
- **Purity Options**: Returns comprehensive prices for both 22-carat and 24-carat gold.
- **Silver Rates**: Returns silver prices in per gram, per 10 grams, per tola, and per kg.

## Endpoints

### `GET /gold`

Returns the current gold prices and source accuracy metadata.

**Example Response:**
```json
{
  "status": "ok",
  "currency": "INR",
  "prices": {
    "22k": {
      "per_gram": 6620.0,
      "per_10g": 66200.0,
      "per_tola": 77214.36
    },
    "24k": {
      "per_gram": 7222.0,
      "per_10g": 72220.0,
      "per_tola": 84237.9
    }
  },
  "meta": {
    "source": "goodreturns.in (IBJA rate)",
    "accuracy": "actual Indian market rate",
    "note": "Excludes making charges & hallmarking fees",
    "updated_at": "2024-03-24T10:00:00+00:00"
  }
}
```

### `GET /silver`

Returns the current silver prices and source metadata.

**Example Response:**
```json
{
  "status": "ok",
  "provider": "navkar",
  "prices": {
    "silver": {
      "per_gram": 96.5,
      "per_10g": 965.0,
      "per_tola": 1125.56,
      "per_kg": 96500.0
    }
  },
  "meta": {
    "source": "navkargold.com (Surat - Smart API)",
    "location": "Surat, Gujarat",
    "updated_at": "2026-04-27T12:00:00+00:00"
  }
}
```

### `GET /`

Health check endpoint.

**Example Response:**
```json
{
  "api": "India Gold Rate API",
  "usage": "/gold"
}
```

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Data Gathering**: `requests`, `beautifulsoup4`, `lxml`
- **Fallback Market Data**: `yfinance`
- **Server**: `uvicorn`

## Local Development

### Requirements

- Python 3.8+

### Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application locally using Uvicorn:
   ```bash
   uvicorn main:app --reload
   ```

3. Visit either:
   - Available API: `http://127.0.0.1:8000/gold`
   - Generated API Docs (Swagger UI): `http://127.0.0.1:8000/docs`

## Deployment

This app includes a `Procfile` already configured for deployment to platforms like Heroku, Render, or Railway:

```procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```
