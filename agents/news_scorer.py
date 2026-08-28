"""
News Scoring Module

This module scores news articles based on relevance and quality.

Why this file exists:
- Automatically ranks articles by importance
- Considers multiple factors (relevance, impact, freshness, etc.)
- Helps select the BEST article, not just any article

How it works:
1. Each article gets scored on multiple criteria (0-10 scale)
2. Criteria are weighted by importance
3. Final score is 0-100
4. Highest scoring article wins

Scoring Criteria:
- AI Relevance: How related to AI/ML is this?
- Developer Relevance: Useful for developers?
- Innovation: Is this new/groundbreaking?
- Impact: How significant is this announcement?
- Freshness: How recent? (newer = better)
- Source Credibility: Trust level of source
"""

from datetime import datetime, timedelta
from models import NewsArticle
from config import config
from utils import get_logger
import re

logger = get_logger(__name__)


class NewsScorer:
    """
    Scores news articles based on multiple relevance criteria.
    """

    # Keywords that boost AI relevance score
    HIGH_RELEVANCE_KEYWORDS = [
        "gpt", "llm", "large language model", "transformer", "neural network",
        "deep learning", "machine learning", "artificial intelligence",
        "model", "training", "fine-tuning", "embeddings", "rag",
        "agents", "chatbot", "generative ai", "diffusion"
    ]

    # Keywords that indicate developer relevance
    DEVELOPER_KEYWORDS = [
        "api", "sdk", "library", "framework", "open source", "github",
        "release", "documentation", "tutorial", "code", "python",
        "integration", "tool", "cli", "package"
    ]

    # Keywords indicating innovation/breakthrough
    INNOVATION_KEYWORDS = [
        "breakthrough", "first", "new", "launch", "announce", "introduce",
        "revolutionary", "state-of-the-art", "sota", "beats", "outperforms",
        "record", "unprecedented"
    ]

    # High-credibility sources (weight their articles higher)
    HIGH_CREDIBILITY_SOURCES = [
        "OpenAI Blog", "Anthropic Blog", "Google AI Blog", "DeepMind Blog",
        "Meta AI Blog", "Microsoft AI Blog", "NVIDIA Blog", "Papers with Code"
    ]

    def __init__(self):
        """Initialize the news scorer."""
        pass

    def score_article(self, article: NewsArticle) -> float:
        """
        Calculate overall score for an article.

        Args:
            article: NewsArticle to score

        Returns:
            Score from 0-100
        """
        scores = {
            "ai_relevance": self._score_ai_relevance(article),
            "developer_relevance": self._score_developer_relevance(article),
            "innovation": self._score_innovation(article),
            "freshness": self._score_freshness(article),
            "credibility": self._score_credibility(article),
        }

        # Weights for each criterion (must sum to 1.0)
        weights = {
            "ai_relevance": 0.30,
            "developer_relevance": 0.25,
            "innovation": 0.20,
            "freshness": 0.15,
            "credibility": 0.10,
        }

        # Calculate weighted score
        final_score = sum(scores[key] * weights[key] for key in scores)
        final_score = final_score * 10  # Scale to 0-100

        logger.debug(f"Scored '{article.title}': {final_score:.1f} {scores}")

        return round(final_score, 2)

    def _score_ai_relevance(self, article: NewsArticle) -> float:
        """
        Score based on AI/ML relevance.

        Returns:
            Score from 0-10
        """
        text = f"{article.title} {article.summary}".lower()

        # Count keyword matches
        keyword_matches = sum(1 for keyword in self.HIGH_RELEVANCE_KEYWORDS if keyword in text)

        # More matches = higher score
        score = min(10, keyword_matches * 1.5)

        return score

    def _score_developer_relevance(self, article: NewsArticle) -> float:
        """
        Score based on developer/practical relevance.

        Returns:
            Score from 0-10
        """
        text = f"{article.title} {article.summary}".lower()

        keyword_matches = sum(1 for keyword in self.DEVELOPER_KEYWORDS if keyword in text)

        score = min(10, keyword_matches * 2)

        return score

    def _score_innovation(self, article: NewsArticle) -> float:
        """
        Score based on innovation/novelty indicators.

        Returns:
            Score from 0-10
        """
        text = f"{article.title} {article.summary}".lower()

        keyword_matches = sum(1 for keyword in self.INNOVATION_KEYWORDS if keyword in text)

        score = min(10, keyword_matches * 2.5)

        return score

    def _score_freshness(self, article: NewsArticle) -> float:
        """
        Score based on how recent the article is.

        Returns:
            Score from 0-10 (newer = higher)
        """
        now = datetime.now(article.published_date.tzinfo)
        age_hours = (now - article.published_date).total_seconds() / 3600

        # Score decreases with age
        if age_hours < 6:
            score = 10
        elif age_hours < 12:
            score = 8
        elif age_hours < 18:
            score = 6
        elif age_hours < 24:
            score = 4
        else:
            score = 2

        return score

    def _score_credibility(self, article: NewsArticle) -> float:
        """
        Score based on source credibility.

        Returns:
            Score from 0-10
        """
        if article.source in self.HIGH_CREDIBILITY_SOURCES:
            return 10
        else:
            return 6  # Neutral score for other sources

    def rank_articles(self, articles: list[NewsArticle]) -> list[NewsArticle]:
        """
        Score and rank articles by relevance.

        Args:
            articles: List of NewsArticle objects

        Returns:
            Same list, sorted by score (highest first), with scores populated
        """
        logger.info(f"Scoring {len(articles)} articles")

        # Score each article
        for article in articles:
            article.score = self.score_article(article)

        # Sort by score (highest first)
        ranked = sorted(articles, key=lambda x: x.score, reverse=True)

        logger.info(f"Top article: {ranked[0].title} (score: {ranked[0].score})")

        return ranked

    def select_diverse_candidates(
        self,
        ranked_articles: list[NewsArticle],
        quality_threshold: int = None,
        top_n: int = None,
        max_per_source: int = None
    ) -> list[NewsArticle]:
        """
        Select diverse candidates using per-source best + quality threshold.

        Phase 3C: This approach ensures source diversity even when one source
        (e.g., arXiv) dominates both volume (95%) and top rankings. Instead of
        considering only top-N articles (which may all be from one source), we
        take the best article from each source and filter by quality.

        Algorithm:
        1. Group articles by source
        2. Select best article from each source
        3. Filter by minimum quality threshold
        4. Sort by score (highest first)

        Args:
            ranked_articles: Articles already scored and ranked (highest first)
            quality_threshold: Minimum score required (default from config)
            top_n: DEPRECATED - kept for backward compatibility, not used
            max_per_source: DEPRECATED - kept for backward compatibility, not used

        Returns:
            List of diverse candidates sorted by score (highest first)
        """
        # Use config default if not specified
        quality_threshold = quality_threshold if quality_threshold is not None else config.DIVERSITY_QUALITY_THRESHOLD

        # Edge case: empty list
        if not ranked_articles:
            return []

        # Edge case: invalid threshold
        if quality_threshold < 0:
            logger.warning(f"Invalid quality threshold: {quality_threshold}, using 0")
            quality_threshold = 0

        # Group by source, keeping only the best (first occurrence in ranked list)
        source_best = {}
        for article in ranked_articles:
            source = article.source if article.source else "Unknown"
            # Only keep first (best) article from each source
            if source not in source_best:
                source_best[source] = article

        # Filter by quality threshold
        candidates = [
            article for article in source_best.values()
            if article.score >= quality_threshold
        ]

        # Sort by score (highest first) to preserve quality ranking
        candidates.sort(key=lambda x: x.score, reverse=True)

        # Edge case: no candidates meet threshold
        if not candidates and ranked_articles:
            logger.warning(f"No candidates meet quality threshold {quality_threshold}, falling back to top article")
            return ranked_articles[:1]

        # Count unique sources
        unique_sources = len(set(c.source for c in candidates))

        logger.info(f"Diversity selection: {len(candidates)} candidates from {unique_sources} sources")
        logger.debug(f"Sources: {[c.source for c in candidates]}")

        return candidates
