from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models

# Import the new ui router along with the others
from .routes import auth, meraki, ui  

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meraki Dashboard App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include all the routes!
app.include_router(ui.router)      # <--- Add the UI router
app.include_router(auth.router)
app.include_router(meraki.router)

@app.get("/health")
def health_check():
    return {"status": "Backend is running!"}