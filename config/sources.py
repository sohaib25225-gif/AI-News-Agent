"""
News Sources Configuration

This file defines all the AI news sources we'll fetch from.
Each source includes its RSS feed URL and metadata.

Why this file exists:
- Centralizes all news sources in one place
- Makes it easy to add/remove sources
- Documents which sources we trust
- Separates data from logic

How it works:
- We prefer RSS feeds (free, reliable, no API limits)
- Each source has a name, URL, and category
- Sources are grouped by priority
"""

from typing import TypedDict


class NewsSource(TypedDict):
    """Structure for a news source."""
    name: str
    url: str
    category: str
    source_type: str  # 'rss' or 'api'


# Primary AI News Sources (RSS Feeds)
RSS_SOURCES: list[NewsSource] = [
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "Anthropic Blog",
        "url": "https://www.anthropic.com/news/rss.xml",
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "DeepMind Blog",
        "url": "https://deepmind.google/blog/rss.xml",
        "category": "research",
        "source_type": "rss"
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "community",
        "source_type": "rss"
    },
    {
        "name": "GitHub Blog - AI",
        "url": "https://github.blog/feed/",
        "category": "developer",
        "source_type": "rss"
    },
    {
        "name": "LangChain Blog",
        "url": "https://blog.langchain.dev/rss/",
        "category": "developer",
        "source_type": "rss"
    },
    {
        "name": "Meta AI Blog",
        "url": "https://ai.meta.com/blog/rss/",
        "category": "research",
        "source_type": "rss"
    },
    {
        "name": "Microsoft AI Blog",
        "url": "https://blogs.microsoft.com/ai/feed/",
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "NVIDIA Blog - AI",
        "url": "https://blogs.nvidia.com/feed/",
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "Mistral AI Blog",
        "url": "https://mistral.ai/news/rss.xml",
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "Papers with Code",
        "url": "https://paperswithcode.com/feeds/latest/",
        "category": "research",
        "source_type": "rss"
    },
    {
        "name": "arXiv AI",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "category": "research",
        "source_type": "rss"
    },
]

# Additional sources (can be enabled later)
ADDITIONAL_SOURCES: list[NewsSource] = [
    {
        "name": "Hacker News - AI",
        "url": "https://hn.algolia.com/api/v1/search?tags=story&query=AI",
        "category": "community",
        "source_type": "api"
    },
]


def get_active_sources() -> list[NewsSource]:
    """
    Get list of currently active news sources.

    Returns:
        List of news sources to fetch from
    """
    return RSS_SOURCES


def get_source_by_name(name: str) -> NewsSource | None:
    """
    Find a specific source by name.

    Args:
        name: Name of the source to find

    Returns:
        NewsSource if found, None otherwise
    """
    all_sources = RSS_SOURCES + ADDITIONAL_SOURCES
    for source in all_sources:
        if source["name"] == name:
            return source
    return None
