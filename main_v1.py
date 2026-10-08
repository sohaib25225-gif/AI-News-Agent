"""
AI Competitive Intelligence Worker V1 - Main Script

This script implements the V1 competitive intelligence workflow:
1. Fetch news from competitor sources (past 7 days)
2. Classify articles into findings
3. Store findings in database
4. Generate intelligence brief from findings
5. Email brief to user

Run weekly to get a comprehensive competitive intelligence brief.

How to run:
    python main_v1.py
"""

import sys
from datetime import datetime, timedelta
from config import config
from utils import get_logger
from services import NewsFetcher, EmailService
from agents.intelligence_classifier import IntelligenceClassifier
from agents.brief_generator import BriefGenerator
from agents.deduplicator import Deduplicator
from agents.relevance_scorer import RelevanceScorer
from database import NewsDatabase

logger = get_logger(__name__)


def validate_configuration() -> bool:
    """
    Validate that all required configuration is present.

    Returns:
        True if valid, False otherwise
    """
    logger.info("Validating configuration...")
    is_valid, missing = config.validate()

    if not is_valid:
        logger.error("Configuration validation failed!")
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please check your .env file.")
        return False

    logger.info("Configuration validated successfully")
    return True


def fetch_news(days: int = 7) -> list:
    """
    Fetch news from all sources.

    Args:
        days: Number of days to look back

    Returns:
        List of NewsArticle objects
    """
    logger.info("=" * 60)
    logger.info("STEP 1: Fetching AI News")
    logger.info("=" * 60)

    logger.info(f"Fetching articles from the past {days} days")

    fetcher = NewsFetcher()
    articles = fetcher.fetch_all()

    # Filter to articles from the past N days
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_articles = []
    for article in articles:
        pub_date = article.published_date
        # Handle timezone-aware vs naive comparison
        if pub_date.tzinfo is not None:
            # Strip timezone info for comparison
            pub_date = pub_date.replace(tzinfo=None)
        if pub_date >= cutoff_date:
            recent_articles.append(article)

    logger.info(f"Fetched {len(articles)} total articles")
    logger.info(f"Recent articles (past {days} days): {len(recent_articles)}")

    return recent_articles


def deduplicate_articles(articles: list) -> list:
    """
    Remove duplicate articles reporting the same event.

    Args:
        articles: List of NewsArticle objects

    Returns:
        Deduplicated list of NewsArticle objects
    """
    logger.info("=" * 60)
    logger.info("STEP 2: Deduplicating Articles")
    logger.info("=" * 60)

    deduplicator = Deduplicator(similarity_threshold=0.7)
    unique_articles = deduplicator.deduplicate(articles)

    logger.info(f"Deduplication: {len(unique_articles)} unique articles (removed {len(articles) - len(unique_articles)} duplicates)")

    return unique_articles


def score_relevance(articles: list) -> list:
    """
    Score articles for competitive intelligence relevance.

    Args:
        articles: List of NewsArticle objects

    Returns:
        Filtered list of relevant articles (with scores set)
    """
    logger.info("=" * 60)
    logger.info("STEP 3: Scoring Relevance")
    logger.info("=" * 60)

    scorer = RelevanceScorer(min_score=0.3)
    relevant_articles = scorer.score_and_filter(articles)

    logger.info(f"Relevance filtering: {len(relevant_articles)} relevant articles")

    if relevant_articles:
        logger.info("Top 5 by relevance:")
        for i, article in enumerate(relevant_articles[:5], 1):
            logger.info(f"  {i}. [{article.score:.2f}] {article.title[:60]}")

    return relevant_articles


def classify_into_findings(articles: list) -> list:
    """
    Classify articles into competitive intelligence findings.

    Args:
        articles: List of NewsArticle objects

    Returns:
        List of Finding objects
    """
    logger.info("=" * 60)
    logger.info("STEP 4: Classifying Findings")
    logger.info("=" * 60)

    classifier = IntelligenceClassifier()
    findings = classifier.classify_articles(articles)

    logger.info(f"Classified {len(findings)} findings from {len(articles)} articles")

    # Log breakdown by competitor
    competitor_counts = {}
    for finding in findings:
        competitor_counts[finding.competitor] = competitor_counts.get(finding.competitor, 0) + 1

    logger.info("Findings by competitor:")
    for competitor, count in sorted(competitor_counts.items()):
        logger.info(f"  {competitor}: {count}")

    # Log review flags
    review_count = sum(1 for f in findings if f.requires_review)
    logger.info(f"Findings requiring review: {review_count}/{len(findings)}")

    return findings


def save_findings(findings: list, db: NewsDatabase) -> list:
    """
    Save findings to database.

    Args:
        findings: List of Finding objects
        db: Database instance

    Returns:
        List of Finding objects with IDs populated
    """
    logger.info("=" * 60)
    logger.info("STEP 5: Saving Findings")
    logger.info("=" * 60)

    saved_count = 0

    for finding in findings:
        finding_id = db.save_finding(finding)
        if finding_id:
            finding.id = finding_id
            saved_count += 1

    logger.info(f"Saved {saved_count} findings to database")

    return findings


def generate_brief(findings: list, period_start: datetime, period_end: datetime):
    """
    Generate intelligence brief from findings.

    Args:
        findings: List of Finding objects
        period_start: Start of reporting period
        period_end: End of reporting period

    Returns:
        IntelligenceBrief object or None
    """
    logger.info("=" * 60)
    logger.info("STEP 6: Generating Intelligence Brief")
    logger.info("=" * 60)

    if not findings:
        logger.warning("No findings to generate brief from")
        return None

    logger.info(f"Generating brief from {len(findings)} findings")
    logger.info(f"Period: {period_start.date()} to {period_end.date()}")

    generator = BriefGenerator()
    brief = generator.generate_brief(findings, period_start, period_end)

    if brief:
        logger.info("Successfully generated intelligence brief")
        logger.info(f"Executive summary: {brief.executive_summary[:100]}...")
        logger.info(f"Key findings: {len(brief.key_findings)}")
        logger.info(f"Competitors covered: {len(brief.competitor_activity)}")

    return brief


def save_brief(brief, db: NewsDatabase) -> bool:
    """
    Save intelligence brief to database.

    Args:
        brief: IntelligenceBrief object
        db: Database instance

    Returns:
        True if saved successfully
    """
    logger.info("=" * 60)
    logger.info("STEP 7: Saving Brief")
    logger.info("=" * 60)

    brief_id = db.save_intelligence_brief(brief)

    if brief_id:
        brief.id = brief_id
        logger.info(f"Saved intelligence brief #{brief_id}")
        return True
    else:
        logger.error("Failed to save intelligence brief")
        return False


def send_email(brief):
    """
    Send the intelligence brief via email.

    Args:
        brief: IntelligenceBrief object to send

    Returns:
        True if sent successfully
    """
    logger.info("=" * 60)
    logger.info("STEP 8: Sending Email")
    logger.info("=" * 60)

    try:
        email_service = EmailService()
        success = email_service.send_intelligence_brief(brief)

        if success:
            logger.info("Intelligence brief email sent successfully")
        else:
            logger.error("Failed to send intelligence brief email")

        return success

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}", exc_info=True)
        return False


def main():
    """
    Main V1 intelligence workflow.
    """
    logger.info("=" * 60)
    logger.info("AI COMPETITIVE INTELLIGENCE WORKER V1 - STARTED")
    logger.info(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        # Step 0: Validate configuration
        if not validate_configuration():
            sys.exit(1)

        # Initialize database
        db = NewsDatabase()

        # Define reporting period (past 7 days)
        period_end = datetime.now()
        period_start = period_end - timedelta(days=7)

        logger.info(f"Reporting period: {period_start.date()} to {period_end.date()}")

        # Step 1: Fetch news
        articles = fetch_news(days=7)

        if not articles:
            logger.warning("No articles fetched. Exiting.")
            return

        # Step 2: Deduplicate articles
        unique_articles = deduplicate_articles(articles)

        if not unique_articles:
            logger.warning("No unique articles after deduplication. Exiting.")
            return

        # Step 3: Score relevance and filter
        relevant_articles = score_relevance(unique_articles)

        if not relevant_articles:
            logger.warning("No relevant articles found. Exiting.")
            return

        # Step 4: Classify into findings
        findings = classify_into_findings(relevant_articles)

        if not findings:
            logger.warning("No competitor findings detected. Exiting.")
            return

        # Step 5: Save findings
        findings = save_findings(findings, db)

        # Step 6: Generate brief
        brief = generate_brief(findings, period_start, period_end)

        if not brief:
            logger.error("Failed to generate intelligence brief")
            return

        # Step 7: Save brief
        if not save_brief(brief, db):
            logger.warning("Brief not saved, but continuing to email")

        # Step 8: Send email
        success = send_email(brief)

        if success:
            logger.info("Successfully completed all steps!")
        else:
            logger.error("Failed to send email")

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("=" * 60)
        logger.info("AI COMPETITIVE INTELLIGENCE WORKER V1 - FINISHED")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
