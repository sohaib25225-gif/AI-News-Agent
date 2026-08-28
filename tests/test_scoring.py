"""
Test News Scoring

This script tests the news scoring algorithm and diversity selection.
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


def test_diversity_basic():
    """TEST 1: Per-source selection with quality threshold."""
    print("\n" + "=" * 60)
    print("TEST 1: PER-SOURCE SELECTION")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    # Create articles with multiple sources
    articles = [
        NewsArticle("Article 1", "Source A", "http://1", datetime.now(tz), "text", score=90),
        NewsArticle("Article 2", "Source A", "http://2", datetime.now(tz), "text", score=85),
        NewsArticle("Article 3", "Source A", "http://3", datetime.now(tz), "text", score=80),
        NewsArticle("Article 4", "Source A", "http://4", datetime.now(tz), "text", score=75),
        NewsArticle("Article 5", "Source B", "http://5", datetime.now(tz), "text", score=70),
        NewsArticle("Article 6", "Source C", "http://6", datetime.now(tz), "text", score=65),
    ]

    candidates = scorer.select_diverse_candidates(articles, quality_threshold=60)

    # Verify one article per source (best from each)
    source_counts = {}
    for article in candidates:
        source_counts[article.source] = source_counts.get(article.source, 0) + 1

    print(f"Candidates: {len(candidates)}")
    print(f"Source distribution: {source_counts}")

    assert len(candidates) == 3, "Should have 3 candidates (one per source)"
    assert source_counts["Source A"] == 1, "Source A should have exactly 1 (best)"
    assert source_counts["Source B"] == 1, "Source B should have exactly 1"
    assert source_counts["Source C"] == 1, "Source C should have exactly 1"
    # Verify best from Source A (highest score: 90)
    source_a_articles = [c for c in candidates if c.source == "Source A"]
    assert source_a_articles[0].score == 90, "Should select best from Source A"

    print("PASS: PASSED: One best article per source")


def test_diversity_ranking_preserved():
    """TEST 2: Ranking is preserved (sorted by score)."""
    print("\n" + "=" * 60)
    print("TEST 2: RANKING PRESERVED")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    articles = [
        NewsArticle("High Score A", "Source A", "http://1", datetime.now(tz), "text", score=95),
        NewsArticle("High Score B", "Source B", "http://2", datetime.now(tz), "text", score=90),
        NewsArticle("Mid Score A", "Source A", "http://3", datetime.now(tz), "text", score=85),
        NewsArticle("Low Score C", "Source C", "http://4", datetime.now(tz), "text", score=60),
    ]

    candidates = scorer.select_diverse_candidates(articles, quality_threshold=50)

    # Should have 3 candidates (one best from each source)
    assert len(candidates) == 3, f"Expected 3 candidates, got {len(candidates)}"

    # Verify scores are descending
    for i in range(len(candidates) - 1):
        assert candidates[i].score >= candidates[i+1].score, "Scores not descending"

    print("Candidate scores:", [c.score for c in candidates])
    print("PASS: PASSED: Ranking preserved")


def test_diversity_arxiv_dominance():
    """TEST 3: arXiv dominance prevention via per-source selection."""
    print("\n" + "=" * 60)
    print("TEST 3: ARXIV DOMINANCE PREVENTION")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    # Simulate realistic scenario with many arXiv articles
    articles = [
        NewsArticle("arXiv 1", "arXiv AI", "http://1", datetime.now(tz), "text", score=85),
        NewsArticle("arXiv 2", "arXiv AI", "http://2", datetime.now(tz), "text", score=82),
        NewsArticle("arXiv 3", "arXiv AI", "http://3", datetime.now(tz), "text", score=80),
        NewsArticle("arXiv 4", "arXiv AI", "http://4", datetime.now(tz), "text", score=78),
        NewsArticle("arXiv 5", "arXiv AI", "http://5", datetime.now(tz), "text", score=76),
        NewsArticle("Company 1", "OpenAI Blog", "http://6", datetime.now(tz), "text", score=74),
        NewsArticle("News 1", "TechCrunch AI", "http://7", datetime.now(tz), "text", score=72),
        NewsArticle("arXiv 6", "arXiv AI", "http://8", datetime.now(tz), "text", score=70),
    ]

    candidates = scorer.select_diverse_candidates(articles, quality_threshold=65)

    source_counts = {}
    for article in candidates:
        source_counts[article.source] = source_counts.get(article.source, 0) + 1

    print(f"Source distribution: {source_counts}")

    # Per-source approach: only 1 article per source (the best)
    assert source_counts.get("arXiv AI", 0) == 1, "arXiv should have exactly 1 (best)"
    assert "OpenAI Blog" in source_counts, "Company source should be included"
    assert "TechCrunch AI" in source_counts, "News source should be included"
    assert len(candidates) == 3, "Should have 3 sources represented"

    print("PASS: PASSED: arXiv limited to best, other sources included")


def test_diversity_high_quality_non_arxiv():
    """TEST 4: High-quality non-arXiv article wins."""
    print("\n" + "=" * 60)
    print("TEST 4: HIGH-QUALITY NON-ARXIV")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    articles = [
        NewsArticle("arXiv 1", "arXiv AI", "http://1", datetime.now(tz), "text", score=85),
        NewsArticle("arXiv 2", "arXiv AI", "http://2", datetime.now(tz), "text", score=83),
        NewsArticle("Breaking News", "OpenAI Blog", "http://3", datetime.now(tz), "text", score=88),  # Higher score
        NewsArticle("arXiv 3", "arXiv AI", "http://4", datetime.now(tz), "text", score=82),
    ]

    # Sort by score (select_diverse_candidates expects ranked articles)
    articles_ranked = sorted(articles, key=lambda x: x.score, reverse=True)

    candidates = scorer.select_diverse_candidates(articles_ranked, quality_threshold=70)

    # Should have 2 candidates (best from each source)
    assert len(candidates) == 2, f"Expected 2 candidates, got {len(candidates)}"

    # Verify the highest-scoring article (Breaking News) is in candidates
    assert any(a.title == "Breaking News" for a in candidates), "High-scoring company article missing"
    # Verify it's the first candidate (highest score)
    assert candidates[0].title == "Breaking News", "Highest-scoring article should be first"

    print("PASS: PASSED: High-quality company article prioritized")


def test_diversity_single_source():
    """TEST 5: All articles from one source - selects best."""
    print("\n" + "=" * 60)
    print("TEST 5: SINGLE SOURCE")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    articles = [
        NewsArticle("Article 1", "Source A", "http://1", datetime.now(tz), "text", score=90),
        NewsArticle("Article 2", "Source A", "http://2", datetime.now(tz), "text", score=85),
        NewsArticle("Article 3", "Source A", "http://3", datetime.now(tz), "text", score=80),
        NewsArticle("Article 4", "Source A", "http://4", datetime.now(tz), "text", score=75),
        NewsArticle("Article 5", "Source A", "http://5", datetime.now(tz), "text", score=70),
    ]

    candidates = scorer.select_diverse_candidates(articles, quality_threshold=60)

    # Per-source approach: only 1 article (best from source)
    assert len(candidates) == 1, f"Expected 1 candidate, got {len(candidates)}"
    assert all(a.source == "Source A" for a in candidates), "All should be from Source A"
    assert candidates[0].score == 90, "Should select best article"

    print(f"Candidates: {len(candidates)}")
    print("PASS: PASSED: Single source handled gracefully")


def test_diversity_fewer_than_top_n():
    """TEST 6: Small article set - all sources represented."""
    print("\n" + "=" * 60)
    print("TEST 6: SMALL ARTICLE SET")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    articles = [
        NewsArticle("Article 1", "Source A", "http://1", datetime.now(tz), "text", score=90),
        NewsArticle("Article 2", "Source B", "http://2", datetime.now(tz), "text", score=85),
        NewsArticle("Article 3", "Source C", "http://3", datetime.now(tz), "text", score=80),
    ]

    candidates = scorer.select_diverse_candidates(articles, quality_threshold=70)

    # Should have one from each source
    assert len(candidates) == 3, f"Expected 3 candidates, got {len(candidates)}"
    sources = set(c.source for c in candidates)
    assert len(sources) == 3, "Should have 3 unique sources"

    print(f"Candidates: {len(candidates)}")
    print("PASS: PASSED: All available articles processed")


def test_diversity_empty_list():
    """TEST 7: Empty list."""
    print("\n" + "=" * 60)
    print("TEST 7: EMPTY LIST")
    print("=" * 60)

    scorer = NewsScorer()
    candidates = scorer.select_diverse_candidates([], quality_threshold=25)

    assert candidates == [], "Empty list should return empty list"
    print("PASS: PASSED: Empty list handled safely")


def test_diversity_missing_source():
    """TEST 8: Missing/None source - treated as 'Unknown'."""
    print("\n" + "=" * 60)
    print("TEST 8: MISSING SOURCE")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    articles = [
        NewsArticle("Article 1", None, "http://1", datetime.now(tz), "text", score=90),
        NewsArticle("Article 2", "Source B", "http://2", datetime.now(tz), "text", score=85),
        NewsArticle("Article 3", None, "http://3", datetime.now(tz), "text", score=80),
    ]

    # Should not crash
    candidates = scorer.select_diverse_candidates(articles, quality_threshold=70)

    assert len(candidates) > 0, "Should return candidates"
    assert len(candidates) == 2, "Should have 2 sources (Unknown and Source B)"
    print(f"Candidates: {len(candidates)}")
    print("PASS: PASSED: Missing source handled safely")


def test_diversity_final_selection_one():
    """TEST 9: Final selection is exactly ONE article (highest score)."""
    print("\n" + "=" * 60)
    print("TEST 9: FINAL SELECTION IS ONE")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    articles = [
        NewsArticle("Article 1", "Source A", "http://1", datetime.now(tz), "text", score=90),
        NewsArticle("Article 2", "Source B", "http://2", datetime.now(tz), "text", score=85),
        NewsArticle("Article 3", "Source C", "http://3", datetime.now(tz), "text", score=80),
    ]

    candidates = scorer.select_diverse_candidates(articles, top_n=10, max_per_source=3)

    # Simulate final selection
    best_article = candidates[0]

    assert best_article is not None, "Should select one article"
    assert best_article.score == 90, "Should select highest-scoring article"

    print(f"Final selected: {best_article.title} (score: {best_article.score})")
    print("PASS: PASSED: Exactly one article selected")


def test_scoring_unchanged():
    """TEST 10: Existing scoring behavior unchanged."""
    print("\n" + "=" * 60)
    print("TEST 10: SCORING REGRESSION TEST")
    print("=" * 60)

    tz = pytz.timezone("Asia/Karachi")
    scorer = NewsScorer()

    # Use same test case as original test_scoring
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
    ]

    ranked = scorer.rank_articles(articles)

    # Verify scoring still works
    assert ranked[0].score > 0, "Articles should be scored"
    assert ranked[0].score > ranked[1].score, "First article should score higher"
    assert ranked[0].title.startswith("OpenAI"), "OpenAI article should rank first"

    print(f"Article 1 score: {ranked[0].score}")
    print(f"Article 2 score: {ranked[1].score}")
    print("PASS: PASSED: Existing scoring behavior unchanged")


def run_all_diversity_tests():
    """Run all diversity tests."""
    print("\n" + "=" * 70)
    print("RUNNING COMPREHENSIVE DIVERSITY TESTS")
    print("=" * 70)

    tests = [
        ("Basic Diversity", test_diversity_basic),
        ("Ranking Preserved", test_diversity_ranking_preserved),
        ("arXiv Dominance Prevention", test_diversity_arxiv_dominance),
        ("High-Quality Non-arXiv", test_diversity_high_quality_non_arxiv),
        ("Single Source", test_diversity_single_source),
        ("Fewer Than TOP_N", test_diversity_fewer_than_top_n),
        ("Empty List", test_diversity_empty_list),
        ("Missing Source", test_diversity_missing_source),
        ("Final Selection One", test_diversity_final_selection_one),
        ("Scoring Unchanged", test_scoring_unchanged),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\nFAIL: FAILED: {test_name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\nFAIL: ERROR: {test_name}")
            print(f"  Exception: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"PASSED: {passed}/{len(tests)}")
    print(f"FAILED: {failed}/{len(tests)}")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    # Run original test
    test_scoring()

    # Run all diversity tests
    all_passed = run_all_diversity_tests()

    if all_passed:
        print("\nPASS: ALL TESTS PASSED")
    else:
        print("\nFAIL: SOME TESTS FAILED")
        sys.exit(1)
