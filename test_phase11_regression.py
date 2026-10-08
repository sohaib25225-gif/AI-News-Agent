"""
Regression Tests for Phase 11 Database Persistence and Partnership Actor Verification

Tests:
1. Partnership actor verification (Anthropic partners with AWS → accepted)
2. Reverse partnership (AWS partners with Anthropic → accepted)
3. Product usage (AWS uses Claude → not automatically Anthropic actor)
4. Customer story (How AWS uses Claude → existing behavior preserved)
5. Comparison (Anthropic vs OpenAI → existing filtering preserved)
6. Author bio (Anthropic only in author bio → rejected)
7. Database persistence of Phase 11 fields
"""

import sys
import os
import tempfile
from datetime import datetime

# Ensure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import NewsArticle, Finding
from agents.intelligence_classifier import IntelligenceClassifier
from database.news_db import NewsDatabase


def create_test_article(title, source, summary, content=""):
    """Helper to create test articles."""
    return NewsArticle(
        title=title,
        source=source,
        url=f"https://test.com/{title.replace(' ', '-').lower()[:30]}",
        published_date=datetime.now(),
        summary=summary,
        content=content,
        score=0.5
    )


def run_tests():
    """Run all regression tests."""
    classifier = IntelligenceClassifier()

    print("=" * 80)
    print("PHASE 11 REGRESSION TESTS: PARTNERSHIP + DATABASE")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    # ========================================================================
    # TEST 1: Anthropic partners with AWS → accepted
    # ========================================================================
    print("TEST 1: Anthropic partners with AWS (subject position)")
    print("-" * 80)
    article = create_test_article(
        title="Anthropic partners with AWS to offer Claude on SageMaker",
        source="AWS ML Blog",
        summary="Anthropic's Claude models are now available through Amazon SageMaker.",
        content="The partnership enables enterprise customers to deploy Claude..."
    )
    finding = classifier.classify_article(article)

    if finding and finding.competitor == "Anthropic" and finding.event_type == "partnership":
        print(f"[PASS] Anthropic detected as actor, event: {finding.event_type}")
        print(f"       Actor score: {finding.actor_score:.2f}, Priority: {finding.priority}")
        passed += 1
    else:
        print(f"[FAIL] Expected Anthropic/partnership, got: {finding.competitor if finding else 'None'}/{finding.event_type if finding else 'None'}")
        failed += 1
    print()

    # ========================================================================
    # TEST 2: AWS partners with Anthropic → accepted (competitor as participant)
    # ========================================================================
    print("TEST 2: AWS partners with Anthropic (participant position)")
    print("-" * 80)
    article = create_test_article(
        title="AWS partners with Anthropic to bring Claude to SageMaker",
        source="TechCrunch AI",
        summary="Amazon Web Services announced a partnership with Anthropic to make Claude available on SageMaker.",
        content="The collaboration brings Anthropic's Claude models to AWS customers..."
    )
    finding = classifier.classify_article(article)

    if finding and finding.competitor == "Anthropic":
        print(f"[PASS] Anthropic detected as participant, event: {finding.event_type}")
        print(f"       Actor score: {finding.actor_score:.2f}, Priority: {finding.priority}")
        passed += 1
    else:
        print(f"[FAIL] Expected Anthropic, got: {finding.competitor if finding else 'None'}")
        failed += 1
    print()

    # ========================================================================
    # TEST 3: AWS uses Claude → not automatically Anthropic actor
    # ========================================================================
    print("TEST 3: AWS uses Claude (product usage, not actor)")
    print("-" * 80)
    article = create_test_article(
        title="AWS uses Claude to power its new AI assistant",
        source="TechCrunch AI",
        summary="Amazon Web Services has integrated Anthropic's Claude model into its internal AI assistant.",
        content="AWS engineers deployed Claude as the foundation for their new tool..."
    )
    finding = classifier.classify_article(article)

    # This could be filtered (actor verification) or pass as low-priority customer story
    # Either way, it should NOT be high-priority active event
    if finding is None:
        print("[PASS] Filtered by actor verification (AWS is actor, not Anthropic)")
        passed += 1
    elif finding.action_context == "passive" and finding.priority == "low":
        print(f"[PASS] Passed but correctly flagged as low-priority passive")
        print(f"       Event: {finding.event_type}, Priority: {finding.priority}")
        passed += 1
    elif finding.action_context != "active":
        print(f"[PASS] Not classified as active event")
        print(f"       Event: {finding.event_type}, Context: {finding.action_context}")
        passed += 1
    else:
        print(f"[FAIL] Should not be active event for Anthropic")
        print(f"       Got: event={finding.event_type}, context={finding.action_context}")
        failed += 1
    print()

    # ========================================================================
    # TEST 4: How AWS uses Claude → customer story behavior preserved
    # ========================================================================
    print("TEST 4: How AWS uses Claude (customer story)")
    print("-" * 80)
    article = create_test_article(
        title="How AWS uses Claude to build internal tools",
        source="TechCrunch AI",
        summary="AWS has adopted Claude for internal development workflows.",
        content="The company implemented Claude across multiple teams..."
    )
    finding = classifier.classify_article(article)

    if finding is None:
        print("[PASS] Filtered (customer story, not Anthropic actor)")
        passed += 1
    elif finding.content_type == "customer_story" and finding.priority == "low":
        print(f"[PASS] Correctly classified as low-priority customer story")
        print(f"       Content type: {finding.content_type}, Priority: {finding.priority}")
        passed += 1
    else:
        print(f"[FAIL] Should be customer_story/low-priority or filtered")
        if finding:
            print(f"       Got: content_type={finding.content_type}, priority={finding.priority}")
        failed += 1
    print()

    # ========================================================================
    # TEST 5: Anthropic vs OpenAI → comparison filtering preserved
    # ========================================================================
    print("TEST 5: Anthropic vs OpenAI (comparison)")
    print("-" * 80)
    article = create_test_article(
        title="Anthropic vs OpenAI: Which AI is better for coding?",
        source="TechCrunch AI",
        summary="We compare Anthropic's Claude with OpenAI's GPT-4 across benchmarks.",
        content="Both models have strengths in different areas..."
    )
    finding = classifier.classify_article(article)

    if finding is None:
        print("[PASS] Comparison article correctly filtered")
        passed += 1
    else:
        print(f"[FAIL] Should be filtered (comparison)")
        print(f"       Got: {finding.competitor}/{finding.event_type}, actor_score={finding.actor_score:.2f}")
        failed += 1
    print()

    # ========================================================================
    # TEST 6: Anthropic only in author bio → rejected
    # ========================================================================
    print("TEST 6: Anthropic only in author bio (rejection)")
    print("-" * 80)
    author_bio = "Author bio: David is a Solutions Architect who passed all 12 AWS and 4 Anthropic certificates."
    main_content = "uniopen is a digital platform from Taiwan. " * 50

    article = create_test_article(
        title="How uniopen customized Amazon Nova to their retail moderation policies",
        source="AWS ML Blog",
        summary="See how uniopen adapted Amazon Nova 2 Lite using supervised fine-tuning.",
        content=main_content + author_bio
    )
    finding = classifier.classify_article(article)

    if finding is None:
        print("[PASS] Author bio mention correctly rejected")
        passed += 1
    else:
        print(f"[FAIL] Should be filtered (author bio)")
        print(f"       Got: {finding.competitor}, actor_score={finding.actor_score:.2f}")
        failed += 1
    print()

    # ========================================================================
    # TEST 7: Phase 11 fields persist through database save/retrieve
    # ========================================================================
    print("TEST 7: Phase 11 fields persist through database save/retrieve")
    print("-" * 80)

    # Use a temporary database to avoid polluting the real one
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        db = NewsDatabase(db_path=tmp_path)

        # Create a finding with non-default Phase 11 values
        finding = Finding(
            competitor="OpenAI",
            event_type="product_launch",
            title="OpenAI Launches GPT-5",
            summary="OpenAI released GPT-5 with new capabilities.",
            evidence="OpenAI released GPT-5",
            original_title="OpenAI Launches GPT-5",
            original_summary="OpenAI released GPT-5 with new capabilities.",
            original_content=None,
            source_name="OpenAI Blog",
            source_url="https://openai.com/gpt5",
            published_at=datetime.now(),
            relevance_score=0.85,
            source_confidence=0.9,
            source_confidence_factors="source_type=official(0.6), corroboration=single_source(+0.1)",
            requires_review=False,
            detected_at=datetime.now(),
            # Phase 11 fields with non-default values
            priority="high",
            content_type="technical",
            action_context="active",
            actor_score=0.9,
        )

        # Save
        finding_id = db.save_finding(finding)
        if not finding_id:
            print("[FAIL] Failed to save finding")
            failed += 1
        else:
            print(f"       Saved finding #{finding_id}")

            # Retrieve
            retrieved = db.get_findings(competitor="OpenAI")
            if not retrieved:
                print("[FAIL] No findings retrieved")
                failed += 1
            else:
                r = retrieved[0]

                # Check Phase 11 fields
                all_match = True
                checks = [
                    ("priority", r.priority, "high"),
                    ("content_type", r.content_type, "technical"),
                    ("action_context", r.action_context, "active"),
                    ("actor_score", r.actor_score, 0.9),
                ]
                for name, actual, expected in checks:
                    if actual == expected:
                        print(f"       [OK] {name}: {actual}")
                    else:
                        print(f"       [FAIL] {name}: expected {expected}, got {actual}")
                        all_match = False

                # Also check core fields
                if r.competitor == "OpenAI" and r.event_type == "product_launch":
                    print(f"       [OK] competitor: {r.competitor}")
                    print(f"       [OK] event_type: {r.event_type}")
                else:
                    print(f"       [FAIL] core fields: {r.competitor}/{r.event_type}")
                    all_match = False

                if all_match:
                    print("[PASS] All Phase 11 fields persisted correctly")
                    passed += 1
                else:
                    print("[FAIL] Some Phase 11 fields not persisted")
                    failed += 1
    finally:
        # Clean up temp database
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 80)
    print("REGRESSION TEST SUMMARY")
    print("=" * 80)
    print(f"Total: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed / (passed + failed) * 100):.1f}%")
    print()

    if failed == 0:
        print("[PASS] ALL REGRESSION TESTS PASSED")
        return 0
    else:
        print(f"[FAIL] {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
