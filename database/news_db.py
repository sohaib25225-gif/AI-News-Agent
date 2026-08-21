"""
Database Management Module

This module handles all database operations for the AI News Agent.

Why this file exists:
- Stores news articles we've already used (duplicate detection)
- Tracks posting history
- Ensures we don't repeat the same news within 30 days

How it works:
- Uses SQLite (simple, no server needed, file-based)
- Creates tables automatically on first run
- Provides clean methods to check/save articles
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from models import NewsArticle
from config import config
from utils import get_logger

logger = get_logger(__name__)


class NewsDatabase:
    """
    Manages the SQLite database for news articles and posting history.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file (default from config)
        """
        self.db_path = db_path or config.DATABASE_PATH
        self._ensure_db_exists()
        self._create_tables()

    def _ensure_db_exists(self) -> None:
        """Create database directory if it doesn't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection.

        Returns:
            SQLite connection object
        """
        conn = sqlite3.Connection(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn

    def _create_tables(self) -> None:
        """
        Create database tables if they don't exist.

        Tables:
        - posted_articles: Stores articles we've posted about
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Table for posted articles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posted_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    published_date TEXT NOT NULL,
                    posted_date TEXT NOT NULL,
                    summary TEXT,
                    score REAL DEFAULT 0.0
                )
            """)

            # Index for faster duplicate checking
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posted_date
                ON posted_articles(posted_date)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_url
                ON posted_articles(url)
            """)

            conn.commit()
            logger.debug("Database tables created/verified")

        except sqlite3.Error as e:
            logger.error(f"Database table creation error: {str(e)}")
            raise
        finally:
            conn.close()

    def is_duplicate(self, article: NewsArticle, days: int = None) -> bool:
        """
        Check if article is a duplicate within specified days.

        An article is considered duplicate if:
        - Same URL was already posted
        - Very similar title was posted within the time window

        Args:
            article: Article to check
            days: Number of days to look back (default from config)

        Returns:
            True if duplicate, False otherwise
        """
        days = days or config.DUPLICATE_CHECK_DAYS
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Check exact URL match
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM posted_articles
                WHERE url = ? AND posted_date >= ?
            """, (article.url, cutoff_str))

            if cursor.fetchone()["count"] > 0:
                logger.debug(f"Duplicate URL found: {article.url}")
                return True

            # Check similar title
            # We'll use simple similarity: same words (case-insensitive)
            cursor.execute("""
                SELECT title
                FROM posted_articles
                WHERE posted_date >= ?
            """, (cutoff_str,))

            article_title_lower = article.title.lower()
            for row in cursor.fetchall():
                existing_title = row["title"].lower()
                # Simple similarity check: if titles share 70%+ words
                if self._title_similarity(article_title_lower, existing_title) > 0.7:
                    logger.debug(f"Similar title found: {existing_title}")
                    return True

            return False

        except sqlite3.Error as e:
            logger.error(f"Database duplicate check error: {str(e)}")
            # On error, assume not duplicate to avoid blocking
            return False
        finally:
            conn.close()

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate simple word-based similarity between titles.

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score between 0 and 1
        """
        # Split into words, remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}

        words1 = set(word for word in title1.split() if word not in stopwords)
        words2 = set(word for word in title2.split() if word not in stopwords)

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def save_posted_article(self, article: NewsArticle) -> bool:
        """
        Save an article to the posted articles database.

        Args:
            article: Article that was posted

        Returns:
            True if saved successfully, False otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO posted_articles
                (title, source, url, published_date, posted_date, summary, score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                article.title,
                article.source,
                article.url,
                article.published_date.isoformat(),
                datetime.now().isoformat(),
                article.summary,
                article.score
            ))

            conn.commit()
            logger.info(f"Saved article to database: {article.title}")
            return True

        except sqlite3.IntegrityError:
            logger.warning(f"Article already exists in database: {article.url}")
            return False
        except sqlite3.Error as e:
            logger.error(f"Database save error: {str(e)}")
            return False
        finally:
            conn.close()

    def get_recent_articles(self, days: int = 30) -> list[dict]:
        """
        Get articles posted within the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of article dictionaries
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM posted_articles
                WHERE posted_date >= ?
                ORDER BY posted_date DESC
            """, (cutoff_str,))

            articles = []
            for row in cursor.fetchall():
                articles.append(dict(row))

            return articles

        except sqlite3.Error as e:
            logger.error(f"Database query error: {str(e)}")
            return []
        finally:
            conn.close()

    def cleanup_old_entries(self, days: int = 90) -> int:
        """
        Remove entries older than specified days.

        Args:
            days: Keep entries from last N days

        Returns:
            Number of entries deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM posted_articles
                WHERE posted_date < ?
            """, (cutoff_str,))

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Cleaned up {deleted_count} old entries")
            return deleted_count

        except sqlite3.Error as e:
            logger.error(f"Database cleanup error: {str(e)}")
            return 0
        finally:
            conn.close()
