"""
tools.py — Atomized utility functions for the Glaido AI News Aggregator.
All functions are pure, deterministic, and independently testable.
No user interaction or side effects inside domain functions.
"""

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
ARTICLES_FILE = DATA_DIR / "articles.json"
SAVED_FILE = DATA_DIR / "saved.json"
SCRAPE_STATE_FILE = DATA_DIR / "scrape_state.json"


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def hash_url(url: str) -> str:
    """Generate a deterministic unique ID from a URL using SHA-256."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Date Utilities
# ---------------------------------------------------------------------------
def parse_date(date_str: str) -> datetime | None:
    """
    Attempt to parse a date string from various newsletter formats.
    Returns a timezone-aware datetime or None on failure.
    """
    formats = [
        "%b %d, %Y",   # "Jan 29, 2026"
        "%b %d",        # "Jan 29" (assume current year)
        "%B %d, %Y",   # "January 29, 2026"
        "%B %d",        # "January 29"
        "%Y-%m-%d",     # "2026-01-29"
        "%d %b %Y",    # "29 Jan 2026"
        "%d %B %Y",    # "29 January 2026"
    ]
    cleaned = date_str.strip().upper().replace(",", ",").replace("  ", " ")
    # Normalize month abbreviations
    cleaned_lower = date_str.strip()

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned_lower, fmt)
            # If no year was in the format, assume current year
            if "%Y" not in fmt:
                dt = dt.replace(year=datetime.now().year)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def is_within_24h(dt: datetime) -> bool:
    """Check if a datetime is within the last 24 hours."""
    if dt is None:
        return False
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt) <= timedelta(hours=24)


def is_within_days(dt: datetime, days: int = 7) -> bool:
    """Check if a datetime is within the last N days."""
    if dt is None:
        return False
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt) <= timedelta(days=days)


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Text Utilities
# ---------------------------------------------------------------------------
def truncate_summary(text: str | None, max_len: int = 200) -> str | None:
    """Truncate text to max_len characters, appending '…' if trimmed."""
    if not text:
        return None
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def clean_text(text: str | None) -> str | None:
    """Remove excess whitespace and normalize a text string."""
    if not text:
        return None
    return " ".join(text.split()).strip()


# ---------------------------------------------------------------------------
# JSON File I/O
# ---------------------------------------------------------------------------
def ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict | list:
    """Load JSON from a file. Returns empty dict/list if file doesn't exist."""
    if not path.exists():
        return [] if "articles" in str(path) or "saved" in str(path) else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict | list):
    """Save data to a JSON file, creating the directory if needed."""
    ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Article Storage
# ---------------------------------------------------------------------------
def load_articles() -> list[dict]:
    """Load all stored articles."""
    return load_json(ARTICLES_FILE)


def save_articles(articles: list[dict]):
    """Save all articles to disk."""
    save_json(ARTICLES_FILE, articles)


def load_saved_ids() -> list[dict]:
    """Load saved/bookmarked article entries."""
    return load_json(SAVED_FILE)


def save_saved_ids(saved: list[dict]):
    """Save bookmarked article entries to disk."""
    save_json(SAVED_FILE, saved)


def load_scrape_state() -> dict:
    """Load the scrape state tracking object."""
    data = load_json(SCRAPE_STATE_FILE)
    return data if isinstance(data, dict) else {}


def save_scrape_state(state: dict):
    """Save scrape state to disk."""
    save_json(SCRAPE_STATE_FILE, state)


def merge_articles(existing: list[dict], new_articles: list[dict]) -> list[dict]:
    """
    Merge new articles into existing list, deduplicating by ID.
    New articles with the same ID update the existing entry.
    Returns the merged list sorted by published_date descending.
    """
    by_id = {a["id"]: a for a in existing}
    for article in new_articles:
        by_id[article["id"]] = article
    merged = list(by_id.values())
    merged.sort(key=lambda a: a.get("published_date") or "", reverse=True)
    return merged
