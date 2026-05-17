"""
crunchbase_client.py — Crunchbase API v4 Client

Docs: https://data.crunchbase.com/docs/using-the-api
Requires: CRUNCHBASE_API_KEY in environment

Fetches:
  - Company profile (description, HQ, founded, employees)
  - Funding rounds
  - Key investors
  - Founders & leadership
  - Acquisitions
"""
import os
import httpx
from typing import Optional

BASE_URL = "https://api.crunchbase.com/api/v4"


class CrunchbaseClient:
    def __init__(self):
        self.api_key = os.environ.get("CRUNCHBASE_API_KEY", "")
        self.timeout = 20.0

    def get_company(self, company_name: str, slug: Optional[str] = None) -> dict:
        """
        Fetch company data from Crunchbase.
        If no slug provided, auto-generates one from company name.
        Falls back gracefully if API key is missing.
        """
        if not self.api_key:
            return self._mock_response(company_name)

        # Derive slug from name if not provided
        if not slug:
            slug = company_name.lower().replace(" ", "-").replace(".", "").replace(",", "")

        try:
            entity = self._fetch_entity(slug)
            funding = self._fetch_funding_rounds(slug)
            people = self._fetch_people(slug)

            return {
                "company": entity,
                "funding_rounds": funding,
                "key_people": people,
            }
        except Exception as e:
            return {"error": str(e), "company_name": company_name}

    def _fetch_entity(self, slug: str) -> dict:
        url = f"{BASE_URL}/entities/organizations/{slug}"
        params = {
            "user_key": self.api_key,
            "field_ids": ",".join([
                "short_description", "long_description", "founded_on",
                "headquarters_identifiers", "num_employees_enum",
                "stock_exchange_symbol", "stock_symbol",
                "last_funding_type", "last_funding_total",
                "total_funding_usd", "num_funding_rounds",
                "website_url", "categories", "operating_status",
            ]),
        }
        r = httpx.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("properties", {})

    def _fetch_funding_rounds(self, slug: str) -> list[dict]:
        url = f"{BASE_URL}/entities/organizations/{slug}/cards/funding_rounds"
        params = {
            "user_key": self.api_key,
            "field_ids": "announced_on,investment_type,money_raised,num_investors,lead_investor_identifiers",
            "order": "announced_on DESC",
            "limit": 10,
        }
        r = httpx.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        items = r.json().get("entities", [])
        return [i.get("properties", {}) for i in items]

    def _fetch_people(self, slug: str) -> list[dict]:
        url = f"{BASE_URL}/entities/organizations/{slug}/cards/founders"
        params = {
            "user_key": self.api_key,
            "field_ids": "first_name,last_name,title,short_bio",
            "limit": 10,
        }
        r = httpx.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        items = r.json().get("entities", [])
        return [i.get("properties", {}) for i in items]

    def _mock_response(self, company_name: str) -> dict:
        """Returns a structured empty response when no API key is set."""
        return {
            "company": {
                "short_description": f"No Crunchbase data available for {company_name} (API key not configured).",
                "note": "Set CRUNCHBASE_API_KEY in .env to enable Crunchbase integration.",
            },
            "funding_rounds": [],
            "key_people": [],
        }


# ── Crunchbase Search (for name → slug resolution) ─────────────────────────────

def search_company_slug(company_name: str, api_key: str) -> Optional[str]:
    """Search Crunchbase for a company and return its slug."""
    url = f"{BASE_URL}/searches/organizations"
    payload = {
        "field_ids": ["identifier", "short_description"],
        "query": [
            {
                "type": "predicate",
                "field_id": "facet_ids",
                "operator_id": "includes",
                "values": ["company"],
            }
        ],
        "predicate_values_scope": "all",
        "limit": 5,
        "name": company_name,
    }
    try:
        r = httpx.post(
            url,
            json=payload,
            params={"user_key": api_key},
            timeout=10.0,
        )
        r.raise_for_status()
        entities = r.json().get("entities", [])
        if entities:
            return entities[0].get("identifier", {}).get("permalink")
    except Exception:
        pass
    return None