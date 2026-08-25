"""
Configuration Management Module

This file loads and validates all configuration settings from environment variables.
It acts as a single source of truth for all configuration across the application.

Why this file exists:
- Centralizes all configuration in one place
- Validates settings at startup (fail fast if misconfigured)
- Provides type-safe access to configuration values
- Makes it easy to change settings without touching code
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Application configuration class.

    All configuration values are loaded from environment variables.
    If required values are missing, the application will fail at startup.
    """

    # API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Email Configuration
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    SENDER_PASSWORD: str = os.getenv("SENDER_PASSWORD", "")
    RECEIVER_EMAIL: str = os.getenv("RECEIVER_EMAIL", "")

    # Database Configuration
    PROJECT_ROOT = Path(__file__).parent.parent
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH",
        str(PROJECT_ROOT / "database" / "news.db")
    )

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv(
        "LOG_FILE",
        str(PROJECT_ROOT / "logs" / "agent.log")
    )

    # Timezone Configuration
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Karachi")

    # News Configuration
    NEWS_MAX_AGE_HOURS: int = 24  # Only consider news from last 24 hours
    DUPLICATE_CHECK_DAYS: int = 30  # Check for duplicates within last 30 days
    RSS_FETCH_TIMEOUT: int = int(os.getenv("RSS_FETCH_TIMEOUT", "10"))  # Timeout for RSS requests in seconds

    # Source Diversity Configuration
    DIVERSITY_TOP_N: int = int(os.getenv("DIVERSITY_TOP_N", "10"))  # Consider top N ranked articles for diversity
    DIVERSITY_MAX_PER_SOURCE: int = int(os.getenv("DIVERSITY_MAX_PER_SOURCE", "3"))  # Max articles per source in candidate pool

    # LinkedIn Post Configuration
    MAX_POST_WORDS: int = 180
    MIN_HASHTAGS: int = 4
    MAX_HASHTAGS: int = 6

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate that all required configuration values are present.

        Returns:
            tuple: (is_valid, list_of_missing_fields)
        """
        missing = []

        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.SENDER_EMAIL:
            missing.append("SENDER_EMAIL")
        if not cls.SENDER_PASSWORD:
            missing.append("SENDER_PASSWORD")
        if not cls.RECEIVER_EMAIL:
            missing.append("RECEIVER_EMAIL")

        return (len(missing) == 0, missing)

    @classmethod
    def ensure_directories(cls) -> None:
        """
        Create necessary directories if they don't exist.
        """
        # Create database directory
        Path(cls.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

        # Create logs directory
        Path(cls.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)


# Create a singleton instance
config = Config()
