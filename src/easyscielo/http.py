"""HTTP client for easyscielo with User-Agent rotation, retries, and caching."""

import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any, Optional, Union

import httpx

from easyscielo.errors import BackendError, BlockedError

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/15.1 Safari/605.1.15"
    ),
]

FIXED_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BLOCKED_ERROR_MESSAGE = (
    "Access denied with HTTP 403. SciELO may be blocking automated requests. "
    "Try slowing down or rotating headers."
)


class HttpClient:
    """HTTP client wrapping httpx.Client with scraping features."""

    def __init__(
        self,
        delay: tuple[float, float] = (1.0, 3.0),
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        cache_dir: Optional[Union[str, Path]] = None,
        transport: Optional[httpx.BaseTransport] = None,
        timeout: float = 30.0,
    ) -> None:
        self.delay = delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._client = httpx.Client(
            transport=transport,
            timeout=timeout,
            follow_redirects=True,
        )

    def _should_delay(self) -> bool:
        return self.delay[0] > 0 or self.delay[1] > 0

    def _apply_delay(self) -> None:
        if self._should_delay():
            sleep_time = random.uniform(self.delay[0], self.delay[1])
            time.sleep(sleep_time)

    def _get_headers(self, user_headers: Optional[dict] = None) -> dict[str, str]:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            **FIXED_HEADERS,
        }
        if user_headers:
            headers.update(user_headers)
        return headers

    def _get_cache_key(self, url: str, params: Optional[dict] = None) -> str:
        req = self._client.build_request("GET", url, params=params)
        full_url = str(req.url)
        return hashlib.sha256(full_url.encode("utf-8")).hexdigest()

    def _read_cache(
        self, cache_key: str, request: httpx.Request
    ) -> Optional[httpx.Response]:
        if not self.cache_dir:
            return None
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return httpx.Response(
                status_code=data["status_code"],
                headers=data["headers"],
                content=data["content"].encode("utf-8"),
                request=request,
            )
        except Exception:
            return None

    def _write_cache(self, cache_key: str, response: httpx.Response) -> None:
        if not self.cache_dir:
            return
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform GET request with caching, UA rotation, delay, and retries."""
        cache_key = self._get_cache_key(url, params=params)
        req = self._client.build_request("GET", url, params=params)

        cached_response = self._read_cache(cache_key, req)
        if cached_response is not None:
            return cached_response

        self._apply_delay()

        last_exception: Optional[Exception] = None
        response: Optional[httpx.Response] = None

        for attempt in range(1, self.max_retries + 1):
            req_headers = self._get_headers(headers)
            try:
                response = self._client.get(
                    url, params=params, headers=req_headers, **kwargs
                )
            except httpx.RequestError as exc:
                last_exception = exc
                if attempt == self.max_retries:
                    raise BackendError(
                        f"Request failed after {self.max_retries} attempts: {exc}"
                    ) from exc
                if self._should_delay():
                    time.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                continue

            if response.status_code == 403:
                raise BlockedError(BLOCKED_ERROR_MESSAGE)

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt < self.max_retries:
                    if self._should_delay():
                        time.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                    continue
                else:
                    raise BackendError(
                        f"HTTP error {response.status_code} after "
                        f"{self.max_retries} attempts."
                    )

            if response.status_code == 200:
                self._write_cache(cache_key, response)
            return response

        if last_exception:
            raise BackendError(
                f"Request failed after {self.max_retries} attempts: {last_exception}"
            ) from last_exception
        if response is not None:
            return response
        raise BackendError("Request failed without response.")

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
