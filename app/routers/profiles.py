from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import asyncio
import httpx
from datetime import datetime, timezone
from uuid6 import uuid7
from typing import Optional

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
        results = await asyncio.gather(
            client.get(GENDERIZE_URL, params={"name": name}),
            client.get(AGIFY_URL, params={"name": name}),
            client.get(NATIONALIZE_URL, params={"name": name}),
            return_exceptions=True
        )
    return results


@router.get("/profiles")
async def list_profiles(
    gender: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Profile)
    if gender:
        query = query.filter(Profile.gender == gender.lower())
    if age_group:
        query = query.filter(Profile.age_group == age_group.lower())
    if country_id:
        query = query.filter(Profile.country_id == country_id.upper())
    profiles = query.all()
    return JSONResponse(
        status_code=200,
        headers={"Access-Control-Allow-Origin": "*"},
        content={
