# SK04 real pilot

`python3 skills/sbs-rag-hibrido/scripts/run_real_pilot.py` verifies SK02 caches, pins
SK05 model identity, freezes the SK09 pilot protocol, and counts all planned input.
The authorized run was executed with `--execute`; completed invocations verify
persisted index artifacts and make no additional inference calls.

Run `python3 skills/sbs-rag-hibrido/scripts/verify_real_pilot.py` for the offline
artifact and metric audit. It verifies all saved model responses, the reconstructed
index identity, raw citation slices, metric calculations, and reranker window coverage.

The successful pilot indexed 135 raw pages from six PDFs using 18 embedding
requests and 122269 observed prompt tokens (123373 reserved), and reranked three
queries on local ONNX CPU with two threads. Monetary cost is unknown. No generation
model is selected. It uses the existing endpoint and creates no remote resources.

Success caches persist after each batch and count against the original run quota
when resumed. A persisted attempt without a success cache blocks automatic retry;
an ambiguous or failed call needs new explicit scope. No fixture fallback exists.
The same vectors serve all four retrieval variants; query and ranking configuration
were frozen before inference. No result-driven changes were applied.

SK04 0.1.0, SK05 0.1.2 and SK09 0.1.2 are the owning provisional skills. The strategy
is `span-limpio-contexto-v1@1`, explicitly adapted to preserve input page units
without previous context. Pages are not certified semantic boundaries. Full page
citations remain unchanged when reranker scoring splits their text into contiguous
character windows and aggregates maximum raw logits.

The protocol intentionally has no independent tune/holdout split: all three
reviewed examples are related. The existing `freeze_protocol` API requires two
nonempty independent partitions, so this pilot records a canonical write-once
hash instead of fabricating partitions. Thresholds remain frozen but operational
acceptance is not evaluated. The three AI-reviewed qrels are partial, not human
gold. Amending acts are indexed but the three queries restrict retrieval to their
consolidated before/after pairs. Current global legal coverage is not established.
