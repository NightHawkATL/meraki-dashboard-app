from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models
from .routes import auth, meraki

# Create all tables in PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meraki Dashboard App")

# Allow the frontend to communicate with this backend securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static directory for CSS, JS, and Images
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API Routes
app.include_router(auth.router)
app.include_router(meraki.router)

@app.get("/health")
def health_check():
    return {"status": "Backend is running!"}