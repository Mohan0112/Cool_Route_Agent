"""Async client for the FortyGuard Temperature API.

Response envelope (confirmed 2026-08-18 against the live API, matching the official
temperature-api-quickstart's own source): every response is `{"data": {...}}` on success or
`{"error": true, "message": "..."}` on failure. Submit endpoints return `data.activity_id`;
status polling returns `data.status` and, once terminal, `data.result`.
"""
import asyncio
from typing import Any, Awaitable, Callable, Optional

import httpx

from . import demo_fixtures
from .cache import ResponseCache
from .errors import FortyGuardApiError, PlanRestrictedError
from .validation import validate_heatmap_request, validate_point_request

TERMINAL_SUCCESS = {"succeeded", "completed"}
TERMINAL_FAILURE = {"failed", "error"}

ProgressCallback = Optional[Callable[[str], Awaitable[None]]]


async def _noop(_msg: str) -> None:
    return None


class FortyGuardClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        cache: ResponseCache,
        demo_mode: bool = True,
        poll_backoff: Optional[list[float]] = None,
        timeout_s: float = 30.0,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._cache = cache
        self._demo_mode = demo_mode
        self._poll_backoff = poll_backoff or [3, 6, 12, 12, 12]
        self._timeout_s = timeout_s

    def _headers(self) -> dict:
        return {"api-key": self._api_key, "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, *, json: Optional[dict] = None, retries: int = 2) -> dict:
        url = f"{self._base_url}{path}"
        last_exc: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            for attempt in range(retries + 1):
                try:
                    resp = await client.request(method, url, headers=self._headers(), json=json)
                except httpx.HTTPError as exc:
                    last_exc = exc
                    if attempt < retries:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    raise FortyGuardApiError(0, f"Network error calling {path}: {exc}") from exc

                if resp.status_code == 403:
                    raise PlanRestrictedError(403, "Premium plan required for this endpoint.", _safe_json(resp))
                if resp.status_code >= 500 and attempt < retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                if not resp.is_success:
                    body = _safe_json(resp)
                    raise FortyGuardApiError(resp.status_code, body.get("message", resp.text[:300]), body)
                return _safe_json(resp)
        raise FortyGuardApiError(0, f"Exhausted retries calling {path}: {last_exc}")

    # ---- submit + poll primitives -------------------------------------------------

    async def _submit(self, path: str, payload: dict) -> str:
        body = await self._request("POST", path, json=payload)
        activity_id = body.get("data", {}).get("activity_id")
        if not activity_id:
            raise FortyGuardApiError(0, f"No activity_id in response from {path}: {body}")
        return activity_id

    async def get_status(self, activity_id: str) -> dict:
        body = await self._request("GET", f"/v1/status/{activity_id}")
        return body.get("data", body)

    async def poll_until_done(self, activity_id: str, on_progress: ProgressCallback = None) -> dict:
        on_progress = on_progress or _noop
        for i, wait_s in enumerate([0, *self._poll_backoff]):
            if wait_s:
                await asyncio.sleep(wait_s)
            data = await self.get_status(activity_id)
            status = str(data.get("status", "")).lower()
            await on_progress(f"poll #{i}: {status}")
            if status in TERMINAL_SUCCESS:
                return data.get("result", data)
            if status in TERMINAL_FAILURE:
                raise FortyGuardApiError(0, f"Task {activity_id} failed: {data}", data)
        raise FortyGuardApiError(0, f"Task {activity_id} timed out waiting for a terminal status.")

    # ---- high-level tool-facing methods --------------------------------------------

    async def create_heatmap(
        self,
        polygon_aoi: dict,
        date_time: dict,
        granularity: int = 100,
        analytic_type: Optional[str] = None,
        on_progress: ProgressCallback = None,
    ) -> dict:
        on_progress = on_progress or _noop
        polygon_aoi = validate_heatmap_request(polygon_aoi, date_time["start_date"])
        params = {"polygon_aoi": polygon_aoi, "date_time": date_time, "granularity": granularity, "analytic_type": analytic_type}

        cached = self._cache.get("heatmap", params)
        if cached is not None:
            await on_progress("cache hit")
            return {**cached, "from_cache": True}

        if self._demo_mode:
            await on_progress("submitted (demo mode)")
            result = demo_fixtures.fake_heatmap_result(polygon_aoi, date_time, granularity, analytic_type)
            self._cache.put("heatmap", params, result)
            return result

        await on_progress("submitted")
        payload = {k: v for k, v in params.items() if v is not None}
        activity_id = await self._submit("/v1/heatmap", payload)
        result = await self.poll_until_done(activity_id, on_progress)
        result = {"activity_id": activity_id, "result": result, "from_cache": False}
        self._cache.put("heatmap", params, result)
        return result

    async def environmental_parameters(self, point: dict, date_time: dict, on_progress: ProgressCallback = None) -> dict:
        on_progress = on_progress or _noop
        validate_point_request(point["lat"], point["lon"], date_time["start_date"])
        params = {"point": point, "date_time": date_time}

        cached = self._cache.get("env_params", params)
        if cached is not None:
            await on_progress("cache hit")
            return {**cached, "from_cache": True}

        if self._demo_mode:
            await on_progress("submitted (demo mode)")
            result = demo_fixtures.fake_env_params_result(point, date_time)
            self._cache.put("env_params", params, result)
            return result

        await on_progress("submitted")
        activity_id = await self._submit("/v1/env_params", params)
        result = await self.poll_until_done(activity_id, on_progress)
        result = {"activity_id": activity_id, "result": result, "from_cache": False}
        self._cache.put("env_params", params, result)
        return result

    async def _premium_endpoint(self, name: str, path: str, payload: dict, on_progress: ProgressCallback) -> dict:
        on_progress = on_progress or _noop
        if self._demo_mode:
            await on_progress(f"{name} restricted (demo mode)")
            demo_fixtures.raise_premium_restricted(name)
        activity_id = await self._submit(path, payload)
        result = await self.poll_until_done(activity_id, on_progress)
        return {"activity_id": activity_id, "result": result, "from_cache": False}

    async def satellite_segmentation(self, point: dict, date_time: dict, on_progress: ProgressCallback = None) -> dict:
        return await self._premium_endpoint("satellite", "/v1/satellite", {"point": point, "date_time": date_time}, on_progress)

    async def street_view_segmentation(self, point: dict, date_time: dict, on_progress: ProgressCallback = None) -> dict:
        return await self._premium_endpoint("streetview", "/v1/streetview", {"point": point, "date_time": date_time}, on_progress)

    async def heat_intelligence(self, point: dict, date_time: dict, on_progress: ProgressCallback = None) -> dict:
        return await self._premium_endpoint("heat_intelligence", "/v1/heat_intelligence", {"point": point, "date_time": date_time}, on_progress)

    async def fetch_api_key_usage(self) -> dict:
        if self._demo_mode:
            return demo_fixtures.fake_usage_result()
        # Confirmed quirk (live-tested 2026-08-18): this endpoint 422s unless api_key is
        # ALSO present in the JSON body, not just the api-key header.
        body = await self._request("POST", "/v1/system/fetch-api-key-usage", json={"api_key": self._api_key})
        return body


def _safe_json(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except ValueError:
        return {"message": resp.text[:500]}
