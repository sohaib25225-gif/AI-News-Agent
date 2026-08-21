"""
Test News Scoring

This script tests the news scoring algorithm.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import NewsScorer
from models import NewsArticle
from utils import get_logger
import pytz

logger = get_logger(__name__)


def test_scoring():
    """Test news scoring functionality."""
    print("\n" + "=" * 60)
    print("TESTING NEWS SCORING")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    # Create test articles with different characteristics
    articles = [
        NewsArticle(
            title="OpenAI Releases GPT-5: Revolutionary Large Language Model",
            source="OpenAI Blog",
            url="https://example.com/1",
            published_date=datetime.now(tz),
            summary="OpenAI announces GPT-5, a breakthrough in AI with new API and SDK for developers.",
            score=0
        ),
        NewsArticle(
            title="Company Updates Terms of Service",
            source="Random Blog",
            url="https://example.com/2",
            published_date=datetime.now(tz),
            summary="We have updated our terms of service.",
            score=0
        ),
        NewsArticle(
            title="New Python Library for Machine Learning Released on GitHub",
            source="GitHub Blog",
            url="https://example.com/3",
            published_date=datetime.now(tz),
            summary="Open source library for training neural networks with simple API.",
            score=0
        ),
    ]

    print("\nScoring articles...\n")

    ranked = scorer.rank_articles(articles)

    for i, article in enumerate(ranked, 1):
        print(f"{i}. [{article.score:.1f}/100] {article.title}")
        print(f"   Source: {article.source}")
        print(f"   URL: {article.url}")
        print()

    print("=" * 60)
    print(f"BEST ARTICLE: {ranked[0].title}")
    print(f"SCORE: {ranked[0].score}")
    print("=" * 60)


if __name__ == "__main__":
    test_scoring()
