# Contrato de trabajo: construir el E2E SBS completo

Confirmación de alcance del usuario: levantar el E2E considerando las 12 decisiones, las 9 capas de arquitectura y las 9 etapas de preparación; reutilizar lo previo cuando corresponda. La investigación entregada es una fase, no el cierre del encargo E2E.

## Cómo se conectan los tres marcos

| Etapa/eje de preparación | Decisiones que orientan el trabajo | Capas runtime principales | Entregable para el E2E |
|---|---|---|---|
| Fundación de datos | A03,A04,A05 | Entrada; recuperación | Corpus real, versiones y control de extracción |
| Contratos y gobierno | A01,A03,A05,A07 | Entrada; borde; tools | Diccionario, esquemas, autoridad y permisos |
| Conocimiento y recuperación | A04,A05,A08,A10 | Recuperación; validación | Pasajes citables y benchmark de recuperación |
| Orquestación | A06,A07,A08 | Ruteo; razonamiento; acción | Flujo ejecutable y herramientas conectadas |
| Modelo | A02,A06,A10,A11 | Razonamiento | Selección medida y configuración reproducible |
| Seguridad y cumplimiento | A07,A09 | Borde; validación; acción | Controles y revisión humana verificables |
| Evaluación y calidad | A05,A10,A12 | Validación; observabilidad | Referencias, holdout, regresiones y aceptación |
| Observabilidad | A10,A11 | Observabilidad, transversal | Trazas, calidad, latencia y costo por expediente |
| IA responsable y despliegue | A01,A07,A11,A12 | Canal; acción; observabilidad | UI completa, deploy, rollback y runbook |

El canal se diseña desde A01/A08; no se deja para el final aunque el despliegue cierre el recorrido. Todas las decisiones y capas deben tener evidencia o una exclusión justificada.

## Entregables de construcción

1. Ficha A01–A12 aplicada y decisiones abiertas identificadas.
2. Corpus oficial piloto con versiones, manifiesto, hash y referencia experta; no fixtures presentados como normas reales.
3. Pipeline de ingesta/extracción/alineamiento/diff con persistencia histórica y manejo de fallos.
4. Agente Genie configurado y conectado a datos/evidencias; mecanismos adicionales solo si el caso los requiere.
5. Canal usable con consulta, antes/después, citas, faltantes y revisión humana.
6. Pruebas por componente y E2E real, incluida la configuración que recibe el usuario, permisos y disponibilidad.
7. Material reproducible: notebook, configuración, instrucciones, evidencia, límites y runbook.

## Reutilización condicionada

S05 SBS aporta ideas y diff inicial; research-citas aporta validación; Ianbal aporta IaC/evaluación; el curso aporta patrones de serving/observabilidad y documentación. Cada parte debe pasar una prueba del nuevo caso. El hecho de existir no acredita su adecuación.

## Dependencias reales

Familia normativa, periodo y destinatario específicos todavía no confirmados. Se puede avanzar con diseño y evaluación técnica sobre corpus público; no afirmar aplicabilidad bancaria ni aceptar el gold en nombre de un especialista. El entorno destino y sus capacidades se verifican antes del despliegue. Los recursos Apex no quedan autorizados para modificación por haber sido citados como antecedente.

## Criterio de cierre

El usuario recorre de punta a punta una comparación real, abre las dos fuentes, revisa faltantes y propuesta de impacto; quedan trazas y resultados reproducibles. No equivale a producción operada ni a certificación jurídica. Los gates humanos/operativos pendientes se reportan explícitamente.
