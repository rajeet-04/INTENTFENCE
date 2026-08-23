import httpx


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
        response = self._client.post(
            f"{self.base_url}/api/web_search",
            headers=self._authorization_headers(),
            json={"query": query, "max_results": max_results},
        )
        response.raise_for_status()
        return response.json()

    def fetch(self, url: str) -> dict[str, object]:
        response = self._client.post(
            f"{self.base_url}/api/web_fetch",
            headers=self._authorization_headers(),
            json={"url": url},
        )
        response.raise_for_status()
        return response.json()

    def _authorization_headers(self) -> dict[str, str]:
        key = self.api_key.strip() if self.api_key else ""
        if not key:
            raise RuntimeError("INTENTFENCE_OLLAMA_API_KEY is required for live web access")
        return {"Authorization": f"Bearer {key}"}

    def close(self) -> None:
        self._client.close()
