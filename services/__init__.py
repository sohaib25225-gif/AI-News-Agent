"""
Services package.

This package contains all external service integrations:
- News fetching
- Email sending
- AI content generation
"""

from .news_fetcher import NewsFetcher
from .email_service import EmailService

__all__ = ["NewsFetcher", "EmailService"]
