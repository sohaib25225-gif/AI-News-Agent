"""
Source Confidence Calculator Module

Calculates multi-factor source confidence scores.

IMPORTANT: source_confidence is NOT factual truth confidence.
It represents confidence in the source and reporting quality, incorporating:
1. Source type (official vs third-party)
2. Independent corroboration
3. Language certainty

Used to flag findings that require human review.
"""

from typing import List, Tuple
from models import NewsArticle
from utils import get_logger

logger = get_logger(__name__)


class SourceConfidenceCalculator:
    """
    Calculates source confidence with multi-factor scoring.
    """

    # Source type base scores
    SOURCE_TYPE_SCORES = {
        "official": 0.6,      # Official company source
        "credible": 0.4,      # Credible third-party
        "unknown": 0.2,       # Unknown or uncertain source
    }

    # Corroboration bonuses
    CORROBORATION_BONUSES = {
        1: 0.1,   # Single source (base)
        2: 0.2,   # Two independent sources
        3: 0.3,   # Three+ independent sources
    }

    # Language adjustment
    LANGUAGE_ADJUSTMENTS = {
        "uncertain": -0.1,  # Uncertain language ("may", "reportedly", "allegedly")
        "definite": 0.1,    # Definite language ("announced", "confirmed", "official")
    }

    # Review threshold
    REVIEW_THRESHOLD = 0.6

    def __init__(self):
        """Initialize source confidence calculator."""
        pass

    def calculate(
        self,
        article: NewsArticle,
        corroborating_articles: List[NewsArticle] = None
    ) -> Tuple[float, str, bool]:
        """
        Calculate source confidence for an article.

        Args:
            article: Article to evaluate
            corroborating_articles: Other articles reporting the same event (optional)

        Returns:
            Tuple of (confidence_score, confidence_factors, requires_review)
        """
        factors = []

        # Factor 1: Source type
        source_type = self._classify_source_type(article.source)
        source_score = self.SOURCE_TYPE_SCORES[source_type]
        factors.append(f"source_type={source_type}({source_score:.1f})")

        # Factor 2: Corroboration
        if corroborating_articles:
            # Count truly independent sources (different domains)
            independent_count = self._count_independent_sources([article] + corroborating_articles)
            corroboration_bonus = self.CORROBORATION_BONUSES.get(
                min(independent_count, 3), 0.1
            )
            factors.append(f"corroboration={independent_count}_sources(+{corroboration_bonus:.1f})")
        else:
            independent_count = 1
            corroboration_bonus = 0.1
            factors.append("corroboration=single_source(+0.1)")

        # Factor 3: Language analysis
        language_type = self._analyze_language(article.title, article.summary)
        language_adj = self.LANGUAGE_ADJUSTMENTS.get(language_type, 0.0)
        if language_adj != 0:
            factors.append(f"language={language_type}({language_adj:+.1f})")

        # Calculate final score
        confidence = source_score + corroboration_bonus + language_adj

        # Clamp to 0.0-1.0
        confidence = max(0.0, min(1.0, confidence))

        # Determine if review required
        requires_review = confidence < self.REVIEW_THRESHOLD

        # Format factors string
        factors_str = ", ".join(factors)

        logger.debug(f"Source confidence for '{article.title[:50]}': {confidence:.2f} ({factors_str})")

        return confidence, factors_str, requires_review

    def _classify_source_type(self, source_name: str) -> str:
        """
        Classify source as official, credible third-party, or unknown.

        Args:
            source_name: Name of the source

        Returns:
            Source type string
        """
        # Official company sources
        official_sources = [
            "OpenAI Blog", "Google AI Blog", "DeepMind Blog",
            "Meta Blog", "Microsoft Blog"
        ]

        # Credible third-party sources
        credible_sources = [
            "TechCrunch AI", "MIT Technology Review AI",
            "Hugging Face Blog", "GitHub Blog"
        ]

        if source_name in official_sources:
            return "official"
        elif source_name in credible_sources:
            return "credible"
        else:
            return "unknown"

    def _count_independent_sources(self, articles: List[NewsArticle]) -> int:
        """
        Count genuinely independent sources.

        Sources are independent if they have different domains.
        Same URL/domain counts as one source.

        Args:
            articles: List of articles

        Returns:
            Count of independent sources
        """
        domains = set()

        for article in articles:
            # Extract domain from URL
            url = article.url.lower()
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                # Remove www prefix
                if domain.startswith("www."):
                    domain = domain[4:]
                domains.add(domain)

        return len(domains)

    def _analyze_language(self, title: str, summary: str) -> str:
        """
        Analyze language for certainty markers.

        Args:
            title: Article title
            summary: Article summary

        Returns:
            Language type: "uncertain", "definite", or "neutral"
        """
        text = f"{title} {summary}".lower()

        # Uncertain markers
        uncertain_markers = [
            "may", "might", "could", "reportedly", "allegedly",
            "rumor", "unconfirmed", "claim", "suggest", "speculate"
        ]

        # Definite markers
        definite_markers = [
            "announce", "confirmed", "official", "release",
            "launch", "unveiled", "published", "stated"
        ]

        uncertain_count = sum(1 for marker in uncertain_markers if marker in text)
        definite_count = sum(1 for marker in definite_markers if marker in text)

        if uncertain_count > definite_count:
            return "uncertain"
        elif definite_count > uncertain_count:
            return "definite"
        else:
            return "neutral"
