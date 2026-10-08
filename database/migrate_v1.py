"""
V1 Database Migration Script

This script adds the V1 intelligence tables to the existing database
WITHOUT modifying or deleting any V0 data.

New tables:
- findings: Stores competitor intelligence findings
- intelligence_briefs: Stores generated weekly briefs

IMPORTANT: This is an ADDITIVE migration. It does not modify posted_articles.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config
from utils import get_logger

logger = get_logger(__name__)


def verify_v0_schema(conn: sqlite3.Connection) -> bool:
    """
    Verify that V0 schema exists and is intact.

    Returns:
        True if V0 schema is valid
    """
    cursor = conn.cursor()

    # Check that posted_articles table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='posted_articles'
    """)

    if not cursor.fetchone():
        logger.error("V0 posted_articles table not found!")
        return False

    # Check that required columns exist
    cursor.execute("PRAGMA table_info(posted_articles)")
    columns = {row[1] for row in cursor.fetchall()}

    required_columns = {'id', 'title', 'source', 'url', 'published_date', 'posted_date', 'summary', 'score'}

    if not required_columns.issubset(columns):
        missing = required_columns - columns
        logger.error(f"V0 schema invalid. Missing columns: {missing}")
        return False

    logger.info("V0 schema verified successfully")
    return True


def create_v1_tables(conn: sqlite3.Connection) -> bool:
    """
    Create V1 tables (findings and intelligence_briefs).

    Returns:
        True if successful
    """
    cursor = conn.cursor()

    try:
        # Create findings table
        logger.info("Creating findings table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_confidence REAL NOT NULL,
                detected_at TEXT NOT NULL,
                article_published_date TEXT NOT NULL
            )
        """)

        # Create indexes for findings
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

        logger.info("Findings table created successfully")

        # Create intelligence_briefs table
        logger.info("Creating intelligence_briefs table...")
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

        # Create index for intelligence_briefs
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_briefs_generated_at
            ON intelligence_briefs(generated_at)
        """)

        logger.info("Intelligence_briefs table created successfully")

        conn.commit()
        return True

    except sqlite3.Error as e:
        logger.error(f"Error creating V1 tables: {e}")
        conn.rollback()
        return False


def verify_v1_schema(conn: sqlite3.Connection) -> bool:
    """
    Verify that V1 tables were created successfully.

    Returns:
        True if V1 schema is valid
    """
    cursor = conn.cursor()

    # Check findings table
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='findings'
    """)

    if not cursor.fetchone():
        logger.error("Findings table not found!")
        return False

    # Check intelligence_briefs table
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='intelligence_briefs'
    """)

    if not cursor.fetchone():
        logger.error("Intelligence_briefs table not found!")
        return False

    logger.info("V1 schema verified successfully")
    return True


def run_migration(db_path: str = None) -> bool:
    """
    Run the V1 database migration.

    Args:
        db_path: Path to database file (defaults to config.DATABASE_PATH)

    Returns:
        True if migration successful
    """
    db_path = db_path or config.DATABASE_PATH

    logger.info("=" * 60)
    logger.info("V1 DATABASE MIGRATION")
    logger.info(f"Database: {db_path}")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Verify database file exists
    if not Path(db_path).exists():
        logger.error(f"Database file not found: {db_path}")
        return False

    # Connect to database
    conn = sqlite3.Connection(db_path)

    try:
        # Step 1: Verify V0 schema
        logger.info("Step 1: Verifying V0 schema...")
        if not verify_v0_schema(conn):
            return False

        # Step 2: Create V1 tables
        logger.info("Step 2: Creating V1 tables...")
        if not create_v1_tables(conn):
            return False

        # Step 3: Verify V1 schema
        logger.info("Step 3: Verifying V1 schema...")
        if not verify_v1_schema(conn):
            return False

        logger.info("=" * 60)
        logger.info("MIGRATION SUCCESSFUL")
        logger.info("=" * 60)

        # Show summary
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM posted_articles")
        v0_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM findings")
        findings_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM intelligence_briefs")
        briefs_count = cursor.fetchone()[0]

        logger.info(f"V0 posted_articles: {v0_count} records (preserved)")
        logger.info(f"V1 findings: {findings_count} records")
        logger.info(f"V1 intelligence_briefs: {briefs_count} records")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
