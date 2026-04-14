# HNG Stage 1 — Profile API

A FastAPI service that aggregates Genderize, Agify, and Nationalize API data into a stored profile.

## Endpoint

### `POST /api/profiles`

**Request body:**
```json
{ "name": "john" }
```

**Success response (200):**
```json
{
  "status": "success",
  "data": {
    "id": "019d8e14-9f01-74e8-807c-6bd9f580a1b9",
    "name": "john",
    "gender": "male",
    "gender_probability": 0.99,
    "sample_size": 123456,
    "age": 38,
    "age_group": "adult",
    "country_id": "US",
    "country_probability": 0.45,
    "created_at": "2026-04-14T12:00:00Z"
  }
}
```

**Idempotency (200):** submitting the same name again returns the existing record with `"message": "Profile already exists"`.

**Error responses:**
| Case | Status |
|---|---|
| Missing or empty name | 400 |
| Non-string name | 422 |
| Null gender or count=0 from Genderize | 422 |
| Null age from Agify | 422 |
| No country data from Nationalize | 422 |
| External API unreachable | 502 |

## Local development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`

## Deploy to Render

1. Push this repo to GitHub (make it **public**)
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variable:
   - `DATABASE_URL` → use Render's free PostgreSQL (or leave blank for SQLite)
6. Deploy

## Tech stack

- **FastAPI** — web framework
- **SQLAlchemy** — ORM
- **SQLite** (local) / **PostgreSQL** (production)
- **httpx** — async HTTP client for external APIs
- **uuid6** — UUID v7 generation
