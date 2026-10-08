"""
Article Deduplicator Module

Detects and removes duplicate articles reporting the same event.

Uses multiple signals:
- URL matching (exact duplicates)
- Title similarity (same story, different source)
- Content overlap (similar reporting)
"""

import re
from typing import List
from models import NewsArticle
from utils import get_logger

logger = get_logger(__name__)


class Deduplicator:
    """
    Deduplicates articles reporting the same event.
    """

    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize deduplicator.

        Args:
            similarity_threshold: Minimum similarity to consider duplicate (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """
        Remove duplicate articles from list.

        Strategy:
        1. Group by exact URL (same article)
        2. Group by title similarity (same story)
        3. Keep highest-quality version of each unique event

        Args:
            articles: List of articles to deduplicate

        Returns:
            Deduplicated list of articles
        """
        if not articles:
            return []

        logger.info(f"Deduplicating {len(articles)} articles")

        # Track unique articles
        unique_articles = []
        seen_urls = set()
        seen_titles = []

        for article in articles:
            # Skip exact URL duplicates
            if article.url in seen_urls:
                logger.debug(f"Skipping duplicate URL: {article.url}")
                continue

            # Check title similarity with existing articles
            is_duplicate = False
            for existing in seen_titles:
                similarity = self._title_similarity(article.title, existing)
                if similarity >= self.similarity_threshold:
                    logger.debug(f"Skipping similar title: {article.title[:50]}... (similarity: {similarity:.2f})")
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(article)
                seen_urls.add(article.url)
                seen_titles.append(article.title)

        logger.info(f"Deduplication complete: {len(unique_articles)} unique articles (removed {len(articles) - len(unique_articles)})")

        return unique_articles

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles.

        Uses Jaccard similarity on words (ignoring common stopwords).

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score (0.0-1.0)
        """
        # Stopwords to ignore
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are'
        }

        # Tokenize and normalize
        words1 = set(word.lower() for word in re.findall(r'\b\w+\b', title1) if word.lower() not in stopwords)
        words2 = set(word.lower() for word in re.findall(r'\b\w+\b', title2) if word.lower() not in stopwords)

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def group_duplicates(self, articles: List[NewsArticle]) -> List[List[NewsArticle]]:
        """
        Group articles that report the same event (for corroboration).

        Args:
            articles: List of articles

        Returns:
            List of groups (each group is a list of duplicate articles)
        """
        groups = []
        remaining = articles.copy()

        while remaining:
            article = remaining.pop(0)
            group = [article]

            # Find similar articles
            to_remove = []
            for other in remaining:
                similarity = self._title_similarity(article.title, other.title)
                if similarity >= self.similarity_threshold:
                    group.append(other)
                    to_remove.append(other)

            # Remove articles added to this group
            for item in to_remove:
                remaining.remove(item)

            groups.append(group)

        logger.info(f"Grouped {len(articles)} articles into {len(groups)} unique events")
        return groups
