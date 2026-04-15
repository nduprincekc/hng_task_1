from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import asyncio
import httpx
from datetime import datetime, timezone
from uuid6 import uuid7

from app.database import get_db
from app.models import Profile

router = APIRouter()

GENDERIZE_URL = "https://api.genderize.io"
AGIFY_URL = "https://api.agify.io"
NATIONALIZE_URL = "https://api.nationalize.io"


def classify_age_group(age: int) -> str:
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


def format_profile(profile: Profile) -> dict:
    return {
        "id": profile.id,
        "name": profile.name,
        "gender": profile.gender,
        "gender_probability": profile.gender_probability,
        "sample_size": profile.sample_size,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
        "country_probability": profile.country_probability,
        "created_at": profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


async def fetch_all(name: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        gender_req = client.get(GENDERIZE_URL, params={"name": name})
        age_req = client.get(AGIFY_URL, params={"name": name})
        nation_req = client.get(NATIONALIZE_URL, params={"name": name})
        results = await asyncio.gather(gender_req, age_req, nation_req, return_exceptions=True)
    return results


@router.post("/profiles")
async def create_profile(request: Request, db: Session = Depends(get_db)):
    # --- Parse body ---
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid JSON body"},
        )

    name = body.get("name")

    # --- Input validation ---
    if name is None or (isinstance(name, str) and name.strip() == ""):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "name is required and cannot be empty"},
        )

    if not isinstance(name, str):
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "name must be a string"},
        )

    name = name.strip().lower()

    # --- Idempotency check ---
    existing = db.query(Profile).filter(Profile.name == name).first()
    if existing:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Profile already exists",
                "data": format_profile(existing),
            },
        )

    # --- Call all 3 APIs concurrently ---
    results = await fetch_all(name)

    for r in results:
        if isinstance(r, Exception):
            return JSONResponse(
                status_code=502,
                content={"status": "error", "message": "Failed to reach external API"},
            )

    gender_res, age_res, nation_res = results

    try:
        gender_data = gender_res.json()
        age_data = age_res.json()
        nation_data = nation_res.json()
    except Exception:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Invalid response from external API"},
        )

    # --- Edge case validation ---
    if gender_data.get("gender") is None or gender_data.get("count", 0) == 0:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "Insufficient gender data for this name"},
        )

    if age_data.get("age") is None:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "Insufficient age data for this name"},
        )

    countries = nation_data.get("country", [])
    if not countries:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "Insufficient nationality data for this name"},
        )

    # --- Process data ---
    gender = gender_data["gender"]
    gender_probability = gender_data["probability"]
    sample_size = gender_data["count"]

    age = age_data["age"]
    age_group = classify_age_group(age)

    top_country = max(countries, key=lambda c: c["probability"])
    country_id = top_country["country_id"]
    country_probability = top_country["probability"]

    # --- Save to DB ---
    profile = Profile(
        id=str(uuid7()),
        name=name,
        gender=gender,
        gender_probability=gender_probability,
        sample_size=sample_size,
        age=age,
        age_group=age_group,
        country_id=country_id,
        country_probability=country_probability,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return JSONResponse(
        status_code=200,
        content={"status": "success", "data": format_profile(profile)},
    )
