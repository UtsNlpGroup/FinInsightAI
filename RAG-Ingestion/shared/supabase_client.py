"""
Fetches the list of tracked companies from the Supabase `public.companies` table
using the Supabase REST API (no extra client library needed — just `requests`).

Required env vars (in RAG-Ingestion/env or the environment):
  SUPABASE_URL   – e.g. https://xyzxyz.supabase.co
  SUPABASE_KEY   – service-role or anon key
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

from shared import config as cfg


@dataclass
class Company:
    ticker: str
    company_name: str
    sector: str | None


def fetch_companies() -> list[Company]:
    """
    Query the `public.companies` table in Supabase and return a list of
    Company objects ordered by ticker.

    Returns:
        List of Company objects with ticker, company_name, sector.

    Raises:
        EnvironmentError: If SUPABASE_URL or SUPABASE_KEY are not set.
        RuntimeError:     If the Supabase REST request fails.
    """
    load_dotenv()

    url = os.getenv(cfg.SUPABASE_URL_KEY)
    key = os.getenv(cfg.SUPABASE_KEY_KEY)

    if not url:
        raise EnvironmentError(f"Missing required env var: {cfg.SUPABASE_URL_KEY}")
    if not key:
        raise EnvironmentError(f"Missing required env var: {cfg.SUPABASE_KEY_KEY}")

    endpoint = f"{url.rstrip('/')}/rest/v1/companies"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    params = {
        "select": "ticker,company_name,sector",
        "order": "ticker.asc",
    }

    print(f"[Supabase] Sending GET request to: {endpoint}")
    response = requests.get(endpoint, headers=headers, params=params, timeout=15)
    print(f"[Supabase] Response received with status code: {response.status_code}")

    if not response.ok:
        raise RuntimeError(
            f"Supabase request failed [{response.status_code}]: {response.text}"
        )

    rows = response.json()
    print(f"[Supabase] Raw response body: {response.text[:500]}")
    return [
        Company(
            ticker=row["ticker"],
            company_name=row.get("company_name", row["ticker"]),
            sector=row.get("sector"),
        )
        for row in rows
    ]
