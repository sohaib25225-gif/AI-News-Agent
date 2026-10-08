"""
Test V1 Components

This script tests V1 components individually without making external API calls.
"""

import sys
from datetime import datetime, timedelta
from models import NewsArticle, Finding
from agents.intelligence_classifier import IntelligenceClassifier
from config.sources import get_competitor_from_source, get_source_confidence, get_tracked_competitors
from database import NewsDatabase

print("=" * 60)
print("TESTING V1 COMPONENTS")
print("=" * 60)

# Test 1: Competitor mapping
print("\nTest 1: Competitor Mapping")
print("-" * 40)
test_sources = ["OpenAI Blog", "Google AI Blog", "Meta Blog", "Unknown Source"]
for source in test_sources:
    competitor = get_competitor_from_source(source)
    confidence = get_source_confidence(source)
    competitor_str = competitor if competitor else "None"
    print(f"{source:25} -> {competitor_str:10} (confidence: {confidence:.2f})")

print(f"\nTracked competitors: {get_tracked_competitors()}")

# Test 2: Event classification
print("\n\nTest 2: Event Classification")
print("-" * 40)

test_articles = [
    NewsArticle(
        title="OpenAI Launches GPT-5 with Revolutionary Capabilities",
        source="OpenAI Blog",
        url="https://openai.com/gpt5",
        published_date=datetime.now(),
        summary="OpenAI today announced the release of GPT-5, introducing breakthrough features"
    ),
    NewsArticle(
        title="Google AI Publishes New Research on Transformer Architecture",
        source="Google AI Blog",
        url="https://ai.google/research/paper",
        published_date=datetime.now(),
        summary="Researchers at Google AI have published a paper on novel transformer improvements"
    ),
    NewsArticle(
        title="Meta Partners with Microsoft on AI Development",
        source="Meta Blog",
        url="https://meta.com/partnership",
        published_date=datetime.now(),
        summary="Meta and Microsoft announce strategic partnership to collaborate on AI research"
    ),
    NewsArticle(
        title="Some Random Tech News",
        source="Random Blog",
        url="https://random.com/news",
        published_date=datetime.now(),
        summary="This is some generic tech news not about a tracked competitor"
    ),
]

classifier = IntelligenceClassifier()

findings = []
for article in test_articles:
    finding = classifier.classify_article(article)
    if finding:
        findings.append(finding)
        print(f"[OK] {finding.competitor:15} | {finding.event_type:18} | {finding.title[:50]}")
    else:
        print(f"[--] No finding        | Not tracked           | {article.title[:50]}")

# Test 3: Database operations
print("\n\nTest 3: Database Operations")
print("-" * 40)

db = NewsDatabase()

# Save findings
print(f"\nSaving {len(findings)} findings...")
for finding in findings:
    finding_id = db.save_finding(finding)
    if finding_id:
        finding.id = finding_id
        print(f"  Saved finding #{finding_id}: {finding.competitor} - {finding.event_type}")

# Retrieve findings
print("\nRetrieving findings from database...")
start_date = datetime.now() - timedelta(days=1)
retrieved_findings = db.get_findings(start_date=start_date)
print(f"Retrieved {len(retrieved_findings)} findings")

for finding in retrieved_findings[:5]:  # Show first 5
    print(f"  #{finding.id}: {finding.competitor} - {finding.event_type} - {finding.title[:40]}")

# Group by competitor
competitor_counts = {}
for finding in retrieved_findings:
    competitor_counts[finding.competitor] = competitor_counts.get(finding.competitor, 0) + 1

print(f"\nFindings by competitor:")
for competitor, count in sorted(competitor_counts.items()):
    print(f"  {competitor}: {count}")

# Test 4: Finding citation format
print("\n\nTest 4: Finding Citation Format")
print("-" * 40)

if findings:
    test_finding = findings[0]
    citation = test_finding.to_citation_dict()
    print("Citation format:")
    for key, value in citation.items():
        print(f"  {key}: {value}")

print("\n" + "=" * 60)
print("V1 COMPONENT TESTS COMPLETE")
print("=" * 60)
print("\nNext steps:")
print("1. Run main_v1.py to test full workflow (will make API calls)")
print("2. Check email for intelligence brief")
print("3. Verify findings and briefs in database")
