# Structural evidence implementation plan

> **For agentic workers:** Use executing-plans and the named SBS skill for each task; construction/refinement uses skill-creator-z, independent review uses SK09. Execution already authorized by the mission.

**Goal:** Make the before/after evidence include final provisions and correctly associated editorial notes, without replacing original text.

**Architecture:** Retain immutable raw text and contiguous citation spans. Add separately cited notes, explicit links and recoverable excluded ranges in the structural sidecar. Comparison uses a derived view with a reversible mapping; raw citations remain authoritative.

**Tech Stack:** Existing Python extraction, contracts and comparison; no new model or remote service.

**Spec:** `docs/12-spec-agente-v0.2.md`; observed failures in `runs/sk09-structure-019-astra-review.json` and `runs/sk09-structure-019-review.json`.

## Global constraints

- Preserve all019 predictions, originals and reference006. Subsequent refinement is exposed development, not a new holdout.
- Every construction and review begins with its skill invocation and hashes. Skills remain provisional unless their own behavioral evidence supports more.
- No inferred legal effect from repository versions; no human approval requirement for conversation.
- No cloud/inference/production publication during this local increment. New embedding inputs remain pending until vectors are available under an authorized configuration.

## Review focus

1. A sentence starting “disposiciones” must not truncate an article: task1 regression.
2. A final provision with two paragraphs must retain both: task2.
3. A note physically inside the next article must not acquire that article's ownership: task3.
4. An ambiguous marker must remain unresolved and citable, not disappear: task3.
5. A derived display string must not be presented as a contiguous verbatim quote: task4.

## Task1 — close019 defects, SK02

- [ ] Preserve and reproduce ST19-01/02/03 and AstraF2; fix index boundaries, complete unique parent citations, compatible instrument identity and sentence/header distinction.
- [ ] Run `PYTHONPATH=src .venv/bin/python -m pytest tests/unit/test_foundation_structure.py tests/unit/test_foundation.py tests/unit/test_comparison.py -q` plus independent probes; freeze new record and obtain SK09 resolution.

## Task2 — complete structural classes, SK02

Files: `src/sbs/foundation/structure.py`, `tests/unit/test_foundation_structure.py`, SK02 reference. Keep `structuralize(raw_bundle)` and its compatible Provision outputs.

- [ ] Add RED cases for final-provision headings within an explicit final-disposition section, ordinal resolution articles with a separate scope, and identical labels in different sections. No fixed4036 offsets in production code.
- [ ] Preserve exact span boundaries, section identity and pages. Segment the Second Final Provision in both4036 copies including its added paragraph; distinguish unavailable external annexes from available but unsegmented text.
- [ ] Represent excluded intervals with start/end/pages/reason so consumers can recover raw evidence. Do not claim complete legal coverage.
- [ ] Freeze predictions and verify exact citations and section isolation on4036 and a different already captured document. SK09 checks against006 as exposed regression, not acceptance.

## Task3 — editorial note ownership, SK02

Files: new `src/sbs/foundation/structure_notes.py`, tests `tests/unit/test_structure_notes.py`; connect through the structural sidecar.

Interface: `extract_note_links(raw_bundle, structural_bundle) -> dict` with `notes`, `links`, `unresolved` and `version`. Each note has an independent contiguous citation, marker, pages and raw offsets. Each link identifies a note citation, candidate owner provision and exact marker span; status is `unique_textual_match` or `unresolved`, never legal verification.

- [ ] RED: notes8/9 on the4036 page link to14.1/14.2 rather than15; note10 remains discoverable and links to15.2(h) when a unique marker supports it.
- [ ] RED variants: repeated numbering in another section, missing marker, ordinary number/cross-reference, multiline note and missing following boundary. Require explicit evidence for a link; retain ambiguity and full note evidence.
- [ ] Implement textual note/marker detection with document/section scope. Never choose the nearest article merely by position. Preserve original intervals even where notes interrupt body text.
- [ ] Test all intervals against raw text and ensure note identity is independent of body citation identity. Freeze result; SK09 independently inspects ownership and gaps.

## Task4 — comparison and consumer integration, SK03/SK11

Files: new `src/sbs/comparison/structural.py`, tests `tests/unit/test_structural_comparison.py`, then `src/sbs/operations/preparers.py` and its tests.

Interface: `compare_structural(pair, before, after) -> dict` accepts raw before/after bundles, builds their structural/note layers and returns `original_comparison` (the full existing comparison output) plus `alignment_provenance`, `evidence_context`, `excluded_ranges` and derived comparison details. Exact raw citations and all physical pages travel with each result.

- [ ] RED: a difference consisting solely of explicitly identified whitespace/page furniture/notes must be distinguishable from a body-text candidate; ambiguous removal cannot silently erase text.
- [ ] Keep a reversible span map for the derived view; store each omitted range and reason. Do not merge disjoint pieces into a purported exact quote. No materiality claim based only on normalized equality or inequality.
- [ ] Compare the4036 regression: locate all five reference units in the structured evidence; preserve timing/annex limitations. Report body and editorial candidates separately with their supporting spans.
- [ ] Persist sidecars and their hashes in refresh closure; propagate heuristic provenance and recovery gaps through SK06/runtime before promotion. Test restore/readback and citation resolution. Keep RAG input strategy explicit; a changed input without its exact embedding is pending, not silently served with an old vector.

## Completion evidence for this increment

Independent SK09 technical and Astra reviews resolve the stated defects; a real local preparation→comparison→consumer test retains both counterparts, all pages and note provenance. This increment does not satisfy remote Genie, generated conversation, UI, independent-family acceptance or timing gates by itself.
