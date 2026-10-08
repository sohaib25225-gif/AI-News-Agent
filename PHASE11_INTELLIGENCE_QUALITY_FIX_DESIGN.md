# PHASE 11: COMPETITOR ATTRIBUTION & INTELLIGENCE QUALITY FIX DESIGN

**Date:** 2026-10-05  
**Type:** Design Document (READ-ONLY)  
**Status:** COMPLETE - Awaiting Implementation Authorization  
**References:** PHASE10_INTELLIGENCE_QUALITY_AUDIT.md

---

## EXECUTIVE SUMMARY

This document designs three targeted fixes to address the intelligence quality issues identified in Phase 10:

**Fix A:** Competitor Actor/Subject Verification (CRITICAL)
- Eliminates false positives from ancillary mentions (author bios, footnotes)
- Distinguishes competitor as ACTOR vs MENTIONED entity
- Estimated impact: 33% false positive rate → 0-5%

**Fix B:** Intelligence Value / Marketing Filter (HIGH PRIORITY)
- Filters or flags low-value marketing and customer case study content
- Preserves high-value competitive intelligence
- Estimated impact: 0% high-value rate → 50-70%

**Fix C:** Event Classification Context (MEDIUM PRIORITY)
- Distinguishes active company actions from passive usage/mentions
- Improves event type accuracy
- Estimated impact: 43% event misclassification → 10-15%

**Implementation Risk:** LOW - All fixes are additive filters/validators, no breaking changes  
**Estimated Timeline:** 10-14 hours total (4-6h Fix A, 4-6h Fix B, 2-3h Fix C)  
**Recommended Order:** Fix A → Fix B → Fix C (or A+B together, then C)

---

## PART 1: ROOT CAUSE ANALYSIS

### Current System Flow

```
Article
  ↓
[1] Relevance Scorer (keyword-based)
  ↓ (score >= 0.3)
[2] Intelligence Classifier
  ↓
  [2a] Competitor Detection
       - Official source mapping (authoritative)
       - Content alias matching (regex search in title+summary+content)
       - Returns highest-scoring competitor
  ↓
  [2b] Event Classification  
       - Keyword matching with weighted scoring (title=3x, summary=2x, content=1x)
       - Returns highest-scoring event type
  ↓
  [2c] Source Confidence
       - Multi-factor scoring (source type, corroboration, language)
       - Flags for review if < 0.6
  ↓
Finding Created (if competitor detected)
```

### Root Cause #1: Competitor Detection Is Position-Agnostic

**Current Implementation (intelligence_classifier.py:177-238):**

```python
def _detect_competitor_from_content(self, article):
    text = f"{article.title} {article.summary}".lower()
    if article.content:
        text += f" {article.content}".lower()  # ALL content included
    
    for competitor, aliases in COMPETITOR_ALIASES.items():
        for alias in aliases:
            if re.search(pattern, text):
                score += 1
    
    return max_scoring_competitor
```

**Problem:**
- Searches entire document uniformly
- Author bio at position 10,965 has same weight as title at position 0
- No distinction between "Anthropic launches Claude" vs "Author has Anthropic certificates"
- No section awareness (main content vs metadata vs author bio)

**Evidence from Phase 10:**
- Finding #72: "Anthropic" appeared once at position 10,965 in author bio
- Article was about Amazon Nova, not Anthropic
- False positive created

### Root Cause #2: Keyword-Based Relevance Includes Marketing Language

**Current Implementation (relevance_scorer.py:25-44):**

```python
HIGH_IMPACT_KEYWORDS = [
    "launch", "announce", "release", "breakthrough", "first",
    "acquisition", "merger", "funding", "raise", "investment",
    "partnership", "collaborate", "pricing", "price", "api",
    "leadership", "ceo", "founder", "executive"
]

INNOVATION_KEYWORDS = [
    "new", "novel", "revolutionary", "breakthrough", "innovation",
    "first", "unprecedented", "state-of-the-art", "sota",
    "outperform", "beats", "achieves", "milestone"
]
```

**Problem:**
- These keywords appear in BOTH technical announcements AND consumer marketing
- "Announcing Ranveer Singh as Brand Ambassador" → triggers "announce"
- "New updates to our AI glasses" → triggers "new"
- No distinction between:
  - "Announcing GPT-5 release" (technical)
  - "Announcing celebrity brand ambassador" (marketing)

**Evidence from Phase 10:**
- Finding #71: Celebrity brand ambassador announcement passed relevance (0.42)
- Finding #73: Customer case study passed relevance (0.3)
- Both are low competitive intelligence value

### Root Cause #3: Event Classification Is Context-Blind

**Current Implementation (intelligence_classifier.py:240-293):**

```python
def _classify_event_type(self, article):
    for event_type, keywords in self.EVENT_KEYWORDS.items():
        for keyword in keywords:
            if re.search(pattern, title_text):
                score += 3
            if re.search(pattern, summary_text):
                score += 2
            if re.search(pattern, content_text):
                score += 1
    
    return max_scoring_event_type
```

**Problem:**
- Keyword "api" triggers api_change regardless of context
- No distinction between:
  - "OpenAI changes API pricing" → api_change (correct)
  - "Albertsons uses OpenAI API" → api_change (incorrect)
- No verb analysis (active "launches" vs passive "uses")

**Evidence from Phase 10:**
- Finding #73: "Albertsons Cos. is using ChatGPT Enterprise and the OpenAI API"
- Classified as api_change because "api" keyword matched
- Actually a customer case study, not an API change

---

## PART 2: FIX A — COMPETITOR ACTOR/SUBJECT VERIFICATION

### Design Goals

1. **Eliminate false positives** from ancillary mentions (author bios, footnotes, references)
2. **Distinguish actor vs mentioned**: "OpenAI launches X" vs "Study compares with OpenAI"
3. **Preserve official source accuracy**: Official blogs should bypass verification
4. **Minimize false negatives**: Don't filter legitimate third-party reporting

### Proposed Algorithm

**Multi-Stage Actor Verification:**

```
Stage 1: Official Source Check
  IF article.source in COMPETITOR_MAPPING:
    RETURN mapped_competitor  # Authoritative, skip verification
    
Stage 2: Alias Detection (Current)
  competitors = detect_all_competitor_mentions_in_text()
  IF no competitors detected:
    RETURN None
  IF len(competitors) == 1:
    candidate = competitors[0]
    GOTO Stage 3
  IF len(competitors) > 1:
    candidate = highest_scoring_competitor
    GOTO Stage 3

Stage 3: Actor/Subject Verification (NEW)
  FOR each candidate competitor:
    actor_score = calculate_actor_evidence(article, candidate)
    IF actor_score >= ACTOR_THRESHOLD:
      RETURN candidate
  RETURN None  # Detected but not the actor

Stage 4: Multi-Competitor Handling (NEW)
  IF multiple candidates have actor_score >= ACTOR_THRESHOLD:
    # Both are actors (rare: joint announcement, partnership)
    IF title contains "and" or "partnership" or "collaborate":
      RETURN primary_competitor (highest actor_score)
    ELSE:
      RETURN None  # Ambiguous, requires review
```

### Actor Evidence Scoring

**Signals that competitor is the ACTOR (subject of article):**

```python
def calculate_actor_evidence(article, competitor) -> float:
    """
    Calculate evidence score that competitor is the primary actor/subject.
    
    Returns: score 0.0-1.0 (threshold: 0.6 recommended)
    """
    score = 0.0
    
    # Signal 1: Title presence (STRONGEST - 0.4)
    if competitor_in_title(article.title, competitor):
        score += 0.4
    
    # Signal 2: Lead paragraph presence (0.3)
    # First 300 chars of content = article lead
    if article.content and len(article.content) >= 300:
        lead = article.content[:300]
        if competitor_in_text(lead, competitor):
            score += 0.3
    elif competitor_in_text(article.summary, competitor):
        # Fallback: summary if no content
        score += 0.3
    
    # Signal 3: Grammatical subject detection (0.2)
    # Check if competitor appears as sentence subject
    if is_grammatical_subject(article.title, competitor):
        score += 0.2
    
    # Signal 4: Frequency in main content (0.1)
    # Multiple mentions suggest primary subject
    if article.content:
        # Exclude last 20% (likely author bio/footnotes)
        main_content = article.content[:int(len(article.content) * 0.8)]
        mention_count = count_competitor_mentions(main_content, competitor)
        if mention_count >= 3:
            score += 0.1
    
    # Penalty: Appears only in final 20% (-0.5)
    # Strong signal of author bio / footnote mention
    if article.content:
        final_section = article.content[int(len(article.content) * 0.8):]
        main_content = article.content[:int(len(article.content) * 0.8)]
        if (competitor_in_text(final_section, competitor) and 
            not competitor_in_text(main_content, competitor)):
            score -= 0.5
    
    return max(0.0, min(1.0, score))
```

### Grammatical Subject Detection (Simplified)

**Heuristic-Based Approach (No NLP Library Required):**

```python
def is_grammatical_subject(sentence, competitor):
    """
    Check if competitor appears as grammatical subject using heuristics.
    
    Simple patterns:
    - "[Competitor] [verb]" (e.g., "OpenAI launches")
    - "[Competitor]'s [noun]" (e.g., "Anthropic's Claude")
    - Sentence starts with competitor name
    """
    sentence_lower = sentence.lower()
    
    # Get competitor aliases
    aliases = get_competitor_aliases(competitor)
    
    for alias in aliases:
        alias_lower = alias.lower()
        
        # Pattern 1: Sentence starts with competitor
        if sentence_lower.startswith(alias_lower):
            return True
        
        # Pattern 2: "Competitor [action verb]"
        # Common action verbs in competitive intelligence
        action_verbs = [
            'launches', 'announces', 'releases', 'introduces',
            'unveils', 'reveals', 'publishes', 'partners',
            'acquires', 'raises', 'hires', 'appoints'
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
```

### Architecture Integration

**Location:** `agents/intelligence_classifier.py`

**New Method:**
```python
def _verify_competitor_is_actor(
    self, 
    article: NewsArticle, 
    candidate_competitor: str
) -> bool:
    """
    Verify that detected competitor is the article's primary actor/subject.
    
    Args:
        article: NewsArticle being classified
        candidate_competitor: Detected competitor to verify
    
    Returns:
        True if competitor is the actor, False if just mentioned
    """
    actor_score = self._calculate_actor_evidence(article, candidate_competitor)
    
    ACTOR_THRESHOLD = 0.6
    
    if actor_score >= ACTOR_THRESHOLD:
        logger.debug(f"Actor verification PASSED: {candidate_competitor} (score: {actor_score:.2f})")
        return True
    else:
        logger.debug(f"Actor verification FAILED: {candidate_competitor} (score: {actor_score:.2f}) - detected but not primary actor")
        return False
```

**Modified Flow in `classify_article()`:**

```python
def classify_article(self, article, corroborating_articles=None):
    # Step 1: Detect competitor
    competitor = get_competitor_from_source(article.source)
    
    # If official source, skip verification (authoritative)
    if competitor:
        logger.debug(f"Official source: {article.source} → {competitor} (skip verification)")
    else:
        # Content-based detection for third-party sources
        competitor = self._detect_competitor_from_content(article)
        
        if competitor:
            # NEW: Verify competitor is the actor
            if not self._verify_competitor_is_actor(article, competitor):
                logger.info(f"Competitor '{competitor}' detected but not primary actor: {article.title}")
                return None  # Filter out
    
    if not competitor:
        return None
    
    # Continue with existing flow...
```

### Official Source Handling

**Official sources bypass verification:**
- Articles from "OpenAI Blog" → OpenAI (always)
- Articles from "Meta Blog" → Meta AI (always)
- Articles from "Google AI Blog" → Google AI (always)

**Reasoning:**
- Official blogs are authoritative for that competitor
- Even customer case studies are "OpenAI activity" when published by OpenAI
- Avoids false negatives on official announcements

### Multiple Competitor Handling

**When multiple competitors are detected:**

1. Calculate actor_score for each
2. If only one passes threshold → that competitor
3. If multiple pass threshold:
   - Check for partnership keywords ("and", "with", "partnership")
   - If partnership: choose highest actor_score as primary
   - If not partnership: log ambiguity, return None (requires review)

**Example:**
- "OpenAI partners with Microsoft on AI development"
  - Both OpenAI and Microsoft detected
  - Both have high actor_scores
  - "partners with" keyword present
  - Primary: OpenAI (appears first in title)

### False Positive Risks

**Potential false positives (cases that should pass but might be filtered):**

1. **Short articles with competitor only in title:**
   - Risk: LOW
   - Mitigation: Title presence alone gives 0.4 score (below 0.6 threshold)
   - Solution: Adjust title weight to 0.5 if needed

2. **Academic papers with competitor in abstract but methodology in body:**
   - Risk: LOW
   - Mitigation: Lead paragraph check (first 300 chars) captures abstract

3. **News aggregation where competitor is subject but mentioned late:**
   - Risk: MEDIUM
   - Mitigation: Summary check provides backup signal

**Recommended threshold tuning:**
- Start with 0.6 threshold
- Monitor false negatives in first week
- Lower to 0.5 if legitimate findings are filtered

### False Negative Risks

**Potential false negatives (cases that should be filtered but might pass):**

1. **Competitor mentioned in title but article is about someone else:**
   - Example: "Company X rivals OpenAI with new model"
   - Risk: LOW
   - Reason: Title mentions OpenAI but grammatical subject is "Company X"
   - Current design: Would likely give OpenAI score 0.4 (title) + 0.2 (subject) = 0.6 (pass)
   - **Recommendation:** Add negative signal for "rival", "competes with", "versus" patterns

2. **Comparison articles:**
   - Example: "GPT-5 vs Claude 4: Which is better?"
   - Risk: MEDIUM
   - Current design: Both competitors in title → both get 0.4+ scores
   - Mitigation: Multi-competitor handler detects no partnership → returns None

**Recommended enhancement:**
```python
# Add to actor evidence calculation:

# Negative signal: Comparison/rival context
comparison_patterns = [
    'versus', 'vs', 'compared to', 'rivals', 'competes with',
    'alternative to', 'instead of', 'rather than'
]
for pattern in comparison_patterns:
    if pattern in article.title.lower() or pattern in article.summary.lower():
        score -= 0.3  # Strong penalty for comparison context
```

---

## PART 3: FIX B — INTELLIGENCE VALUE / MARKETING FILTER

### Design Goals

1. **Identify low-value content** (consumer marketing, customer case studies)
2. **Preserve high-value intelligence** (product launches, API changes, research)
3. **Provide graceful degradation** (flag/priority rather than hard filter)
4. **Maintain explainability** (clear reasons for filtering/flagging)

### Content Classification Dimensions

**High-Value Competitive Intelligence:**
- Product launches with technical details
- API changes affecting developers
- Research releases with novel capabilities
- Funding/acquisition affecting market position
- Strategic partnerships with technical integration
- Pricing changes
- Leadership changes affecting technical direction

**Low-Value Content (Marketing/PR):**
- Celebrity brand ambassador announcements
- Regional marketing campaigns
- Consumer product marketing (non-technical)
- Customer testimonials and case studies
- General "innovation" claims without substance
- Routine operational updates

### Proposed Algorithm

**Two-Stage Classification:**

```
Stage 1: Content Type Detection
  content_type = detect_content_type(article)
  # Returns: 'technical', 'customer_story', 'consumer_marketing', 'other'

Stage 2: Priority Assignment
  IF content_type == 'technical':
    priority = 'high'
  ELIF content_type == 'customer_story':
    priority = 'low'
  ELIF content_type == 'consumer_marketing':
    priority = 'low'
  ELSE:
    priority = 'medium'
```

### Content Type Detection

```python
def detect_content_type(article: NewsArticle) -> str:
    """
    Detect content type to assess competitive intelligence value.
    
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
    # "How [Company] uses [Product]"
    # "Company adopts/implements/deploys X"
    customer_story_patterns = [
        r'how \w+ (uses?|implements?|deploys?|adopts?|builds? with)',
        r'(customer|company|enterprise|organization) (uses?|adopts?|implements?)',
        r'case study',
        r'success story',
        r'(is using|has adopted|has implemented)',
        r'reimagining \w+ with',  # "reimagining retail with X"
    ]
    
    for pattern in customer_story_patterns:
        if re.search(pattern, text):
            return 'customer_story'
    
    # Pattern 2: Consumer Marketing
    # Celebrity/brand ambassador
    # Regional marketing campaigns
    # Non-technical product marketing
    consumer_marketing_patterns = [
        r'brand ambassador',
        r'ambassador for',
        r'(celebrity|actor|artist|influencer)',
        r'announces? \w+ as',  # "announces X as brand ambassador"
        r'(launches?|expands?) in (india|china|brazil|region)',  # Regional expansion
        r'(smart glasses|wearables|consumer device|headset)' # Consumer hardware
    ]
    
    consumer_marketing_keywords = [
        'brand ambassador', 'celebrity', 'bollywood', 'hollywood',
        'consumer', 'retail launch', 'fashion', 'style'
    ]
    
    for pattern in consumer_marketing_patterns:
        if re.search(pattern, text):
            return 'consumer_marketing'
    
    # Pattern 3: Technical Content
    # API, SDK, documentation, model release, benchmark, research
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
            return 'technical'
    
    if tech_count >= 3:
        return 'technical'
    
    # Pattern 4: Partnership
    if 'partnership' in text or 'partners with' in text or 'collaboration' in text:
        return 'partnership'
    
    return 'other'
```

### Priority Scoring Enhancement

**Extend RelevanceScorer with priority classification:**

```python
# Add to RelevanceScorer class

def score_with_priority(self, article: NewsArticle) -> Tuple[float, str]:
    """
    Score article and assign priority level.
    
    Returns:
        (relevance_score, priority_level)
        priority_level: 'high', 'medium', 'low'
    """
    # Existing relevance score
    score = self.score_article(article)
    
    # Content type detection
    content_type = self._detect_content_type(article)
    
    # Priority assignment
    if content_type == 'technical':
        priority = 'high'
    elif content_type in ['customer_story', 'consumer_marketing']:
        priority = 'low'
        # Optionally reduce relevance score
        score *= 0.7  # 30% penalty for low-priority content
    elif content_type == 'partnership':
        # Partnerships vary - keep medium
        priority = 'medium'
    else:
        priority = 'medium'
    
    return score, priority
```

### Integration Approach: Filter vs Flag

**Option 1: Hard Filter (Aggressive)**
```python
if priority == 'low':
    logger.info(f"Filtering low-priority content: {article.title}")
    return None  # Don't create finding
```

**Option 2: Soft Flag (Conservative)**
```python
# Create finding but mark as low priority
finding.priority = priority
finding.requires_review = (priority == 'low')
```

**Option 3: Hybrid (Recommended)**
```python
if priority == 'low' and relevance_score < 0.5:
    # Low priority AND low relevance → filter
    logger.info(f"Filtering low-value content: {article.title}")
    return None
elif priority == 'low':
    # Low priority but high relevance → flag for review
    finding.priority = 'low'
    finding.requires_review = True
else:
    finding.priority = priority
    finding.requires_review = (source_confidence < 0.6)
```

### Architecture Integration

**Location:** 
- Primary: `agents/relevance_scorer.py` (add content type detection)
- Secondary: `agents/intelligence_classifier.py` (use priority in finding creation)

**New Fields in Finding Model:**
```python
@dataclass
class Finding:
    # ... existing fields ...
    priority: str = 'medium'  # 'high', 'medium', 'low'
    content_type: str = 'other'  # 'technical', 'customer_story', etc.
```

**Modified Classification Flow:**
```python
def classify_article(self, article, corroborating_articles=None):
    # ... competitor detection ...
    
    # NEW: Content type and priority
    content_type = self._detect_content_type(article)
    priority = self._assign_priority(content_type, article.score)
    
    # Hybrid filtering
    if priority == 'low' and article.score < 0.5:
        logger.info(f"Filtering low-value content: {content_type} - {article.title[:50]}")
        return None
    
    # ... create finding ...
    finding.priority = priority
    finding.content_type = content_type
    
    # Adjust review flag
    if priority == 'low':
        finding.requires_review = True
    
    return finding
```

### Tradeoff Analysis

**Option 1: Hard Filter**
- ✅ Pros: Clean output, high signal-to-noise
- ❌ Cons: May filter legitimate edge cases, less flexibility
- Use case: High-volume system, manual review burden is high

**Option 2: Soft Flag**
- ✅ Pros: No false negatives, human has final say
- ❌ Cons: Low-value findings still appear in brief, review burden
- Use case: Low-volume system, human review is acceptable

**Option 3: Hybrid (Recommended)**
- ✅ Pros: Filters obvious low-value, flags borderline cases
- ✅ Pros: Balanced precision/recall
- ⚠️ Cons: Requires threshold tuning (relevance < 0.5 cutoff)
- Use case: Weekly intelligence brief (current system)

**Recommendation:** Use **Option 3 (Hybrid)** with:
- Hard filter: priority='low' AND relevance < 0.5
- Soft flag: priority='low' AND relevance >= 0.5
- This catches Finding #71 (relevance=0.42) while preserving borderline cases

### Official Source Special Handling

**Question:** Should customer case studies from official sources be filtered?

**Example:**
- Finding #73: "How Albertsons uses OpenAI API" from OpenAI Blog
- Content type: customer_story
- Priority: low
- But: Official OpenAI announcement

**Recommendation:** 
- Official sources should be FLAGGED, not FILTERED
- Reason: Even customer stories from official blogs indicate market activity
- Implementation:
  ```python
  if priority == 'low':
      if is_official_source(article.source):
          finding.requires_review = True  # Flag, don't filter
      elif relevance_score < 0.5:
          return None  # Filter third-party low-value content
  ```

---

## PART 4: FIX C — EVENT CLASSIFICATION CONTEXT

### Design Goals

1. **Distinguish active actions from passive usage**
2. **Improve event type accuracy**
3. **Maintain backward compatibility** with existing event types
4. **Minimize false classification changes**

### Problem Analysis

**Current Issue:**
- Keyword "api" triggers api_change classification
- No distinction between:
  - "OpenAI releases new API endpoint" → api_change (correct)
  - "Company uses OpenAI API" → customer_story (not api_change)

**Root Cause:**
Keyword matching without verb analysis or context understanding.

### Proposed Algorithm

**Context-Aware Event Classification:**

```python
def _classify_event_type_with_context(self, article: NewsArticle) -> str:
    """
    Classify event type with context awareness.
    
    Stages:
    1. Detect action verbs (active vs passive)
    2. Keyword matching (existing logic)
    3. Context validation (new logic)
    4. Return validated event type
    """
    # Stage 1: Detect action context
    action_context = self._detect_action_context(article)
    # Returns: 'active' (company action), 'passive' (usage/adoption), 'neutral'
    
    # Stage 2: Existing keyword matching
    event_type = self._classify_event_type(article)  # Current method
    
    # Stage 3: Context validation
    validated_event = self._validate_event_with_context(
        event_type, 
        action_context, 
        article
    )
    
    return validated_event
```

### Action Context Detection

```python
def _detect_action_context(self, article: NewsArticle) -> str:
    """
    Detect whether article describes active company action or passive usage.
    
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
        'partners with', 'acquires', 'raises', 'appoints', 'hires'
    ]
    
    # Passive verbs - someone is USING something
    passive_verbs = [
        'uses', 'adopts', 'implements', 'deploys', 'integrates',
        'builds with', 'powered by', 'based on', 'relies on',
        'chooses', 'selects', 'migrates to', 'switches to'
    ]
    
    # Descriptive verbs - neither active nor passive
    descriptive_verbs = [
        'is', 'are', 'has', 'have', 'offers', 'provides',
        'features', 'includes', 'supports'
    ]
    
    active_count = sum(1 for verb in active_verbs if verb in text)
    passive_count = sum(1 for verb in passive_verbs if verb in text)
    descriptive_count = sum(1 for verb in descriptive_verbs if verb in text)
    
    if active_count > passive_count and active_count > 0:
        return 'active'
    elif passive_count > active_count and passive_count > 0:
        return 'passive'
    else:
        return 'neutral'
```

### Event Validation with Context

```python
def _validate_event_with_context(
    self, 
    event_type: str, 
    action_context: str, 
    article: NewsArticle
) -> str:
    """
    Validate and adjust event type based on action context.
    
    Rules:
    - api_change with passive context → 'other'
    - product_launch with passive context → 'other' 
    - Any event with passive context → likely 'other' unless specific
    """
    # Special handling for context-sensitive events
    
    if action_context == 'passive':
        # Usage/adoption context
        
        if event_type == 'api_change':
            # "Company uses OpenAI API" → not an API change
            logger.debug(f"Reclassifying api_change to 'other' (passive context)")
            return 'other'
        
        if event_type == 'product_launch':
            # "Company adopts Product X" → not a product launch
            logger.debug(f"Reclassifying product_launch to 'other' (passive context)")
            return 'other'
        
        if event_type == 'feature_update':
            # "Company uses new feature" → not a feature update
            logger.debug(f"Reclassifying feature_update to 'other' (passive context)")
            return 'other'
        
        # Other events less affected by passive context
        if event_type in ['partnership', 'research_release', 'funding', 'acquisition']:
            return event_type  # These are valid even in passive context
        
        # Default for passive context
        return 'other'
    
    elif action_context == 'active':
        # Company action - existing classification is likely correct
        return event_type
    
    else:
        # Neutral context - trust existing classification
        return event_type
```

### Specific Case: API Context

**Enhanced API Classification:**

```python
def _classify_api_event(self, article: NewsArticle, action_context: str) -> str:
    """
    Specialized classifier for API-related events.
    
    Distinguishes:
    - API changes (pricing, endpoints, deprecation)
    - API usage (customer adoption)
    - API announcements (new API release)
    """
    text = f"{article.title} {article.summary}".lower()
    
    # Strong API change signals
    api_change_keywords = [
        'api change', 'api update', 'new api endpoint', 
        'api pricing', 'api version', 'deprecating api',
        'api rate limit', 'api key', 'breaking change'
    ]
    
    for keyword in api_change_keywords:
        if keyword in text:
            return 'api_change'
    
    # API usage signals
    api_usage_keywords = [
        'using the api', 'uses the api', 'with the api',
        'api integration', 'api to', 'via the api'
    ]
    
    if action_context == 'passive':
        for keyword in api_usage_keywords:
            if keyword in text:
                return 'other'  # Usage, not change
    
    # API general mention
    if 'api' in text:
        if action_context == 'active':
            return 'api_change'  # Likely an announcement
        else:
            return 'other'  # Generic mention
    
    return 'api_change'  # Default if keyword matched
```

### Architecture Integration

**Location:** `agents/intelligence_classifier.py`

**Modified `classify_article()` flow:**

```python
def classify_article(self, article, corroborating_articles=None):
    # ... competitor detection ...
    
    # Event classification with context
    action_context = self._detect_action_context(article)
    raw_event_type = self._classify_event_type(article)  # Existing
    validated_event_type = self._validate_event_with_context(
        raw_event_type, 
        action_context, 
        article
    )
    
    logger.debug(f"Event classification: raw={raw_event_type}, context={action_context}, final={validated_event_type}")
    
    # Use validated_event_type for Finding
    finding.event_type = validated_event_type
    
    return finding
```

### Backward Compatibility

**Concerns:**
- Existing event keywords and scoring logic should remain unchanged
- New context validation is ADDITIVE, not replacing existing logic
- Only affects ambiguous cases (api_change with passive context)

**Migration:**
- No database schema changes needed
- Existing findings unchanged
- New findings will have improved accuracy

### Edge Cases

**Case 1: Partnership announcements**
- "OpenAI partners with Microsoft"
- Context: active (partnership action)
- Event: partnership (correct)
- No change needed ✅

**Case 2: Customer partnership**
- "Albertsons partners with OpenAI"
- Context: active (partnership action)
- Event: partnership (correct even if customer-focused)
- Fix B (marketing filter) will handle priority ✅

**Case 3: Research paper using competitor model**
- "Research study uses GPT-4 for evaluation"
- Context: passive
- Event: might trigger 'research_release' or 'other'
- Should be: filtered by Fix A (not primary actor) ✅

**Case 4: API pricing change**
- "OpenAI changes API pricing"
- Context: active
- Event: api_change (correct)
- No change needed ✅

---

## PART 5: COMPREHENSIVE TEST PLAN

### Test Suite Design

**20+ test cases covering:**
1. Competitor detection edge cases (actor vs mention)
2. Content type classification (technical vs marketing)
3. Event classification with context
4. Official vs third-party sources
5. Single vs multiple competitors
6. Boundary cases and ambiguities

---

### TEST CASE 1: Competitor as Actor (Product Launch)

**Input:**
```
Title: "OpenAI Launches GPT-5 with Breakthrough Multimodal Capabilities"
Source: TechCrunch AI
Summary: "OpenAI today announced GPT-5, featuring advanced reasoning and image generation."
Content: "OpenAI has released GPT-5, marking a significant advancement in AI capabilities..."
```

**Expected Behavior:**
- **Competitor:** OpenAI
- **Actor Verification:** PASS (title presence, grammatical subject, active verbs)
- **Event Type:** product_launch
- **Content Type:** technical
- **Priority:** high
- **Finding Created:** YES
- **Relevance:** ~0.8

---

### TEST CASE 2: Competitor in Author Bio (False Positive)

**Input:**
```
Title: "How uniopen customized Amazon Nova to their retail moderation policies"
Source: AWS ML Blog
Summary: "See how uniopen adapted Amazon Nova 2 Lite using supervised fine-tuning."
Content: "uniopen is a digital platform... [10,000 chars] ...Author bio: David is a Solutions Architect who passed all 12 AWS and 4 Anthropic certificates..."
```

**Expected Behavior:**
- **Competitor:** Anthropic initially detected
- **Actor Verification:** FAIL (only in final 20%, not in title/lead/main content)
- **Event Type:** N/A
- **Finding Created:** NO (filtered by Fix A)
- **Reason:** Anthropic mentioned in author bio, not article subject

---

### TEST CASE 3: Customer Case Study (Low Priority)

**Input:**
```
Title: "How Albertsons Companies is reimagining retail with ChatGPT Enterprise"
Source: OpenAI Blog
Summary: "Albertsons is using ChatGPT Enterprise and OpenAI API to improve customer experiences."
Content: "Albertsons Cos. deployed ChatGPT Enterprise to help teams work faster..."
```

**Expected Behavior:**
- **Competitor:** OpenAI (official source)
- **Actor Verification:** PASS (official source, skip verification)
- **Event Type:** other (not api_change - passive context "is using")
- **Content Type:** customer_story
- **Priority:** low
- **Finding Created:** YES (official source, but flagged)
- **Requires Review:** TRUE
- **Relevance:** 0.3-0.4

---

### TEST CASE 4: Consumer Marketing (Low Priority)

**Input:**
```
Title: "Announcing Ranveer Singh as Brand Ambassador for Ray-Ban Meta in India"
Source: Meta Blog
Summary: "Ranveer Singh becomes the first Brand Ambassador for Ray-Ban and Ray-Ban Meta in India."
Content: "Ranveer has a long-standing relationship with Meta... exciting new updates to our AI glasses..."
```

**Expected Behavior:**
- **Competitor:** Meta AI (official source)
- **Actor Verification:** PASS (official source)
- **Event Type:** product_launch (from "announcing" keyword)
- **Content Type:** consumer_marketing
- **Priority:** low
- **Finding Created:** YES (official source, but flagged)
- **Requires Review:** TRUE
- **Relevance:** 0.42

---

### TEST CASE 5: Comparison Article (Should Filter)

**Input:**
```
Title: "GPT-5 vs Claude 4: Which AI model is better for coding?"
Source: TechCrunch AI
Summary: "We compare OpenAI's GPT-5 with Anthropic's Claude 4 across multiple benchmarks."
Content: "In this comprehensive comparison, we evaluate both models..."
```

**Expected Behavior:**
- **Competitor:** Both OpenAI and Anthropic detected
- **Actor Verification:** FAIL for both (comparison context, negative signal from "vs")
- **Event Type:** N/A
- **Finding Created:** NO (neither is the actor, both are comparison subjects)
- **Reason:** Comparison article, not about either competitor's action

---

### TEST CASE 6: Competitor in Related Work

**Input:**
```
Title: "New breakthrough in language models achieves 95% accuracy"
Source: MIT Technology Review AI
Summary: "Researchers developed a novel architecture that outperforms previous models."
Content: "Our approach builds on prior work... Previous models like GPT-4 and Claude achieved 85%... We improve on these by..."
```

**Expected Behavior:**
- **Competitor:** OpenAI and Anthropic detected in content
- **Actor Verification:** FAIL (mentioned in related work section, not primary actors)
- **Event Type:** N/A
- **Finding Created:** NO
- **Reason:** Competitors referenced in related work, not the subject

---

### TEST CASE 7: Multiple Competitors (Partnership)

**Input:**
```
Title: "OpenAI and Microsoft announce expanded partnership on AI infrastructure"
Source: OpenAI Blog
Summary: "OpenAI and Microsoft today announced a deepened collaboration on AI development."
Content: "The partnership will focus on Azure integration..."
```

**Expected Behavior:**
- **Competitor:** OpenAI (primary, official source)
- **Actor Verification:** PASS (official source, partnership context)
- **Event Type:** partnership
- **Content Type:** technical (partnership with technical focus)
- **Priority:** high
- **Finding Created:** YES
- **Note:** Microsoft AI also detected but OpenAI is primary (official source)

---

### TEST CASE 8: API Change (Active Context)

**Input:**
```
Title: "OpenAI announces API pricing changes and new endpoints"
Source: OpenAI Blog
Summary: "OpenAI today released new API pricing tiers and deprecated legacy endpoints."
Content: "Starting March 1st, the following API changes take effect..."
```

**Expected Behavior:**
- **Competitor:** OpenAI (official source)
- **Actor Verification:** PASS
- **Event Type:** api_change (active context "announces", "released")
- **Action Context:** active
- **Content Type:** technical
- **Priority:** high
- **Finding Created:** YES

---

### TEST CASE 9: API Usage (Passive Context - Should NOT be api_change)

**Input:**
```
Title: "How Shopify uses OpenAI API to power 24/7 customer support"
Source: TechCrunch AI
Summary: "Shopify implemented OpenAI's API to provide instant customer service responses."
Content: "Shopify integrated the OpenAI API into their support system..."
```

**Expected Behavior:**
- **Competitor:** OpenAI detected
- **Actor Verification:** FAIL (Shopify is the actor, not OpenAI)
- **Event Type:** N/A
- **Finding Created:** NO
- **Reason:** Customer usage story, OpenAI not the actor

---

### TEST CASE 10: Research Release

**Input:**
```
Title: "Google DeepMind publishes breakthrough paper on AI reasoning"
Source: DeepMind Blog
Summary: "DeepMind researchers present a novel approach to multi-step reasoning in language models."
Content: "Our paper, published in Nature, demonstrates..."
```

**Expected Behavior:**
- **Competitor:** Google AI (official source, DeepMind → Google AI mapping)
- **Actor Verification:** PASS (official source)
- **Event Type:** research_release
- **Content Type:** technical
- **Priority:** high
- **Finding Created:** YES

---

### TEST CASE 11: Funding Announcement

**Input:**
```
Title: "Anthropic raises $4B in Series C led by Google"
Source: TechCrunch AI
Summary: "AI startup Anthropic announced a $4 billion Series C funding round."
Content: "Anthropic, maker of Claude, secured significant funding..."
```

**Expected Behavior:**
- **Competitor:** Anthropic
- **Actor Verification:** PASS (title presence, active "raises")
- **Event Type:** funding
- **Content Type:** technical (funding is strategic intelligence)
- **Priority:** high
- **Finding Created:** YES

---

### TEST CASE 12: Acquisition

**Input:**
```
Title: "Microsoft acquires AI startup founded by former OpenAI researcher"
Source: TechCrunch AI
Summary: "Microsoft has acquired Inflection AI, a startup founded by Mustafa Suleyman."
Content: "The acquisition brings key AI talent to Microsoft..."
```

**Expected Behavior:**
- **Competitor:** Microsoft AI (primary actor)
- **Actor Verification:** PASS (title subject, active "acquires")
- **Event Type:** acquisition
- **Content Type:** technical
- **Priority:** high
- **Finding Created:** YES

---

### TEST CASE 13: Leadership Change

**Input:**
```
Title: "Former Google AI lead joins Anthropic as Chief Scientist"
Source: TechCrunch AI
Summary: "Dr. Jane Smith, former Google Brain researcher, appointed Chief Scientist at Anthropic."
Content: "Anthropic today announced the appointment of..."
```

**Expected Behavior:**
- **Competitor:** Anthropic (primary, receiving the leader)
- **Actor Verification:** PASS (title presence, Anthropic is hiring)
- **Event Type:** leadership
- **Content Type:** technical (leadership is strategic signal)
- **Priority:** high
- **Finding Created:** YES

---

### TEST CASE 14: No Competitor (Generic AI News)

**Input:**
```
Title: "AI regulation debate intensifies in European Parliament"
Source: MIT Technology Review AI
Summary: "European lawmakers discuss new AI safety regulations."
Content: "The proposed regulations would affect all AI companies..."
```

**Expected Behavior:**
- **Competitor:** None detected
- **Event Type:** N/A
- **Finding Created:** NO
- **Reason:** Generic AI news, no specific tracked competitor

---

### TEST CASE 15: Competitor Mentioned but Another Company is Actor

**Input:**
```
Title: "Startup claims to have built 'GPT-5 killer' model"
Source: TechCrunch AI
Summary: "New AI startup announces model that allegedly outperforms GPT-5."
Content: "The startup, founded last year, released benchmarks showing..."
```

**Expected Behavior:**
- **Competitor:** OpenAI detected (from "GPT-5")
- **Actor Verification:** FAIL (startup is actor, OpenAI just mentioned for comparison)
- **Event Type:** N/A
- **Finding Created:** NO
- **Reason:** OpenAI is benchmark/comparison reference, not the actor

---

### TEST CASE 16: Partnership (Technical Integration)

**Input:**
```
Title: "Anthropic partners with AWS to offer Claude on SageMaker"
Source: AWS ML Blog
Summary: "Anthropic's Claude models are now available through Amazon SageMaker."
Content: "The partnership enables enterprise customers to deploy Claude..."
```

**Expected Behavior:**
- **Competitor:** Anthropic (primary actor in partnership)
- **Actor Verification:** PASS (title subject, active "partners")
- **Event Type:** partnership
- **Content Type:** technical (technical integration)
- **Priority:** high
- **Finding Created:** YES

---

### TEST CASE 17: Ambiguous Article (Requires Review)

**Input:**
```
Title: "Inside the AI arms race: How tech giants are competing"
Source: MIT Technology Review AI
Summary: "An analysis of competitive dynamics between OpenAI, Google, Meta, and Anthropic."
Content: "All four companies are racing to develop AGI... OpenAI recently... Google announced... Meta focuses on..."
```

**Expected Behavior:**
- **Competitor:** Multiple detected (OpenAI, Google AI, Meta AI, Anthropic)
- **Actor Verification:** FAIL for all (analytical article, no single actor)
- **Event Type:** N/A
- **Finding Created:** NO
- **Reason:** Industry analysis, not specific competitor action

---

### TEST CASE 18: Official Source Customer Story

**Input:**
```
Title: "How DuoLingo uses GPT-4 to create personalized language lessons"
Source: OpenAI Blog
Summary: "DuoLingo built an AI tutor using GPT-4 that adapts to each learner."
Content: "DuoLingo partnered with OpenAI to integrate GPT-4..."
```

**Expected Behavior:**
- **Competitor:** OpenAI (official source)
- **Actor Verification:** PASS (official source, bypass verification)
- **Event Type:** partnership or other (passive/adoption context)
- **Action Context:** passive ("uses")
- **Content Type:** customer_story
- **Priority:** low
- **Finding Created:** YES (official source)
- **Requires Review:** TRUE (low priority content)

---

### TEST CASE 19: Regional Product Launch (Marketing)

**Input:**
```
Title: "Meta AI expands Llama availability to 10 new countries"
Source: Meta Blog
Summary: "Meta announces Llama is now available in India, Brazil, and 8 other markets."
Content: "This expansion brings our AI assistant to millions more users..."
```

**Expected Behavior:**
- **Competitor:** Meta AI (official source)
- **Actor Verification:** PASS (official source)
- **Event Type:** product_launch
- **Content Type:** Could be consumer_marketing (regional expansion) or technical (product availability)
- **Priority:** medium (regional expansion has some value)
- **Finding Created:** YES
- **Requires Review:** FALSE (medium priority, official announcement)

---

### TEST CASE 20: Benchmark/Evaluation Article

**Input:**
```
Title: "Independent benchmark shows Claude 4 leads in coding tasks"
Source: Hugging Face Blog
Summary: "New evaluation framework ranks Claude 4 ahead of GPT-5 and Gemini Pro in programming."
Content: "We evaluated multiple models... Claude 4 scored 87%, GPT-5 scored 82%..."
```

**Expected Behavior:**
- **Competitor:** Anthropic (Claude 4), also OpenAI and Google AI detected
- **Actor Verification:** PASS for Anthropic (primary subject, wins the benchmark)
- **Event Type:** other or research_release
- **Content Type:** technical (benchmark results are valuable)
- **Priority:** high (third-party validation is valuable competitive intelligence)
- **Finding Created:** YES (for Anthropic - they're performing well)

---

### TEST CASE 21: Pricing Change

**Input:**
```
Title: "OpenAI reduces GPT-4 API pricing by 50%"
Source: OpenAI Blog
Summary: "OpenAI announced significant price reductions across all API tiers."
Content: "Effective immediately, GPT-4 API pricing is reduced from $0.03 to $0.015 per 1K tokens..."
```

**Expected Behavior:**
- **Competitor:** OpenAI (official source)
- **Actor Verification:** PASS
- **Event Type:** pricing_change
- **Content Type:** technical
- **Priority:** high
- **Finding Created:** YES

---

### TEST CASE 22: Feature Update

**Input:**
```
Title: "Claude now supports 200K context window"
Source: Anthropic Blog
Summary: "Anthropic announces expanded context window for Claude 2.1"
Content: "We've increased Claude's context window from 100K to 200K tokens..."
```

**Expected Behavior:**
- **Competitor:** Anthropic (official source)
- **Actor Verification:** PASS
- **Event Type:** feature_update
- **Content Type:** technical
- **Priority:** high
- **Finding Created:** YES

---

### TEST CASE 23: Competitor as Object in Acquisition

**Input:**
```
Title: "Tech giant XYZ acquires OpenAI competitor Cohere"
Source: TechCrunch AI
Summary: "XYZ Corp announced acquisition of Cohere, a startup competing with OpenAI."
Content: "The deal values Cohere at $2B... Cohere's models compete directly with GPT..."
```

**Expected Behavior:**
- **Competitor:** OpenAI detected (mentioned as comparison)
- **Actor Verification:** FAIL (OpenAI is comparison reference, not actor or subject)
- **Event Type:** N/A
- **Finding Created:** NO
- **Reason:** OpenAI mentioned for context, not the subject

---

### TEST CASE 24: Third-Party Technical Analysis

**Input:**
```
Title: "Anthropic's Constitutional AI approach shows promise in safety benchmarks"
Source: MIT Technology Review AI
Summary: "Independent researchers evaluate Anthropic's safety approach and find significant improvements."
Content: "Anthropic's Constitutional AI method... benchmarks show 40% reduction in harmful outputs..."
```

**Expected Behavior:**
- **Competitor:** Anthropic
- **Actor Verification:** PASS (title subject, article about Anthropic's technology)
- **Event Type:** research_release or other
- **Content Type:** technical
- **Priority:** high (third-party validation)
- **Finding Created:** YES

---

### TEST CASE 25: Regulatory News

**Input:**
```
Title: "EU opens investigation into OpenAI's data practices"
Source: TechCrunch AI
Summary: "European regulators launch formal inquiry into OpenAI's GDPR compliance."
Content: "The investigation follows complaints about data collection..."
```

**Expected Behavior:**
- **Competitor:** OpenAI
- **Actor Verification:** PASS (OpenAI is subject of regulatory action)
- **Event Type:** regulation
- **Content Type:** technical (regulatory is strategic intelligence)
- **Priority:** high
- **Finding Created:** YES

---

## PART 6: EXPECTED BEFORE/AFTER BEHAVIOR

### Finding #72 (Amazon Nova / Anthropic False Positive)

**BEFORE FIX A:**
```
Competitor: Anthropic
Event: product_launch
Source: AWS ML Blog
Confidence: 0.4
Requires Review: TRUE
Created: YES ❌ (FALSE POSITIVE)
Reason: "Anthropic" detected in author bio
```

**AFTER FIX A:**
```
Competitor: None
Event: N/A
Finding Created: NO ✅
Reason: Actor verification failed - Anthropic only in author bio (final 20% of content), not primary subject
Actor Score: 0.0 (penalty for final-section-only)
```

---

### Finding #71 (Ray-Ban Meta Brand Ambassador)

**BEFORE FIX B:**
```
Competitor: Meta AI
Event: product_launch
Content Type: N/A
Priority: N/A
Requires Review: FALSE
Created: YES ⚠️ (LOW VALUE)
Relevance: 0.42
```

**AFTER FIX B:**
```
Competitor: Meta AI
Event: product_launch
Content Type: consumer_marketing
Priority: low
Requires Review: TRUE ✅
Created: YES (official source, not filtered)
Relevance: 0.29 (0.42 * 0.7 penalty)
Notes: Flagged for review due to low competitive value
```

---

### Finding #73 (OpenAI / Albertsons Case Study)

**BEFORE FIX B + FIX C:**
```
Competitor: OpenAI
Event: api_change ❌
Content Type: N/A
Priority: N/A
Action Context: N/A
Requires Review: FALSE
Created: YES ⚠️
```

**AFTER FIX B + FIX C:**
```
Competitor: OpenAI
Event: other ✅ (was api_change, corrected)
Content Type: customer_story
Priority: low
Action Context: passive ("is using")
Requires Review: TRUE ✅
Created: YES (official source)
Notes: Customer case study, flagged for review
```

---

### New Test Article: "GPT-5 vs Claude 4 comparison"

**BEFORE FIX A:**
```
Competitor: OpenAI or Anthropic (highest scorer)
Event: product_launch or research_release
Created: YES ❌ (should be filtered)
```

**AFTER FIX A:**
```
Competitor: None
Event: N/A
Finding Created: NO ✅
Reason: Comparison article detected (negative signal for "vs")
Both competitors detected but actor verification failed for both
```

---

### Official Technical Announcement

**BEFORE & AFTER (NO CHANGE - WORKING CORRECTLY):**
```
Title: "OpenAI releases GPT-5 with breakthrough capabilities"
Source: OpenAI Blog

Competitor: OpenAI ✅
Event: product_launch ✅
Content Type: technical ✅
Priority: high ✅
Actor Verification: PASS (official source, skip)
Finding Created: YES ✅
```

---

## PART 7: IMPLEMENTATION RISKS

### Risk 1: False Negatives from Fix A (Actor Verification)

**Risk Level:** MEDIUM

**Scenario:**
Legitimate competitive intelligence filtered because actor score below threshold.

**Example:**
- Short article with competitor only mentioned in summary (not title)
- Actor score: title(0) + lead(0.3) + subject(0) = 0.3 < 0.6 threshold
- Result: False negative

**Mitigation:**
- Start with threshold 0.6, monitor for false negatives
- Lower to 0.5 if needed after 1 week
- Official sources bypass verification (no false negatives there)

**Rollback Plan:**
- If false negative rate > 10%, disable Fix A temporarily
- Adjust scoring weights (increase lead paragraph weight to 0.4)
- Re-enable with new weights

---

### Risk 2: Excessive Filtering from Fix B (Marketing Filter)

**Risk Level:** LOW

**Scenario:**
Technical content misclassified as marketing/customer story.

**Example:**
- Partnership announcement with customer use case details
- Pattern matches "how [company] uses" but is actually a technical partnership
- Result: Flagged as low priority incorrectly

**Mitigation:**
- Use hybrid approach (flag, not hard filter)
- Official sources are flagged but never filtered
- Review flags are visible in brief, human can override

**Rollback Plan:**
- If too many findings flagged (> 50% require review), adjust patterns
- Disable customer story pattern matching
- Keep consumer marketing patterns (higher precision)

---

### Risk 3: Event Type Instability from Fix C (Context Classification)

**Risk Level:** LOW

**Scenario:**
Event types change for existing pattern articles, breaking historical consistency.

**Example:**
- Previous customer stories were classified as "api_change"
- After Fix C, reclassified as "other"
- Result: Week-over-week comparison shows drop in api_change events

**Mitigation:**
- This is actually CORRECT behavior (fixing previous misclassifications)
- Document in release notes that event classification improved
- No rollback needed (improvement, not regression)

**Monitoring:**
- Track event type distribution before/after
- Expected: api_change count decreases, "other" count increases
- If api_change drops to zero: investigate over-filtering

---

### Risk 4: Performance Degradation

**Risk Level:** LOW

**Scenario:**
Additional processing steps slow down classification pipeline.

**Impact:**
- Fix A: Actor verification adds ~50-100ms per article (string operations, regex)
- Fix B: Content type detection adds ~30-50ms per article (pattern matching)
- Fix C: Context detection adds ~20-30ms per article (verb analysis)
- Total: ~100-200ms per article

**Mitigation:**
- Current pipeline processes ~30-50 articles per run
- Additional latency: 3-10 seconds total
- Weekly execution: performance impact negligible

**Optimization if needed:**
- Cache competitor alias lookups
- Combine regex patterns into single pass
- Process articles in parallel (not needed for current volume)

---

### Risk 5: Regression in Existing Tests

**Risk Level:** VERY LOW

**Scenario:**
Changes break existing test_v1_components.py tests.

**Impact:**
Existing tests may fail if they depend on specific event classification or finding creation behavior.

**Mitigation:**
- Review existing tests before implementation
- Update test expectations to match new behavior
- Add new tests for Fix A, B, C edge cases

**Rollback Plan:**
- All fixes are in separate functions, can be individually disabled
- Feature flags for each fix:
  ```python
  ENABLE_ACTOR_VERIFICATION = True  # Fix A
  ENABLE_CONTENT_TYPE_FILTER = True  # Fix B
  ENABLE_CONTEXT_CLASSIFICATION = True  # Fix C
  ```

---

### Risk 6: Database Schema Changes

**Risk Level:** NONE

**Scenario:**
Adding new fields to Finding model requires database migration.

**Impact:**
None - new fields are optional and have defaults.

**New Fields:**
```python
priority: str = 'medium'  # Default value
content_type: str = 'other'  # Default value
action_context: str = 'neutral'  # Default value (Fix C)
actor_score: float = 0.0  # Default value (Fix A debugging)
```

**Migration:**
- SQLite allows adding columns with defaults without migration
- Existing findings get default values
- No data loss risk

---

## PART 8: RECOMMENDED IMPLEMENTATION ORDER

### Phase 1: Fix A (Competitor Actor Verification) - CRITICAL

**Priority:** MUST-HAVE for production

**Rationale:**
- Addresses 33% false positive rate (Finding #72)
- Highest user trust impact
- Prevents misleading competitive intelligence

**Implementation Steps:**
1. Add `_calculate_actor_evidence()` method
2. Add `_verify_competitor_is_actor()` method
3. Add `is_grammatical_subject()` helper
4. Integrate into `classify_article()` after content-based detection
5. Add actor_score field to Finding model (optional, for debugging)
6. Test with Finding #72 reproduction case

**Testing:**
- Run test cases 2, 5, 6, 9, 15, 23 (actor verification scenarios)
- Verify Finding #72 scenario is filtered
- Verify legitimate findings still pass (test cases 1, 7, 8, 10, 11, 12, 13)

**Estimated Time:** 4-6 hours

---

### Phase 2: Fix B (Intelligence Value Filter) - HIGH PRIORITY

**Priority:** SHOULD-HAVE for production

**Rationale:**
- Addresses 67% low-value finding rate
- Improves signal-to-noise ratio
- Reduces review burden

**Implementation Steps:**
1. Add `_detect_content_type()` method to RelevanceScorer
2. Add `_assign_priority()` method
3. Add priority and content_type fields to Finding model
4. Implement hybrid filter logic in `classify_article()`
5. Update requires_review logic to include priority
6. Test with Finding #71 and #73 reproduction cases

**Testing:**
- Run test cases 3, 4, 18, 19 (marketing/customer story scenarios)
- Verify Finding #71 is flagged (not filtered, official source)
- Verify Finding #73 is flagged
- Verify high-value technical findings not affected (test cases 1, 8, 10, 11, 21, 22)

**Estimated Time:** 4-6 hours

---

### Phase 3: Fix C (Event Classification Context) - MEDIUM PRIORITY

**Priority:** NICE-TO-HAVE for production (can be delayed)

**Rationale:**
- Addresses event type accuracy
- Lower impact than Fix A and B
- Can be implemented after production launch

**Implementation Steps:**
1. Add `_detect_action_context()` method
2. Add `_validate_event_with_context()` method
3. Add action_context field to Finding model (optional)
4. Integrate into `_classify_event_type()` flow
5. Test with Finding #73 api_change correction

**Testing:**
- Run test cases 8, 9, 18 (api_change context scenarios)
- Verify Finding #73 event type corrected (api_change → other)
- Verify active API announcements still classified as api_change (test case 8)
- Verify passive usage not classified as api_change (test case 9)

**Estimated Time:** 2-3 hours

---

### Alternative: Parallel Implementation (Recommended)

**Fix A + Fix B Together:**
- Both address Phase 10 critical findings
- Independent code changes (different modules)
- Can be implemented in parallel by same developer
- Combined testing after both complete
- Total time: 6-8 hours (parallelized) vs 8-12 hours (sequential)

**Fix C Separately:**
- Lower priority
- Can be deferred to post-launch
- Minimal user impact if delayed

---

## PART 9: PRODUCTION READINESS ASSESSMENT

### Fix A: Competitor Actor Verification

**REQUIRED FOR PRODUCTION:** ✅ **YES**

**Justification:**
- False positives damage credibility and trust
- 33% false positive rate is unacceptable
- Misattribution can mislead business decisions
- Core system integrity issue

**Without Fix A:**
- System produces misleading intelligence
- Manual review burden too high
- Risk of acting on false information

**Production Readiness:** ❌ **BLOCK** without Fix A

---

### Fix B: Intelligence Value Filter

**REQUIRED FOR PRODUCTION:** ⚠️ **STRONGLY RECOMMENDED**

**Justification:**
- 67% low-value finding rate reduces system utility
- Weekly brief with mostly marketing content has low ROI
- Executive time wasted reviewing consumer marketing
- Competitive intelligence value proposition at risk

**Without Fix B:**
- System technically works but delivers low value
- User may lose trust after 2-3 low-quality briefs
- Manual filtering required every week

**Production Readiness:** ⚠️ **SOFT BLOCK** without Fix B (can launch but not recommended)

---

### Fix C: Event Classification Context

**REQUIRED FOR PRODUCTION:** ❌ **NO** (Nice-to-have)

**Justification:**
- Event type accuracy is secondary to content quality
- Incorrect event type doesn't create false positives
- Low user impact (mostly affects categorization, not inclusion)
- Can be improved post-launch

**Without Fix C:**
- Some events misclassified (e.g., api_change instead of other)
- Does not affect finding inclusion/exclusion
- Minor inconvenience, not a blocker

**Production Readiness:** ✅ **OK TO LAUNCH** without Fix C

---

### Minimum Viable Fix Set

**For Production Launch:**
1. ✅ **MUST HAVE:** Fix A (Competitor Actor Verification)
2. ⚠️ **SHOULD HAVE:** Fix B (Intelligence Value Filter)
3. ❌ **OPTIONAL:** Fix C (Event Classification Context)

**Recommended Launch Configuration:**
- Implement Fix A + Fix B before production
- Launch with 2-week evaluation period
- Implement Fix C in v1.1 after initial production validation
- Total implementation time: 8-12 hours

---

## PART 10: POST-IMPLEMENTATION VALIDATION PLAN

### Validation Approach

**Run controlled test with same 7-day window as Phase 10:**
- Same date range: 2026-09-23 to 2026-09-30
- Same sources
- Compare before/after results

### Success Criteria

**Fix A (Actor Verification):**
- ✅ Finding #72 filtered (False positive eliminated)
- ✅ Test case 2, 5, 6, 9, 15, 23 filtered
- ✅ Zero false positives from author bio/footnote mentions
- ✅ All legitimate official source findings preserved

**Fix B (Marketing Filter):**
- ✅ Finding #71 flagged as low priority
- ✅ Finding #73 flagged as low priority
- ✅ Test case 3, 4, 18 flagged or filtered appropriately
- ✅ High-value technical findings not affected

**Fix C (Event Classification):**
- ✅ Finding #73 event type corrected (api_change → other)
- ✅ Test case 8 remains api_change (active context)
- ✅ Test case 9 not classified as api_change (passive context)

### Quality Metrics

**Expected Improvements:**
- False positive rate: 33% → 0-5%
- High-value finding rate: 0% → 50-70%
- Event classification accuracy: 57% → 85-90%
- Requires review rate: 14% → 30-40% (expected increase, better flagging)

### Rollback Triggers

**Trigger rollback if:**
- False negative rate > 15% (legitimate findings filtered)
- All findings require review (> 80%)
- Zero findings produced (over-filtering)
- System crashes or errors on valid articles

---

## PART 11: SUMMARY & RECOMMENDATIONS

### Root Cause Summary

1. **Competitor detection is position-agnostic** - treats author bio same as title
2. **Keyword-based relevance includes marketing language** - can't distinguish technical vs consumer content
3. **Event classification is context-blind** - keyword matching without semantic understanding

### Proposed Architecture

**Three additive, independent fixes:**

**Fix A:** Actor/subject verification layer after competitor detection
- Location: `agents/intelligence_classifier.py`
- New methods: `_calculate_actor_evidence()`, `_verify_competitor_is_actor()`
- Integration: Filter after content-based detection, before finding creation

**Fix B:** Content type classification and priority filtering
- Location: `agents/relevance_scorer.py` + `agents/intelligence_classifier.py`
- New methods: `_detect_content_type()`, `_assign_priority()`
- Integration: Hybrid filter (hard filter for low-priority third-party, flag for low-priority official)

**Fix C:** Action context validation for event classification
- Location: `agents/intelligence_classifier.py`
- New methods: `_detect_action_context()`, `_validate_event_with_context()`
- Integration: Post-process event classification, adjust based on active/passive context

### Minimal Change Set

**Modified Files:**
1. `agents/intelligence_classifier.py` - Add Fix A and Fix C methods
2. `agents/relevance_scorer.py` - Add Fix B content type detection
3. `models/__init__.py` - Add optional fields (priority, content_type, action_context)

**New Files:**
- None (all logic integrated into existing modules)

**Database Changes:**
- None required (new fields have defaults)
- Optional: Add columns for debugging/analytics

**Total Lines of Code:**
- Fix A: ~150 lines (actor verification)
- Fix B: ~100 lines (content type detection)
- Fix C: ~80 lines (context validation)
- Total: ~330 lines

### Test Cases

**25 comprehensive test cases covering:**
- ✅ Competitor as actor vs mentioned
- ✅ Author bio false positives
- ✅ Customer case studies
- ✅ Consumer marketing
- ✅ Comparison articles
- ✅ Partnership announcements
- ✅ API changes vs API usage
- ✅ Official vs third-party sources
- ✅ Multiple competitors
- ✅ Ambiguous articles
- ✅ All event types

### Expected Before/After Behavior

**Phase 10 Findings Corrected:**
- Finding #72: FALSE POSITIVE → FILTERED ✅
- Finding #71: NO FLAG → FLAGGED (low priority) ✅
- Finding #73: WRONG EVENT + NO FLAG → CORRECT EVENT + FLAGGED ✅

**Quality Improvements:**
- False positive rate: 33% → 0-5%
- High-value rate: 0% → 50-70%
- Event accuracy: 57% → 85-90%

### Implementation Risks

**Risk Assessment:**
- False negatives from Fix A: MEDIUM (mitigated by threshold tuning)
- Excessive filtering from Fix B: LOW (hybrid approach, official sources protected)
- Event type instability from Fix C: LOW (improvement, not regression)
- Performance: LOW (< 200ms added latency)
- Regression: VERY LOW (additive changes, feature flags available)

### Recommended Implementation Order

1. **Phase 1 (CRITICAL):** Fix A - Competitor Actor Verification (4-6 hours)
2. **Phase 2 (HIGH):** Fix B - Intelligence Value Filter (4-6 hours)
3. **Phase 3 (MEDIUM):** Fix C - Event Classification Context (2-3 hours)

**Alternative:** Fix A + B in parallel (6-8 hours), then Fix C later

### Production Requirements

**MUST HAVE:**
- ✅ Fix A (blocks false positives)

**SHOULD HAVE:**
- ⚠️ Fix B (delivers value, prevents low-quality briefs)

**NICE TO HAVE:**
- ❌ Fix C (improves accuracy, not blocking)

**Recommended for launch:** Fix A + Fix B  
**Can be deferred:** Fix C (implement in v1.1)

---

## EXPLICIT CONFIRMATION

✅ **NO CODE CHANGES MADE**  
✅ **NO MODIFICATIONS TO FILES**  
✅ **NO COMMITS MADE**  
✅ **NO PUSHES MADE**  
✅ **NO DEPLOYMENTS MADE**  
✅ **NO EMAILS SENT**  
✅ **DESIGN DOCUMENT ONLY**

This is a **READ-ONLY DESIGN** as requested.

---

**Design Document Completed:** 2026-10-05  
**Next Action:** Await explicit authorization to implement Fix A, Fix B, and/or Fix C  
**Estimated Implementation Time:** 10-14 hours total (Fix A: 4-6h, Fix B: 4-6h, Fix C: 2-3h)  
**Recommended Start:** Fix A + Fix B in parallel, then validate before implementing Fix C
