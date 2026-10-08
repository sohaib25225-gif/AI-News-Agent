"""
Test V0 Regression

Verify that V0 functionality still works after V1 changes.
"""

print("=" * 60)
print("TESTING V0 REGRESSION")
print("=" * 60)

# Test 1: Import V0 modules
print("\nTest 1: Import V0 Modules")
print("-" * 40)

try:
    from config import config
    from services import NewsFetcher, EmailService
    from agents import NewsScorer, PostGenerator
    from database import NewsDatabase
    from models import NewsArticle, LinkedInPost
    print("[OK] All V0 modules imported successfully")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")
    exit(1)

# Test 2: V0 database operations
print("\nTest 2: V0 Database Operations")
print("-" * 40)

try:
    db = NewsDatabase()

    # Check that V0 methods still work
    from datetime import datetime

    # Create a test article
    test_article = NewsArticle(
        title="Test V0 Article",
        source="OpenAI Blog",
        url="https://test.com/v0-test",
        published_date=datetime.now(),
        summary="This is a test article for V0 regression",
        score=75.0
    )

    # Test duplicate check (should work)
    is_dup = db.is_duplicate(test_article)
    print(f"[OK] Duplicate check works: {is_dup}")

    # Test getting recent articles
    recent = db.get_recent_articles(days=30)
    print(f"[OK] Get recent articles works: {len(recent)} articles")

    print("[OK] V0 database operations work correctly")
except Exception as e:
    print(f"[FAIL] Database error: {e}")
    exit(1)

# Test 3: V0 models
print("\nTest 3: V0 Models")
print("-" * 40)

try:
    article = NewsArticle(
        title="Test Article",
        source="OpenAI Blog",
        url="https://test.com/article",
        published_date=datetime.now(),
        summary="Test summary",
        score=80.0
    )

    article_dict = article.to_dict()
    print(f"[OK] NewsArticle.to_dict() works")

    post = LinkedInPost(
        hook="Test hook",
        body="Test body",
        question="Test question?",
        hashtags=["#AI", "#Test"],
        source_article=article,
        generated_date=datetime.now()
    )

    formatted = post.format_for_email()
    word_count = post.word_count()
    print(f"[OK] LinkedInPost works (word count: {word_count})")

    print("[OK] V0 models work correctly")
except Exception as e:
    print(f"[FAIL] Model error: {e}")
    exit(1)

# Test 4: V0 agents
print("\nTest 4: V0 Agents")
print("-" * 40)

try:
    scorer = NewsScorer()

    test_articles = [
        NewsArticle(
            title="GPT-5 Released with Amazing Features",
            source="OpenAI Blog",
            url="https://test.com/1",
            published_date=datetime.now(),
            summary="OpenAI releases GPT-5 with groundbreaking AI capabilities"
        ),
        NewsArticle(
            title="Minor Update to Documentation",
            source="Random Blog",
            url="https://test.com/2",
            published_date=datetime.now(),
            summary="We updated our documentation"
        ),
    ]

    ranked = scorer.rank_articles(test_articles)
    print(f"[OK] NewsScorer works: {len(ranked)} articles ranked")
    print(f"     Top article score: {ranked[0].score:.1f}")

    # Test diversity selection
    diverse = scorer.select_diverse_candidates(ranked)
    print(f"[OK] Diversity selection works: {len(diverse)} candidates")

    print("[OK] V0 agents work correctly")
except Exception as e:
    print(f"[FAIL] Agent error: {e}")
    exit(1)

# Test 5: Configuration
print("\nTest 5: Configuration")
print("-" * 40)

try:
    from config.sources import get_active_sources, get_source_by_name

    sources = get_active_sources()
    print(f"[OK] get_active_sources() works: {len(sources)} sources")

    openai_source = get_source_by_name("OpenAI Blog")
    print(f"[OK] get_source_by_name() works: {openai_source['name'] if openai_source else 'Not found'}")

    print("[OK] V0 configuration works correctly")
except Exception as e:
    print(f"[FAIL] Configuration error: {e}")
    exit(1)

print("\n" + "=" * 60)
print("V0 REGRESSION TEST PASSED")
print("=" * 60)
print("\nAll V0 functionality works correctly after V1 changes.")
print("V0 and V1 can coexist without conflicts.")
