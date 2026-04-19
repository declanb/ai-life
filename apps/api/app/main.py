from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import vercel, transit
from app.core.settings import get_settings
from app.core.observability import init_sentry
# from app.api.routers import trips  # Temporarily disabled - requires google.auth

settings = get_settings()
init_sentry(settings)

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
# app.include_router(trips.router, prefix="/api/v1")  # Temporarily disabled
app.include_router(transit.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to ai-life API", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
