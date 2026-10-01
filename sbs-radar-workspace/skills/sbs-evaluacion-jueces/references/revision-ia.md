# Revisión normativa IA — protocolo v1

Designación del usuario (2026-09-27): GPT-6 Astra, razonamiento high. Esta designación reemplaza la búsqueda de un revisor humano para el piloto; no otorga aprobación institucional. Toda revisión se ejecuta como invocación de SK09.

## Entradas y registro

Leer únicamente originales/derivados fijados por SK02, VersionPair y resultados SK03, cuando existan. Registrar skill_id, skill_version, skill_path, skill_sha256, modelo, esfuerzo, entradas con hashes y alcance. No tratar resúmenes ni noticias como sustitutos de las disposiciones.

## Encargo del juez

1. Confirmar identidad de ambas fuentes, cobertura y procedencia. Separar fecha de captura, publicación y vigencia. No inferir precedencia normativa del número de carpeta.
2. Para cada cambio candidato, cotejar pasajes completos y citas localizables. Distinguir adición, eliminación, modificación, renumeración y reorganización; comprobar tablas y anexos afectados.
3. Responder qué decía antes, qué dice después y qué cambió literalmente. Citar ambas versiones. Registrar ambigüedades de alineación.
4. Analizar implicancias como inferencias explícitas, enlazando la disposición que las sustenta; indicar supuestos de aplicabilidad y evidencia faltante. El banco de procesos es ficticio.
5. Buscar omisiones y falsos positivos independientemente de la propuesta del constructor. Conservar desacuerdos; no cambiar el conjunto reservado para mejorar métricas.
6. Emitir por caso passed/failed/not_evaluated con evidencia y severidad. Falta de originales, contraparte o cobertura crítica exige not_evaluated para la afirmación afectada, sin bloquear resultados verificables de otras partes.

Salida: informe de revisión IA, nunca referencia humana. Métricas contra anotaciones IA deben identificar ese origen y su incertidumbre. No declarar eficacia operacional, ahorro humano ni exactitud jurídica global por esta sola revisión. La aprobación de impactos institucionales es otro flujo.

## Estado

Protocolo provisional: revisión inicial en curso. La ejecución registra el hash exacto de la versión leída; no actualizar retroactivamente dicho hash tras un refinamiento. Una nueva corrida usa la nueva versión.
