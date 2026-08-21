"""
Test Post Generator Module

This file tests the LinkedIn post generation functionality.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import NewsArticle
from agents import PostGenerator
from utils import get_logger

logger = get_logger(__name__)


def test_post_generation():
    """Test generating a LinkedIn post from a sample article."""

    # Create a sample article
    sample_article = NewsArticle(
        title="OpenAI Releases GPT-5 with Enhanced Reasoning Capabilities",
        source="OpenAI Blog",
        url="https://openai.com/blog/gpt-5-release",
        published_date=datetime.now(),
        summary="OpenAI has announced GPT-5, featuring significant improvements in reasoning, "
                "coding abilities, and multimodal understanding. The new model demonstrates "
                "state-of-the-art performance on mathematical reasoning and complex problem-solving tasks.",
        score=95.0
    )

    logger.info("=" * 60)
    logger.info("Testing Post Generator with Sample Article")
    logger.info("=" * 60)

    try:
        # Initialize generator
        generator = PostGenerator()
        logger.info("Post generator initialized successfully")

        # Generate post
        logger.info("Generating LinkedIn post...")
        post = generator.generate_post(sample_article)

        if post:
            logger.info("✓ Post generated successfully!")
            logger.info("=" * 60)
            logger.info("GENERATED POST:")
            logger.info("=" * 60)
            print("\n" + post.format_for_linkedin() + "\n")
            logger.info("=" * 60)
            logger.info(f"Word count: {post.word_count()}")
            logger.info(f"Hashtags: {len(post.hashtags)}")
            logger.info("=" * 60)
            return True
        else:
            logger.error("✗ Failed to generate post")
            return False

    except Exception as e:
        logger.error(f"✗ Test failed with error: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_post_generation()
    sys.exit(0 if success else 1)
