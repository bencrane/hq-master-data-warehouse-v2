from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import leads, filters, views, auth, companies
from db import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database pool
    await init_pool()
    yield
    # Shutdown: close database pool
    await close_pool()


app = FastAPI(
    title="HQ Master Data API",
    description="API for querying the HQ canonical leads database",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS - allowed origins for revenueactivation.com and radarrevenue.com
ALLOWED_ORIGINS = [
    # revenueactivation.com
    "https://revenueactivation.com",
    "https://app.revenueactivation.com",
    "https://admin.revenueactivation.com",
    "https://hq.revenueactivation.com",
    "https://demo.revenueactivation.com",
    # radarrevenue.com
    "https://radarrevenue.com",
    "https://app.radarrevenue.com",
    "https://admin.radarrevenue.com",
    "https://hq.radarrevenue.com",
    "https://demo.radarrevenue.com",
    # localhost for development
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)
app.include_router(filters.router)
app.include_router(views.router)
app.include_router(auth.router)
app.include_router(companies.router)


@app.get("/")
async def root():
    return {
        "name": "HQ Master Data API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
