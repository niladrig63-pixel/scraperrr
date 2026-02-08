"""
core_logic.py — Core scraper modules for the Glaido AI News Aggregator.

Each source has its own scraper class that:
  1. Fetches the source HTML
  2. Parses article metadata (title, url, date, subtitle, thumbnail)
  3. Returns a list of Article dicts matching the schema in data_logic.md

The Golden Rule: No logic changes in code before updating the logic docs.
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from tools import hash_url, parse_date, truncate_summary, clean_text, now_iso, is_within_days

# ---------------------------------------------------------------------------
# HTTP Helpers
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_html(url: str, timeout: int = 15) -> str | None:
    """Fetch HTML from a URL. Returns None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Ben's Bites Scraper (Substack)
# ---------------------------------------------------------------------------
class BensBitesScraper:
    """Scraper for Ben's Bites newsletter on Substack."""

    SOURCE = "bens_bites"
    SOURCE_DISPLAY = "Ben's Bites"
    ARCHIVE_URL = "https://www.bensbites.com/archive"
    BASE_URL = "https://www.bensbites.com"

    def scrape(self) -> list[dict]:
        """Scrape the archive page and return article dicts."""
        print(f"[SCRAPER] Fetching {self.SOURCE_DISPLAY} archive...")
        html = fetch_html(self.ARCHIVE_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        articles = []
        seen_urls = set()

        # Substack archive uses <time datetime="..."> elements alongside
        # post links. We pair them by walking the DOM.
        # Strategy: find all <time> elements, then find the nearest /p/ links.
        time_elements = soup.find_all("time")

        for time_el in time_elements:
            # Get the ISO datetime from the <time> element
            dt_str = time_el.get("datetime")
            if not dt_str:
                continue

            try:
                published_date = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                published_date = parse_date(time_el.get_text())

            # Walk up to find the containing post wrapper, then find the /p/ link
            wrapper = time_el.find_parent(["div", "article", "section", "tr"])
            # If direct parent is too small, go up further
            for _ in range(5):
                if wrapper is None:
                    break
                links = wrapper.find_all("a", href=lambda h: h and "/p/" in h)
                if links:
                    break
                wrapper = wrapper.parent

            if not wrapper:
                continue

            # Process all /p/ links found near this time element
            for link in wrapper.find_all("a", href=lambda h: h and "/p/" in h):
                href = link["href"]
                if href.startswith("/"):
                    full_url = self.BASE_URL + href
                elif href.startswith("http"):
                    full_url = href
                else:
                    continue

                full_url = full_url.split("?")[0]
                if full_url in seen_urls:
                    continue

                title = clean_text(link.get_text())
                if not title or len(title) < 5:
                    continue
                seen_urls.add(full_url)

                # Look for subtitle text (second link or preview text)
                subtitle = None
                all_links = wrapper.find_all("a", href=lambda h: h and "/p/" in h)
                for other_link in all_links:
                    other_text = clean_text(other_link.get_text())
                    if other_text and other_text != title and len(other_text) > 10:
                        subtitle = other_text
                        break

                article = {
                    "id": hash_url(full_url),
                    "title": title,
                    "subtitle": subtitle,
                    "url": full_url,
                    "source": self.SOURCE,
                    "source_display": self.SOURCE_DISPLAY,
                    "author": "Ben Tossell",
                    "published_date": published_date.isoformat() if published_date else None,
                    "scraped_at": now_iso(),
                    "thumbnail": None,
                    "summary": subtitle,
                    "tags": ["AI", "Newsletter"],
                    "is_new": False,
                }
                articles.append(article)
                break  # one article per time element

        print(f"[SCRAPER] {self.SOURCE_DISPLAY}: Found {len(articles)} articles")
        return articles


# ---------------------------------------------------------------------------
# The Rundown AI Scraper
# ---------------------------------------------------------------------------
class RundownScraper:
    """Scraper for The Rundown AI newsletter."""

    SOURCE = "the_rundown"
    SOURCE_DISPLAY = "The Rundown AI"
    URL = "https://www.therundown.ai/"
    BASE_URL = "https://www.therundown.ai"

    def scrape(self) -> list[dict]:
        """Scrape the homepage and return article dicts."""
        print(f"[SCRAPER] Fetching {self.SOURCE_DISPLAY}...")
        html = fetch_html(self.URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        articles = []
        seen_urls = set()

        # The Rundown: articles are linked with /p/ pattern
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/p/" not in href:
                continue

            if href.startswith("/"):
                full_url = self.BASE_URL + href
            elif href.startswith("http"):
                full_url = href
            else:
                continue

            full_url = full_url.split("?")[0]

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Extract title — the link text often contains the full title
            title_text = clean_text(link.get_text())
            if not title_text or len(title_text) < 10:
                continue

            # Sometimes the link text contains title + subtitle concatenated
            # Try to split smartly
            title = title_text
            subtitle = None

            # Look for "PLUS:" pattern which separates title from subtitle
            if "PLUS:" in title_text:
                parts = title_text.split("PLUS:", 1)
                title = clean_text(parts[0])
                subtitle = clean_text("PLUS: " + parts[1]) if len(parts) > 1 else None

            # Try to find thumbnail image
            thumbnail = None
            parent = link.find_parent(["div", "article", "li"])
            if parent:
                img = parent.find("img", src=True)
                if img and "logo" not in img.get("src", "").lower():
                    thumbnail = img["src"]

            article = {
                "id": hash_url(full_url),
                "title": title,
                "subtitle": subtitle,
                "url": full_url,
                "source": self.SOURCE,
                "source_display": self.SOURCE_DISPLAY,
                "author": "Rowan Cheung",
                "published_date": None,  # Homepage doesn't always show dates
                "scraped_at": now_iso(),
                "thumbnail": thumbnail,
                "summary": subtitle or truncate_summary(title_text),
                "tags": ["AI", "Newsletter"],
                "is_new": False,
            }
            articles.append(article)

        print(f"[SCRAPER] {self.SOURCE_DISPLAY}: Found {len(articles)} articles")
        return articles


# ---------------------------------------------------------------------------
# Reddit AI Scraper
# ---------------------------------------------------------------------------
class RedditScraper:
    """Scraper for AI-related subreddits using RSS/Atom feeds."""

    SOURCE = "reddit"
    SOURCE_DISPLAY = "Reddit AI"
    SUBREDDITS = ["artificial", "MachineLearning", "singularity"]

    def scrape(self) -> list[dict]:
        """Scrape recent posts from AI subreddits via RSS feeds."""
        print(f"[SCRAPER] Fetching {self.SOURCE_DISPLAY} ({', '.join(self.SUBREDDITS)})...")
        articles = []
        seen_urls = set()

        for subreddit in self.SUBREDDITS:
            try:
                posts = self._fetch_subreddit(subreddit)
                for post in posts:
                    if post["url"] not in seen_urls:
                        seen_urls.add(post["url"])
                        articles.append(post)
            except Exception as e:
                print(f"[ERROR] Reddit r/{subreddit} failed: {e}")

        print(f"[SCRAPER] {self.SOURCE_DISPLAY}: Found {len(articles)} posts")
        return articles

    def _fetch_subreddit(self, subreddit: str) -> list[dict]:
        """Fetch posts from a subreddit via the public Atom RSS feed."""
        url = f"https://www.reddit.com/r/{subreddit}/.rss"
        headers = {
            "User-Agent": "Glaido-AI-Aggregator/1.0 (educational project)",
            "Accept": "application/atom+xml,application/xml,text/xml",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[ERROR] Reddit r/{subreddit} RSS: {e}")
            return []

        try:
            soup = BeautifulSoup(resp.text, "xml")
        except Exception:
            soup = BeautifulSoup(resp.text, "html.parser")
        entries = soup.find_all("entry")
        articles = []

        for entry in entries[:20]:
            # Title
            title_el = entry.find("title")
            if not title_el:
                continue
            title = clean_text(title_el.get_text())
            if not title or len(title) < 10:
                continue

            # URL (link element)
            link_el = entry.find("link")
            post_url = link_el.get("href", "") if link_el else ""
            if not post_url:
                continue
            post_url = post_url.split("?")[0]

            # Published date
            updated_el = entry.find("updated")
            published_date = None
            if updated_el:
                try:
                    published_date = datetime.fromisoformat(
                        updated_el.get_text().strip().replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            # Author
            author_name = "unknown"
            author_el = entry.find("author")
            if author_el:
                name_el = author_el.find("name")
                if name_el:
                    author_name = name_el.get_text().strip().lstrip("/u/")

            # Content / summary — extract thumbnail and text preview from HTML content
            thumbnail = None
            summary_text = ""
            content_el = entry.find("content")
            if content_el:
                content_html = content_el.get_text()
                content_soup = BeautifulSoup(content_html, "html.parser")

                # Look for images
                img = content_soup.find("img", src=True)
                if img and img["src"].startswith("http"):
                    thumbnail = img["src"]

                # Get text preview
                text = content_soup.get_text(separator=" ", strip=True)
                summary_text = truncate_summary(text, 200) if text else ""

            # Category tag (flair)
            category_el = entry.find("category")
            flair = category_el.get("label", "") if category_el else ""

            subtitle = f"r/{subreddit}"
            if flair:
                subtitle += f" \u00b7 {flair}"

            articles.append({
                "id": hash_url(post_url),
                "title": title,
                "subtitle": subtitle,
                "url": post_url,
                "source": self.SOURCE,
                "source_display": self.SOURCE_DISPLAY,
                "author": f"u/{author_name}",
                "published_date": published_date.isoformat() if published_date else None,
                "scraped_at": now_iso(),
                "thumbnail": thumbnail,
                "summary": summary_text or subtitle,
                "tags": ["AI", "Reddit", f"r/{subreddit}"],
                "is_new": False,
            })

        return articles


# ---------------------------------------------------------------------------
# Scraper Registry
# ---------------------------------------------------------------------------
SCRAPERS = {
    "bens_bites": BensBitesScraper,
    "the_rundown": RundownScraper,
    "reddit": RedditScraper,
}


def scrape_all() -> list[dict]:
    """Run all scrapers and return combined article list."""
    all_articles = []
    for name, scraper_cls in SCRAPERS.items():
        try:
            scraper = scraper_cls()
            articles = scraper.scrape()
            all_articles.extend(articles)
        except Exception as e:
            print(f"[ERROR] Scraper '{name}' failed: {e}")
    return all_articles


def scrape_source(source: str) -> list[dict]:
    """Run a specific scraper by source key."""
    scraper_cls = SCRAPERS.get(source)
    if not scraper_cls:
        print(f"[ERROR] Unknown source: {source}")
        return []
    try:
        return scraper_cls().scrape()
    except Exception as e:
        print(f"[ERROR] Scraper '{source}' failed: {e}")
        return []
