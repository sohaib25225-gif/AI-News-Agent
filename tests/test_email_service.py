"""
Test Email Service Module

This file tests the email sending functionality.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import NewsArticle, LinkedInPost
from services import EmailService
from utils import get_logger

logger = get_logger(__name__)


def test_email_configuration():
    """Test that email configuration is valid."""
    logger.info("=" * 60)
    logger.info("Testing Email Configuration")
    logger.info("=" * 60)

    try:
        email_service = EmailService()
        logger.info("Email service initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize email service: {str(e)}")
        return False


def test_send_test_email():
    """Test sending a simple test email."""
    logger.info("=" * 60)
    logger.info("Sending Test Email")
    logger.info("=" * 60)

    try:
        email_service = EmailService()
        success = email_service.send_test_email()

        if success:
            logger.info("Test email sent successfully!")
            logger.info("Check your inbox to verify.")
            return True
        else:
            logger.error("Failed to send test email")
            return False
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return False


def test_send_post_email():
    """Test sending a complete LinkedIn post email."""
    logger.info("=" * 60)
    logger.info("Sending LinkedIn Post Email")
    logger.info("=" * 60)

    try:
        # Create sample article
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

        # Create sample post
        sample_post = LinkedInPost(
            hook="A new era of AI reasoning is here! OpenAI has officially announced GPT-5.",
            body="This latest iteration boasts significant improvements across the board, particularly in "
                 "advanced reasoning, coding proficiency, and sophisticated multimodal understanding. "
                 "Developers and AI practitioners will find unprecedented power at their fingertips.\n\n"
                 "GPT-5 demonstrates state-of-the-art performance on complex mathematical reasoning and "
                 "intricate problem-solving tasks.",
            question="How do you envision GPT-5 transforming your current projects or opening up new opportunities?",
            hashtags=["#AI", "#GPT5", "#OpenAI", "#ArtificialIntelligence", "#MachineLearning", "#TechNews"],
            source_article=sample_article,
            generated_date=datetime.now()
        )

        # Send email
        email_service = EmailService()
        success = email_service.send_post(sample_post)

        if success:
            logger.info("LinkedIn post email sent successfully!")
            logger.info("Check your inbox to see the formatted post.")
            return True
        else:
            logger.error("Failed to send post email")
            return False
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return False


def main():
    """Run all email tests."""
    logger.info("=" * 60)
    logger.info("EMAIL SERVICE TEST SUITE")
    logger.info("=" * 60)

    results = []

    # Test 1: Configuration
    logger.info("\n[Test 1/3] Email Configuration")
    results.append(("Configuration", test_email_configuration()))

    # Test 2: Simple test email
    logger.info("\n[Test 2/3] Simple Test Email")
    results.append(("Test Email", test_send_test_email()))

    # Test 3: Full post email
    logger.info("\n[Test 3/3] LinkedIn Post Email")
    results.append(("Post Email", test_send_post_email()))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        logger.info(f"{test_name}: {status}")

    all_passed = all(result[1] for result in results)
    logger.info("=" * 60)

    if all_passed:
        logger.info("All tests passed!")
        logger.info("Check your email inbox for test messages.")
        return True
    else:
        logger.error("Some tests failed. Check logs above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
