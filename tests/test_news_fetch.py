"""
Test News Fetching

This script tests the news fetching functionality.
Run it to verify that RSS feeds are working correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import NewsFetcher
from utils import get_logger

logger = get_logger(__name__)


def test_news_fetching():
    """Test fetching news from RSS feeds."""
    logger.info("Testing news fetching...")

    fetcher = NewsFetcher()
    articles = fetcher.fetch_all()

    print("\n" + "=" * 60)
    print(f"FETCHED {len(articles)} ARTICLES")
    print("=" * 60)

    if articles:
        print("\nSample articles:")
        for i, article in enumerate(articles[:5], 1):
            print(f"\n{i}. {article.title}")
            print(f"   Source: {article.source}")
            print(f"   Published: {article.published_date}")
            print(f"   URL: {article.url}")
            print(f"   Summary: {article.summary[:100]}...")
    else:
        print("No articles fetched!")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_news_fetching()
