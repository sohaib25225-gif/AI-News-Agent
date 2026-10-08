"""
Test Suite for Phase 12 Intelligence Quality Fixes

Tests all three fixes:
- Fix A: Competitor Actor/Subject Verification
- Fix B: Intelligence Value / Marketing Filter
- Fix C: Event Classification Context

Based on Phase 11 design test cases.
"""

import sys
from datetime import datetime
from models import NewsArticle
from agents.intelligence_classifier import IntelligenceClassifier

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
    """Run all Phase 12 test cases."""
    classifier = IntelligenceClassifier()

    print("=" * 80)
    print("PHASE 12 INTELLIGENCE QUALITY TEST SUITE")
    print("=" * 80)
    print()

    passed = 0
    failed = 0
    test_results = []

    # ========================================================================
    # TEST CASE 1: Competitor as Actor (Product Launch) - SHOULD PASS
    # ========================================================================
    print("TEST 1: Competitor as Actor (Product Launch)")
    print("-" * 80)
    article = create_test_article(
        title="OpenAI Launches GPT-5 with Breakthrough Multimodal Capabilities",
        source="TechCrunch AI",
        summary="OpenAI today announced GPT-5, featuring advanced reasoning and image generation.",
        content="OpenAI has released GPT-5, marking a significant advancement in AI capabilities..."
    )
    finding = classifier.classify_article(article)

    if finding and finding.competitor == "OpenAI" and finding.event_type == "product_launch":
        print("[OK] PASS - OpenAI detected as actor, event: product_launch")
        print(f"   Actor score: {finding.actor_score:.2f}, Priority: {finding.priority}, Content: {finding.content_type}")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Expected OpenAI/product_launch, got: {finding.competitor if finding else 'None'}/{finding.event_type if finding else 'None'}")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 2: Competitor in Author Bio (FALSE POSITIVE) - SHOULD FILTER
    # ========================================================================
    print("TEST 2: Competitor in Author Bio (Finding #72 Reproduction)")
    print("-" * 80)

    # Simulate Finding #72: Amazon Nova article with Anthropic only in author bio
    author_bio = "Author bio: David is a Solutions Architect who passed all 12 AWS and 4 Anthropic certificates to make his technical field not only deep but wide."
    main_content = "uniopen is a digital platform from Taiwan. " * 50  # Lots of non-Anthropic content

    article = create_test_article(
        title="How uniopen customized Amazon Nova to their retail moderation policies",
        source="AWS ML Blog",
        summary="See how uniopen adapted Amazon Nova 2 Lite using supervised fine-tuning.",
        content=main_content + author_bio
    )
    finding = classifier.classify_article(article)

    if finding is None:
        print("[OK] PASS - False positive filtered (Anthropic only in author bio)")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Should be filtered, but got: {finding.competitor}/{finding.event_type}")
        print(f"   Actor score: {finding.actor_score:.2f}")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 3: Customer Case Study (Official Source) - SHOULD FLAG
    # ========================================================================
    print("TEST 3: Customer Case Study from Official Source (Finding #73 Reproduction)")
    print("-" * 80)
    article = create_test_article(
        title="How Albertsons Companies is reimagining retail with ChatGPT Enterprise",
        source="OpenAI Blog",
        summary="Albertsons is using ChatGPT Enterprise and OpenAI API to improve customer experiences.",
        content="Albertsons Cos. deployed ChatGPT Enterprise to help teams work faster..."
    )
    article.score = 0.3  # Lower relevance
    finding = classifier.classify_article(article)

    if (finding and finding.competitor == "OpenAI" and
        finding.content_type == "customer_story" and
        finding.priority == "low" and
        finding.requires_review == True and
        finding.event_type != "api_change"):  # Fix C: should NOT be api_change
        print("[OK] PASS - Customer story flagged as low priority, not api_change")
        print(f"   Priority: {finding.priority}, Content: {finding.content_type}, Event: {finding.event_type}")
        print(f"   Requires Review: {finding.requires_review}, Action: {finding.action_context}")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Expected low-priority customer_story, not api_change")
        if finding:
            print(f"   Got: content_type={finding.content_type}, priority={finding.priority}")
            print(f"   Event: {finding.event_type}, Review: {finding.requires_review}")
        else:
            print("   Finding was filtered (should be flagged, not filtered)")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 4: Consumer Marketing - SHOULD FLAG
    # ========================================================================
    print("TEST 4: Consumer Marketing (Finding #71 Reproduction)")
    print("-" * 80)
    article = create_test_article(
        title="Announcing Ranveer Singh as Brand Ambassador for Ray-Ban Meta in India",
        source="Meta Blog",
        summary="Ranveer Singh becomes the first Brand Ambassador for Ray-Ban and Ray-Ban Meta in India.",
        content="Ranveer has a long-standing relationship with Meta... exciting new updates to our AI glasses..."
    )
    article.score = 0.42
    finding = classifier.classify_article(article)

    if (finding and finding.competitor == "Meta AI" and
        finding.content_type == "consumer_marketing" and
        finding.priority == "low" and
        finding.requires_review == True):
        print("[OK] PASS - Consumer marketing flagged as low priority")
        print(f"   Priority: {finding.priority}, Content: {finding.content_type}")
        print(f"   Requires Review: {finding.requires_review}")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Expected low-priority consumer_marketing")
        if finding:
            print(f"   Got: content_type={finding.content_type}, priority={finding.priority}")
        else:
            print("   Finding was filtered")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 5: Comparison Article - SHOULD FILTER
    # ========================================================================
    print("TEST 5: Comparison Article (GPT-5 vs Claude 4)")
    print("-" * 80)
    article = create_test_article(
        title="GPT-5 vs Claude 4: Which AI model is better for coding?",
        source="TechCrunch AI",
        summary="We compare OpenAI's GPT-5 with Anthropic's Claude 4 across multiple benchmarks.",
        content="In this comprehensive comparison, we evaluate both models..."
    )
    finding = classifier.classify_article(article)

    if finding is None:
        print("[OK] PASS - Comparison article filtered (neither competitor is actor)")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Should be filtered, but got: {finding.competitor}/{finding.event_type}")
        print(f"   Actor score: {finding.actor_score:.2f}")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 6: API Change (Active Context) - SHOULD PASS
    # ========================================================================
    print("TEST 6: API Change with Active Context")
    print("-" * 80)
    article = create_test_article(
        title="OpenAI announces API pricing changes and new endpoints",
        source="OpenAI Blog",
        summary="OpenAI today released new API pricing tiers and deprecated legacy endpoints.",
        content="Starting March 1st, the following API changes take effect..."
    )
    finding = classifier.classify_article(article)

    if (finding and finding.competitor == "OpenAI" and
        finding.event_type == "api_change" and
        finding.action_context == "active" and
        finding.priority == "high"):
        print("[OK] PASS - API change detected with active context")
        print(f"   Event: {finding.event_type}, Action: {finding.action_context}, Priority: {finding.priority}")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Expected api_change with active context")
        if finding:
            print(f"   Got: event={finding.event_type}, action={finding.action_context}")
        else:
            print("   Finding was filtered")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 7: API Usage (Passive Context) - SHOULD NOT BE api_change
    # ========================================================================
    print("TEST 7: API Usage with Passive Context")
    print("-" * 80)
    article = create_test_article(
        title="How Shopify uses OpenAI API to power 24/7 customer support",
        source="TechCrunch AI",
        summary="Shopify implemented OpenAI's API to provide instant customer service responses.",
        content="Shopify integrated the OpenAI API into their support system..."
    )
    finding = classifier.classify_article(article)

    # Should be filtered by Fix A (Shopify is actor, not OpenAI)
    if finding is None:
        print("[OK] PASS - API usage story filtered (Shopify is actor, not OpenAI)")
        passed += 1
    elif finding.event_type != "api_change":
        print("[OK] PASS - Not classified as api_change (if it passed actor verification)")
        print(f"   Event: {finding.event_type}, Action: {finding.action_context}")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Should not be api_change or should be filtered")
        print(f"   Got: {finding.competitor}/{finding.event_type}, action={finding.action_context}")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 8: Research Release - SHOULD PASS
    # ========================================================================
    print("TEST 8: Research Release")
    print("-" * 80)
    article = create_test_article(
        title="Google DeepMind publishes breakthrough paper on AI reasoning",
        source="DeepMind Blog",
        summary="DeepMind researchers present a novel approach to multi-step reasoning in language models.",
        content="Our paper, published in Nature, demonstrates..."
    )
    finding = classifier.classify_article(article)

    if (finding and finding.competitor == "Google AI" and
        finding.event_type == "research_release" and
        finding.priority == "high"):
        print("[OK] PASS - Research release detected, high priority")
        print(f"   Competitor: {finding.competitor}, Event: {finding.event_type}, Priority: {finding.priority}")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Expected Google AI/research_release/high")
        if finding:
            print(f"   Got: {finding.competitor}/{finding.event_type}/{finding.priority}")
        else:
            print("   Finding was filtered")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 9: Funding Announcement - SHOULD PASS
    # ========================================================================
    print("TEST 9: Funding Announcement")
    print("-" * 80)
    article = create_test_article(
        title="Anthropic raises $4B in Series C led by Google",
        source="TechCrunch AI",
        summary="AI startup Anthropic announced a $4 billion Series C funding round.",
        content="Anthropic, maker of Claude, secured significant funding..."
    )
    finding = classifier.classify_article(article)

    if (finding and finding.competitor == "Anthropic" and
        finding.event_type == "funding" and
        finding.priority == "high"):
        print("[OK] PASS - Funding announcement detected, high priority")
        print(f"   Competitor: {finding.competitor}, Event: {finding.event_type}, Priority: {finding.priority}")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Expected Anthropic/funding/high")
        if finding:
            print(f"   Got: {finding.competitor}/{finding.event_type}/{finding.priority}")
        else:
            print("   Finding was filtered")
        failed += 1
    print()

    # ========================================================================
    # TEST CASE 10: Partnership (Technical) - SHOULD PASS
    # ========================================================================
    print("TEST 10: Technical Partnership")
    print("-" * 80)
    article = create_test_article(
        title="Anthropic partners with AWS to offer Claude on SageMaker",
        source="AWS ML Blog",
        summary="Anthropic's Claude models are now available through Amazon SageMaker.",
        content="The partnership enables enterprise customers to deploy Claude..."
    )
    finding = classifier.classify_article(article)

    if (finding and finding.competitor == "Anthropic" and
        finding.event_type == "partnership" and
        finding.content_type in ["partnership", "technical"] and
        finding.priority in ["high", "medium"]):
        print("[OK] PASS - Partnership detected")
        print(f"   Event: {finding.event_type}, Content: {finding.content_type}, Priority: {finding.priority}")
        passed += 1
    else:
        print(f"[FAIL] FAIL - Expected Anthropic/partnership")
        if finding:
            print(f"   Got: {finding.competitor}/{finding.event_type}/{finding.content_type}")
        else:
            print("   Finding was filtered")
        failed += 1
    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed / (passed + failed) * 100):.1f}%")
    print()

    if failed == 0:
        print("[OK] ALL TESTS PASSED")
        return 0
    else:
        print(f"[FAIL] {failed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
