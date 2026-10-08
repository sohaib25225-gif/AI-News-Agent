"""
Intelligence Classifier Module

This module classifies news articles into competitive intelligence findings.

Key responsibilities:
- Deterministic event classification based on keywords
- Source confidence calculation
- Finding creation from articles

Event Types:
- pricing_change: Pricing, cost, or billing changes
- product_launch: New products, services, or models
- feature_update: Updates to existing products
- api_change: API changes, model access, endpoint changes
- funding: Funding rounds, investments
- partnership: Collaborations, integrations, partnerships
- acquisition: Acquisitions, mergers
- research_release: Research papers, publications, breakthroughs
- leadership: Executive changes, founder news
- regulation: Regulatory news, policy changes
- other: Events that don't fit other categories
"""

from datetime import datetime
from typing import Optional
import re

from models import NewsArticle, Finding
from config.sources import get_competitor_from_source, COMPETITOR_ALIASES
from agents.source_confidence_calculator import SourceConfidenceCalculator
from utils import get_logger

logger = get_logger(__name__)


class IntelligenceClassifier:
    """
    Classifies news articles into competitive intelligence findings.
    """

    # Event classification keywords (case-insensitive)
    # Priority order: More specific types checked first
    EVENT_KEYWORDS = {
        # High-priority specific events
        "pricing_change": [
            "pricing", "price", "cost", "billing", "subscription",
            "tier", "pay", "payment", "free tier", "paid",
            "charge", "pricing model", "pricing change"
        ],
        "api_change": [
            "api", "endpoint", "api change", "model access",
            "api key", "rate limit", "api update", "deprecat",
            "api version", "rest api", "graphql"
        ],
        "leadership": [
            "ceo", "cto", "founder", "executive", "appoint",
            "resign", "depart", "join", "hire", "lead",
            "chief", "director", "president", "officer"
        ],
        "acquisition": [
            "acquisition", "acquire", "merger", "bought", "purchase",
            "acquires", "acquired", "buys", "takeover", "merge"
        ],
        "funding": [
            "funding", "investment", "raise", "series", "venture capital",
            "investors", "round", "valuation", "capital", "invested",
            "fund", "investor"
        ],

        # Medium-priority events
        "product_launch": [
            "launch", "launches", "launched", "launching",
            "announce", "announces", "announced", "announcing",
            "release", "released", "releasing",
            "unveil", "unveils", "unveiled", "unveiling",
            "introduce", "introduces", "introduced", "introducing",
            "new model", "new product", "debuts", "available now", "now available"
        ],
        "research_release": [
            "research", "paper", "study", "findings", "arxiv",
            "publication", "journal", "breakthrough", "discovery",
            "published", "preprint", "conference", "research paper"
        ],
        "partnership": [
            "partnership", "partner", "collaboration", "collaborate",
            "integration", "integrate", "alliance", "team up",
            "join forces", "working with", "partners with"
        ],
        "regulation": [
            "regulation", "regulatory", "policy", "compliance",
            "law", "legal", "government", "legislation", "rules",
            "regulator", "regulate"
        ],

        # Lower-priority catch-all for updates (be specific but catch real feature updates)
        "feature_update": [
            "new feature", "adds feature", "adds new", "improved",
            "enhancement", "adds support", "now supports", "upgrade",
            "optimization"
        ],
    }

    def __init__(self):
        """Initialize the classifier."""
        self.confidence_calculator = SourceConfidenceCalculator()

    def classify_article(self, article: NewsArticle, corroborating_articles: list = None) -> Optional[Finding]:
        """
        Classify an article into a Finding.

        Phase 12 Enhanced Steps:
        1. Detect competitor from source (official) or content (third-party)
        2. [FIX A] Verify competitor is actor/subject (not just mentioned)
        3. [FIX B] Detect content type and assign priority
        4. [FIX C] Classify event type with action context
        5. Calculate source confidence (multi-factor)
        6. [FIX B] Apply hybrid filtering (filter low-value third-party, flag official)
        7. Create Finding object with enhanced metadata

        Args:
            article: NewsArticle to classify
            corroborating_articles: Other articles reporting the same event (for confidence calculation)

        Returns:
            Finding object if article is about a tracked competitor, None otherwise
        """
        # Step 1: Detect competitor
        # First try official source mapping
        competitor = get_competitor_from_source(article.source)
        is_official_source = competitor is not None

        # If no official source match, try content-based detection
        if not competitor:
            competitor = self._detect_competitor_from_content(article)

        if not competitor:
            # Not a tracked competitor
            logger.debug(f"Article not about tracked competitor: {article.source} - {article.title[:50]}")
            return None

        # Step 2: [FIX A] Verify competitor is actor/subject
        is_actor, actor_score = self._verify_competitor_is_actor(article, competitor, is_official_source)

        if not is_actor:
            # Competitor detected but not primary actor - filter out
            logger.info(f"Filtering: '{competitor}' detected but not primary actor (score: {actor_score:.2f})")
            return None

        # Step 3: [FIX B] Detect content type and priority
        content_type = self._detect_content_type(article)
        relevance_score = article.score if hasattr(article, 'score') and article.score else 0.5
        priority = self._assign_priority(content_type, relevance_score, is_official_source)

        # Step 4: [FIX C] Detect action context
        action_context = self._detect_action_context(article)

        # Step 5: Classify event type
        raw_event_type = self._classify_event_type(article)

        if not raw_event_type:
            # Could not classify event type - use "other"
            raw_event_type = "other"
            logger.debug(f"Could not classify event type for: {article.title}, using 'other'")

        # Step 6: [FIX C] Validate event type with context
        event_type = self._validate_event_with_context(raw_event_type, action_context, article)

        if event_type != raw_event_type:
            logger.info(f"Event type adjusted by context: {raw_event_type} -> {event_type} (context: {action_context})")

        # Step 7: Calculate source confidence (multi-factor)
        source_confidence, confidence_factors, requires_review = self.confidence_calculator.calculate(
            article,
            corroborating_articles
        )

        # Step 8: [FIX B] Hybrid filtering for low-priority content
        if priority == 'low':
            if is_official_source:
                # Official source: Flag for review, don't filter
                requires_review = True
                logger.info(f"Low-priority official source content flagged for review: {content_type} - {article.title[:60]}")
            elif relevance_score < 0.5:
                # Third-party + low priority + low relevance: Filter
                logger.info(f"Filtering low-value third-party content: {content_type} (relevance: {relevance_score:.2f}) - {article.title[:60]}")
                return None
            else:
                # Third-party + low priority + high relevance: Flag for review
                requires_review = True
                logger.info(f"Low-priority third-party content flagged for review: {content_type} (relevance: {relevance_score:.2f})")

        # Step 9: Create Finding with all required fields + Phase 12 enhancements
        finding = Finding(
            competitor=competitor,
            event_type=event_type,
            title=article.title,
            summary=article.summary,
            evidence=article.summary,
            original_title=article.title,
            original_summary=article.summary,
            original_content=article.content,
            source_name=article.source,
            source_url=article.url,
            published_at=article.published_date,
            relevance_score=relevance_score,
            source_confidence=source_confidence,
            source_confidence_factors=confidence_factors,
            requires_review=requires_review,
            detected_at=datetime.now(),
            included_in_brief_id=None,
            # Phase 12 enhancements
            priority=priority,
            content_type=content_type,
            action_context=action_context,
            actor_score=actor_score
        )

        logger.info(f"Classified finding: [{finding.priority}] {finding.competitor} - {finding.event_type} - {finding.title[:50]}")

        return finding

    def _detect_competitor_from_content(self, article: NewsArticle) -> Optional[str]:
        """
        Detect competitor from article content using aliases.

        This is used for third-party sources that report on competitors.
        Uses word boundaries and contextual matching to avoid false positives.

        Args:
            article: NewsArticle to analyze

        Returns:
            Competitor name if detected, None otherwise
        """
        # Combine title, summary, and content for analysis
        text = f"{article.title} {article.summary}".lower()
        if article.content:
            text += f" {article.content}".lower()

        # Count matches for each competitor
        competitor_scores = {}

        for competitor, aliases in COMPETITOR_ALIASES.items():
            score = 0
            for alias in aliases:
                alias_lower = alias.lower()

                # Special handling for short/ambiguous aliases
                if alias_lower in ["meta", "gpt"]:
                    # Require word boundary or specific context
                    # For "meta": must be "meta ai" or standalone "meta" followed by AI context
                    if alias_lower == "meta":
                        # Only match "meta ai" or "meta" in AI context (not "metadata", "metaverse")
                        if "meta ai" in text or re.search(r'\bmeta\b(?=.*\b(?:ai|llama|facebook ai|zuckerberg)\b)', text, re.IGNORECASE):
                            score += 2  # Strong match
                    elif alias_lower == "gpt":
                        # Match "gpt" followed by dash/space/number (GPT-4, GPT 5, etc.)
                        if re.search(r'\bgpt[\-\s]?\d', text, re.IGNORECASE) or re.search(r'\bgpt\s+model', text, re.IGNORECASE):
                            score += 2  # Strong match
                    continue

                # Multi-word aliases: exact phrase matching
                if " " in alias_lower:
                    if alias_lower in text:
                        score += 2  # Multi-word matches are strong signals
                    continue

                # Single-word aliases: word boundary matching
                # Use word boundaries to avoid substring matches
                pattern = r'\b' + re.escape(alias_lower) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1

            if score > 0:
                competitor_scores[competitor] = score

        # Return competitor with highest score (if any)
        if competitor_scores:
            best_competitor = max(competitor_scores.items(), key=lambda x: x[1])
            logger.debug(f"Content-based detection scores: {competitor_scores}, selected: {best_competitor[0]}")
            return best_competitor[0]

        return None

    def _calculate_actor_evidence(self, article: NewsArticle, competitor: str) -> float:
        """
        Calculate evidence score that competitor is the primary actor/subject.

        Phase 12 Fix A: Distinguishes competitor as ACTOR vs merely MENTIONED.

        Signals:
        - Title presence (0.4): Strong signal - title subjects are primary actors
        - Lead paragraph (0.3): First 300 chars indicate article subject
        - Grammatical subject (0.2): Competitor performing an action
        - Frequency in main content (0.1): Multiple mentions suggest primary subject
        - Penalty (-0.5): Only in final 20% (likely author bio/footnotes)

        Args:
            article: NewsArticle being analyzed
            competitor: Competitor name to verify

        Returns:
            Actor score (0.0-1.0), threshold 0.6 recommended
        """
        score = 0.0

        # Get competitor aliases for matching
        aliases = COMPETITOR_ALIASES.get(competitor, [competitor.lower()])

        # Signal 1: Title presence (STRONGEST - 0.4)
        title_lower = article.title.lower()
        for alias in aliases:
            alias_lower = alias.lower()
            # Use word boundaries for clean matching
            if alias_lower in title_lower:
                score += 0.4
                logger.debug(f"Actor signal: '{alias}' in title (+0.4)")
                break

        # Signal 2: Lead paragraph presence (0.3)
        # First 300 chars of content = article lead
        if article.content and len(article.content) >= 300:
            lead = article.content[:300].lower()
            for alias in aliases:
                if alias.lower() in lead:
                    score += 0.3
                    logger.debug(f"Actor signal: '{alias}' in lead paragraph (+0.3)")
                    break
        elif article.summary:
            # Fallback: summary if no content
            summary_lower = article.summary.lower()
            for alias in aliases:
                if alias.lower() in summary_lower:
                    score += 0.3
                    logger.debug(f"Actor signal: '{alias}' in summary (+0.3)")
                    break

        # Signal 3: Grammatical subject detection (0.2)
        if self._is_grammatical_subject(article.title, competitor, aliases):
            score += 0.2
            logger.debug(f"Actor signal: '{competitor}' is grammatical subject (+0.2)")

        # Signal 3b: Partnership/relationship context (0.2)
        # Detects direct partnership phrases where competitor is a named participant.
        # Handles both "[Competitor] partners with X" and "X partners with [Competitor]".
        partnership_phrases = [
            'partners with', 'partnered with', 'partnership with',
            'teams up with', 'collaboration with', 'collaborates with',
            'joins forces with', 'works with',
        ]
        title_summary = f"{article.title} {article.summary}".lower()
        for phrase in partnership_phrases:
            for alias in aliases:
                alias_lower = alias.lower()
                # "[Competitor] partners with X"
                if f"{alias_lower} {phrase}" in title_summary:
                    score += 0.2
                    logger.debug(f"Actor signal: '{competitor}' in partnership context as subject (+0.2)")
                    break
                # "X partners with [Competitor]"
                if f"{phrase} {alias_lower}" in title_summary:
                    score += 0.2
                    logger.debug(f"Actor signal: '{competitor}' in partnership context as participant (+0.2)")
                    break
            else:
                continue
            break

        # Signal 4: Frequency in main content (0.1)
        if article.content:
            # Exclude last 20% (likely author bio/footnotes)
            main_content = article.content[:int(len(article.content) * 0.8)].lower()
            mention_count = sum(main_content.count(alias.lower()) for alias in aliases)
            if mention_count >= 3:
                score += 0.1
                logger.debug(f"Actor signal: {mention_count} mentions in main content (+0.1)")

        # Penalty 1: Comparison context (-0.4)
        # "GPT-5 vs Claude 4", "X compared to Y"
        comparison_patterns = [
            r'\bvs\b', r'\bversus\b', r'compared to', r'comparison',
            r'rivals?', r'competes? with', r'alternative to',
            r'instead of', r'rather than', r'which .* better'
        ]
        text_for_comparison = f"{article.title} {article.summary}".lower()
        for pattern in comparison_patterns:
            if re.search(pattern, text_for_comparison):
                score -= 0.4
                logger.debug(f"Actor penalty: comparison context detected (pattern: {pattern}) (-0.4)")
                break

        # Penalty 2: Appears only in final 20% (author bio/footnote) (-0.5)
        # Only applies when competitor is NOT already established as primary actor
        # via title presence or grammatical subject. This prevents short articles
        # from being penalized when a product/model alias appears late in content.
        if article.content:
            final_section = article.content[int(len(article.content) * 0.8):].lower()
            main_content = article.content[:int(len(article.content) * 0.8)].lower()

            # Check if mentioned in final section
            in_final = any(alias.lower() in final_section for alias in aliases)
            # Check if NOT mentioned in main content
            not_in_main = not any(alias.lower() in main_content for alias in aliases)

            if in_final and not_in_main:
                # Skip penalty if competitor is already established as primary actor
                # via title presence or grammatical subject
                if score >= 0.4:  # title presence (0.4) or title + grammar (0.6)
                    logger.debug(f"Actor penalty skipped: '{competitor}' has strong primary signals (score: {score:.2f})")
                else:
                    score -= 0.5
                    logger.debug(f"Actor penalty: '{competitor}' only in final 20% (likely author bio) (-0.5)")

        # Clamp to 0.0-1.0
        score = max(0.0, min(1.0, score))

        return score

    def _is_grammatical_subject(self, sentence: str, competitor: str, aliases: list) -> bool:
        """
        Check if competitor appears as grammatical subject using heuristics.

        Simple patterns (no NLP library required):
        - Sentence starts with competitor name
        - "[Competitor] [action verb]"
        - "[Competitor]'s [noun]"

        Args:
            sentence: Sentence to analyze (typically title)
            competitor: Competitor name
            aliases: List of competitor aliases

        Returns:
            True if competitor is likely the grammatical subject
        """
        sentence_lower = sentence.lower()

        for alias in aliases:
            alias_lower = alias.lower()

            # Pattern 1: Sentence starts with competitor
            if sentence_lower.startswith(alias_lower):
                return True

            # Pattern 2: "Competitor [action verb]"
            action_verbs = [
                'launches', 'announces', 'releases', 'introduces',
                'unveils', 'reveals', 'publishes', 'partners',
                'acquires', 'raises', 'hires', 'appoints',
                'expands', 'opens', 'closes', 'updates',
                'partners with', 'collaborates with',
                # Partnership/relationship verbs (Fix 2: narrow scope)
                'partnered with', 'partnership with', 'teams up with',
                'collaboration with', 'joins forces with', 'works with',
            ]
            for verb in action_verbs:
                pattern = f"{alias_lower} {verb}"
                if pattern in sentence_lower:
                    return True

            # Pattern 3: "Competitor's"
            possessive_pattern = f"{alias_lower}'s"
            if possessive_pattern in sentence_lower:
                # Check position - should be early in sentence
                pos = sentence_lower.find(possessive_pattern)
                if pos < len(sentence_lower) * 0.3:  # First 30% of sentence
                    return True

        return False

    def _verify_competitor_is_actor(self, article: NewsArticle, candidate_competitor: str, is_official_source: bool) -> tuple[bool, float]:
        """
        Verify that detected competitor is the article's primary actor/subject.

        Phase 12 Fix A: Prevents false positives from ancillary mentions.

        Args:
            article: NewsArticle being classified
            candidate_competitor: Detected competitor to verify
            is_official_source: Whether this is from an official competitor source

        Returns:
            Tuple of (is_actor: bool, actor_score: float)
        """
        # Official sources: Skip verification (authoritative)
        # Even customer case studies from official sources are "company activity"
        if is_official_source:
            logger.debug(f"Official source: {article.source} → {candidate_competitor} (skip actor verification)")
            return True, 1.0

        # Third-party sources: Verify competitor is the actor
        actor_score = self._calculate_actor_evidence(article, candidate_competitor)

        ACTOR_THRESHOLD = 0.6

        if actor_score >= ACTOR_THRESHOLD:
            logger.debug(f"Actor verification PASSED: {candidate_competitor} (score: {actor_score:.2f})")
            return True, actor_score
        else:
            logger.info(f"Actor verification FAILED: {candidate_competitor} (score: {actor_score:.2f}) - detected but not primary actor in '{article.title[:60]}'")
            return False, actor_score

    def _detect_content_type(self, article: NewsArticle) -> str:
        """
        Detect content type to assess competitive intelligence value.

        Phase 12 Fix B: Distinguishes high-value technical intelligence from
        low-value marketing/customer stories.

        Returns:
            'technical' - High-value competitive intelligence
            'customer_story' - Customer case study / adoption story
            'consumer_marketing' - Consumer-focused marketing
            'partnership' - Business partnership (evaluate context)
            'other' - Default / unclear
        """
        title_lower = article.title.lower()
        summary_lower = article.summary.lower() if article.summary else ""
        text = f"{title_lower} {summary_lower}"

        # Pattern 1: Customer Case Study
        customer_story_patterns = [
            r'how \w+ (uses?|implements?|deploys?|adopts?|builds? with)',
            r'(customer|company|enterprise|organization) (uses?|adopts?|implements?)',
            r'case study',
            r'success story',
            r'(is using|has adopted|has implemented)',
            r'reimagining \w+ (with|from)',
        ]

        for pattern in customer_story_patterns:
            if re.search(pattern, text):
                logger.debug(f"Content type: customer_story (pattern: {pattern})")
                return 'customer_story'

        # Pattern 2: Consumer Marketing
        consumer_marketing_patterns = [
            r'brand ambassador',
            r'ambassador for',
            r'(celebrity|actor|artist|influencer)',
            r'announces? \w+ as',
            r'(launches?|expands?) in (india|china|brazil|region|market)',
            r'(smart glasses|wearables|consumer device|headset)',
        ]

        consumer_marketing_keywords = [
            'brand ambassador', 'celebrity', 'fashion', 'style',
            'consumer', 'retail launch', 'regional', 'market expansion'
        ]

        for pattern in consumer_marketing_patterns:
            if re.search(pattern, text):
                logger.debug(f"Content type: consumer_marketing (pattern: {pattern})")
                return 'consumer_marketing'

        # Pattern 3: Technical Content
        technical_patterns = [
            r'\bapi\b (change|update|release|version|endpoint)',
            r'(model|algorithm|architecture) (release|update|improvement)',
            r'(benchmark|performance|accuracy|evaluation)',
            r'(research|paper|study|findings)',
            r'(developer|sdk|library|framework)',
            r'(pricing|price|cost) (change|update|model)',
            r'(funding|acquisition|acquires|raises \$)',
            r'(ceo|cto|founder) (joins|leaves|appointed)',
        ]

        technical_keywords = [
            'api', 'sdk', 'developer', 'model', 'benchmark', 'accuracy',
            'research paper', 'architecture', 'algorithm', 'dataset',
            'fine-tuning', 'training', 'inference', 'token', 'latency'
        ]

        # Count technical keywords
        tech_count = sum(1 for kw in technical_keywords if kw in text)

        for pattern in technical_patterns:
            if re.search(pattern, text):
                logger.debug(f"Content type: technical (pattern: {pattern})")
                return 'technical'

        if tech_count >= 3:
            logger.debug(f"Content type: technical (keyword count: {tech_count})")
            return 'technical'

        # Pattern 4: Partnership
        if 'partnership' in text or 'partners with' in text or 'collaboration' in text:
            logger.debug("Content type: partnership")
            return 'partnership'

        logger.debug("Content type: other (no specific pattern matched)")
        return 'other'

    def _assign_priority(self, content_type: str, relevance_score: float, is_official_source: bool) -> str:
        """
        Assign priority level based on content type and relevance.

        Phase 12 Fix B: Hybrid filtering approach.

        Args:
            content_type: Detected content type
            relevance_score: Relevance score from scorer
            is_official_source: Whether from official source

        Returns:
            Priority: 'high', 'medium', or 'low'
        """
        if content_type == 'technical':
            return 'high'
        elif content_type in ['customer_story', 'consumer_marketing']:
            return 'low'
        elif content_type == 'partnership':
            # Partnerships vary - use relevance as tiebreaker
            return 'high' if relevance_score >= 0.5 else 'medium'
        else:
            return 'medium'

    def _detect_action_context(self, article: NewsArticle) -> str:
        """
        Detect whether article describes active company action or passive usage.

        Phase 12 Fix C: Distinguishes active events from passive adoption/usage.

        Returns:
            'active' - Company is performing an action
            'passive' - Usage, adoption, implementation by another party
            'neutral' - Unclear or descriptive
        """
        text = f"{article.title} {article.summary}".lower()

        # Active verbs - company is DOING something
        active_verbs = [
            'launches', 'announces', 'releases', 'unveils', 'introduces',
            'publishes', 'reveals', 'updates', 'changes', 'modifies',
            'adds', 'removes', 'deprecates', 'improves', 'enhances',
            'partners with', 'acquires', 'raises', 'appoints', 'hires',
            'expands', 'opens', 'unveils'
        ]

        # Passive verbs - someone is USING something
        passive_verbs = [
            'uses', 'adopts', 'implements', 'deploys', 'integrates',
            'builds with', 'powered by', 'based on', 'relies on',
            'chooses', 'selects', 'migrates to', 'switches to',
            'is using', 'has adopted', 'has implemented'
        ]

        active_count = sum(1 for verb in active_verbs if verb in text)
        passive_count = sum(1 for verb in passive_verbs if verb in text)

        if active_count > passive_count and active_count > 0:
            logger.debug(f"Action context: active (active_verbs={active_count}, passive_verbs={passive_count})")
            return 'active'
        elif passive_count > active_count and passive_count > 0:
            logger.debug(f"Action context: passive (active_verbs={active_count}, passive_verbs={passive_count})")
            return 'passive'
        else:
            logger.debug(f"Action context: neutral (active_verbs={active_count}, passive_verbs={passive_count})")
            return 'neutral'

    def _validate_event_with_context(self, event_type: str, action_context: str, article: NewsArticle) -> str:
        """
        Validate and adjust event type based on action context.

        Phase 12 Fix C: Corrects event classification using context.

        Rules:
        - api_change with passive context → 'other'
        - product_launch with passive context → 'other'
        - feature_update with passive context → 'other'

        Args:
            event_type: Initially classified event type
            action_context: Detected action context
            article: NewsArticle for additional context

        Returns:
            Validated event type
        """
        if action_context == 'passive':
            # Usage/adoption context

            if event_type == 'api_change':
                # "Company uses OpenAI API" → not an API change
                logger.debug(f"Event validation: api_change → other (passive context)")
                return 'other'

            if event_type == 'product_launch':
                # "Company adopts Product X" → not a product launch
                logger.debug(f"Event validation: product_launch → other (passive context)")
                return 'other'

            if event_type == 'feature_update':
                # "Company uses new feature" → not a feature update
                logger.debug(f"Event validation: feature_update → other (passive context)")
                return 'other'

            # Other events less affected by passive context
            if event_type in ['partnership', 'research_release', 'funding', 'acquisition', 'leadership']:
                return event_type  # These are valid even in passive context

            # Default for passive context
            return 'other'

        elif action_context == 'active':
            # Company action - existing classification likely correct
            return event_type

        else:
            # Neutral context - trust existing classification
            return event_type

    def _classify_event_type(self, article: NewsArticle) -> Optional[str]:
        """
        Classify the event type based on article content.

        This is a deterministic, keyword-based classification with priority ordering.
        More specific event types (pricing, api, leadership) are checked first.

        Weighting: Title (3x) > Summary (2x) > Content (1x) to capture primary intent.

        Args:
            article: NewsArticle to classify

        Returns:
            Event type string or None if no match
        """
        # Prepare text for matching with separate weighting zones
        title_text = article.title.lower()
        summary_text = article.summary.lower() if article.summary else ""
        content_text = article.content.lower() if article.content else ""

        # Count keyword matches for each event type
        # Title=3x, Summary=2x, Content=1x to capture primary intent
        event_scores = {}

        for event_type, keywords in self.EVENT_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(keyword) + r'\b'

                # Check title (weighted 3x - strongest signal)
                if re.search(pattern, title_text, re.IGNORECASE):
                    score += 3

                # Check summary (weighted 2x - strong signal)
                if re.search(pattern, summary_text, re.IGNORECASE):
                    score += 2

                # Check content (weighted 1x - weaker signal)
                if re.search(pattern, content_text, re.IGNORECASE):
                    score += 1

            if score > 0:
                event_scores[event_type] = score

        # Return event type with highest score
        # Priority is implicit in the ordered dict (Python 3.7+)
        if event_scores:
            best_event_type = max(event_scores.items(), key=lambda x: x[1])[0]
            logger.debug(f"Event classification scores: {event_scores}, selected: {best_event_type}")
            return best_event_type

        return None

    def classify_articles(self, articles: list[NewsArticle]) -> list[Finding]:
        """
        Classify multiple articles into findings.

        Args:
            articles: List of NewsArticle objects

        Returns:
            List of Finding objects
        """
        findings = []

        for article in articles:
            finding = self.classify_article(article)
            if finding:
                findings.append(finding)

        logger.info(f"Classified {len(findings)} findings from {len(articles)} articles")

        return findings

    def get_event_types(self) -> list[str]:
        """
        Get list of all supported event types.

        Returns:
            List of event type strings
        """
        return list(self.EVENT_KEYWORDS.keys())
