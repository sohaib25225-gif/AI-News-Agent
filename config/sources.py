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
# Updated 2026-08-25: Verified all URLs, fixed redirects, replaced broken sources
RSS_SOURCES: list[NewsSource] = [
    # Major AI Companies
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",  # Verified working
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",  # Verified working
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "Meta Blog",
        "url": "https://about.fb.com/feed/",  # Updated URL - Meta company blog
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "Microsoft Blog",
        "url": "https://www.microsoft.com/en-us/microsoft-365/blog/feed/",  # Updated - general MS blog
        "category": "company",
        "source_type": "rss"
    },
    {
        "name": "NVIDIA Blog - AI",
        "url": "https://blogs.nvidia.com/feed/",
        "category": "company",
        "source_type": "rss"
    },
    # Research & Academic
    {
        "name": "DeepMind Blog",
        "url": "https://deepmind.google/blog/rss.xml",
        "category": "research",
        "source_type": "rss"
    },
    # Developer & Community
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "community",
        "source_type": "rss"
    },
    {
        "name": "GitHub Blog",
        "url": "https://github.blog/feed/",
        "category": "developer",
        "source_type": "rss"
    },
    {
        "name": "AWS ML Blog",
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",  # Added - AWS ML content
        "category": "developer",
        "source_type": "rss"
    },
    # Tech News & Industry
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",  # Added - current AI news
        "category": "news",
        "source_type": "rss"
    },
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/feed/",  # Added - quality AI journalism
        "category": "news",
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


# ============================================================================
# V1 Configuration - Competitive Intelligence
# ============================================================================

# Competitor Mapping - Approved V1 Scope: 5 competitors only
# Maps source names to competitor names for intelligence gathering
COMPETITOR_MAPPING = {
    "OpenAI Blog": "OpenAI",
    "Google AI Blog": "Google AI",
    "DeepMind Blog": "Google AI",  # DeepMind is part of Google
    "Meta Blog": "Meta AI",
    "Microsoft Blog": "Microsoft AI",
    # Note: Anthropic not yet in RSS sources, but included in approved scope
    "Anthropic Blog": "Anthropic",  # If/when added to sources
    # REMOVED: NVIDIA, AWS, Hugging Face (not in approved scope)
}

# Competitor Aliases - For detection in article content
# Use with caution to avoid false positives
COMPETITOR_ALIASES = {
    "OpenAI": ["openai", "gpt-", "chatgpt", "dall-e", "dall e", "sam altman"],
    "Anthropic": ["anthropic", "claude", "constitutional ai", "dario amodei"],
    "Google AI": ["google ai", "gemini", "bard", "palm", "vertex ai", "deepmind", "demis hassabis"],
    "Meta AI": ["meta ai", "llama", "facebook ai research", "fair", "mark zuckerberg"],
    "Microsoft AI": ["microsoft", "microsoft ai", "azure ai", "copilot", "satya nadella"],
}

# Source Confidence Scores
# Based on source type and reliability for competitive intelligence
SOURCE_CONFIDENCE_SCORES = {
    "company_blog": 0.9,      # Official company announcements
    "research": 0.85,         # Peer-reviewed research, official research blogs
    "news": 0.75,             # Tech news outlets
    "developer": 0.70,        # Developer platforms and blogs
    "community": 0.60,        # Community-driven sources
}


def get_competitor_from_source(source_name: str) -> str | None:
    """
    Get competitor name from source name.

    Args:
        source_name: Name of the news source

    Returns:
        Competitor name if mapped, None otherwise
    """
    return COMPETITOR_MAPPING.get(source_name)


def get_source_confidence(source_name: str) -> float:
    """
    Get source confidence score based on source type.

    Args:
        source_name: Name of the news source

    Returns:
        Confidence score (0.0-1.0)
    """
    # Find the source in our sources list
    source = get_source_by_name(source_name)

    if not source:
        # Unknown source, use conservative confidence
        return 0.5

    # Map source category to confidence score
    category = source.get("category", "news")

    # Map category to source type for confidence scoring
    category_to_type = {
        "company": "company_blog",
        "research": "research",
        "news": "news",
        "developer": "developer",
        "community": "community",
    }

    source_type = category_to_type.get(category, "news")
    return SOURCE_CONFIDENCE_SCORES.get(source_type, 0.6)


def get_tracked_competitors() -> list[str]:
    """
    Get list of all tracked competitors.

    Returns:
        List of unique competitor names
    """
    return sorted(set(COMPETITOR_MAPPING.values()))
