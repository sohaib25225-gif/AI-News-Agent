"""
News Fetcher Service

This service fetches news articles from RSS feeds.

Why this file exists:
- Handles all news fetching logic
- Parses RSS feeds into our NewsArticle model
- Filters articles by date (last 24 hours only)
- Handles errors gracefully (one source failing doesn't break everything)

How it works:
1. Takes a list of news sources
2. Fetches RSS feed from each source
3. Parses the feed into articles
4. Filters by date
5. Returns list of NewsArticle objects
"""

from datetime import datetime, timedelta
from typing import Optional
import feedparser
import pytz
from models import NewsArticle
from config import config
from config.sources import NewsSource, get_active_sources
from utils import get_logger

logger = get_logger(__name__)


class NewsFetcher:
    """
    Fetches news articles from RSS feeds.
    """

    def __init__(self, max_age_hours: int = None):
        """
        Initialize the news fetcher.

        Args:
            max_age_hours: Maximum age of articles to consider (default from config)
        """
        self.max_age_hours = max_age_hours or config.NEWS_MAX_AGE_HOURS
        self.timezone = pytz.timezone(config.TIMEZONE)

    def fetch_all(self) -> list[NewsArticle]:
        """
        Fetch articles from all active sources.

        Returns:
            List of NewsArticle objects from all sources
        """
        logger.info("Starting news fetch from all sources")
        sources = get_active_sources()
        all_articles = []

        for source in sources:
            try:
                articles = self.fetch_from_source(source)
                all_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {source['name']}")
            except Exception as e:
                logger.error(f"Failed to fetch from {source['name']}: {str(e)}")
                # Continue with other sources even if one fails

        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles

    def fetch_from_source(self, source: NewsSource) -> list[NewsArticle]:
        """
        Fetch articles from a single RSS source.

        Args:
            source: NewsSource configuration

        Returns:
            List of NewsArticle objects from this source
        """
        if source["source_type"] != "rss":
            logger.warning(f"Source type {source['source_type']} not yet implemented")
            return []

        logger.debug(f"Fetching RSS feed: {source['url']}")
        feed = feedparser.parse(source["url"])

        if feed.bozo:
            # 'bozo' means the feed has errors
            logger.warning(f"Feed parsing warning for {source['name']}: {feed.bozo_exception}")

        articles = []
        cutoff_time = datetime.now(self.timezone) - timedelta(hours=self.max_age_hours)

        for entry in feed.entries:
            try:
                article = self._parse_entry(entry, source)
                if article and article.published_date >= cutoff_time:
                    articles.append(article)
            except Exception as e:
                logger.error(f"Failed to parse entry from {source['name']}: {str(e)}")
                continue

        return articles

    def _parse_entry(self, entry, source: NewsSource) -> Optional[NewsArticle]:
        """
        Parse a single RSS entry into a NewsArticle.

        Args:
            entry: RSS entry from feedparser
            source: Source this entry came from

        Returns:
            NewsArticle object or None if parsing fails
        """
        # Extract title
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Extract URL
        url = entry.get("link", "").strip()
        if not url:
            return None

        # Extract published date
        published_date = self._parse_date(entry)
        if not published_date:
            logger.warning(f"Could not parse date for: {title}")
            return None

        # Extract summary/description
        summary = entry.get("summary", entry.get("description", "")).strip()
        # Remove HTML tags from summary
        summary = self._clean_html(summary)

        # Extract content (if available)
        content = None
        if hasattr(entry, "content"):
            content = entry.content[0].value if entry.content else None
            if content:
                content = self._clean_html(content)

        return NewsArticle(
            title=title,
            source=source["name"],
            url=url,
            published_date=published_date,
            summary=summary,
            content=content
        )

    def _parse_date(self, entry) -> Optional[datetime]:
        """
        Parse published date from RSS entry.

        RSS feeds use different date formats. This tries multiple fields.

        Args:
            entry: RSS entry

        Returns:
            datetime object or None if parsing fails
        """
        # Try different date fields
        date_fields = ["published_parsed", "updated_parsed", "created_parsed"]

        for field in date_fields:
            if hasattr(entry, field):
                time_struct = getattr(entry, field)
                if time_struct:
                    try:
                        dt = datetime(*time_struct[:6])
                        # Make timezone-aware
                        if dt.tzinfo is None:
                            dt = self.timezone.localize(dt)
                        return dt
                    except Exception:
                        continue

        return None

    def _clean_html(self, text: str) -> str:
        """
        Remove HTML tags from text.

        Args:
            text: Text potentially containing HTML

        Returns:
            Clean text without HTML tags
        """
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
