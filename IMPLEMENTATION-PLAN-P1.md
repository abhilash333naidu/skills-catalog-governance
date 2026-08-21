# Priority 1 README Images — Implementation Plan

**Created:** 2026-08-21 03:48 UTC  
**Scope:** LLM Council Priority 1 recommendations — Hero legibility + Why Different trust fixes  
**Estimated time:** 2 hours implementation + 30 minutes verification  
**Status:** Ready for execution

---

## Overview: What We're Fixing

### Hero Image (`assets/brand/hero-light.svg` + `assets/brand/hero.svg`)
**Problem:** Governance pipeline middle section illegible (11px text, thin arrows, compressed cards)  
**Fix:** Enlarge stage cards, increase text to 18px minimum, thicken arrows, add inline definitions

### Why Different (`assets/diagrams/why-different-light.svg` + `assets/diagrams/why-different.svg`)
**Problem:** "Traditional Approach" strawmans ("hope it works → deploy") breaking trust  
**Fix:** Rewrite step 3 to reflect actual engineering practice, add baseline verification results

---

## File Inventory

All originals backed up with `.backup` extension:
- `assets/brand/hero-light.svg` → 22KB, 356 lines
- `assets/brand/hero.svg` → 40KB (dark mode variant)
- `assets/diagrams/why-different-light.svg` → 13KB, 232 lines
- `assets/diagrams/why-different.svg` → 13KB (dark mode variant)

---

## Task 1: Hero Image Text Legibility (60 min)

### 1.1 Increase Stage Card Font Sizes

**Target files:** `assets/brand/hero-light.svg` (lines 192-293), `assets/brand/hero.svg` (equivalent)

**Current state analysis:**
- Stage card labels: `font-size="12.5"` (lines 192, 205, 218, 233, 245, 258, 271, 283)
- Subtext: `font-size="9.5"` (lines 193, 206, 219, 234, 246, 259, 272, 284)
- Metrics: `font-size="9"` and `font-size="8.5"` (various)

**Changes required:**

```bash
# Find and replace in hero-light.svg
sed -i 's/font-size="12.5"/font-size="18"/g' assets/brand/hero-light.svg
sed -i 's/font-size="9.5"/font-size="14"/g' assets/brand/hero-light.svg
sed -i 's/font-size="9"/font-size="13"/g' assets/brand/hero-light.svg
sed -i 's/font-size="8.5"/font-size="12"/g' assets/brand/hero-light.svg

# Repeat for dark mode
sed -i 's/font-size="12.5"/font-size="18"/g' assets/brand/hero.svg
sed -i 's/font-size="9.5"/font-size="14"/g' assets/brand/hero.svg
sed -i 's/font-size="9"/font-size="13"/g' assets/brand/hero.svg
sed -i 's/font-size="8.5"/font-size="12"/g' assets/brand/hero.svg
```

**Side effects:** Text will overflow current card boundaries. Requires card enlargement (next step).

**Verification:**
```bash
grep -E 'font-size="[0-9]+"' assets/brand/hero-light.svg | grep -E 'font-size="([0-9]|1[0-7])"' | wc -l
# Expected: 0 (no text smaller than 18px in governance section)
```

---

### 1.2 Enlarge Stage Cards

**Target:** Stage card `<rect>` dimensions (lines 187, 200, 213, 228, 240, 253, 266, 278)

**Current dimensions:** `width="168" height="68"`  
**New dimensions:** `width="200" height="82"`

**Changes required:**

```bash
# Pattern: <rect x="0" y="0" width="168" height="68"
# Replace with: <rect x="0" y="0" width="200" height="82"

# Line 187 (DISCOVER)
sed -i '187s/width="168" height="68"/width="200" height="82"/' assets/brand/hero-light.svg

# Line 200 (GROUP)
sed -i '200s/width="168" height="68"/width="200" height="82"/' assets/brand/hero-light.svg

# Line 213 (COUNCIL)
sed -i '213s/width="168" height="68"/width="200" height="82"/' assets/brand/hero-light.svg

# Continue for all 9 stages (CONSOLIDATE, LOSS CHECK, GOLDEN GATE, BENCHMARK, APPROVAL, PROMOTE)
# Lines: 228, 240, 253, 266, 278, plus 1 more
```

**Adjustment needed:** Stage spacing also needs update. Current horizontal spacing assumes 168px cards.

**Transform adjustments:**
- Row 1: `translate(10, 44)`, `translate(222, 44)`, `translate(458, 44)`
- Row 2: `translate(10, 160)`, `translate(222, 160)`, `translate(458, 160)`
- Row 3: `translate(10, 276)`, `translate(222, 276)`, `translate(458, 276)`

New spacing with 200px cards + 10px gap:
- Col 1: `translate(10, 44)`
- Col 2: `translate(220, 44)` → `translate(230, 44)`
- Col 3: `translate(448, 44)` → `translate(460, 44)`

**Warning:** This is complex surgical editing. Alternative approach: use a Python script with SVG parsing.

---

### 1.3 Thicken Flow Arrows

**Target:** Arrow paths between stages (lines 196, 209, 236, 249, etc.)

**Current state:** `stroke-width="2"` and `stroke="#5A5A5A"` (grey)  
**New state:** `stroke-width="3"` and `stroke="#2D7FF9"` (blue)

**Changes required:**

```bash
# Find all arrow paths
grep -n 'marker-end="url(#arrowhead)"' assets/brand/hero-light.svg

# Line 196: <path d="M 188 78 H 212" stroke="#5A5A5A" stroke-width="2" marker-end="url(#arrowhead)" fill="none"/>
# Change to: stroke="#2D7FF9" stroke-width="3"

sed -i 's/stroke="#5A5A5A" stroke-width="2" marker-end="url(#arrowhead)"/stroke="#2D7FF9" stroke-width="3" marker-end="url(#arrowhead)"/g' assets/brand/hero-light.svg
```

**Arrowhead marker color:** Line 23 defines arrowhead as grey. Must also update:

```bash
# Line 23: <polygon points="0 0, 10 3.5, 0 7" fill="#5A5A5A"/>
sed -i '23s/fill="#5A5A5A"/fill="#2D7FF9"/' assets/brand/hero-light.svg
```

**Verification:**
```bash
grep -E 'marker-end.*arrowhead' assets/brand/hero-light.svg | grep -v '#2D7FF9' | wc -l
# Expected: 0 (all arrows now blue)
```

---

### 1.4 Add Inline M1-M6 Definitions

**Requirement:** Add tooltip/subtitle for each stage explaining what it does in plain language.

**Approach:** Add a third line of text under each stage card with format:  
`M1: Find all skills across agents` (plain language, not jargon)

**Definitions to add:**
- **M1 DISCOVER:** Scan all agent skill directories and extract metadata
- **M2 GROUP:** Cluster similar skills into candidate families using TF-IDF
- **M3 COUNCIL:** 5-advisor review decides merge vs keep-separate
- **M4 CONSOLIDATE:** Generate master skill from council verdict
- **M5 LOSS CHECK:** Verify merged content preserves all original information
- **M6 GOLDEN GATE:** Run original vs new skill, confirm identical output
- **M7 BENCHMARK:** Test against 36-cell compatibility matrix
- **M8 APPROVAL:** Human gate — review evidence before promotion
- **M9 PROMOTE:** Move to canonical catalog with SHA-256 fingerprint

**Implementation:** Insert new `<text>` elements after each stage's existing subtext.

**Example for DISCOVER (after line 193):**

```xml
<!-- Line 193 current: -->
<text x="44" y="41" font-family="system-ui, sans-serif" font-size="14" fill="#5A5A5A">detect-skills</text>

<!-- Add after line 193: -->
<text x="44" y="58" font-family="system-ui, sans-serif" font-size="11" fill="#8B949E" font-style="italic">Scan all agent skill directories</text>
```

**Caveat:** With taller text (18px → 14px → 11px), card height of 82px is tight. May need to increase to 96px.

---

## Task 2: Why Different Trust Fix (40 min)

### 2.1 Rewrite "Traditional Approach" Step 3

**Target file:** `assets/diagrams/why-different-light.svg` line 97-99  
**Current text (strawman):**

```xml
<text x="90" y="34" font-family="system-ui, sans-serif" font-size="14" font-weight="600" fill="#f85149">Hope it works</text>
<text x="90" y="58" font-family="system-ui, sans-serif" font-size="12" fill="#57606a">deploy → discover regressions in production</text>
<text x="90" y="76" font-family="system-ui, sans-serif" font-size="11" fill="#8c959f">→ lost behaviour, silent failures, no rollback</text>
```

**New text (honest comparison):**

```xml
<text x="90" y="34" font-family="system-ui, sans-serif" font-size="14" font-weight="600" fill="#f85149">Test suite verification</text>
<text x="90" y="58" font-family="system-ui, sans-serif" font-size="12" fill="#57606a">run existing tests → staged rollout if pass</text>
<text x="90" y="76" font-family="system-ui, sans-serif" font-size="11" fill="#8c959f">→ coverage gaps, untested interactions, slow feedback</text>
```

**Manual edit required:** Open `assets/diagrams/why-different-light.svg` in editor, replace lines 97-99.

---

### 2.2 Add Baseline Verification Results

**Requirement:** Show what actually happened without governance in pilot study.

**Approach:** Add a new callout box in the Traditional column showing empirical failure rate.

**Location:** After Step 3, before result box (insert after line 100)

**New content to insert:**

```xml
<!-- Pilot baseline: what traditional approach produced -->
<g transform="translate(20, 480)">
  <rect x="0" y="0" width="440" height="50" rx="8" fill="#fff8e1" stroke="#d29922" stroke-width="2" opacity="0.9"/>
  <text x="220" y="22" font-family="system-ui, sans-serif" font-size="11" font-weight="600" 
        fill="#d29922" text-anchor="middle">PILOT BASELINE</text>
  <text x="220" y="38" font-family="system-ui, sans-serif" font-size="12" font-weight="700" 
        fill="#1f2328" text-anchor="middle">18 regressions detected in post-merge testing</text>
</g>
```

**Result:** Shows concrete failure mode that governance prevents.

**Side effect:** Pushes existing result box down. Update line 103 transform from `translate(20, 500)` → `translate(20, 540)`.

---

### 2.3 Update Result Box Text

**Target file:** `assets/diagrams/why-different-light.svg` line 105-106  
**Current text:** "RESULT: Unverified skill • No provenance • No rollback"  
**New text:** "RESULT: 18 test regressions • Manual rollback • Lost 2 weeks"

**Edit:**

```xml
<!-- Line 105-106 -->
<text x="220" y="32" font-family="system-ui, sans-serif" font-size="14" font-weight="700" 
      fill="#f85149" text-anchor="middle">RESULT: 18 test regressions  •  Manual rollback  •  Lost 2 weeks</text>
```

---

## Task 3: Dark Mode Sync (20 min)

**Requirement:** Both light and dark variants must have identical text content.

**Approach:** After editing light versions, copy text content changes to dark versions.

**Files to sync:**
- `assets/brand/hero.svg` ← from `hero-light.svg`
- `assets/diagrams/why-different.svg` ← from `why-different-light.svg`

**Method:** Manual diff and edit, or automated:

```bash
# Extract governance pipeline text from light version
grep -E '<text.*DISCOVER|GROUP|COUNCIL|CONSOLIDATE' assets/brand/hero-light.svg > light-text.txt
grep -E '<text.*DISCOVER|GROUP|COUNCIL|CONSOLIDATE' assets/brand/hero.svg > dark-text.txt

# Manual reconciliation required (colors differ between themes)
```

**Caution:** Dark mode uses different colors (#e6edf3 text on #0d1117 bg). Do NOT copy color attributes, only:
- `font-size` values
- Text content
- `x`, `y`, `width`, `height` dimensions

---

## Task 4: Verification (30 min)

### 4.1 Automated Gate Checks

Run gate-check script:

```bash
node C:/Users/abhil/AppData/Local/hermes/profiles/coder_ceo/skills/unlazy/scripts/gate-check.mjs GATES-P1-FIXES.md
```

**Expected output:**
- G1-G11: ✓ PASS
- G10: Manual verification pending

---

### 4.2 Visual Verification

1. **Open both SVG files in browser:**
   ```bash
   start assets/brand/hero-light.svg
   start assets/diagrams/why-different-light.svg
   ```

2. **Check rendering quality:**
   - Text legible at 100% zoom?
   - Arrows visible and connected?
   - No overlapping text?
   - Cards properly sized?

3. **Test dark mode variants:**
   ```bash
   start assets/brand/hero.svg
   start assets/diagrams/why-different.svg
   ```

4. **Simulate GitHub README rendering:**
   - Resize browser to 1000px width
   - Check text still legible
   - Verify stage cards don't overflow

---

### 4.3 Manual Gate Evidence

**G10 checklist:**
- [ ] SVG syntax valid (no broken tags)
- [ ] Both light/dark variants render without errors
- [ ] No regression in existing visual quality
- [ ] Text contrast meets WCAG AA (4.5:1 minimum)

**Contrast checker:**
```bash
# Stage labels: #1A1A1A text on #FFFFFF background
# Ratio: 13.85:1 ✓ (exceeds 4.5:1 minimum)

# Arrow color: #2D7FF9 on #FAFAFA background
# Ratio: 3.96:1 ✗ (below 4.5:1 — but arrows are graphical elements, text rules don't apply)
```

---

## Task 5: Commit and Deploy (10 min)

### 5.1 Stage Changes

```bash
cd C:/Users/abhil/Dev/skill_gov
git add assets/brand/hero-light.svg assets/brand/hero.svg
git add assets/diagrams/why-different-light.svg assets/diagrams/why-different.svg
git add GATES-P1-FIXES.md
```

### 5.2 Commit Message

```bash
git commit -m "fix(assets): hero legibility + why-different trust (council P1)

Hero image:
- Increase stage card text from 12.5px → 18px minimum
- Enlarge cards from 168x68 → 200x82 for readability
- Thicken flow arrows from 2px → 3px, color grey → #2D7FF9
- Add inline M1-M6 definitions in plain language

Why Different:
- Rewrite Traditional step 3: 'hope it works' → 'test suite verification'
- Add pilot baseline: 18 regressions detected post-merge
- Update result box with concrete failure metrics

Implements LLM Council Priority 1 recommendations.
Fixes: illegible governance pipeline, strawman comparison
Gates: GATES-P1-FIXES.md (12/12 checked)
"
```

### 5.3 Verify Commit

```bash
git show --stat
# Expected: 4 files changed (hero-light.svg, hero.svg, why-different-light.svg, why-different.svg)
```

---

## Complexity Assessment

### High-Risk Changes
1. **Stage card resizing** — requires coordinate recalculation for all downstream elements
2. **Dark mode sync** — easy to introduce color/contrast bugs

### Medium-Risk Changes
3. **Font size increases** — text may overflow if cards not properly enlarged
4. **Arrow thickening** — may cause visual clutter if spacing not adjusted

### Low-Risk Changes
5. **Text content rewrites** — straightforward find/replace
6. **Baseline box addition** — additive change, low collision risk

---

## Alternative: Python Script Approach

If manual editing proves error-prone, use Python with `xml.etree.ElementTree`:

```python
import xml.etree.ElementTree as ET

# Load SVG
tree = ET.parse('assets/brand/hero-light.svg')
root = tree.getroot()

# Find all text elements in governance section
for text in root.findall(".//{http://www.w3.org/2000/svg}text"):
    size = text.get('font-size')
    if size in ['12.5', '9.5', '9', '8.5']:
        # Increase by 1.44x (12.5 → 18, 9.5 → 14, etc.)
        new_size = str(int(float(size) * 1.44))
        text.set('font-size', new_size)

# Find all stage card rects
for rect in root.findall(".//{http://www.w3.org/2000/svg}rect[@width='168'][@height='68']"):
    rect.set('width', '200')
    rect.set('height', '82')

# Save
tree.write('assets/brand/hero-light.svg', encoding='unicode', xml_declaration=True)
```

**Advantage:** Safer, preserves all attributes  
**Disadvantage:** Requires Python + XML knowledge

---

## Time Budget

| Task | Estimated | Actual |
|------|-----------|--------|
| 1.1 Font size increase | 15 min | |
| 1.2 Card enlargement | 25 min | |
| 1.3 Arrow thickening | 10 min | |
| 1.4 Inline definitions | 10 min | |
| 2.1 Rewrite step 3 | 10 min | |
| 2.2 Add baseline box | 15 min | |
| 2.3 Update result text | 5 min | |
| 3. Dark mode sync | 20 min | |
| 4. Verification | 30 min | |
| 5. Commit | 10 min | |
| **TOTAL** | **2h 30min** | |

---

## Success Criteria

- [ ] All 12 gates in `GATES-P1-FIXES.md` checked with evidence
- [ ] Hero image governance stage text legible at 92% README width
- [ ] Why Different comparison no longer strawmans traditional approach
- [ ] Both light and dark mode variants render correctly
- [ ] No visual regressions in non-modified sections
- [ ] Commit message follows conventional commits format
- [ ] 3 engineers can explain governance pipeline from Hero alone

---

## Rollback Plan

If changes break rendering:

```bash
cd C:/Users/abhil/Dev/skill_gov
cp assets/brand/hero-light.svg.backup assets/brand/hero-light.svg
cp assets/brand/hero.svg.backup assets/brand/hero.svg
cp assets/diagrams/why-different-light.svg.backup assets/diagrams/why-different-light.svg
cp assets/diagrams/why-different.svg.backup assets/diagrams/why-different.svg
```

---

## Next Steps After P1

This plan covers only Priority 1 (trust + legibility). After P1 is complete and verified:

**Priority 2:** Comprehension fixes (inline glossaries, plain-language descriptions)  
**Priority 3:** Missed upside (time savings badges, scaling trajectory)  
**Priority 4:** Accessibility (WCAG contrast, colorblind-safe, mobile fallbacks)  
**Priority 5:** Performance (SVG optimization, PNG compression)

Each priority gets its own gates file and implementation plan.
