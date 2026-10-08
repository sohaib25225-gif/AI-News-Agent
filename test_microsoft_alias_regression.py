"""
Microsoft Alias Regression Tests

Tests that the confirmed false-negative bug is fixed:
- "microsoft" must be in the Microsoft AI alias list
- Articles with bare "Microsoft" in the title must detect Microsoft AI
- Actor verification must pass for co-announcements where Microsoft is a primary actor
- Existing competitor detection must not regress
"""

from datetime import datetime
import unittest

from models import NewsArticle
from config.sources import COMPETITOR_ALIASES, get_competitor_from_source
from agents.intelligence_classifier import IntelligenceClassifier


class TestMicrosoftAlias(unittest.TestCase):
    """Confirm the missing 'microsoft' alias is now present."""

    def test_microsoft_alias_in_list(self):
        """The bare word 'microsoft' must be an alias for Microsoft AI."""
        self.assertIn("microsoft", COMPETITOR_ALIASES["Microsoft AI"])

    def test_existing_aliases_still_present(self):
        """Adding 'microsoft' must not have removed any existing aliases."""
        aliases = COMPETITOR_ALIASES["Microsoft AI"]
        for alias in ["microsoft ai", "azure ai", "copilot", "satya nadella"]:
            self.assertIn(alias, aliases)

    def test_no_duplicate_aliases(self):
        """No duplicates should exist in the alias list."""
        aliases = COMPETITOR_ALIASES["Microsoft AI"]
        self.assertEqual(len(aliases), len(set(aliases)))


class TestMicrosoftDetection(unittest.TestCase):
    """Test the two confirmed false-negative articles."""

    def setUp(self):
        self.classifier = IntelligenceClassifier()

    # ----------------------------------------------------------------
    # False negative 1: Microsoft AI PCs (TechCrunch)
    # Article was NOT detected at all before the fix.
    # ----------------------------------------------------------------
    def test_microsoft_ai_pc_article_detects_competitor(self):
        """'Microsoft releases new Nvidia-chip AI PCs' must detect Microsoft AI."""
        article = NewsArticle(
            title="Microsoft releases new Nvidia-chip AI PCs with revamped Windows 11",
            source="TechCrunch AI",
            url="https://techcrunch.com/2026/10/07/microsoft-releases-new-nvidia-chip-ai-pcs-with-revamped-windows-11",
            published_date=datetime(2026, 10, 7, 20, 22, 37),
            summary="Microsoft revealed the specs and price for its Surface Laptop Ultra, AI PCs that run on Nvidia chips that are designed to run AI models and agents.",
            score=0.33,
            content=None
        )

        # Content-based detection
        competitor = self.classifier._detect_competitor_from_content(article)
        self.assertEqual(competitor, "Microsoft AI",
            f"Expected 'Microsoft AI', got '{competitor}'")

        # Full classification must produce a finding
        finding = self.classifier.classify_article(article)
        self.assertIsNotNone(finding,
            "Article must produce a finding (not be filtered)")
        self.assertEqual(finding.competitor, "Microsoft AI")

    # ----------------------------------------------------------------
    # False negative 2: NVIDIA/Microsoft co-announcement (NVIDIA Blog)
    # Article was detected as Microsoft AI but actor verification scored 0.30.
    # ----------------------------------------------------------------
    def test_nvidia_microsoft_co_announcement_actor_score(self):
        """'NVIDIA, Microsoft Kick Off...' must have actor_score >= 0.6."""
        article = NewsArticle(
            title="NVIDIA, Microsoft Kick Off a New Beginning for Windows PCs With RTX Spark and AI Agents",
            source="NVIDIA Blog - AI",
            url="https://blogs.nvidia.com/blog/local-ai-rtx-spark-microsoft-windows-event/",
            published_date=datetime(2026, 10, 7, 18, 45, 28),
            summary="At a Microsoft event in San Francisco on Wednesday, NVIDIA founder and CEO Jensen Huang and Microsoft CEO Satya Nadella outlined how NVIDIA and Microsoft are co-engineering hardware and software for AI agents to run on Windows PCs.",
            score=0.33,
            content="At a Microsoft event in San Francisco on Wednesday, NVIDIA founder and CEO Jensen Huang and Microsoft CEO Satya Nadella outlined how NVIDIA and Microsoft are co-engineering hardware and software for AI agents to run on Windows PCs. NVIDIA was founded because of Windows, Huang said. Now AI agents are bringing a new era for Windows PCs, with NVIDIA RTX Spark enabling local AI models and Copilot+ PCs to run AI agents for the first time."
        )

        # Detection must find Microsoft AI
        competitor = self.classifier._detect_competitor_from_content(article)
        self.assertEqual(competitor, "Microsoft AI")

        # Actor verification must PASS (score >= 0.6)
        is_actor, actor_score = self.classifier._verify_competitor_is_actor(
            article, competitor, is_official_source=False
        )
        self.assertTrue(is_actor,
            f"Microsoft must pass actor verification, got score={actor_score:.2f}")
        self.assertGreaterEqual(actor_score, 0.6,
            f"Actor score must be >= 0.6, got {actor_score:.2f}")

        # Full classification must produce a finding
        finding = self.classifier.classify_article(article)
        self.assertIsNotNone(finding,
            "Co-announcement must produce a finding")
        self.assertEqual(finding.competitor, "Microsoft AI")


class TestNoRegression(unittest.TestCase):
    """Existing competitor detection must not regress."""

    def setUp(self):
        self.classifier = IntelligenceClassifier()

    def test_openai_still_detected(self):
        """OpenAI articles must still be detected."""
        article = NewsArticle(
            title="OpenAI Launches GPT-5 with Breakthrough Multimodal Capabilities",
            source="TechCrunch AI",
            url="https://techcrunch.com/test/openai-gpt5",
            published_date=datetime(2026, 10, 7),
            summary="OpenAI announced GPT-5 with new multimodal capabilities.",
            score=0.5
        )
        finding = self.classifier.classify_article(article)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.competitor, "OpenAI")

    def test_anthropic_still_detected(self):
        """Anthropic articles must still be detected."""
        article = NewsArticle(
            title="Anthropic Partners with AWS to Offer Claude on SageMaker",
            source="TechCrunch AI",
            url="https://techcrunch.com/test/anthropic-aws",
            published_date=datetime(2026, 10, 7),
            summary="Anthropic and AWS announce deep integration for Claude.",
            score=0.5
        )
        finding = self.classifier.classify_article(article)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.competitor, "Anthropic")

    def test_google_ai_still_detected(self):
        """Google AI articles must still be detected."""
        article = NewsArticle(
            title="Google AI Releases New Gemini Model with Enhanced Reasoning",
            source="TechCrunch AI",
            url="https://techcrunch.com/test/google-gemini",
            published_date=datetime(2026, 10, 7),
            summary="Google releases new Gemini model.",
            score=0.5
        )
        finding = self.classifier.classify_article(article)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.competitor, "Google AI")

    def test_meta_ai_still_detected(self):
        """Meta AI articles must still be detected."""
        article = NewsArticle(
            title="Meta AI Launches Llama 4 with Open Weights",
            source="TechCrunch AI",
            url="https://techcrunch.com/test/meta-llama4",
            published_date=datetime(2026, 10, 7),
            summary="Meta releases Llama 4 with open weights.",
            score=0.5
        )
        finding = self.classifier.classify_article(article)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.competitor, "Meta AI")

    def test_healthleap_still_filtered(self):
        """Non-competitor articles (like Healthleap) must still be filtered."""
        article = NewsArticle(
            title="Healthleap raises $38M for its AI that flags hospital patients",
            source="TechCrunch AI",
            url="https://techcrunch.com/test/healthleap",
            published_date=datetime(2026, 10, 7),
            summary="Healthleap raises funding from Sequoia and First Round Capital.",
            score=0.39
        )
        finding = self.classifier.classify_article(article)
        self.assertIsNone(finding,
            "Healthleap article must not produce a finding")

    def test_microsoft_official_source_bypasses_actor_check(self):
        """Microsoft Blog as official source must bypass actor verification."""
        article = NewsArticle(
            title="Microsoft Unveils New AI Features for Copilot",
            source="Microsoft Blog",
            url="https://microsoft.com/blog/copilot-features",
            published_date=datetime(2026, 10, 7),
            summary="Microsoft announces new AI features for Copilot.",
            score=0.5
        )

        # Official source check
        competitor = get_competitor_from_source(article.source)
        self.assertEqual(competitor, "Microsoft AI")

        # Actor verification must pass immediately for official sources
        is_actor, actor_score = self.classifier._verify_competitor_is_actor(
            article, competitor, is_official_source=True
        )
        self.assertTrue(is_actor)
        self.assertEqual(actor_score, 1.0)


if __name__ == "__main__":
    unittest.main()
