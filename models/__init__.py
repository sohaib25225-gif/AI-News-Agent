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
from typing import Optional


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
