"""
RSS Feed Diagnostic Tool

This script tests each RSS feed individually to diagnose why some sources
are not returning articles.
"""

import sys
from pathlib import Path
import feedparser
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.sources import RSS_SOURCES
from utils import get_logger

logger = get_logger(__name__)


def test_feed(source_name: str, feed_url: str):
    """Test a single RSS feed and report findings."""

    print(f"\n{'='*70}")
    print(f"Testing: {source_name}")
    print(f"URL: {feed_url}")
    print(f"{'='*70}")

    try:
        # Fetch feed
        feed = feedparser.parse(feed_url)

        # Check for errors
        if hasattr(feed, 'bozo') and feed.bozo:
            print(f"⚠️  Feed parsing warning: {feed.get('bozo_exception', 'Unknown error')}")

        # Check feed status
        if hasattr(feed, 'status'):
            print(f"HTTP Status: {feed.status}")
            if feed.status != 200:
                print(f"❌ HTTP error - feed may be unavailable")
                return

        # Check entries
        total_entries = len(feed.entries)
        print(f"Total entries in feed: {total_entries}")

        if total_entries == 0:
            print(f"❌ No entries found in feed")
            return

        # Check entry structure
        print(f"\nFirst entry structure:")
        first_entry = feed.entries[0]

        print(f"  - Has title: {'title' in first_entry}")
        print(f"  - Has link: {'link' in first_entry}")
        print(f"  - Has summary: {'summary' in first_entry or 'description' in first_entry}")
        print(f"  - Has published: {'published' in first_entry or 'updated' in first_entry}")

        # Show first entry details
        if 'title' in first_entry:
            print(f"\nMost recent article:")
            print(f"  Title: {first_entry.title[:80]}...")

            if 'link' in first_entry:
                print(f"  Link: {first_entry.link}")

            # Check date
            if 'published_parsed' in first_entry:
                pub_date = datetime(*first_entry.published_parsed[:6], tzinfo=pytz.UTC)
                print(f"  Published: {pub_date}")

                # Check if within last 24 hours
                now = datetime.now(pytz.UTC)
                age_hours = (now - pub_date).total_seconds() / 3600
                print(f"  Age: {age_hours:.1f} hours ago")

                if age_hours <= 24:
                    print(f"  ✅ Within last 24 hours")
                else:
                    print(f"  ⚠️  Older than 24 hours (would be filtered out)")
            elif 'updated_parsed' in first_entry:
                pub_date = datetime(*first_entry.updated_parsed[:6], tzinfo=pytz.UTC)
                print(f"  Updated: {pub_date}")

                now = datetime.now(pytz.UTC)
                age_hours = (now - pub_date).total_seconds() / 3600
                print(f"  Age: {age_hours:.1f} hours ago")

                if age_hours <= 24:
                    print(f"  ✅ Within last 24 hours")
                else:
                    print(f"  ⚠️  Older than 24 hours (would be filtered out)")
            else:
                print(f"  ⚠️  No date information found")

        # Count recent articles (last 24 hours)
        now = datetime.now(pytz.UTC)
        recent_count = 0

        for entry in feed.entries:
            pub_date = None

            if 'published_parsed' in entry and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.UTC)
                except:
                    continue
            elif 'updated_parsed' in entry and entry.updated_parsed:
                try:
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=pytz.UTC)
                except:
                    continue

            if pub_date:
                age_hours = (now - pub_date).total_seconds() / 3600
                if age_hours <= 24:
                    recent_count += 1

        print(f"\nArticles from last 24 hours: {recent_count}")

        if recent_count > 0:
            print(f"✅ Source has recent content")
        else:
            print(f"⚠️  No articles from last 24 hours (source may not publish daily)")

    except Exception as e:
        print(f"❌ Error testing feed: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Test all RSS feeds."""
    print("\n" + "="*70)
    print("RSS FEED DIAGNOSTIC TOOL")
    print("="*70)
    print(f"Testing {len(RSS_SOURCES)} RSS feeds...")
    print(f"Current time: {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    results = []

    for source in RSS_SOURCES:
        test_feed(source['name'], source['url'])
        results.append(source['name'])

    print("\n" + "="*70)
    print("DIAGNOSTIC COMPLETE")
    print("="*70)
    print(f"Total feeds tested: {len(results)}")
    print("\nSummary:")
    print("  ✅ = Has recent articles (last 24h)")
    print("  ⚠️  = No recent articles OR parsing issues")
    print("  ❌ = Feed error or unavailable")


if __name__ == "__main__":
    main()
