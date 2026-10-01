# Server binding — local verification, remote execution still pending

`from sbs.genie.runtime import load_runtime_binding, ServerDependencies`

`binding = load_runtime_binding(project_root)` verifies the frozen pilot002 config,
export file hashes, curation/snapshot hashes, complete registered contexts,
reference queries, raw-page RAG mapping, frozen source bytes and six structural
subspans. It does not recurate, extract, embed, compare or contact cloud. Load once
per server runtime; missing/corrupt inputs raise `GENIE_LOCAL_EXPORT_INVALID`.
Paths are contained/rebased with `project_path`. Optional `expected_config_sha256`
is an independently pinned deployment digest. Without it the trust anchor is the
controlled server filesystem; manifests are integrity checks, not signatures.

Read-only properties: `genie_snapshot`, `rag_snapshot`, `mapping_sha256`.
`contexts` and `snapshot_map` return detached copies. `readiness()` does no I/O:
`unavailable` with reasons for missing warehouse/space or server dependencies.
With supplied dependencies it says `configured_pending_remote_verification`;
`available=true` means configured capability only, `remote_verified=false`.
No runtime construction starts a warehouse or conversation.

`binding.ask_scoped(question, context=context)` rejects any mismatch in the full
registered QueryContext before calling a dependency. The default config returns
`unavailable`, empty rows and scope_verified=false. It preserves SK06 snapshot;
RAG snapshot and verified mapping digest are additional fields, never replacements.
Root SK07 must compare binding.rag_snapshot to its own session snapshot and exact
context before accepting the server mapping. No request may supply dependencies,
config paths, snapshot labels or mapping attestations.

For future authorized remote use, a server-owned configuration must specify the
actual warehouse and Genie space. Inject `ServerDependencies(genie=client.genie,
query_history=client.query_history, permission_probe=..., publication_lookup=...,
executor_id=...)`. The permission probe is an independent backend check of
warehouse RUNNING/type/CAN USE, Genie access, table SELECT-only grants and pinned
publication scope; never derive it from expected config flags. Transport deadlines
are the SDK owner's responsibility. SDK calls occur only from ask_scoped.

Before invoking Genie, publication_lookup receives exact table names and the
current millisecond instant and must return an independent readback certificate
covering that instant. Table hash profile: `sbs.genie.digest(rows)` on all curated
row objects in id order, preserving payload_json/lineage_json strings and native
scalar types. A future publisher must recompute it from complete actual backend
readback and enforce a write-free interval. Local expected hashes alone prove no
publication. There is currently no deployed table/certificate store in this bundle.

After execution, DatabricksHistoryProbe independently checks the actual statement
ID, warehouse, executor, Genie attribution, SELECT status, SQL, timestamps and a
publication certificate covering the entire real execution interval. ScopedCatalog
compares safe literalized SQL or bindings and all rows against the pinned reference.
Missing provenance, global aggregate SQL, wrong family or unverifiable rows fail
closed. A present callback or pre-query certificate cannot waive those checks.

No production permission/certificate provider is fabricated. Their implementation,
backend grants, published tables, Genie space configuration and live E2E remain
pending authorized deployment. Runtime tests use explicit SDK/history/certificate
doubles and establish local contract behavior only. No remote SQL/start/create,
model call or actual Genie query was executed for this refinement.
