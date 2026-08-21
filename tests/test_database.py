"""
Test Database Functionality

This script tests database operations:
- Creating tables
- Saving articles
- Checking duplicates
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import NewsDatabase
from models import NewsArticle
from utils import get_logger
import pytz

logger = get_logger(__name__)


def test_database():
    """Test database operations."""
    print("\n" + "=" * 60)
    print("TESTING DATABASE OPERATIONS")
    print("=" * 60)

    # Use a test database
    test_db_path = "database/test_news.db"
    db = NewsDatabase(test_db_path)

    # Create a sample article
    tz = pytz.timezone("Asia/Karachi")
    article = NewsArticle(
        title="Test AI Article: GPT-5 Released",
        source="OpenAI Blog",
        url="https://example.com/gpt5",
        published_date=datetime.now(tz),
        summary="This is a test article about GPT-5 release.",
        score=85.5
    )

    print("\n1. Saving article to database...")
    success = db.save_posted_article(article)
    print(f"   Result: {'SUCCESS' if success else 'FAILED'}")

    print("\n2. Checking if article is duplicate...")
    is_dup = db.is_duplicate(article)
    print(f"   Result: {'DUPLICATE FOUND' if is_dup else 'NOT DUPLICATE'}")

    print("\n3. Getting recent articles...")
    recent = db.get_recent_articles(days=7)
    print(f"   Found {len(recent)} recent articles")

    if recent:
        print("\n   Recent articles:")
        for art in recent:
            print(f"   - {art['title']}")
            print(f"     Posted: {art['posted_date']}")

    print("\n4. Testing duplicate detection with similar title...")
    similar_article = NewsArticle(
        title="Test AI Article: GPT-5 Released Today",
        source="Another Source",
        url="https://example.com/gpt5-different",
        published_date=datetime.now(tz),
        summary="Similar article.",
        score=80.0
    )
    is_dup = db.is_duplicate(similar_article)
    print(f"   Result: {'DUPLICATE FOUND (Good!)' if is_dup else 'NOT DUPLICATE (Unexpected)'}")

    print("\n" + "=" * 60)
    print("DATABASE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_database()
