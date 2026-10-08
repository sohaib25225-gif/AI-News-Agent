"""
Data Models Module

This file defines the structure of data used throughout the application.
Think of models as blueprints that define what information we store and how.

Why this file exists:
- Provides clear structure for news articles
- Makes code more readable (we know exactly what fields exist)
- Enables type checking to catch errors early
- Documents what data we're working with
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class NewsArticle:
    """
    Represents a single news article.

    Attributes:
        title: The headline of the article
        source: Where the article came from (e.g., "OpenAI Blog")
        url: Link to the original article
        published_date: When the article was published
        summary: Brief description of the article content
        score: Relevance score (0-100), calculated by our scoring algorithm
        content: Full article content (if available)
    """
    title: str
    source: str
    url: str
    published_date: datetime
    summary: str
    score: float = 0.0
    content: Optional[str] = None

    def __str__(self) -> str:
        """String representation for logging and debugging."""
        return f"{self.source}: {self.title} (Score: {self.score:.1f})"

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "published_date": self.published_date.isoformat(),
            "summary": self.summary,
            "score": self.score,
            "content": self.content
        }


@dataclass
class LinkedInPost:
    """
    Represents a generated LinkedIn post.

    Attributes:
        hook: Opening line to grab attention
        body: Main content (2-3 paragraphs)
        question: Engaging question to prompt discussion
        hashtags: List of relevant hashtags
        source_article: The news article this post is based on
        generated_date: When this post was created
    """
    hook: str
    body: str
    question: str
    hashtags: list[str]
    source_article: NewsArticle
    generated_date: datetime

    def format_for_email(self) -> str:
        """
        Format the post for email delivery.

        Returns:
            Formatted string ready to be sent via email
        """
        return f"""
{self.hook}

{self.body}

{self.question}

{' '.join(self.hashtags)}
        """.strip()

    def format_for_linkedin(self) -> str:
        """
        Format the post exactly as it should appear on LinkedIn.

        Returns:
            Copy-paste ready LinkedIn post
        """
        return self.format_for_email()

    def word_count(self) -> int:
        """Calculate total word count of the post."""
        text = f"{self.hook} {self.body} {self.question}"
        return len(text.split())


# ============================================================================
# V1 Models - Competitive Intelligence
# ============================================================================


@dataclass
class Finding:
    """
    Represents a competitive intelligence finding.

    This model captures structured information about a competitor event
    detected from news sources.

    Attributes:
        competitor: Name of competitor (e.g., "OpenAI", "Anthropic", "Google AI")
        event_type: Type of event (e.g., "product_launch", "research_release", "partnership")
        title: Finding title/headline (processed)
        summary: Brief description of what happened (processed)
        evidence: Key evidence supporting this finding
        original_title: Original article title
        original_summary: Original article summary
        original_content: Full article content (if available)
        source_name: Name of source (e.g., "OpenAI Blog")
        source_url: URL to original article
        published_at: When the original article was published
        relevance_score: Relevance/importance score (0.0-1.0)
        source_confidence: Confidence in source reliability (0.0-1.0)
        source_confidence_factors: Explanation of confidence score
        requires_review: Flag for low-confidence items requiring human review
        detected_at: When this finding was created
        included_in_brief_id: ID of brief that included this finding (if any)
        id: Database ID (set after saving)
    """
    competitor: str
    event_type: str
    title: str
    summary: str
    evidence: str
    original_title: str
    original_summary: str
    original_content: Optional[str]
    source_name: str
    source_url: str
    published_at: datetime
    relevance_score: float
    source_confidence: float
    source_confidence_factors: str
    requires_review: bool
    detected_at: datetime
    included_in_brief_id: Optional[int] = None
    id: Optional[int] = None
    # Phase 12 enhancements: intelligence quality metadata
    priority: str = 'medium'  # 'high', 'medium', 'low'
    content_type: str = 'other'  # 'technical', 'customer_story', 'consumer_marketing', 'partnership', 'other'
    action_context: str = 'neutral'  # 'active', 'passive', 'neutral'
    actor_score: float = 0.0  # Actor verification score (0.0-1.0)

    def __str__(self) -> str:
        """String representation for logging."""
        return f"[{self.competitor}] {self.event_type}: {self.title}"

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "competitor": self.competitor,
            "event_type": self.event_type,
            "title": self.title,
            "summary": self.summary,
            "evidence": self.evidence,
            "original_title": self.original_title,
            "original_summary": self.original_summary,
            "original_content": self.original_content,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "published_at": self.published_at.isoformat(),
            "relevance_score": self.relevance_score,
            "source_confidence": self.source_confidence,
            "source_confidence_factors": self.source_confidence_factors,
            "requires_review": self.requires_review,
            "detected_at": self.detected_at.isoformat(),
            "included_in_brief_id": self.included_in_brief_id,
            "priority": self.priority,
            "content_type": self.content_type,
            "action_context": self.action_context,
            "actor_score": self.actor_score,
        }

    def to_citation_dict(self) -> dict:
        """
        Convert to citation format for brief generation.

        Returns:
            Dictionary with fields needed for LLM context and citation
        """
        return {
            "id": self.id,
            "competitor": self.competitor,
            "event_type": self.event_type,
            "title": self.title,
            "summary": self.summary,
            "evidence": self.evidence,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "source_confidence": self.source_confidence,
            "source_confidence_factors": self.source_confidence_factors,
            "relevance_score": self.relevance_score,
            "published_date": self.published_at.isoformat(),
        }


@dataclass
class IntelligenceBrief:
    """
    Represents a generated intelligence brief.

    This model contains a structured brief summarizing competitor activity
    over a time period, with proper citations and grounding.

    Attributes:
        generated_at: When this brief was generated
        period_start: Start of the reporting period
        period_end: End of the reporting period
        executive_summary: High-level summary paragraph
        key_findings: List of key finding summaries with citations
        competitor_activity: Dictionary mapping competitor -> list of activities
        finding_ids: List of Finding IDs included in this brief
        finding_count: Total number of findings in this brief
        id: Database ID (set after saving)
    """
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    executive_summary: str
    key_findings: List[Dict[str, str]]  # Each: {text: str, source_url: str, source_name: str}
    competitor_activity: Dict[str, List[Dict[str, str]]]  # competitor -> [{text, source_url, source_name}]
    finding_ids: List[int]
    finding_count: int
    id: Optional[int] = None

    def __str__(self) -> str:
        """String representation for logging."""
        return f"Brief {self.period_start.date()} to {self.period_end.date()} ({self.finding_count} findings)"

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        import json
        return {
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "executive_summary": self.executive_summary,
            "key_findings_json": json.dumps(self.key_findings),
            "competitor_activity_json": json.dumps(self.competitor_activity),
            "finding_ids_json": json.dumps(self.finding_ids),
            "finding_count": self.finding_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'IntelligenceBrief':
        """
        Create IntelligenceBrief from database dictionary.

        Args:
            data: Dictionary with database fields

        Returns:
            IntelligenceBrief instance
        """
        import json
        from datetime import datetime

        return cls(
            id=data.get("id"),
            generated_at=datetime.fromisoformat(data["generated_at"]),
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
            executive_summary=data["executive_summary"],
            key_findings=json.loads(data["key_findings_json"]),
            competitor_activity=json.loads(data["competitor_activity_json"]),
            finding_ids=json.loads(data["finding_ids_json"]),
            finding_count=data["finding_count"],
        )

    def format_for_email(self) -> str:
        """
        Format the brief for email delivery (plain text).

        Returns:
            Formatted string ready for email
        """
        lines = []

        lines.append(f"PERIOD: {self.period_start.strftime('%Y-%m-%d')} to {self.period_end.strftime('%Y-%m-%d')}")
        lines.append(f"FINDINGS: {self.finding_count}")
        lines.append("")
        lines.append("=" * 60)
        lines.append("EXECUTIVE SUMMARY")
        lines.append("=" * 60)
        lines.append(self.executive_summary)
        lines.append("")

        lines.append("=" * 60)
        lines.append("KEY FINDINGS")
        lines.append("=" * 60)
        for i, finding in enumerate(self.key_findings, 1):
            lines.append(f"{i}. {finding['text']}")
            lines.append(f"   Source: {finding['source_name']} - {finding['source_url']}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("COMPETITOR ACTIVITY")
        lines.append("=" * 60)
        for competitor, activities in sorted(self.competitor_activity.items()):
            lines.append(f"\n{competitor}:")
            for activity in activities:
                lines.append(f"  • {activity['text']}")
                lines.append(f"    Source: {activity['source_name']} - {activity['source_url']}")

        return "\n".join(lines)
