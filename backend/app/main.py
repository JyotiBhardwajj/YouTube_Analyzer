from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

# ✅ MODELS (import FIRST so tables exist)
from app.models.user import User
from app.models.analysis import AnalysisRun, Video

# ✅ ROUTES
from app.routes.auth import router as auth_router
from app.routes.analyze import router as analyze_router
from app.routes.dashboard import router as dashboard_router
from app.routes.insights import router as insights_router
from app.routes.onboarding import router as onboarding_router
from app.routes.analytics_routes import router as analytics_router
from app.routes.analyze_csv import router as analyze_csv_router
from app.routes.history import router as history_router
from app.routes.users import router as users_router

# ✅ CREATE TABLES ONCE
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Social Media Analyzer API")

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ REGISTER ROUTERS
app.include_router(auth_router)
app.include_router(onboarding_router)   # 🔥 THIS FIXES ONBOARDING LOOP
app.include_router(analyze_router)
app.include_router(dashboard_router)
app.include_router(insights_router)
app.include_router(analytics_router)
app.include_router(analyze_csv_router)
app.include_router(history_router)
app.include_router(users_router)

@app.get("/")
def home():
    return {"message": "API is running 🚀"}
