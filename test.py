"""
test.py — B.L.A.S.T. Phase 2: Link Verification
Sandbox for tool verification & unit testing.
Tests that we can actually reach and scrape both sources.
"""

import sys
from core_logic import BensBitesScraper, RundownScraper, fetch_html

def test_connectivity():
    """Test that we can reach both source websites."""
    print("=" * 60)
    print("PHASE 2: LINK VERIFICATION")
    print("=" * 60)

    sources = {
        "Ben's Bites": "https://www.bensbites.com/archive",
        "The Rundown AI": "https://www.therundown.ai/",
    }

    all_ok = True
    for name, url in sources.items():
        print(f"\n[TEST] Connecting to {name} ({url})...")
        html = fetch_html(url)
        if html:
            print(f"  ✓ Connected. Response length: {len(html)} chars")
        else:
            print(f"  ✗ FAILED to connect!")
            all_ok = False

    return all_ok


def test_bens_bites_scraper():
    """Test Ben's Bites scraper returns articles."""
    print("\n" + "-" * 60)
    print("[TEST] Ben's Bites Scraper")
    print("-" * 60)

    scraper = BensBitesScraper()
    articles = scraper.scrape()

    if not articles:
        print("  ✗ No articles found!")
        return False

    print(f"  ✓ Found {len(articles)} articles")
    print(f"\n  Sample articles:")
    for a in articles[:5]:
        date = a.get("published_date", "No date")
        print(f"    - [{date}] {a['title'][:60]}")
        print(f"      URL: {a['url']}")

    # Validate schema
    required_fields = ["id", "title", "url", "source", "source_display", "scraped_at"]
    for field in required_fields:
        if field not in articles[0]:
            print(f"  ✗ Missing required field: {field}")
            return False
    print(f"\n  ✓ Schema valid (all required fields present)")
    return True


def test_rundown_scraper():
    """Test The Rundown AI scraper returns articles."""
    print("\n" + "-" * 60)
    print("[TEST] The Rundown AI Scraper")
    print("-" * 60)

    scraper = RundownScraper()
    articles = scraper.scrape()

    if not articles:
        print("  ✗ No articles found!")
        return False

    print(f"  ✓ Found {len(articles)} articles")
    print(f"\n  Sample articles:")
    for a in articles[:5]:
        date = a.get("published_date", "No date")
        print(f"    - {a['title'][:60]}")
        print(f"      URL: {a['url']}")

    required_fields = ["id", "title", "url", "source", "source_display", "scraped_at"]
    for field in required_fields:
        if field not in articles[0]:
            print(f"  ✗ Missing required field: {field}")
            return False
    print(f"\n  ✓ Schema valid (all required fields present)")
    return True


def test_tools():
    """Test utility functions."""
    from tools import hash_url, parse_date, is_within_24h, truncate_summary, merge_articles
    from datetime import datetime, timezone, timedelta

    print("\n" + "-" * 60)
    print("[TEST] Tools / Utilities")
    print("-" * 60)

    # hash_url
    h1 = hash_url("https://example.com/p/test")
    h2 = hash_url("https://example.com/p/test")
    h3 = hash_url("https://example.com/p/other")
    assert h1 == h2, "Same URL should produce same hash"
    assert h1 != h3, "Different URLs should produce different hashes"
    print("  ✓ hash_url: deterministic and unique")

    # parse_date
    d1 = parse_date("Jan 29, 2026")
    assert d1 is not None, "Should parse 'Jan 29, 2026'"
    d2 = parse_date("FEB 5")
    assert d2 is not None, "Should parse 'FEB 5'"
    print(f"  ✓ parse_date: 'Jan 29, 2026' → {d1.isoformat()}")
    print(f"  ✓ parse_date: 'FEB 5' → {d2.isoformat()}")

    # is_within_24h
    recent = datetime.now(timezone.utc) - timedelta(hours=2)
    old = datetime.now(timezone.utc) - timedelta(days=3)
    assert is_within_24h(recent) == True
    assert is_within_24h(old) == False
    print("  ✓ is_within_24h: correct")

    # truncate_summary
    long_text = "A" * 300
    short = truncate_summary(long_text, 200)
    assert len(short) <= 201  # 200 + ellipsis
    assert truncate_summary("short") == "short"
    print("  ✓ truncate_summary: correct")

    # merge_articles
    existing = [{"id": "a", "title": "First", "published_date": "2026-01-01"}]
    new = [
        {"id": "a", "title": "First Updated", "published_date": "2026-01-01"},
        {"id": "b", "title": "Second", "published_date": "2026-01-02"},
    ]
    merged = merge_articles(existing, new)
    assert len(merged) == 2
    assert merged[0]["id"] == "b"  # newer first
    print("  ✓ merge_articles: dedup + sort correct")

    return True


if __name__ == "__main__":
    print("\n🚀 GLAIDO AI NEWS AGGREGATOR — TEST SUITE\n")

    results = {}
    results["Tools"] = test_tools()
    results["Connectivity"] = test_connectivity()
    results["Ben's Bites"] = test_bens_bites_scraper()
    results["The Rundown"] = test_rundown_scraper()

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}  {name}")
        if not passed:
            all_pass = False

    if all_pass:
        print(f"\n🟢 ALL TESTS PASSED — Ready to proceed to Phase 3 build.")
    else:
        print(f"\n🔴 SOME TESTS FAILED — Fix before proceeding.")
        sys.exit(1)
