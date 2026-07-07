from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models
from .routes import auth, meraki

# Create all tables in PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meraki Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# <--- TELL FASTAPI TO USE THE ROUTER
app.include_router(auth.router)
app.include_router(meraki.router)

@app.get("/")
def health_check():
    return {"status": "FastAPI is connected to PostgreSQL and running!"}