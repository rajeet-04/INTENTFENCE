import json

import httpx

_MAX_PROVIDER_RESPONSE_BYTES = 1_000_000


class OllamaWebProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://ollama.com",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(transport=transport, timeout=20.0)

    def search(self, query: str, *, max_results: int = 5) -> dict[str, object]:
        return self._post_json(
            "/api/web_search", {"query": query, "max_results": max_results}
        )

    def fetch(self, url: str) -> dict[str, object]:
        return self._post_json("/api/web_fetch", {"url": url})

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        body = bytearray()
        with self._client.stream(
            "POST",
            f"{self.base_url}{path}",
            headers=self._authorization_headers(),
            json=payload,
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes(chunk_size=64 * 1024):
                if len(chunk) > _MAX_PROVIDER_RESPONSE_BYTES - len(body):
                    raise ValueError("web provider response exceeded the safe size limit")
                body.extend(chunk)
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError("web provider response must be an object")
        return value

    def _authorization_headers(self) -> dict[str, str]:
        key = self.api_key.strip() if self.api_key else ""
        if not key:
            raise RuntimeError("INTENTFENCE_OLLAMA_API_KEY is required for live web access")
        return {"Authorization": f"Bearer {key}"}

    def close(self) -> None:
        self._client.close()
