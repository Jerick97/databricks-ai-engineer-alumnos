# Query provenance — SK06 0.1.2

Checked 2026-09-27/28 UTC. Primary sources: [Databricks Query History API](https://docs.databricks.com/api/query-history/v1/query-history), [Databricks string literals](https://docs.databricks.com/aws/en/sql/language-manual/data-types/string-type), [SQLGlot API](https://sqlglot.com/), [Databricks dialect](https://sqlglot.com/sqlglot/dialects/databricks.html). Installed SDK: 0.102.0; pinned parser: 30.20.0.

Query History supports GET filtering by statement IDs and reports executed text,
status, finality, warehouse, executor, time interval and source Genie ID when
available. Its QueryInfo model exposes no bound-parameter field. Thus history
with unresolved markers cannot attest actual values. Source Genie attribution
and executor are required even when an ID-filtered record exists.

Decision: compare one executed SELECT AST against one closed reference after
safe typed literal substitution; preserve all scope predicates. Conservative
profile excludes SQL comments/hints, extra statements and ambiguous escapes.
Identifier quoting/case and whitespace may differ. This validates the returned
query result after execution and is not authorization; backend grants remain
required beforehand. The public API is `DatabricksHistoryProbe` plus the existing
`GenieAdapter.ask_scoped` in `src/sbs/genie`.

Snapshot assertion additionally requires a trusted publication store containing
actual full-table readback hashes and an enforced write-free interval. The
probe cannot establish a publication certificate using GET history alone.
Undeployed SBS tables currently have no such certificate: the safe result is
unavailable/conflict. No expected-context echo can fill the gap.

Real GET evidence: `runs/sk06-provenance-metadata.json`. A historical SELECT was
found again by exact statement ID, without recording SQL text. Its source Genie
attribution was absent. Warehouse remained STOPPED. This proves API availability,
not SBS Genie attribution, table publication or E2E.

`config/genie-rag-snapshot-map.json` proves matching six local source/extraction
identities and 135 raw-page citations while retaining different snapshot hashes.
This map does not translate semantic article IDs to raw-page IDs; structural
export must carry verified offsets and regenerated evidence before article counts.

Assertions and limits: `evals/regressions-v0.1.2.json`,
`tests/unit/test_genie_provenance.py`, `runs/sk06-provenance-*.txt`.
