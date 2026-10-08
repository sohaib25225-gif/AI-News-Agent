"""
V1 Fix Migration Script

This script adds missing columns to the V1 findings table to match the approved specification.

This migration is ADDITIVE and SAFE:
- Adds new columns with default values
- Preserves existing data
- Does not modify or delete existing columns
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


def add_missing_columns(conn: sqlite3.Connection) -> bool:
    """
    Add missing columns to findings table.

    Returns:
        True if successful
    """
    cursor = conn.cursor()

    try:
        # Get existing columns
        cursor.execute("PRAGMA table_info(findings)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        logger.info(f"Existing columns: {existing_columns}")

        # Define new columns with default values
        new_columns = [
            ("evidence", "TEXT DEFAULT ''"),
            ("original_title", "TEXT DEFAULT ''"),
            ("original_summary", "TEXT DEFAULT ''"),
            ("original_content", "TEXT DEFAULT NULL"),
            ("published_at", "TEXT DEFAULT ''"),
            ("relevance_score", "REAL DEFAULT 0.5"),
            ("source_confidence_factors", "TEXT DEFAULT ''"),
            ("requires_review", "INTEGER DEFAULT 0"),  # SQLite uses INTEGER for boolean
            ("included_in_brief_id", "INTEGER DEFAULT NULL"),
            # Phase 11 intelligence quality columns
            ("priority", "TEXT DEFAULT 'medium'"),
            ("content_type", "TEXT DEFAULT 'other'"),
            ("action_context", "TEXT DEFAULT 'neutral'"),
            ("actor_score", "REAL DEFAULT 0.0"),
        ]

        # Add missing columns
        columns_added = 0
        for col_name, col_def in new_columns:
            if col_name not in existing_columns:
                logger.info(f"Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE findings ADD COLUMN {col_name} {col_def}")
                columns_added += 1
            else:
                logger.debug(f"Column already exists: {col_name}")

        # Migrate existing data: populate original_* from current values if empty
        if columns_added > 0:
            logger.info("Migrating existing data...")
            cursor.execute("""
                UPDATE findings
                SET original_title = title,
                    original_summary = summary,
                    evidence = summary,
                    published_at = article_published_date
                WHERE original_title = '' OR original_title IS NULL
            """)

        conn.commit()
        logger.info(f"Added {columns_added} new columns successfully")
        return True

    except sqlite3.Error as e:
        logger.error(f"Error adding columns: {e}")
        conn.rollback()
        return False


def verify_schema(conn: sqlite3.Connection) -> bool:
    """
    Verify that all required columns exist.

    Returns:
        True if schema is valid
    """
    cursor = conn.cursor()

    required_columns = {
        'id', 'competitor', 'event_type', 'title', 'summary', 'evidence',
        'original_title', 'original_summary', 'original_content',
        'source_name', 'source_url', 'published_at',
        'relevance_score', 'source_confidence', 'source_confidence_factors',
        'requires_review', 'detected_at', 'included_in_brief_id',
        'article_published_date',  # Keep old column for backward compatibility
        # Phase 11 intelligence quality columns
        'priority', 'content_type', 'action_context', 'actor_score',
    }

    cursor.execute("PRAGMA table_info(findings)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    missing = required_columns - existing_columns
    if missing:
        logger.error(f"Missing columns: {missing}")
        return False

    logger.info("Schema verification passed")
    return True


def run_migration(db_path: str = None) -> bool:
    """
    Run the V1 fix migration.

    Args:
        db_path: Path to database file (defaults to config.DATABASE_PATH)

    Returns:
        True if migration successful
    """
    db_path = db_path or config.DATABASE_PATH

    logger.info("=" * 60)
    logger.info("V1 FIX MIGRATION")
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
        # Step 1: Add missing columns
        logger.info("Step 1: Adding missing columns...")
        if not add_missing_columns(conn):
            return False

        # Step 2: Verify schema
        logger.info("Step 2: Verifying schema...")
        if not verify_schema(conn):
            return False

        logger.info("=" * 60)
        logger.info("MIGRATION SUCCESSFUL")
        logger.info("=" * 60)

        # Show summary
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM findings")
        findings_count = cursor.fetchone()[0]

        logger.info(f"Findings table: {findings_count} records (preserved)")
        logger.info("All required columns present")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
