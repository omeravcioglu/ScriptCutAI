"""
ScriptCutAI - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="ScriptCutAI",
    description="AI-powered video editing assistant for script-based recordings",
    version="0.1.0"
)

# Allow requests from Premiere Pro CEP extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # CEP extensions run on various localhost ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "ScriptCutAI",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Health check for monitoring"""
    return {"status": "healthy"}

