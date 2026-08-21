"""
LinkedIn Post Generator Module

This module generates engaging LinkedIn posts from news articles using Google Gemini API.

Why this file exists:
- Converts raw news articles into compelling LinkedIn content
- Uses AI to create professional, engaging posts
- Formats content according to LinkedIn best practices

How it works:
1. Takes a scored news article
2. Sends it to Gemini API with a structured prompt
3. Parses the AI response into a LinkedInPost object
4. Validates the output (word count, hashtags, etc.)

Post Structure:
- Hook: Attention-grabbing opening line
- Body: 2-3 paragraphs explaining the news
- Question: Engaging question to prompt discussion
- Hashtags: 4-6 relevant hashtags
"""

import json
import re
from datetime import datetime
from typing import Optional
import requests

from models import NewsArticle, LinkedInPost
from config import config
from utils import get_logger

logger = get_logger(__name__)


class PostGenerator:
    """
    Generates LinkedIn posts from news articles using Google Gemini API.
    """

    # Gemini API endpoint
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    # Post generation prompt template
    PROMPT_TEMPLATE = """You are a professional LinkedIn content creator specializing in AI and technology news.

Your task is to create an engaging LinkedIn post from the following news article.

Article Details:
Title: {title}
Source: {source}
Summary: {summary}
URL: {url}

Requirements:
1. Hook: Start with a compelling opening line (1-2 sentences) that grabs attention
2. Body: Write 2-3 short paragraphs explaining why this matters
3. Question: End with an engaging question to prompt discussion
4. Hashtags: Include 4-6 relevant hashtags
5. Total word count: Maximum 180 words (excluding hashtags)
6. Tone: Professional but conversational, enthusiastic but not overhyped
7. Focus: Practical implications for developers and AI practitioners

Format your response as JSON with this exact structure:
{{
  "hook": "Your attention-grabbing opening line here",
  "body": "Your 2-3 paragraphs here",
  "question": "Your engaging question here",
  "hashtags": ["#AI", "#MachineLearning", "#etc"]
}}

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting."""

    def __init__(self):
        """Initialize the post generator."""
        self.api_key = config.GEMINI_API_KEY

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")

    def generate_post(self, article: NewsArticle) -> Optional[LinkedInPost]:
        """
        Generate a LinkedIn post from a news article.

        Args:
            article: NewsArticle to create post from

        Returns:
            LinkedInPost object or None if generation fails
        """
        logger.info(f"Generating LinkedIn post for: {article.title}")

        try:
            # Create the prompt
            prompt = self._create_prompt(article)

            # Call Gemini API
            response = self._call_gemini_api(prompt)

            if not response:
                logger.error("Failed to get response from Gemini API")
                return None

            # Parse the response
            post = self._parse_response(response, article)

            if not post:
                logger.error("Failed to parse Gemini API response")
                return None

            # Validate the post
            if not self._validate_post(post):
                logger.error("Generated post failed validation")
                return None

            logger.info("Successfully generated LinkedIn post")
            logger.info(f"Word count: {post.word_count()} words")
            logger.info(f"Hashtags: {len(post.hashtags)}")

            return post

        except Exception as e:
            logger.error(f"Error generating post: {str(e)}", exc_info=True)
            return None

    def _create_prompt(self, article: NewsArticle) -> str:
        """
        Create the prompt for Gemini API.

        Args:
            article: NewsArticle to create prompt from

        Returns:
            Formatted prompt string
        """
        return self.PROMPT_TEMPLATE.format(
            title=article.title,
            source=article.source,
            summary=article.summary,
            url=article.url
        )

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """
        Call the Gemini API with the prompt.

        Args:
            prompt: The prompt to send

        Returns:
            API response text or None if request fails
        """
        try:
            url = f"{self.GEMINI_API_URL}?key={self.api_key}"

            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 2048,
                }
            }

            headers = {
                "Content-Type": "application/json"
            }

            logger.debug("Calling Gemini API...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

            data = response.json()

            # Extract text from response
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    text = candidate["content"]["parts"][0].get("text", "")
                    return text

            logger.error("Unexpected response format from Gemini API")
            return None

        except requests.exceptions.Timeout:
            logger.error("Gemini API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini API: {str(e)}")
            return None

    def _parse_response(self, response_text: str, article: NewsArticle) -> Optional[LinkedInPost]:
        """
        Parse the Gemini API response into a LinkedInPost object.

        Args:
            response_text: Raw response from Gemini API
            article: Source article

        Returns:
            LinkedInPost object or None if parsing fails
        """
        try:
            # Clean up response (remove markdown code blocks if present)
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Handle truncated JSON - try to find and extract complete JSON object
            if not cleaned.endswith("}"):
                # Try to find the last complete closing brace
                brace_count = 0
                last_valid_pos = -1
                for i, char in enumerate(cleaned):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            last_valid_pos = i + 1
                            break

                if last_valid_pos > 0:
                    cleaned = cleaned[:last_valid_pos]
                    logger.warning("Response was truncated, extracted partial JSON")

            # Parse JSON
            data = json.loads(cleaned)

            # Extract fields
            hook = data.get("hook", "").strip()
            body = data.get("body", "").strip()
            question = data.get("question", "").strip()
            hashtags = data.get("hashtags", [])

            # Validate required fields
            if not hook or not body or not question or not hashtags:
                logger.error("Missing required fields in Gemini response")
                return None

            # Create LinkedInPost object
            post = LinkedInPost(
                hook=hook,
                body=body,
                question=question,
                hashtags=hashtags,
                source_article=article,
                generated_date=datetime.now()
            )

            return post

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Response text: {response_text}")
            return None
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return None

    def _validate_post(self, post: LinkedInPost) -> bool:
        """
        Validate that the generated post meets requirements.

        Args:
            post: LinkedInPost to validate

        Returns:
            True if valid, False otherwise
        """
        # Check word count
        word_count = post.word_count()
        if word_count > config.MAX_POST_WORDS:
            logger.warning(f"Post exceeds max word count: {word_count} > {config.MAX_POST_WORDS}")
            return False

        if word_count < 50:
            logger.warning(f"Post too short: {word_count} words")
            return False

        # Check hashtag count
        hashtag_count = len(post.hashtags)
        if hashtag_count < config.MIN_HASHTAGS or hashtag_count > config.MAX_HASHTAGS:
            logger.warning(f"Invalid hashtag count: {hashtag_count} (expected {config.MIN_HASHTAGS}-{config.MAX_HASHTAGS})")
            return False

        # Validate hashtag format
        for tag in post.hashtags:
            if not tag.startswith("#"):
                logger.warning(f"Invalid hashtag format: {tag}")
                return False

        # Check for empty fields
        if not post.hook or not post.body or not post.question:
            logger.warning("Post has empty required fields")
            return False

        return True
