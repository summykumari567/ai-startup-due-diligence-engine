"""
tavily_client.py — Tavily AI Search Client

Tavily provides real-time web search optimised for AI agents.
Docs: https://docs.tavily.com

Used for:
  - News and press coverage
  - Patent search (Google Patents, Justia)
  - Legal/court record search
  - Team and executive background research
"""
import os
from typing import Optional
import httpx

BASE_URL = "https://api.tavily.com"


class TavilyClient:
    def __init__(self):
        self.api_key = os.environ.get("TAVILY_API_KEY", "")
        self.timeout = 30.0

    def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "advanced",   # "basic" | "advanced"
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
        include_raw_content: bool = False,
        topic: str = "general",            # "general" | "news"
    ) -> list[dict]:
        """
        Run a Tavily search and return list of result dicts.
        Each result: {title, url, content, score, published_date}
        """
        if not self.api_key:
            return self._mock_results(query)

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": False,
            "include_raw_content": include_raw_content,
            "topic": topic,
        }
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        try:
            r = httpx.post(
                f"{BASE_URL}/search",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json().get("results", [])
        except httpx.HTTPError as e:
            print(f"[TavilyClient] Search error for '{query}': {e}")
            return []

    def search_news(self, query: str, max_results: int = 5) -> list[dict]:
        """Convenience wrapper for news-specific search."""
        return self.search(query, max_results=max_results, topic="news", search_depth="advanced")

    def extract(self, urls: list[str]) -> dict:
        """
        Extract full content from specific URLs.
        Returns {results: [{url, raw_content, ...}]}
        """
        if not self.api_key:
            return {"results": []}
        try:
            r = httpx.post(
                f"{BASE_URL}/extract",
                json={"api_key": self.api_key, "urls": urls},
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[TavilyClient] Extract error: {e}")
            return {"results": []}

    def _mock_results(self, query: str) -> list[dict]:
        """Graceful fallback when no API key is configured."""
        return [
            {
                "title": f"[Mock] Tavily result for: {query}",
                "url": "https://example.com",
                "content": "Set TAVILY_API_KEY in .env to enable real web search.",
                "score": 0.0,
                "published_date": "",
            }
        ]