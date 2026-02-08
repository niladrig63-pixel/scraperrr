"""
supabase_store.py — Supabase persistence layer for Glaido AI News Aggregator.

Replaces local JSON storage (tools.py) with Supabase REST API calls.
Uses requests directly (no supabase-py needed — avoids Python 3.14 compat issues).

Per B.L.A.S.T. Data-First Rule: this module implements the exact same
interface as the JSON storage functions in tools.py.
"""

import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

REST_URL = f"{SUPABASE_URL}/rest/v1"


# ---------------------------------------------------------------------------
# Low-level REST helpers
# ---------------------------------------------------------------------------
def _get(table: str, params: dict = None) -> list[dict]:
    """GET rows from a Supabase table."""
    resp = requests.get(f"{REST_URL}/{table}", headers=HEADERS, params=params or {})
    resp.raise_for_status()
    return resp.json()


def _post(table: str, data: list[dict] | dict, upsert: bool = False) -> list[dict]:
    """POST (insert) rows into a Supabase table. Supports upsert."""
    headers = {**HEADERS}
    if upsert:
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
    resp = requests.post(f"{REST_URL}/{table}", headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


def _delete(table: str, params: dict) -> bool:
    """DELETE rows from a Supabase table using query params as filters."""
    resp = requests.delete(f"{REST_URL}/{table}", headers=HEADERS, params=params)
    resp.raise_for_status()
    return True


def _patch(table: str, data: dict, params: dict) -> list[dict]:
    """PATCH (update) rows in a Supabase table."""
    resp = requests.patch(f"{REST_URL}/{table}", headers=HEADERS, json=data, params=params)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------
def load_articles(source: str = None) -> list[dict]:
    """Load all articles, optionally filtered by source. Sorted by published_date DESC."""
    params = {"order": "published_date.desc.nullslast", "limit": "200"}
    if source:
        params["source"] = f"eq.{source}"
    rows = _get("articles", params)
    # Convert tags from Postgres array to Python list if needed
    for r in rows:
        if isinstance(r.get("tags"), str):
            r["tags"] = [t.strip() for t in r["tags"].strip("{}").split(",") if t.strip()]
    return rows


def save_articles(articles: list[dict]):
    """Upsert articles into Supabase (insert new, update existing by id)."""
    if not articles:
        return
    # Clean data for Supabase
    clean = []
    for a in articles:
        row = {
            "id": a["id"],
            "title": a.get("title"),
            "subtitle": a.get("subtitle"),
            "url": a.get("url"),
            "source": a.get("source"),
            "source_display": a.get("source_display"),
            "author": a.get("author"),
            "published_date": a.get("published_date"),
            "scraped_at": a.get("scraped_at"),
            "thumbnail": a.get("thumbnail"),
            "summary": a.get("summary"),
            "tags": a.get("tags", []),
            "is_new": a.get("is_new", False),
        }
        clean.append(row)

    # Upsert in batches of 50 (Supabase limit safety)
    batch_size = 50
    for i in range(0, len(clean), batch_size):
        batch = clean[i:i + batch_size]
        try:
            _post("articles", batch, upsert=True)
        except requests.HTTPError as e:
            print(f"[SUPABASE] Error upserting articles batch {i}: {e}")
            print(f"[SUPABASE] Response: {e.response.text if e.response else 'N/A'}")


def merge_articles(existing: list[dict], new_articles: list[dict]) -> list[dict]:
    """
    Merge new articles with existing, dedup by ID.
    Then upsert ALL into Supabase.
    Returns the merged list.
    """
    by_id = {a["id"]: a for a in existing}
    for a in new_articles:
        by_id[a["id"]] = a
    merged = list(by_id.values())
    merged.sort(key=lambda a: a.get("published_date") or "", reverse=True)

    # Upsert only the new/updated articles to Supabase
    save_articles(new_articles)

    return merged


# ---------------------------------------------------------------------------
# Saved Articles (Bookmarks)
# ---------------------------------------------------------------------------
def load_saved_ids() -> list[dict]:
    """Load all saved article entries."""
    return _get("saved_articles", {"order": "saved_at.desc"})


def save_bookmark(article_id: str) -> dict:
    """Save/bookmark an article. Returns the saved entry."""
    try:
        result = _post("saved_articles", {
            "article_id": article_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })
        return result[0] if result else {}
    except requests.HTTPError as e:
        if e.response and e.response.status_code == 409:
            return {"status": "already_saved", "article_id": article_id}
        raise


def remove_bookmark(article_id: str) -> bool:
    """Remove a bookmark."""
    return _delete("saved_articles", {"article_id": f"eq.{article_id}"})


def get_saved_article_ids() -> set[str]:
    """Get just the set of saved article IDs."""
    entries = _get("saved_articles", {"select": "article_id"})
    return {e["article_id"] for e in entries}


# ---------------------------------------------------------------------------
# Scrape State
# ---------------------------------------------------------------------------
def load_scrape_state() -> dict:
    """Load scrape state for all sources."""
    rows = _get("scrape_state")
    return {r["source"]: r for r in rows}


def save_scrape_state(state: dict):
    """Upsert scrape state entries."""
    rows = list(state.values()) if isinstance(state, dict) else state
    if not rows:
        return
    try:
        _post("scrape_state", rows, upsert=True)
    except requests.HTTPError as e:
        print(f"[SUPABASE] Error saving scrape state: {e}")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
def check_connection() -> bool:
    """Verify Supabase connection by querying the articles table."""
    try:
        _get("articles", {"limit": "1"})
        return True
    except Exception as e:
        print(f"[SUPABASE] Connection check failed: {e}")
        return False
