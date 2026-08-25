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
        top_n: int = None,
        max_per_source: int = None
    ) -> list[NewsArticle]:
        """
        Select diverse candidates from ranked articles.

        Applies source diversity constraints AFTER scoring to prevent
        a single source from dominating the candidate pool.

        Args:
            ranked_articles: Articles already scored and ranked (highest first)
            top_n: Consider top N ranked articles (default from config)
            max_per_source: Maximum articles per source (default from config)

        Returns:
            List of diverse candidates, preserving rank order
        """
        # Use config defaults if not specified
        top_n = top_n if top_n is not None else config.DIVERSITY_TOP_N
        max_per_source = max_per_source if max_per_source is not None else config.DIVERSITY_MAX_PER_SOURCE

        # Edge case: empty list
        if not ranked_articles:
            return []

        # Edge case: invalid parameters
        if top_n <= 0 or max_per_source <= 0:
            logger.warning(f"Invalid diversity parameters: top_n={top_n}, max_per_source={max_per_source}")
            # Fallback to top 1 article
            return ranked_articles[:1]

        # Consider only top N ranked articles
        candidates_to_consider = ranked_articles[:min(top_n, len(ranked_articles))]

        # Track source counts
        source_counts = {}
        diverse_candidates = []

        for article in candidates_to_consider:
            # Handle missing/None source
            source = article.source if article.source else "Unknown"

            # Check if source has reached limit
            current_count = source_counts.get(source, 0)

            if current_count < max_per_source:
                diverse_candidates.append(article)
                source_counts[source] = current_count + 1

        # Edge case: no candidates passed diversity filter (shouldn't happen with reasonable params)
        if not diverse_candidates and ranked_articles:
            logger.warning("Diversity filter resulted in empty candidates, falling back to top article")
            return ranked_articles[:1]

        logger.info(f"Diversity selection: {len(diverse_candidates)} candidates from {len(source_counts)} sources")
        logger.debug(f"Source distribution in candidates: {source_counts}")

        return diverse_candidates
