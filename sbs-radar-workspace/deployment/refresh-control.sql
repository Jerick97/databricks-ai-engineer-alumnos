-- Propuesta SK11/SK12. NO ejecutada; requiere autorización de cómputo SQL.
-- Tabla nueva propia. CREATE falla si existe: inspeccionar identidad, nunca
-- DROP/recrear ni asumir que un IF NOT EXISTS acredita el esquema esperado.
CREATE TABLE neptuno_manuel_arguelles.sbs_radar.refresh_control (
  control_id STRING NOT NULL,
  revision BIGINT NOT NULL,
  state_json STRING NOT NULL
) USING DELTA TBLPROPERTIES ('delta.isolationLevel' = 'Serializable');

-- INSERT una sola vez sobre esa tabla nueva verificada y vacía.
-- Resultado ambiguo: SELECT y reconciliar; no repetir INSERT.
INSERT INTO neptuno_manuel_arguelles.sbs_radar.refresh_control
VALUES ('control', 0, '{"current":null,"fence":0,"owner":null,"receipts":{},"releases":{},"requests":{}}');

-- Readback obligatorio: exactamente una fila, esquema y propiedad observados.
SELECT control_id, revision, state_json
FROM neptuno_manuel_arguelles.sbs_radar.refresh_control;
