-- Parámetro STRING metrics_table = <catalogo>.<schema_ais08>.inference_flat
-- Token telemetry del agente: dos llamadas Safety adicionales no están incluidas.
-- No transformar tokens en dinero sin tarifas y región vigentes.
SELECT agent_revision, count(*) solicitudes,
  sum(input_tokens) input_tokens, sum(output_tokens) output_tokens,
  percentile_approx(latency_ms,0.95) p95_ms,
  avg(CASE WHEN status_code >= 400 THEN 1.0 ELSE 0.0 END) error_rate
FROM IDENTIFIER(:metrics_table)
GROUP BY agent_revision;
-- Facturación final: system.billing.usage + system.billing.list_prices según SKU/fecha.
-- Los costos de warehouse, serving, App y monitor no se deducen sólo de tokens.
