from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload, chat

app = FastAPI(
    title="RepoZen",
    description="AI Engineering Copilot for Codebases",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/repo", tags=["Repository"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])


@app.get("/")
async def root():
    return {"message": "RepoZen API is running"}