from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import deps
from .config import get_settings
from .routes import coolroute, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    deps.get_db()  # ensure tables exist
    yield


app = FastAPI(title="FortyGuard Track 6 -- CoolRoute Agent", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(coolroute.router)
