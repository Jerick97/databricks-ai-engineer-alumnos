# Real local refresh preparers

API: `build_real_hooks(project_root, *, annotations=(), embedding_adapter=None,
token_counter=None, allow_inference=False, max_embedding_calls=0,
max_embedding_inputs=0, max_embedding_tokens=0)` from `sbs.operations.preparers`.
No client creation, GET or model inference occurs during construction. It verifies
the real frozen SK04 records/index against report hashes, sealed payload, actual
LocalIndex hash and the model bundle identity. The controlled server project is
the trust anchor. Cache is keyed by model identity and exact full `input_parts`,
never citation ID, approximate text or matching vector dimension alone.

Supply explicit VersionPairs through `dataclasses.replace(plan, pairs=(...))`.
`SealedPlan.pairs` defaults to empty for compatibility; actual hooks then return
PAIRS_PENDING. The runner includes pairs in plan fingerprint and same-run conflict
checks. Change plan identity or configuration when changing hook configuration or
annotations, use a fresh run ID and force_revalidate for explicit re-preparation.
Pairs are not inferred by version ordering or dates. If a newly captured source
changes a pinned pair version, PAIR_SOURCE_MISSING requires explicit reviewed pair
configuration; no silent substitution of the latest bytes.

Runner contexts contain current summaries, run ID, complete source set/removals,
plan/pairs/fingerprint, state_root, foundation_root and stage. Preparers resolve
SourceDocuments only from successful captures of that exact run, correlate stable
source_key+SHA+document+family, call SK02 cache verification and verify original,
raw-text and result bytes. New captured_at stays in the source payload but is not
part of the runner's source change comparison. Identical content does not become
changed merely because the clock advanced.

SK03 calls compare for each explicit pair with partial raw-page coverage. Optional
trusted annotation dictionaries have pair_id/provision_id/before/after review
citations. It reuses structural_bundle only after original identity, exact span,
page and offsets match current bundles; stale annotations return pending. All
annotation provenance stays AI reference with human_gold=false. Raw-page alignment
is not semantic article alignment or materiality approval.

SK04 rebuilds current chunk records with SK04 chunk_spans and the same versioned
strategy/model/tokenizer/input profile. Cached exact-input token counts and vectors
are reusable; no input is shortened. Missing text needs a compatible TokenCounter
and explicitly injected model adapter plus allow_inference and finite call/input/
token quotas. Quotas are reserved before a call and not refunded on failure.
A missing tokenizer, vector or quota returns closed pending reason; never generate
hash vectors or relabel fixtures as cloud inference. Adapters own network deadlines.
Output is a new self-contained LocalIndex artifact (records, vectors, dimensions,
model identity, actual index hash, source snapshot and cache provenance).

Strategy: span-limpio-contexto-v1 version1, SBS adaptation preserve_input_raw_pages,
context_chars=0, prefix empty, pinned Qwen model/tokenizer from verified cache.
Literal source span is separate from embedding input. Semantic segmentation,
layout/table fidelity and retrieval relevance remain unvalidated; full selected
raw-page coverage does not establish full legal coverage. No qrels are generated.

SK06 calls curate using the actual current SourceDocuments, pairs, provisions,
comparison outputs and optional validated AI annotations. No old Genie bundle is
copied as new and no fictitious processes are added implicitly. Curation binds
current source snapshot, retrieval index and annotation hashes. It writes no DDL,
Genie space, cloud table or publication certificate.

All three hooks emit atomic staged JSON artifacts with sealed payloads and complete
state-relative file hash closure over actual source/extraction inputs plus staged
upstream artifacts. Runner verifies paths, rejects symlinks/traversal and checks
closure before publication and every current() read. Self-contained records/vectors
are covered by artifact hash; no mutable external cache is needed to read a release.
Missing hooks or closed pending reasons leave backlog and cannot publish.

Demonstration: `runs/sk11-real-hooks-demo.py` writes a new isolated state root,
refuses overwriting a previous demonstration, uses six real sealed PDFs and135real
cached embeddings, tests failure before pointer commit and subsequent recovery.
It asserts original PDFs and existing RAG files unchanged. This establishes local
preparation/pointer semantics only. Runtime consumer promotion, distributed lock/
store, live app/Genie, new-source inference and semantic evaluation remain separate
pending integrations. production_validated remains false; e2e_acceptance remains
not_evaluated. No new remote inference was executed in this task.
