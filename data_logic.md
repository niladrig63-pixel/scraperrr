# 📊 Data Logic — data_logic.md

> **JSON Structures, Data Flows, and Logic Paths**

---

## Data Schema

### Article Object (Core Payload)
```json
{
  "id": "string (unique hash of url)",
  "title": "string",
  "subtitle": "string | null",
  "url": "string (full article URL)",
  "source": "string (e.g., 'bens_bites', 'the_rundown')",
  "source_display": "string (e.g., 'Ben's Bites', 'The Rundown AI')",
  "author": "string | null",
  "published_date": "string (ISO 8601 date)",
  "scraped_at": "string (ISO 8601 datetime)",
  "thumbnail": "string | null (image URL if available)",
  "summary": "string | null (first ~200 chars of content)",
  "tags": ["string"],
  "is_new": "boolean (published within last 24 hours)"
}
```

### Saved Article (User Bookmark)
```json
{
  "article_id": "string (references Article.id)",
  "saved_at": "string (ISO 8601 datetime)"
}
```

### Scrape State (Tracking)
```json
{
  "source": "string",
  "last_scraped_at": "string (ISO 8601 datetime)",
  "articles_found": "integer",
  "status": "string ('success' | 'error' | 'no_new')",
  "error_message": "string | null"
}
```

## Input Shape (Scraper)
```
Source URL → HTTP GET → HTML Response → Parse → Article[]
```

## Output Shape (API → Frontend)
```json
{
  "articles": [Article],
  "saved_ids": ["string"],
  "last_updated": "string (ISO 8601 datetime)",
  "sources": [
    {
      "name": "string",
      "status": "string",
      "last_scraped": "string"
    }
  ]
}
```

## API Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/articles` | Return all scraped articles (supports `?source=` filter) |
| GET | `/api/articles/saved` | Return user's saved/bookmarked articles |
| POST | `/api/articles/save` | Save/bookmark an article `{ "article_id": "..." }` |
| DELETE | `/api/articles/save/{id}` | Unsave/unbookmark an article |
| POST | `/api/scrape` | Manually trigger a scrape cycle |
| GET | `/api/status` | Return scraper health & last-run status per source |

## Data Flow
```
[Scheduler: 24h] → [Scraper Modules] → [JSON Store] → [API Server] → [Dashboard UI]
                         ↓                    ↑
                  [Source Websites]     [User Bookmarks]
```

## Source-Specific Scraping Logic

### Ben's Bites (Substack)
- **Archive URL:** `https://www.bensbites.com/archive`
- **Pattern:** Each post is an `<a>` link with `/p/` path
- **Title:** Extracted from link text
- **Date:** Extracted from date element near each post
- **Article page:** Follow link to get subtitle/summary

### The Rundown AI
- **URL:** `https://www.therundown.ai/`
- **Pattern:** Article cards with `/p/` links
- **Title:** Extracted from link text
- **Article page:** Follow link to get subtitle/summary/thumbnail

## Current State
> Protocol 0 complete. Schema defined. Awaiting user confirmation to proceed.

---

**Status:** 🟡 AWAITING CONFIRMATION — Payload structure must be approved before coding begins.
