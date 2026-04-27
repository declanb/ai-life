from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import vercel, transit, photos, spotify, trips, calendar, schedule, property_finder, free_days
from app.core.settings import get_settings

settings = get_settings()

app = FastAPI(title="ai-life API", version="0.1.0")

# Security: explicit origin allow-list. Never use "*" with allow_credentials=True
# (CORS spec forbids it, and it's a data-exfiltration risk).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

app.include_router(vercel.router, prefix="/api/v1")
app.include_router(trips.router, prefix="/api/v1")
app.include_router(transit.router, prefix="/api/v1")
app.include_router(calendar.router, prefix="/api/v1")
app.include_router(photos.router, prefix="/api/v1")
app.include_router(spotify.router, prefix="/api/v1")
app.include_router(schedule.router, prefix="/api/v1")
app.include_router(property_finder.router, prefix="/api/v1")
app.include_router(free_days.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to ai-life API", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
