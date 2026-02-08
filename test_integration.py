"""Test Reddit scraper + Supabase integration."""
import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"

from core_logic import RedditScraper, scrape_all
from supabase_store import check_connection, save_articles, load_articles, merge_articles

print("=" * 60)
print("TEST: Reddit Scraper")
print("=" * 60)

scraper = RedditScraper()
posts = scraper.scrape()

if posts:
    print(f"\nFound {len(posts)} Reddit posts. Sample:")
    for p in posts[:5]:
        print(f"  - [{p.get('published_date', 'N/A')[:16] if p.get('published_date') else 'N/A'}] {p['title'][:65]}")
        print(f"    {p['subtitle']}")
        print(f"    {p['url'][:80]}")
else:
    print("No Reddit posts found (may be rate-limited, retry in a moment)")

print("\n" + "=" * 60)
print("TEST: Supabase Connection")
print("=" * 60)

ok = check_connection()
print(f"Supabase: {'CONNECTED' if ok else 'FAILED'}")

if ok and posts:
    print("\nUpserting Reddit posts to Supabase...")
    save_articles(posts)
    print("Done. Verifying...")
    stored = load_articles("reddit")
    print(f"Articles in Supabase (reddit): {len(stored)}")

print("\n" + "=" * 60)
print("TEST: Full scrape_all()")
print("=" * 60)

all_articles = scrape_all()
print(f"Total articles from all sources: {len(all_articles)}")
by_source = {}
for a in all_articles:
    by_source[a["source"]] = by_source.get(a["source"], 0) + 1
for src, count in by_source.items():
    print(f"  {src}: {count}")

if ok:
    print("\nMerging all into Supabase...")
    existing = load_articles()
    merged = merge_articles(existing, all_articles)
    print(f"Total in Supabase after merge: {len(merged)}")

print("\nDone!")
