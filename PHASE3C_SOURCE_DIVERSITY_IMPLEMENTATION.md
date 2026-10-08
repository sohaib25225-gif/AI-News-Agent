# PHASE 3C: SOURCE DIVERSITY IMPROVEMENT

**Date:** 2026-08-27  
**Status:** READY FOR REVIEW  
**Type:** Optimization/Improvement

---

## 1. PROBLEM STATEMENT

### Production Observation

Latest successful workflow run (commit fb50497):
- **Total articles:** 372
- **Source distribution:**
  - arXiv AI: 352 (94.6%)
  - All other sources: 20 (5.4%)
- **Top 5 candidates:** ALL from arXiv AI
- **Diversity selection result:** "3 candidates from 1 sources"

### Issue

Despite Phase 3A diversity mechanism being active, source diversity is **insufficient**. The system still selects only arXiv articles even though other credible sources publish relevant content.

---

## 2. ROOT CAUSE ANALYSIS

### Diagnostic Findings

Comprehensive diagnostic revealed:

**Source Distribution:**
```
arXiv AI:                352 articles (94.88%)  Top score: 78.0  Avg: 47.4
TechCrunch AI:             8 articles (2.16%)   Top score: 26.5  Avg: 16.9
AWS ML Blog:               7 articles (1.89%)   Top score: 36.0  Avg: 23.6
NVIDIA Blog:               1 article  (0.27%)   Top score: 26.0  Avg: 26.0
GitHub Blog:               1 article  (0.27%)   Top score: 27.0  Avg: 27.0
MIT Tech Review:           1 article  (0.27%)   Top score: 31.0  Avg: 31.0
DeepMind Blog:             1 article  (0.27%)   Top score: 16.0  Avg: 16.0
```

**Critical Discovery:**
- **First non-arXiv article appears at rank 316** (AWS ML Blog, score 36.0)
- Top 50 ranked articles: **ALL from arXiv AI**
- Quality gap: Top arXiv (78.0) vs Top non-arXiv (36.0) = **42 points (53.8%)**

**Why Phase 3A Approach Failed:**

Phase 3A used `top_n` + `max_per_source`:
- `DIVERSITY_TOP_N=10` → Consider top 10 ranked articles
- `DIVERSITY_MAX_PER_SOURCE=3` → Max 3 per source

**Problem:** When 95% of articles are from one source AND that source dominates quality rankings, ALL top-N articles are from that source.

- `top_n=10` → 10 arXiv articles → limit to 3 → Result: 3 arXiv
- `top_n=20` → 20 arXiv articles → limit to 3 → Result: 3 arXiv
- `top_n=50` → 50 arXiv articles → limit to 3 → Result: 3 arXiv
- `top_n=320` → First non-arXiv appears → But quality drops to 36

**Conclusion:** The `top_n` approach **cannot solve extreme volume imbalance** (95% single source) combined with quality correlation.

---

## 3. SOLUTION DESIGN

### Selected Approach: Per-Source + Quality Threshold

**Algorithm:**
1. Score all articles (unchanged)
2. Group articles by source
3. Select **best article from each source**
4. Filter by **minimum quality threshold**
5. Sort filtered candidates by score (preserve quality)
6. Select highest-scoring candidate for posting

**Key Principles:**
- ✅ **Quality-first:** Threshold filters weak articles
- ✅ **Source fairness:** Each source gets representation opportunity
- ✅ **Preserves scoring:** No score modifications
- ✅ **Deterministic:** No randomness
- ✅ **Simple:** Easy to understand and explain

### Why This Approach?

**Compared to alternatives:**

| Approach | Diversity | Quality | Simplicity | Verdict |
|----------|-----------|---------|------------|---------|
| Expand top_n | ❌ Fails | ✅ Yes | ✅ Simple | **Fails - doesn't work** |
| Quality bands | ⚠️ Limited | ✅ Yes | ❌ Complex | **Overkill** |
| **Per-source + threshold** | ✅ **Excellent** | ✅ **Yes** | ✅ **Simple** | **✅ SELECTED** |

**Evidence from testing:**

With threshold=25:
- **6 sources** represented (vs 1 before)
- **Quality preserved:** Best article still selected (score 78.0)
- **Weak articles filtered:** DeepMind (16.0) excluded
- **Practical articles included:** AWS SageMaker (36.0), GitHub Copilot (27.0)

---

## 4. IMPLEMENTATION

### Configuration Changes

**File:** `config/__init__.py`

**Add:**
```python
# Source Diversity - Quality Threshold
DIVERSITY_QUALITY_THRESHOLD: int = int(os.getenv("DIVERSITY_QUALITY_THRESHOLD", "25"))
```

**Modify:**
```python
# DEPRECATED: Phase 3A parameters (kept for backward compatibility)
DIVERSITY_TOP_N: int = int(os.getenv("DIVERSITY_TOP_N", "10"))
DIVERSITY_MAX_PER_SOURCE: int = int(os.getenv("DIVERSITY_MAX_PER_SOURCE", "3"))
```

### Algorithm Changes

**File:** `agents/news_scorer.py`

**Method:** `select_diverse_candidates()`

**Strategy:** Replace top-N algorithm with per-source + threshold algorithm

**Before (Phase 3A):**
```python
def select_diverse_candidates(ranked_articles, top_n=10, max_per_source=3):
    candidates_to_consider = ranked_articles[:top_n]
    source_counts = {}
    diverse_candidates = []
    
    for article in candidates_to_consider:
        source = article.source or "Unknown"
        if source_counts.get(source, 0) < max_per_source:
            diverse_candidates.append(article)
            source_counts[source] += 1
    
    return diverse_candidates
```

**After (Phase 3C):**
```python
def select_diverse_candidates(ranked_articles, quality_threshold=None):
    """
    Select diverse candidates using per-source best + quality threshold.
    
    This approach ensures source diversity even when one source (e.g., arXiv)
    dominates both volume (95%) and top rankings.
    
    Algorithm:
    1. Group articles by source
    2. Select best article from each source
    3. Filter by minimum quality threshold
    4. Sort by score and return
    
    Args:
        ranked_articles: Articles already scored and ranked
        quality_threshold: Minimum score required (default from config)
    
    Returns:
        List of diverse candidates sorted by score (highest first)
    """
    quality_threshold = quality_threshold if quality_threshold is not None else config.DIVERSITY_QUALITY_THRESHOLD
    
    if not ranked_articles:
        return []
    
    # Group by source, preserving best article (first in ranked list)
    source_best = {}
    for article in ranked_articles:
        source = article.source if article.source else "Unknown"
        if source not in source_best:
            source_best[source] = article
    
    # Filter by quality threshold
    candidates = [
        article for article in source_best.values()
        if article.score >= quality_threshold
    ]
    
    # Sort by score (highest first) to preserve quality ranking
    candidates.sort(key=lambda x: x.score, reverse=True)
    
    logger.info(f"Diversity selection: {len(candidates)} candidates from {len(candidates)} sources")
    
    return candidates
```

**Changes:**
- Remove `top_n` and `max_per_source` parameters (deprecated)
- Add `quality_threshold` parameter
- Use dict to track best per source
- Filter by threshold
- Simpler, more direct logic

### No Changes To:
- ✅ Scoring algorithm (weights, keywords, formulas)
- ✅ Main pipeline orchestration
- ✅ Gemini integration
- ✅ Email service
- ✅ Database schema/persistence
- ✅ RSS fetching
- ✅ Workflow configuration

---

## 5. CONFIGURATION VALUES

### Recommended Default

```python
DIVERSITY_QUALITY_THRESHOLD = 25
```

**Rationale:**
- **Threshold 25** filters out weak articles (DeepMind: 16)
- Includes practical content (AWS: 36, GitHub: 27, TechCrunch: 26.5, NVIDIA: 26)
- Balances quality and diversity
- Based on empirical testing with production data

### Tuning Guidelines

**If too few sources represented:**
```bash
export DIVERSITY_QUALITY_THRESHOLD=20  # More permissive
```

**If quality concerns:**
```bash
export DIVERSITY_QUALITY_THRESHOLD=30  # More strict
```

**Monitor:** Source diversity in selected articles over time

---

## 6. BEFORE vs AFTER

### Production Data (372 articles, 352 arXiv)

**BEFORE (Phase 3A - top_n approach):**
```
Top 10 ranked articles:
1. [78.0] arXiv AI
2. [75.5] arXiv AI
3. [75.5] arXiv AI
4. [75.0] arXiv AI
5. [71.5] arXiv AI
6. [71.0] arXiv AI
7. [71.0] arXiv AI
8. [71.0] arXiv AI
9. [71.0] arXiv AI
10. [70.5] arXiv AI

Diverse candidates: 3 from 1 source
- arXiv AI: 3

Selected: arXiv AI (78.0)
```

**AFTER (Phase 3C - per-source approach):**
```
Best from each source:
1. [78.0] arXiv AI - "Robust Code RL via Faulty-Code-Driven..."
2. [36.0] AWS ML Blog - "Bring your own model with Amazon SageMaker AI..."
3. [31.0] MIT Technology Review AI - "Is Slate Auto's new electric truck..."
4. [27.0] GitHub Blog - "GitHub Copilot app for Beginners..."
5. [26.5] TechCrunch AI - "Radar makes podcasts searchable..."
6. [26.0] NVIDIA Blog - "NVIDIA NVLink Fusion Expands..."
(DeepMind: 16.0 - filtered by threshold)

Diverse candidates: 6 from 6 sources
- arXiv AI: 1
- AWS ML Blog: 1
- MIT Technology Review: 1
- GitHub Blog: 1
- TechCrunch AI: 1
- NVIDIA Blog: 1

Selected: arXiv AI (78.0) - still best quality
```

### Impact

**Source Diversity:**
- Before: 1 source represented
- After: **6 sources represented** (6x improvement)

**Quality Preservation:**
- Best article still selected (78.0 score)
- Weak articles still filtered (threshold 25)

**Practical Relevance:**
- Developer-focused content now eligible (AWS SageMaker, GitHub Copilot)
- News/product announcements now eligible (TechCrunch, NVIDIA)

---

## 7. TESTING STRATEGY

### Existing Tests (Modified)

Update `tests/test_scoring.py` diversity tests:
- Modify to test per-source + threshold approach
- Remove top_n/max_per_source parameters
- Add quality_threshold parameter
- Ensure all edge cases still covered

### Test Scenarios

**1. One source dominates (current production case)**
```
Expected: Top from each source meeting threshold
Result: Multiple sources represented ✅
```

**2. High quality gap (arXiv 78 vs others 26-36)**
```
Expected: All meeting threshold included, best selected
Result: 6 sources, arXiv selected ✅
```

**3. All sources have poor articles**
```
Expected: Only those >= threshold
Result: Filters correctly ✅
```

**4. Single source only**
```
Expected: Returns that source if >= threshold
Result: Works ✅
```

**5. Empty list**
```
Expected: Returns empty list
Result: Handles gracefully ✅
```

**6. Determinism**
```
Expected: Same input = same output
Result: No randomness, deterministic ✅
```

---

## 8. RISKS & MITIGATION

### Risk 1: Quality Reduction

**Risk:** Selecting articles with scores 25-36 instead of 70-78

**Mitigation:**
- Final selection still chooses **highest score** from candidate pool
- In current data, arXiv (78.0) still wins
- Only affects selection if no arXiv articles meet criteria (rare)
- Threshold 25 filters truly weak articles (DeepMind: 16)

**Severity:** LOW (quality-conscious by design)

### Risk 2: Threshold Tuning Needed

**Risk:** Threshold 25 may not work for all future distributions

**Mitigation:**
- Configurable via environment variable
- Monitor source diversity metrics
- Adjust threshold based on production data
- No code changes needed for tuning

**Severity:** LOW (configuration-only)

### Risk 3: Breaking Existing Tests

**Risk:** Phase 3A tests expect top_n/max_per_source behavior

**Mitigation:**
- Update tests to match new algorithm
- Ensure all edge cases still covered
- Run full test suite before commit

**Severity:** MEDIUM (requires careful test updates)

---

## 9. LIMITATIONS

1. **Scoring system unchanged:**
   - Research papers still score higher than blogs
   - Keyword-based scoring may miss practical value
   - Future: Consider category-aware scoring adjustments

2. **One article per source:**
   - If a source publishes 10 great articles, only best is considered
   - Acceptable trade-off for diversity

3. **Threshold is global:**
   - Same threshold for all sources
   - Future: Per-category thresholds?

4. **Still quality-first:**
   - If arXiv has best article, it will be selected
   - Diversity affects candidate pool, not final selection
   - This is by design (quality preservation)

---

## 10. FUTURE IMPROVEMENTS

### Short-term (No Code Changes)
1. Monitor production source diversity
2. Tune threshold based on results
3. Track if non-arXiv articles ever win

### Medium-term (Minor Changes)
1. **Category-aware selection:**
   - Reserve candidate slot for each category (company, news, research, developer)
   - Ensures at least one "company" article if it meets threshold

2. **Adaptive threshold:**
   - Calculate threshold as % of top score (e.g., within 50% of best)
   - More dynamic than fixed value

3. **Source credibility boost:**
   - Slightly boost scores for company blogs (OpenAI, DeepMind, Google AI)
   - Helps them compete with research papers

### Long-term (Significant Changes)
1. **User feedback loop:**
   - Track which selected articles user finds valuable
   - Adjust scoring weights based on feedback

2. **Category-specific scoring:**
   - Different weights for company/news/research/developer categories
   - More nuanced than current global weights

---

## 11. SUCCESS CRITERIA

Phase 3C succeeds if:

1. ✅ **Source diversity increases**
   - Before: 1 source
   - After: 4-6 sources (depending on threshold)

2. ✅ **Quality preserved**
   - Threshold filters weak articles
   - Best article from pool still selected

3. ✅ **Deterministic behavior**
   - No randomness
   - Reproducible results

4. ✅ **Tests pass**
   - All existing tests updated and passing
   - New test scenarios covered

5. ✅ **Production stable**
   - No regressions in workflow
   - No errors in article selection

6. ✅ **Minimal changes**
   - One config parameter added
   - One method modified
   - No changes to scoring, database, workflow, Gemini, email

---

## 12. DEPLOYMENT PLAN

### Phase 1: Implementation
1. Add `DIVERSITY_QUALITY_THRESHOLD` to config
2. Modify `select_diverse_candidates()` method
3. Update diversity tests
4. Run full test suite
5. Verify no regressions

### Phase 2: Testing
1. Run diagnostic scripts
2. Verify 6 sources represented
3. Verify quality threshold works
4. Check determinism
5. Validate edge cases

### Phase 3: Review
1. Git diff review
2. Verify only intended files changed
3. Confirm no secrets/credentials
4. Await approval

### Phase 4: Deployment (After Approval)
1. Commit with descriptive message
2. Push to origin/main
3. Monitor next workflow run
4. Track source diversity in results

### Phase 5: Monitoring (Post-Deploy)
1. Check next 5-7 workflow runs
2. Track source distribution
3. Verify no errors
4. Tune threshold if needed

---

## SUMMARY

### Problem
Phase 3A diversity mechanism insufficient when one source (arXiv) has both volume dominance (95%) and quality dominance (top 300+ articles).

### Root Cause
`top_n` approach cannot work when ALL top-N articles are from single source due to extreme volume imbalance.

### Solution
Per-source + quality threshold approach:
- Take best from each source
- Filter by quality threshold (25)
- Sort by score and select best

### Impact
- **6x improvement** in source diversity (1 → 6 sources)
- **Quality preserved** (best article still selected)
- **Practical content included** (AWS, GitHub, TechCrunch, NVIDIA)

### Changes
- Config: Add `DIVERSITY_QUALITY_THRESHOLD=25`
- Code: Modify `select_diverse_candidates()` algorithm
- Tests: Update diversity tests

### Status
**READY FOR REVIEW**
- Implementation complete
- Tests passing
- Diagnostic validation successful
- Awaiting approval before commit

---

**End of Phase 3C Implementation Report**
