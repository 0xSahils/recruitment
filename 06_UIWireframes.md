# UI Wireframes Document
Text-based wireframes. Each page maps directly to the API contracts in `05_APIContracts.md`.

---

## Page 1 — Login

```
┌─────────────────────────────────────┐
│        [Company Logo]                │
│   AI Recruitment Intelligence         │
│                                        │
│   Email     [______________]          │
│   Password  [______________]          │
│                                        │
│            [ Log In ]                 │
└─────────────────────────────────────┘
```
Single hardcoded recruiter account for beta. Session cookie on success → redirect to Dashboard.

---

## Page 2 — Dashboard (primary page, most time should go here)

```
┌──────────────────────────────────────────────────────────────┐
│ [Logo]   Dashboard   Upload   Candidates            [Profile▾]│
├──────────────────────────────────────────────────────────────┤
│                                                                  │
│  Search by Job Description or natural language                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Paste JD or type: "React developers in Bangalore        │    │
│  │ with AWS and 5+ years"                                  │    │
│  │                                                            │    │
│  └────────────────────────────────────────────────────────┘    │
│                                    [ Find Best Candidates → ]   │
│                                                                  │
│  ── after search runs ──                                       │
│                                                                  │
│  Filter:  [All] [New] [Contacted] [Interview] [Rejected] [Hired]│
│  Found 14 candidates              [ Export Shortlist ↓ ]        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ #1  Priyanshu Bansal                          87% match   │  │
│  │     Software Engineer @ WheelsEye · Gurugram               │  │
│  │     ✓ React, AWS in skills                                 │  │
│  │     ✓ 3 yrs as Software Engineer — close role match         │  │
│  │     ✓ 5.5 yrs total experience meets requirement             │  │
│  │     Status: [New ▾]                    [ View Profile → ]  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ #2  Yamini Sharma                              81% match   │  │
│  │     ... (same card shape, repeated)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────┘
```

**Card behavior notes:**
- Match score shown prominently (not buried) — large, colored (green 80+, amber 60–79, gray <60)
- Match explanation always visible, not hidden behind a click — this is the trust-building feature, don't make recruiters dig for it
- Status dropdown inline on the card — changing it should not require opening the full profile
- If `extraction_confidence < 0.6` for a candidate, show a small amber warning icon next to their name: "⚠ Review recommended"

---

## Page 3 — Upload

```
┌──────────────────────────────────────────────────────────────┐
│ [Logo]   Dashboard   Upload   Candidates            [Profile▾]│
├──────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐  │
│   │                                                            │  │
│   │     Drop LinkedIn PDFs here or click to browse            │  │
│   │              (accepts multiple files, .pdf only)           │  │
│   │                                                            │  │
│   └────────────────────────────────────────────────────────┘  │
│                                                                  │
│   Queue (100 files)                                             │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │ priyanshu_bansal.pdf        ✓ Parsed   New candidate       │ │
│   │ yamini_sharma.pdf           ✓ Parsed   Updated (v2)        │ │
│   │ broken_file.pdf             ✗ Failed   No text layer found │ │
│   │ rahul_kumar.pdf             ⏳ Processing...                │ │
│   │ ... (98 more)                                                │ │
│   └──────────────────────────────────────────────────────────┘ │
│                                                                  │
│   Progress: ████████████████░░░░  64/100 processed              │
│   ✓ 61 new · ✓ 3 updated · ✗ 3 failed                            │
│                                                                  │
└──────────────────────────────────────────────────────────────┘
```

**Behavior notes:**
- Poll `GET /upload/{batch_id}/status` every 2 seconds while processing
- "Updated (v2)" label is important — it's the visible proof the re-upload logic works, show it don't hide it
- Failed files show the reason inline, with a "Retry" button per file

---

## Page 4 — Candidate Profile

```
┌──────────────────────────────────────────────────────────────┐
│ [Logo]   Dashboard   Upload   Candidates            [Profile▾]│
├──────────────────────────────────────────────────────────────┤
│  ← Back to Results                                              │
│                                                                  │
│  Priyanshu Bansal                          [Edit ✎]              │
│  Software Engineer @ WheelsEye                                  │
│  📍 Gurugram, Haryana, India     🔗 linkedin.com/in/priyanshu... │
│  Status: [New ▾]            Version 2  ·  Last updated 12 Aug   │
│                                                                  │
│  ┌─ About ─────────────────────────────────────────────────┐   │
│  │ (editable text block)                                      │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ Experience ───────────────────────────────────────────┐   │
│  │ Software Engineer · WheelsEye                              │   │
│  │ June 2026 – Present                                         │   │
│  │ (description, editable)                          [Edit][×] │   │
│  │                                          [+ Add Experience] │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ Education ────────────────────────────────────────────┐   │
│  │ (same pattern as Experience)                                │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ Skills ───────────────────────────────────────────────┐   │
│  │ [React] [Node.js] [MongoDB] [Express.js]   [+ Add Skill]   │   │
│  │ Originally listed as: "MERN"                                │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ Notes ────────────────────────────────────────────────┐   │
│  │ 15 June — Called, interested, salary expectation ₹18L      │   │
│  │ [+ Add Note]                                                │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ Version History ──────────────────────────────────────┐   │
│  │ Version 2 — 12 Aug 2026                                     │   │
│  │   + Added Software Engineer role                            │   │
│  │   + Added AWS skill                                         │   │
│  │   ~ Updated location                                        │   │
│  │ Version 1 — 1 June 2026                                     │   │
│  │   Initial profile creation                                  │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [📄 View Original PDF]                                          │
└──────────────────────────────────────────────────────────────┘
```

**Behavior notes:**
- Every field is click-to-edit, auto-saves on blur (calls `PATCH /candidates/{id}`)
- Version History is collapsed by default if more than 3 versions exist, expandable
- "View Original PDF" opens the source file — always available, this is the future-proofing payoff

---

## Page 5 — Candidates List (browse all, not just search results)

```
┌──────────────────────────────────────────────────────────────┐
│ [Logo]   Dashboard   Upload   Candidates            [Profile▾]│
├──────────────────────────────────────────────────────────────┤
│  All Candidates (412)                                            │
│  Filter: Status[▾] Location[▾] Skill[▾]      [Export ↓]         │
│                                                                  │
│  ┌─────────────┬──────────────┬───────────┬─────────┬────────┐ │
│  │ Name         │ Headline      │ Location   │ Status  │ Updated│ │
│  ├─────────────┼──────────────┼───────────┼─────────┼────────┤ │
│  │ Priyanshu B. │ SWE @ Wheels..│ Gurugram   │ New     │ 12 Aug │ │
│  │ Yamini S.    │ ...           │ ...        │ Shortl..│ ...    │ │
│  │ ... (sortable, paginated table — TanStack Table)             │ │
│  └─────────────┴──────────────┴───────────┴─────────┴────────┘ │
└──────────────────────────────────────────────────────────────┘
```
Standard sortable/filterable table. This page is for browsing the full database independent of a JD search — recruiters will use this to do general housekeeping (status updates, finding a specific person by name).
