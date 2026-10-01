-- Fixture explícito para probar extracción. No escribe inference tables ni acredita tráfico.
WITH fixtures(case_name,status_code,response) AS (
  VALUES
  ('valido',200,'{"output":[{"content":[{"type":"output_text","text":"Respuesta de prueba"}]}]}'),
  ('texto_movido',200,'{"output":[{"text":"Respuesta en otra ruta"}]}'),
  ('error_http',500,'{"error":"fallo de prueba"}')
)
SELECT case_name,
 length(get_json_object(response,'$.output[0].content[0].text')) AS output_chars,
 CASE WHEN status_code>=400 THEN 'http_error'
      WHEN get_json_object(response,'$.output[0].content[0].text') IS NULL THEN 'parse_error'
      ELSE 'ok' END AS parse_status
FROM fixtures ORDER BY case_name
