from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import leads, filters
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

# CORS - allow all origins for now (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)
app.include_router(filters.router)


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
