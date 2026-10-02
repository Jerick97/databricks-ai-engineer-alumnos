# Canal local SBS Radar — SK10 0.1.1

`create_app(service, mode='local')` usa FastAPI. Ejecutar desde la raíz con `PYTHONPATH=src python3 app.py`, que escucha exclusivamente `127.0.0.1:8090`. Depende del runtime real `sbs.runtime.create_service()`; no hay fallback de fixtures. Modo cloud exige adaptador de identidad, origen HTTPS fijado y runtime cloud. El adaptador verifica current-user; la ejecución detrás de Apps todavía no está acreditada. La sesión local no habilita aprobación institucional.

Contrato del servicio (dict JSON compatible):

- `catalog()` → `{families:[{id,label}], pairs:[{id,family_id,title,before_label?,after_label?,status?,evidence_status?,provisions:[{id,label}]}]}`.
- `comparison(pair_id,provision_id=None)` → `{pair_id,provision_id?,title?,before:{label?,text,source_id?,page?},after:{...},summary?,status?,evidence_status?,citations:[],limitations:[]}`.
- `ask(session_id,question,pair_id,provision_id=None,cross_family=False)` → `{answer,status,evidence_status?,citations:[],limitations:[]}`. `answer` puede estar vacío. Estados: answered, partial, conflict, insufficient_evidence, generation_error, denied, structured_response_pending. El runtime conserva contexto de conversación para el ID de sesión generado por servidor.
- `source(source_id)` → `Path` autorizado mediante mapa de IDs o `{path:Path}`. No se admiten URLs arbitrarias ni rutas del cliente. PDF local inline. `KeyError` indica fuente desconocida.
- Citas: `{source_id,label?,excerpt?,page?}`. `page` es entero positivo, base 1.

API: GET `/api/catalog` (añade `csrf_token`); GET `/api/comparison?pair_id=...&provision_id=...`; POST `/api/ask` con selección/pregunta y `X-CSRF-Token`; GET `/api/sources/{id}`. POST rechaza campos extra, incluidos roles de actor. Comparación y preguntas requieren una disposición explícita del catálogo; la UI muestra la primera seleccionada sin prometer una vista de todas. Cookie HttpOnly, SameSite Strict, sesión de ocho horas; requiere loopback y no debe exponerse por proxy. Historial visual se mantiene en memoria de pestaña, segregado por selección; runtime conserva hasta cuatro turnos normativos validados por foco y ocho focos por sesión, con texto acotado. Esta memoria es contexto no confiable; las citas nuevas proceden exclusivamente de la evidencia actual. Recargar elimina el historial visual, no establece un nuevo ID si la cookie sigue vigente. No hay registro institucional ni acción de propuesta persistida.

Contenido normativo y modelo usa `textContent`, CSP sin scripts inline, recursos nativos sin CDN. Fuentes se abren en pestaña nueva, preservando selección. Navegación usa botones semánticos normales (no tabs ARIA incompletas).

Pruebas de componente: `python3 -m pytest tests/unit/test_webapp.py -q`. No acreditan E2E, revisión visual, ni accesibilidad completa. Pendiente: recorrido real en navegador con runtime y configuración, ambas familias, teclado, móvil, fuentes, seguimiento y error recuperable. Dependencias requeridas: FastAPI, uvicorn; httpx/pytest para pruebas.
