# SK06 local component (0.1.0)

`prepare_project(root)` verifies the two frozen SK02 captures, manifests, PDF bytes,
extraction hashes and SK09-003 citation offsets. It returns `(bundle, config)`.
`export_bundle(bundle, path)` writes eight JSONL tables, proposed DDL and five SQL
examples with local SQLite results, plus five benchmark questions. Reproduction:

```python
from pathlib import Path
from sbs.genie import prepare_project, export_bundle
bundle, config = prepare_project(Path.cwd())
export_bundle(bundle, 'runs/sk06-component-real')
```

Each row includes identity, family, synthetic/source_kind, corpus/config hash,
lineage, publication/knowledge/effect dates, review status and original JSON
payload. Null dates remain unknown. The two `changes` rows are ChangeSets from
SK03 over raw-page evidence, with partial coverage and unresolved alignments;
they are **not counts of confirmed material normative changes**. SK09-003 remains
an AI annotation payload in `reviews`, with human_approved=false. Two illustration
processes are explicitly fictitious and live only in `processes`.

`allowed_query(query_id, params)` returns a closed SELECT template and separate
parameters. It never accepts SQL from a caller. SQLite validation is a local
baseline, not validation of Databricks SQL, a deployed schema or Genie.

`GenieAdapter(workspace_client.genie, config, permission_probe).ask(question)`
uses installed SDK start/get/query-result APIs; `ask(..., conversation_id=...)`
continues a conversation started by that adapter on the same snapshot. The probe
must be a trusted backend integration, not claims from HTTP request fields. It
checks the configured warehouse ID, RUNNING/type, effective CAN USE/table/Genie
permissions, dedicated read-only grant scope, and deployed snapshot. The trusted
probe returns `warehouse_id`, `state`, `warehouse_type`, `can_use`, `tables_read`,
`genie_access`, `read_only_backend`, `scope_verified`, and `snapshot`.

Genie executes generated SQL server-side; this adapter cannot inspect that SQL
before execution. A dedicated principal with SELECT-only grants on the allowed
mission tables must enforce the boundary. Neither prompt rules nor regex are
security controls. No generic local SQL execution tool is exposed. Multi-query
messages are unsupported; paginated or unproven completeness results are partial.
Conversation IDs and query status are retained, errors are sanitized. Poll count
is bounded; configure HTTP deadlines on the injected SDK transport (the JSON
proposes 30 seconds; this package does not instantiate a client).

`config/genie-notebook.json` and `config/genie-space-proposal.json` are explicit
pending templates: catalog, warehouse and space are unset. The observed stopped
warehouse is informational, not permission evidence. The adapter fails closed.
DDL is proposed only; select the authorized catalog and review the namespace
before separately authorized application. No compute, space or course resources
were mutated. Fixture tests do not establish remote integration or E2E.

## Scoped verification (0.1.1, SK07-R1)

`ask_scoped(question, context=QueryContext)` adds an independent result gate.
Instantiate `ScopedCatalog(bundle, trusted_contexts, table_prefix='catalog.sbs_radar')`
from a pinned backend-owned bundle and contexts; pass it to `GenieAdapter` as
`scope_catalog`, together with `execution_probe(query_id)`. The probe must fetch
executed statement/bound parameters and deployment lineage independently from
backend history. It must never construct its response from Genie attachments,
request fields, prompt text, or the requested context. Receipt fields:

```text
query_id, statement, parameters, source_tables, snapshot, state='SUCCEEDED'
```

The gate validates the QueryContext contract and exact registry entry, pinned
pair/source lineage, configured snapshot, executed SQL and bound parameters,
source tables, result columns and complete rows against independently computed
reference results. Requests carry context as prompt assistance only. Successful
output includes `kind='structured_query_result'`, `context`, `scope_verified=true`,
`rows`, `columns`, `query_id`, `source_tables`, `snapshot`, reference query ID and
row/source lineage. It contains no normative EvidencePack. Unsupported/malformed
or unproven results return conflict with scope_verified=false and no rows.

The 0.1.1 baseline accepted exact parameterized SQL only. The 0.1.2 refinement
below adds an explicitly pinned parser for a narrow safe literal profile; all
other equivalent-looking SQL remains rejected.
Supported templates are document-version list/count when no provision is selected,
and provision-row list/count when one is selected. All bind the family, corpus,
before/after document and version identities; provision queries also bind the
provision ID. They do not answer counts of confirmed material normative changes.
Target-date/legal-effect scopes are unsupported. Partial/paginated rows do not
satisfy the verification gate. Scope verification does not prove that an arbitrary
natural-language question is semantically answered by one of these templates;
the caller must expose the explicit reference-query meaning or decline it.

The probe, cloud deployment and transport permissions remain unimplemented trusted
integration dependencies; supplying caller-controlled receipts would violate this
API contract. No resource availability or live Genie success is inferred. Legacy
`ask` remains an unscoped low-level call; SK07 must use `ask_scoped` exclusively.

## Executed SQL provenance (0.1.2)

Install `src/sbs/genie/requirements.txt` (SQLGlot 30.20.0). Importing the base
component does not require the parser; literal verification fails closed if the
pinned version is missing. `sbs.genie.provenance.DatabricksHistoryProbe` is a
callable for `execution_probe`:

```python
probe = DatabricksHistoryProbe(
    workspace_client.query_history,
    warehouse_id=warehouse_id, space_id=space_id, executor_id=app_executor_id,
    snapshot=catalog.snapshot, table_content_sha256=verified_table_hashes,
    publication_lookup=independent_publication_store.lookup,
)
adapter = GenieAdapter(workspace_client.genie, config, permission_probe,
                       scope_catalog=catalog, execution_probe=probe)
```

The GET query-history API is filtered by the actual statement ID. The probe
checks ID, warehouse, executed-as user, Genie source-space ID, SELECT status,
finality and execution times. Cached executions are refused. It extracts the
single fully qualified table from the executed SQL AST. Query history containing
only unbound markers is refused: the API does not supply the missing bindings.
No API here executes SQL, starts compute, mutates resources or invokes inference.

`publication_lookup(source_tables, started_at_ms, ended_at_ms)` must retrieve an
independent, immutable server record with `snapshot`, `source_tables`,
`table_content_sha256`, `attestation_id`, `valid_from_ms` and `valid_until_ms`.
Its hashes must come from actual table readback; the interval must be backed by
an enforced no-write period covering the query. It is NOT a factory that echoes
the expected snapshot/hashes. The probe checks this certificate against pinned
expectations. This project has no published SBS tables/certificate yet; a cloud
caller must decline until that evidence exists. A copied metadata property alone
is not a readback certificate.

Literalized SQL is accepted only when its Databricks AST equals the exact AST of
a closed reference populated with safely typed literals. Identifier case,
quoting and whitespace can vary. Predicate order, projection, joins, tables,
filters and values cannot silently change. Comments/hints, multiple statements,
backslash escapes and quote/control-bearing reference literal values are refused.
Bound-parameter mode still requires independent actual bindings. Output retains
raw executed SQL and separately labels verified literal values with
`parameters_origin=verified_executed_literal_values`. These are NOT claims that
the backend returned bound parameters. `execution_provenance` carries the query
text/history/certificate hashes and source IDs. This is post-execution result
verification; SELECT-only backend privileges remain mandatory before Genie runs.

Official contracts checked: [Query History](https://docs.databricks.com/api/query-history/v1/query-history),
[Databricks string literals](https://docs.databricks.com/aws/en/sql/language-manual/data-types/string-type),
and [SQLGlot Databricks dialect](https://sqlglot.com/sqlglot/dialects/databricks.html).
`runs/sk06-provenance-metadata.json` records successful real GET availability and
exact-ID filtering on one historical SELECT, without persisting its SQL text.
That record lacks Genie source attribution and is not an SBS execution. No E2E
claim follows from the GET or synthetic probe tests.

## Explicit SK06/RAG snapshot map

`build_project_snapshot_mapping(root)` loads frozen SK06 JSONL and SK04 corpus,
records/index/protocol, verifies their envelopes/hashes, rechecks the six original
PDFs and extraction bytes, and compares all 135 citation identities/text offsets
and families. Its output (also `config/genie-rag-snapshot-map.json`) preserves
`sk06_snapshot` and `rag_snapshot` as distinct values, plus source/citation-set
hashes, exact pair counterpart mappings, artifact hashes and limitations. Rebuild
or reverify it against source files before consumption; it is not client input.
`reconcile_snapshots(**snapshot_inputs(root))` exposes the same deterministic API.
A source mapping does not certify remote table publication or model quality.

Article-level RAG focus IDs are NOT equivalent to `raw-page-N` provision IDs.
`ScopedCatalog.references(context)` now refuses a selected ID absent from curated
rows instead of returning a misleading zero count. To support article counts,
first export reviewed structural `Provision` contracts using
`curate(..., provisions=verified_structural_provisions)`, preserving source
identity, exact offsets and distinct IDs; regenerate the corpus snapshot and an
explicit citation mapping. This task does not fabricate those structural rows or
rewrite existing corpus IDs. Future runtime integration must retain both snapshot
IDs and the verified map; it must not assign a common label to bypass comparison.

Pilot002 offline: `sbs.genie.pilot.build_pilot_002(root)` returns bundle, config,
contexts, granularity, explicit snapshot mapping, six scoped reference queries
and five benchmarks. `export_pilot_002(root)` freezes them separately from001.
Use `ScopedCatalog(bundle, contexts, table_prefix=config['table_prefix'])` for
article count/list plans. 135 raw-page rows plus six canonical SK03 article rows
are141 distinct provisions; each selected article yields two version rows, not
two material changes. Mapping verifies each article's source slice and preserves
its parent AI annotation; the RAG index still contains raw-page vectors.
Warehouse/space IDs and publication certificate remain unset: no cloud claim.
