from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from . import models
from .routes import auth, meraki, ui, admin, scripts
from sqlalchemy import text


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Parity Meraki App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS global_ai_provider VARCHAR DEFAULT 'gemini';"))
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS global_ai_custom_url VARCHAR;"))
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS global_ai_model VARCHAR;"))
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS google_places_api_key VARCHAR;"))
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS allow_self_signup BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS allowed_signup_domains VARCHAR;"))
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS allowed_signup_emails VARCHAR;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS user_ai_model VARCHAR;"))
            conn.execute(text("ALTER TABLE meraki_networks ADD COLUMN IF NOT EXISTS phone VARCHAR;"))
            conn.execute(text("ALTER TABLE meraki_networks ADD COLUMN IF NOT EXISTS address VARCHAR;"))
            conn.execute(text("ALTER TABLE meraki_networks ADD COLUMN IF NOT EXISTS lat FLOAT;"))
            conn.execute(text("ALTER TABLE meraki_networks ADD COLUMN IF NOT EXISTS lng FLOAT;"))
            conn.execute(text("ALTER TABLE meraki_devices ADD COLUMN IF NOT EXISTS phone VARCHAR;"))
            conn.commit()
    except Exception as e:
        print(f"Migration Error: {e}")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include all the routes!
app.include_router(ui.router)
app.include_router(auth.router)
app.include_router(meraki.router)
app.include_router(admin.router)
app.include_router(scripts.router)

@app.get("/health")
def health_check():
    return {"status": "Backend is running!"}