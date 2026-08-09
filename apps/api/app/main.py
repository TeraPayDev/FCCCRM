from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CRAM API",
    description="Climate Risk Analytics Management Platform API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://10.1.11.7:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "CRAM API",
        "status": "running",
    }


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "cram-api",
        "version": "0.1.0",
    }
