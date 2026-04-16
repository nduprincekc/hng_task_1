from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.database import engine
from app import models
from app.routers import profiles

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HNG Stage 1 - Profile API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ForceCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

app.add_middleware(ForceCORSMiddleware)

app.include_router(profiles.router, prefix="/api")

@app.get("/")
def root():
    return {"status": "ok", "message": "Profile API is running"}
