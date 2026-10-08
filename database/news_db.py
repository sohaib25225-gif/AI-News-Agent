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
from models import NewsArticle, Finding, IntelligenceBrief
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
        - findings: V1 competitive intelligence findings
        - intelligence_briefs: V1 generated briefs
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

            # V1 findings table (with Phase 11 columns)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competitor TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    evidence TEXT DEFAULT '',
                    original_title TEXT DEFAULT '',
                    original_summary TEXT DEFAULT '',
                    original_content TEXT DEFAULT NULL,
                    source_url TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_confidence REAL NOT NULL,
                    source_confidence_factors TEXT DEFAULT '',
                    published_at TEXT DEFAULT '',
                    relevance_score REAL DEFAULT 0.5,
                    requires_review INTEGER DEFAULT 0,
                    detected_at TEXT NOT NULL,
                    included_in_brief_id INTEGER DEFAULT NULL,
                    article_published_date TEXT DEFAULT '',
                    priority TEXT DEFAULT 'medium',
                    content_type TEXT DEFAULT 'other',
                    action_context TEXT DEFAULT 'neutral',
                    actor_score REAL DEFAULT 0.0
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_findings_competitor
                ON findings(competitor)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_findings_event_type
                ON findings(event_type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_findings_detected_at
                ON findings(detected_at)
            """)

            # V1 intelligence briefs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intelligence_briefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generated_at TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    executive_summary TEXT NOT NULL,
                    key_findings_json TEXT NOT NULL,
                    competitor_activity_json TEXT NOT NULL,
                    finding_ids_json TEXT NOT NULL,
                    finding_count INTEGER NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_briefs_generated_at
                ON intelligence_briefs(generated_at)
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

    # ========================================================================
    # V1 Methods - Competitive Intelligence
    # ========================================================================

    def save_finding(self, finding: Finding) -> Optional[int]:
        """
        Save a finding to the database.

        Args:
            finding: Finding object to save

        Returns:
            Finding ID if saved successfully, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO findings
                (competitor, event_type, title, summary, evidence,
                 original_title, original_summary, original_content,
                 source_name, source_url, published_at,
                 relevance_score, source_confidence, source_confidence_factors,
                 requires_review, detected_at, included_in_brief_id,
                 article_published_date,
                 priority, content_type, action_context, actor_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                finding.competitor,
                finding.event_type,
                finding.title,
                finding.summary,
                finding.evidence,
                finding.original_title,
                finding.original_summary,
                finding.original_content,
                finding.source_name,
                finding.source_url,
                finding.published_at.isoformat(),
                finding.relevance_score,
                finding.source_confidence,
                finding.source_confidence_factors,
                1 if finding.requires_review else 0,
                finding.detected_at.isoformat(),
                finding.included_in_brief_id,
                finding.published_at.isoformat(),  # Keep for backward compatibility
                finding.priority,
                finding.content_type,
                finding.action_context,
                finding.actor_score,
            ))

            conn.commit()
            finding_id = cursor.lastrowid
            logger.info(f"Saved finding #{finding_id}: {finding}")
            return finding_id

        except sqlite3.Error as e:
            logger.error(f"Database save finding error: {str(e)}")
            return None
        finally:
            conn.close()

    def get_findings(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        competitor: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> list[Finding]:
        """
        Get findings with optional filters.

        Args:
            start_date: Filter by detected_at >= start_date
            end_date: Filter by detected_at <= end_date
            competitor: Filter by competitor name
            event_type: Filter by event type

        Returns:
            List of Finding objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            query = "SELECT * FROM findings WHERE 1=1"
            params = []

            if start_date:
                query += " AND detected_at >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND detected_at <= ?"
                params.append(end_date.isoformat())

            if competitor:
                query += " AND competitor = ?"
                params.append(competitor)

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY detected_at DESC"

            cursor.execute(query, params)

            findings = []
            for row in cursor.fetchall():
                # Convert Row to dict for easier access with defaults
                row_dict = dict(row)

                finding = Finding(
                    id=row_dict["id"],
                    competitor=row_dict["competitor"],
                    event_type=row_dict["event_type"],
                    title=row_dict["title"],
                    summary=row_dict["summary"],
                    evidence=row_dict.get("evidence") or "",
                    original_title=row_dict.get("original_title") or row_dict["title"],
                    original_summary=row_dict.get("original_summary") or row_dict["summary"],
                    original_content=row_dict.get("original_content"),
                    source_name=row_dict["source_name"],
                    source_url=row_dict["source_url"],
                    published_at=datetime.fromisoformat(row_dict.get("published_at") or row_dict["detected_at"]),
                    relevance_score=row_dict.get("relevance_score") or 0.5,
                    source_confidence=row_dict["source_confidence"],
                    source_confidence_factors=row_dict.get("source_confidence_factors") or "",
                    requires_review=bool(row_dict.get("requires_review", 0)),
                    detected_at=datetime.fromisoformat(row_dict["detected_at"]),
                    included_in_brief_id=row_dict.get("included_in_brief_id"),
                    # Phase 11 intelligence quality fields
                    priority=row_dict.get("priority") or "medium",
                    content_type=row_dict.get("content_type") or "other",
                    action_context=row_dict.get("action_context") or "neutral",
                    actor_score=row_dict.get("actor_score") or 0.0,
                )
                findings.append(finding)

            return findings

        except sqlite3.Error as e:
            logger.error(f"Database get findings error: {str(e)}")
            return []
        finally:
            conn.close()

    def save_intelligence_brief(self, brief: IntelligenceBrief) -> Optional[int]:
        """
        Save an intelligence brief to the database.

        Args:
            brief: IntelligenceBrief object to save

        Returns:
            Brief ID if saved successfully, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            brief_dict = brief.to_dict()

            cursor.execute("""
                INSERT INTO intelligence_briefs
                (generated_at, period_start, period_end, executive_summary,
                 key_findings_json, competitor_activity_json, finding_ids_json, finding_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                brief_dict["generated_at"],
                brief_dict["period_start"],
                brief_dict["period_end"],
                brief_dict["executive_summary"],
                brief_dict["key_findings_json"],
                brief_dict["competitor_activity_json"],
                brief_dict["finding_ids_json"],
                brief_dict["finding_count"]
            ))

            conn.commit()
            brief_id = cursor.lastrowid
            logger.info(f"Saved intelligence brief #{brief_id}: {brief}")
            return brief_id

        except sqlite3.Error as e:
            logger.error(f"Database save brief error: {str(e)}")
            return None
        finally:
            conn.close()

    def get_latest_intelligence_brief(self) -> Optional[IntelligenceBrief]:
        """
        Get the most recent intelligence brief.

        Returns:
            IntelligenceBrief object or None if no briefs exist
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM intelligence_briefs
                ORDER BY generated_at DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            if not row:
                return None

            brief = IntelligenceBrief.from_dict(dict(row))
            return brief

        except sqlite3.Error as e:
            logger.error(f"Database get latest brief error: {str(e)}")
            return None
        finally:
            conn.close()

    def get_intelligence_briefs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> list[IntelligenceBrief]:
        """
        Get intelligence briefs with optional filters.

        Args:
            start_date: Filter by generated_at >= start_date
            end_date: Filter by generated_at <= end_date
            limit: Maximum number of briefs to return

        Returns:
            List of IntelligenceBrief objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            query = "SELECT * FROM intelligence_briefs WHERE 1=1"
            params = []

            if start_date:
                query += " AND generated_at >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND generated_at <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY generated_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            briefs = []
            for row in cursor.fetchall():
                brief = IntelligenceBrief.from_dict(dict(row))
                briefs.append(brief)

            return briefs

        except sqlite3.Error as e:
            logger.error(f"Database get briefs error: {str(e)}")
            return []
        finally:
            conn.close()
