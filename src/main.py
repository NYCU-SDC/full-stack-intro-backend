from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import notes

# Create the FastAPI application
app = FastAPI(
    title="Notes API",
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

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Notes API is running"
    }

# Include routers
app.include_router(notes.router, prefix="/api/notes", tags=["notes"])

# Startup instruction
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)