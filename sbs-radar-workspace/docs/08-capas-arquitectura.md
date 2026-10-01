# Las nueve capas de arquitectura del agente

Estas son las capas solicitadas: **canal, recuperación, razonamiento**, etc. Se recuperan literalmente de la slide 3 del [apéndice S03](/Users/macdenix/clawd/databricks-ai-engineer/s03-genai/S03-append.html:11). Las9 etapas de preparación organizan el trabajo; estas capas organizan el funcionamiento del sistema. El mapeo SBS es una propuesta, no implementación terminada.

| Capa original | Responsabilidad | Aplicación al E2E SBS | Evidencia de funcionamiento exigida |
|---|---|---|---|
| 1. Canal y experiencia | Interacción con el usuario | Consulta, comparación antes/después y apertura de evidencias | Un analista completa el recorrido real y entiende faltantes |
| 2. Entrada y normalización | Validar y convertir el evento | Norma, versiones, fecha de corte, ámbito; extraer documentos | Contratos y errores explícitos; original preservado |
| 3. Borde, seguridad y gateway | Autenticar y controlar acceso/consumo | Identidad, permisos UC/documentos, límites y secretos | Pruebas con identidades autorizada y no autorizada |
| 4. Clasificación y ruteo | Elegir la capacidad adecuada | Diferenciar comparar texto, consultar vigencia e impacto | Casos de ruteo y abstención, tool elegida trazable |
| 5. Recuperación / grounding | Encontrar evidencia | Pasajes/versiones correctas, SQL y relaciones normativas | Recuperación suficiente, páginas/offsets y aislamiento temporal |
| 6. Razonamiento y decisión | Interpretar, planificar y proponer | Explicar diferencias y proponer impacto con incertidumbre | Afirmaciones sustentadas; no convertir diff en conclusión jurídica automática |
| 7. Validación y guardrails | Verificar política, formato y sustento | Validar citas, cobertura y fechas; solicitar revisión | Casos falsos/insuficientes rechazados y válidos aceptados |
| 8. Acción y herramientas | Ejecutar capacidades autorizadas | Comparador, consultas y registro de revisión | Tools tipadas; escritura idempotente y aprobación registrada |
| 9. Observabilidad, evaluación y mejora | Medir y reconstruir el recorrido | Trazas, versiones, costo, latencia, calidad y feedback | Reproducir una respuesta y detectar regresiones |

Seguridad y observabilidad atraviesan todas las capas: ubicarlas en una columna no las confina a un solo paso.

La [slide 4](09-capas-vs-sesiones.md) cruza estas capas con S02–S08. La slide 7 presenta Foundry/Databricks en el contexto de Apex. No usar una asignación histórica de proveedor como prohibición de resolver una capa en otra plataforma.
