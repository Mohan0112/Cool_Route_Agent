from functools import lru_cache
from pathlib import Path

from .agents.base import AgentRunner
from .config import get_settings
from .fortyguard.cache import ResponseCache
from .fortyguard.client import FortyGuardClient
from .routing.client import RoutingClient
from .storage.db import Database
from .storage.repo import RunRepo


@lru_cache
def get_db() -> Database:
    return Database(get_settings().cache_db_path)


@lru_cache
def get_cache() -> ResponseCache:
    settings = get_settings()
    return ResponseCache(str(Path(settings.cache_db_path).with_name("response_cache.db")))


@lru_cache
def get_fortyguard_client() -> FortyGuardClient:
    settings = get_settings()
    return FortyGuardClient(
        api_key=settings.fortyguard_api_key,
        base_url=settings.fortyguard_base_url,
        cache=get_cache(),
        demo_mode=settings.demo_mode,
        poll_backoff=settings.poll_backoff_list,
    )


@lru_cache
def get_routing_client() -> RoutingClient:
    settings = get_settings()
    return RoutingClient(
        nominatim_base_url=settings.nominatim_base_url,
        cache=get_cache(),
    )


@lru_cache
def get_agent_runner() -> AgentRunner:
    settings = get_settings()
    return AgentRunner(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        max_turns=settings.max_agent_turns,
        timeout_s=settings.agent_timeout_s,
    )


@lru_cache
def get_run_repo() -> RunRepo:
    return RunRepo(get_db())
