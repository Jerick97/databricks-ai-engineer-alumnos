# SK04 local retrieval

Technical implementation, not corpus validation. It requires externally generated
embeddings and an explicitly injected real reranker before anyone can claim a real
semantic/reranking pipeline was executed. Unit tests use synthetic vectors and
counters; no TF-IDF/hash substitute is called an embedding.

## API

1. `chunk_spans(artifact, family=..., counter=TokenCounter(...), model_identity=...,
   limit=..., prefix='', context_chars=0)` consumes SK02-style raw text, its SHA256,
   page offsets and verified provision boundaries. It preserves those units;
   oversize units fail with `budget_exceeded_or_tokenizer_pending` and require an
   explicit versioned segmentation adaptation. It does not automatically truncate.
   Cite `record['citation']`; embed the complete `record['input_parts']`; answer
   with authorized expanded citations. These representations are distinct.
2. `LocalIndex(records, vectors, dimension=..., model_identity=...,
   actual_identity=..., complete=True)` detaches its inputs, validates every vector
   and rejects mixed tokenizer/chunk identities. `index_hash` includes all content,
   configuration and vectors. Retain the previous index when constructing a new
   one. Durable index persistence is not included in this in-memory interface.
3. Alternatively use `LocalIndex.from_adapter(records, adapter)`. The adapter must
   expose `identity`, `dimension`, `embed_documents(list[tuple[str,...]])`, and
   `embed_query(str)`. It owns SK05 provider/tokenizer preflight and must refuse
   truncation. Calling this method performs whatever inference that chosen adapter
   implements; no implicit adapter, credential lookup or paid service is selected.
4. `retrieve(index, query, query_context, server_scope, query_vector=...,
   query_identity=..., top_k=5, candidate_k=20, reranker=...)`. `query_context`
   follows SK01. Construct `ServerScope(frozenset(families),
   frozenset((document_id,version_id) pairs))` in trusted server code from SK08;
   this class is not authentication and must never be deserialized as authority
   from a user, PDF, query or client. Alternatively pass `adapter=` for query
   embedding. Query vectors require the pinned identity and valid shape.
5. Reranker signature: `(query, detached_authorized_records) -> finite scores`,
   exactly one score per candidate. Missing reranker is explicitly reported.
   Its transport/input budget is the adapter's responsibility. Errors and malformed
   score arrays yield `technical_error`, without leaking provider exception text.
6. `counterparts={citation_id: [counterpart_citation_ids]}` comes from explicit SK03
   alignments; `neighbors={citation_id: [neighbor_citation_ids]}` supplies expansion.
   Both are filtered to the server scope and comparison pair. Counterparts may be
   outside top-k and must belong to the other document/version identity.
7. `native_rrf=[(citation_id, score), ...]` accepts a **server-owned already fused**
   ranking, bypasses local lexical/vector scoring and RRF, and declares internal
   lists unavailable. Upstream native retrieval must itself enforce authorization;
   filtering a returned result does not establish upstream enforcement.

The local flow computes BM25 corpus statistics only over authorized candidates,
cosine scores from supplied vectors, one RRF fusion, and optional reranking.
Result keys are `status`, `evidence`, `trace`, and `limitations`. Trace contains
IDs, scores, configuration and index identity, not passage/query/exception text.
Errors differ from `empty`, `access_denied`, `index_incomplete` and `partial`.
EvidencePack remains `coverage=partial`: retrieval never establishes global no
changes, source completeness, legal validity or institutional impact. It does not
modify review status or require expert approval before ordinary conversation.

## Evidence and limitations

The literal citation check is against immutable **extracted raw text**, not the
original PDF's visual layout. Chunking preserves supplied structural units and
records excluded gaps/page seams; semantic continuity, tables and annexes remain
unverified unless upstream evidence establishes them. The in-memory index assumes
trusted SK02 records and SK08 scope construction; it does not authenticate them.
External adapter model identity is a pinned caller/provider assertion, not proof
of actual remote weights. The real SBS corpus, embedding/reranker execution, four
SK09 variants, qrels, recall/nDCG, latency and cost remain separate acceptance work.
