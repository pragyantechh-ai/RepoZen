from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router
from app.core.auth_router import router as auth_router
from app.db.redis_client import get_redis, close_redis

app = FastAPI(
    title="RepoZen",
    description="AI Engineering Copilot for Codebases",
    version="0.2.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "RepoZen API is running",
        "version": "0.2.0",
        "docs": "/docs",
    }
    
app.include_router(auth_router, prefix="/api")

@app.on_event("startup")
async def startup():
    get_redis()  # warm up the connection pool

@app.on_event("shutdown")
async def shutdown():
    close_redis()