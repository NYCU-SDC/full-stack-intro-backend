from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.config.database import Base, engine
from src.routes import notes

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Create the FastAPI application
app = FastAPI(
    title="Digital Note API",
    description="Personal Cloud Notebook API",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def read_root():
    return FileResponse(STATIC_DIR / "index.html")

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Notes API is running"
    }

# Include routers. Each router owns its own prefix and tags.
app.include_router(notes.router)

# Startup instruction
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
