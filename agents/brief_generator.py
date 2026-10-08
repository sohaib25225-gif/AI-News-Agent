"""
Intelligence Brief Generator Module

This module generates structured intelligence briefs from findings using LLM.

Key principles:
- Single LLM call for efficiency
- Grounded in supplied findings only (no hallucination)
- Structured output with proper citations
- Source URLs preserved for every claim
- Validation of output

Output structure:
- Executive summary
- Key findings with citations
- Competitor activity breakdown
- All claims linked to source URLs
"""

import json
import re
import time
from datetime import datetime
from typing import Optional, Dict, List
import requests

from models import Finding, IntelligenceBrief
from config import config
from utils import get_logger

logger = get_logger(__name__)


class BriefGenerator:
    """
    Generates intelligence briefs from findings using LLM.
    """

    # Gemini API endpoint
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"

    # Prompt template for brief generation
    PROMPT_TEMPLATE = """You are a competitive intelligence analyst generating a brief for an AI company executive.

You have been given {finding_count} findings about competitor activity in the AI industry.

YOUR TASK:
Generate a structured intelligence brief that summarizes these findings.

CRITICAL RULES:
1. Use ONLY the information provided in the findings below
2. Do NOT invent, speculate, or add information not present in the findings
3. EVERY statement must be grounded in a specific finding
4. Include source citations (finding ID and URL) for every claim
5. If a competitor has no findings, do NOT mention them

FINDINGS:
{findings_json}

OUTPUT FORMAT:
Return a valid JSON object with this exact structure:
{{
  "executive_summary": "A 2-3 sentence high-level summary of the competitive landscape this period",
  "key_findings": [
    {{
      "text": "Brief description of finding",
      "finding_id": <finding ID>,
      "source_url": "URL to source",
      "source_name": "Source name"
    }}
  ],
  "competitor_activity": {{
    "CompetitorName": [
      {{
        "text": "What they did",
        "finding_id": <finding ID>,
        "source_url": "URL to source",
        "source_name": "Source name"
      }}
    ]
  }}
}}

REQUIREMENTS:
- Executive summary: 2-3 sentences, high-level only
- Key findings: Top 5-8 most important findings across all competitors
- Competitor activity: Group remaining findings by competitor
- Every entry must have: text, finding_id, source_url, source_name
- Text should be concise (1-2 sentences)
- Use past tense ("OpenAI launched...", "Google released...")
- Focus on facts, not speculation

IMPORTANT:
- Return ONLY the JSON object, no markdown formatting, no additional text
- Do not include competitors with zero findings
- Do not duplicate findings between key_findings and competitor_activity
"""

    def __init__(self):
        """Initialize the brief generator."""
        self.api_key = config.GEMINI_API_KEY

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")

    def generate_brief(
        self,
        findings: List[Finding],
        period_start: datetime,
        period_end: datetime
    ) -> Optional[IntelligenceBrief]:
        """
        Generate an intelligence brief from findings.

        Args:
            findings: List of Finding objects to summarize
            period_start: Start of reporting period
            period_end: End of reporting period

        Returns:
            IntelligenceBrief object or None if generation fails
        """
        if not findings:
            logger.warning("No findings provided for brief generation")
            return None

        logger.info(f"Generating brief from {len(findings)} findings")

        try:
            # Step 1: Prepare findings for LLM
            findings_data = self._prepare_findings_for_llm(findings)

            # Step 2: Create prompt
            prompt = self._create_prompt(findings_data, len(findings))

            # Step 3: Call LLM
            response = self._call_gemini_api(prompt)

            if not response:
                logger.error("Failed to get response from Gemini API")
                return None

            # Step 4: Parse and validate response
            brief_data = self._parse_response(response)

            if not brief_data:
                logger.error("Failed to parse Gemini API response")
                return None

            # Step 5: Validate grounding
            if not self._validate_grounding(brief_data, findings):
                logger.error("Brief failed grounding validation")
                return None

            # Step 6: Create IntelligenceBrief object
            brief = self._create_brief_object(
                brief_data,
                findings,
                period_start,
                period_end
            )

            logger.info("Successfully generated intelligence brief")
            return brief

        except Exception as e:
            logger.error(f"Error generating brief: {str(e)}", exc_info=True)
            return None

    def _prepare_findings_for_llm(self, findings: List[Finding]) -> List[Dict]:
        """
        Convert findings to format suitable for LLM.

        Args:
            findings: List of Finding objects

        Returns:
            List of dictionaries with finding data
        """
        findings_data = []

        for finding in findings:
            finding_dict = {
                "id": finding.id,
                "competitor": finding.competitor,
                "event_type": finding.event_type,
                "title": finding.title,
                "summary": finding.summary,
                "source_url": finding.source_url,
                "source_name": finding.source_name,
                "source_confidence": finding.source_confidence,
                "published_date": finding.published_at.isoformat() if finding.published_at else datetime.now().isoformat()
            }
            findings_data.append(finding_dict)

        return findings_data

    def _create_prompt(self, findings_data: List[Dict], finding_count: int) -> str:
        """
        Create the prompt for LLM.

        Args:
            findings_data: Prepared findings data
            finding_count: Total number of findings

        Returns:
            Formatted prompt string
        """
        findings_json = json.dumps(findings_data, indent=2)

        return self.PROMPT_TEMPLATE.format(
            finding_count=finding_count,
            findings_json=findings_json
        )

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """
        Call the Gemini API with the prompt.

        Retries on HTTP 503 (provider capacity) with exponential backoff:
        5s, 15s, 45s (max 3 retries). All other status codes return
        immediately without retry.

        Args:
            prompt: The prompt to send

        Returns:
            API response text or None if request fails
        """
        url = f"{self.GEMINI_API_URL}?key={self.api_key}"

        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,  # Lower temperature for factual content
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 4096,  # Sufficient for weekly briefs
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        max_retries = 3
        retry_delays = [5, 15, 45]  # seconds

        for attempt in range(1 + max_retries):
            try:
                if attempt == 0:
                    logger.debug("Calling Gemini API for brief generation...")
                else:
                    logger.info(f"Gemini API retry {attempt}/{max_retries} after 503...")

                response = requests.post(url, json=payload, headers=headers, timeout=60)

                if response.status_code == 200:
                    break  # Success — fall through to parse below

                # Non-503 errors: log and return immediately (no retry)
                if response.status_code != 503:
                    logger.error(f"Gemini API error: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return None

                # 503 — log and retry
                logger.warning(
                    f"Gemini API 503 (attempt {attempt + 1}/{1 + max_retries}): "
                    f"{response.text[:300]}"
                )

            except requests.exceptions.Timeout:
                logger.error("Gemini API request timed out")
                return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Gemini API request failed: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error calling Gemini API: {str(e)}")
                return None

            # Wait before retry (exponential backoff: 5, 15, 45 seconds)
            if attempt < max_retries:
                delay = retry_delays[attempt]
                logger.info(f"Waiting {delay}s before retry...")
                time.sleep(delay)
        else:
            # All retries exhausted
            logger.error(f"Gemini API failed after {max_retries} retries (all 503)")
            return None

        # Parse successful response
        try:
            data = response.json()

            # Extract text from response
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]

                # Log finish reason for debugging
                finish_reason = candidate.get("finishReason", "UNKNOWN")
                logger.debug(f"Gemini finish reason: {finish_reason}")

                if "content" in candidate and "parts" in candidate["content"]:
                    text = candidate["content"]["parts"][0].get("text", "")

                    # Warn if response was truncated
                    if finish_reason in ["MAX_TOKENS", "SAFETY", "RECITATION"]:
                        logger.warning(f"Response may be incomplete. Finish reason: {finish_reason}")

                    return text

            logger.error("Unexpected response format from Gemini API")
            logger.error(f"Response data: {json.dumps(data, indent=2)[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error parsing successful response: {str(e)}")
            return None

    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse the LLM response into structured data.

        Args:
            response_text: Raw response from LLM

        Returns:
            Parsed dictionary or None if parsing fails
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

            # Parse JSON
            data = json.loads(cleaned)

            # Validate structure
            required_keys = ["executive_summary", "key_findings", "competitor_activity"]
            for key in required_keys:
                if key not in data:
                    logger.error(f"Missing required key in response: {key}")
                    return None

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return None

    def _validate_grounding(self, brief_data: Dict, findings: List[Finding]) -> bool:
        """
        Validate that all claims in the brief are grounded in findings.

        Checks:
        - All finding_ids reference actual findings
        - All source_urls match findings
        - No ungrounded claims

        Args:
            brief_data: Parsed brief data
            findings: Original findings

        Returns:
            True if valid, False otherwise
        """
        # Create lookup of finding IDs
        finding_ids = {f.id for f in findings}
        finding_urls = {f.source_url for f in findings}

        # Check key findings
        for item in brief_data.get("key_findings", []):
            finding_id = item.get("finding_id")
            source_url = item.get("source_url")

            if finding_id not in finding_ids:
                logger.error(f"Invalid finding_id in key_findings: {finding_id}")
                return False

            if source_url not in finding_urls:
                logger.error(f"Invalid source_url in key_findings: {source_url}")
                return False

        # Check competitor activity
        for competitor, activities in brief_data.get("competitor_activity", {}).items():
            for item in activities:
                finding_id = item.get("finding_id")
                source_url = item.get("source_url")

                if finding_id not in finding_ids:
                    logger.error(f"Invalid finding_id in competitor_activity: {finding_id}")
                    return False

                if source_url not in finding_urls:
                    logger.error(f"Invalid source_url in competitor_activity: {source_url}")
                    return False

        logger.info("Brief grounding validation passed")
        return True

    def _create_brief_object(
        self,
        brief_data: Dict,
        findings: List[Finding],
        period_start: datetime,
        period_end: datetime
    ) -> IntelligenceBrief:
        """
        Create IntelligenceBrief object from parsed data.

        Args:
            brief_data: Parsed brief data
            findings: Original findings
            period_start: Start of reporting period
            period_end: End of reporting period

        Returns:
            IntelligenceBrief object
        """
        # Extract finding IDs from brief
        finding_ids = set()

        for item in brief_data.get("key_findings", []):
            finding_ids.add(item.get("finding_id"))

        for activities in brief_data.get("competitor_activity", {}).values():
            for item in activities:
                finding_ids.add(item.get("finding_id"))

        # Create brief object
        brief = IntelligenceBrief(
            generated_at=datetime.now(),
            period_start=period_start,
            period_end=period_end,
            executive_summary=brief_data["executive_summary"],
            key_findings=brief_data["key_findings"],
            competitor_activity=brief_data["competitor_activity"],
            finding_ids=sorted(list(finding_ids)),
            finding_count=len(finding_ids)
        )

        return brief
