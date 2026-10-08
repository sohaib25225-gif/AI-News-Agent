"""
Relevance Scorer Module

Scores articles for competitive intelligence relevance and importance.

Different from V0 LinkedIn scoring - focuses on:
- Strategic importance
- Business impact
- Innovation significance
- Competitive positioning value
"""

import re
from typing import List
from models import NewsArticle
from utils import get_logger

logger = get_logger(__name__)


class RelevanceScorer:
    """
    Scores articles for competitive intelligence relevance.
    """

    # Strategic importance indicators
    HIGH_IMPACT_KEYWORDS = [
        "launch", "announce", "release", "breakthrough", "first",
        "acquisition", "merger", "funding", "raise", "investment",
        "partnership", "collaborate", "pricing", "price", "api",
        "leadership", "ceo", "founder", "executive"
    ]

    # Innovation indicators
    INNOVATION_KEYWORDS = [
        "new", "novel", "revolutionary", "breakthrough", "innovation",
        "first", "unprecedented", "state-of-the-art", "sota",
        "outperform", "beats", "achieves", "milestone"
    ]

    # Low-value indicators (reduce score)
    LOW_VALUE_KEYWORDS = [
        "minor update", "documentation", "typo", "bug fix",
        "maintenance", "routine", "scheduled", "planned maintenance"
    ]

    def __init__(self, min_score: float = 0.3):
        """
        Initialize relevance scorer.

        Args:
            min_score: Minimum relevance score to keep articles (0.0-1.0)
        """
        self.min_score = min_score

    def score_article(self, article: NewsArticle) -> float:
        """
        Calculate relevance score for an article.

        Args:
            article: Article to score

        Returns:
            Relevance score (0.0-1.0)
        """
        score = 0.0

        # Combine title, summary, and content
        text = f"{article.title} {article.summary}".lower()
        if article.content:
            text += f" {article.content[:500]}".lower()  # First 500 chars of content

        # Score components
        impact_score = self._score_impact(text)
        innovation_score = self._score_innovation(text)
        source_boost = self._score_source(article.source)

        # Penalties
        low_value_penalty = self._score_low_value(text)

        # Combine scores (weighted)
        score = (
            impact_score * 0.4 +
            innovation_score * 0.3 +
            source_boost * 0.3 -
            low_value_penalty
        )

        # Clamp to 0.0-1.0
        score = max(0.0, min(1.0, score))

        logger.debug(f"Relevance score for '{article.title[:50]}': {score:.2f} (impact={impact_score:.2f}, innovation={innovation_score:.2f}, source={source_boost:.2f})")

        return score

    def _score_impact(self, text: str) -> float:
        """Score strategic impact based on keywords."""
        matches = sum(1 for keyword in self.HIGH_IMPACT_KEYWORDS if keyword in text)
        return min(1.0, matches * 0.15)  # Each match adds 0.15, cap at 1.0

    def _score_innovation(self, text: str) -> float:
        """Score innovation level based on keywords."""
        matches = sum(1 for keyword in self.INNOVATION_KEYWORDS if keyword in text)
        return min(1.0, matches * 0.2)  # Each match adds 0.2, cap at 1.0

    def _score_source(self, source: str) -> float:
        """Boost score for high-credibility sources."""
        high_credibility = ["OpenAI Blog", "Google AI Blog", "DeepMind Blog", "Meta Blog", "Microsoft Blog"]
        if source in high_credibility:
            return 0.8
        return 0.5

    def _score_low_value(self, text: str) -> float:
        """Penalty for low-value content."""
        matches = sum(1 for keyword in self.LOW_VALUE_KEYWORDS if keyword in text)
        return min(0.5, matches * 0.2)  # Each match subtracts 0.2, max penalty 0.5

    def score_and_filter(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """
        Score articles and filter by minimum relevance.

        Args:
            articles: List of articles to score

        Returns:
            Filtered list of relevant articles (with scores set)
        """
        logger.info(f"Scoring {len(articles)} articles for relevance")

        relevant_articles = []

        for article in articles:
            score = self.score_article(article)
            article.score = score  # Set score on article

            if score >= self.min_score:
                relevant_articles.append(article)
            else:
                logger.debug(f"Filtered low-relevance article: {article.title[:50]} (score: {score:.2f})")

        logger.info(f"Relevance filtering: {len(relevant_articles)} articles pass threshold (removed {len(articles) - len(relevant_articles)})")

        # Sort by score (highest first)
        relevant_articles.sort(key=lambda x: x.score, reverse=True)

        return relevant_articles
