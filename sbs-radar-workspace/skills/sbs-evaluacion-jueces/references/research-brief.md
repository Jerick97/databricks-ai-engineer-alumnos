# SK09 — Creator Z fases0/1/1.5

Fecha2026-09-27, fuentecreadora skill-creator-z ruta openclaw-codex/openclaw-workspace/skills/skill-creator-z/SKILL.md. Baseline ejecutado antesSKILL en runs/sk09-baseline.json. Reutilizar spec12, plan13 ProtocoloRAG, evidence/sbs-forensic-* sobre limitaciones de benchmarks y fuentes-web.md (documentación Genie monitor ya consultada), sin repetir investigación.

Intención: diseñar referencia/evaluación y medir aceptación porfamilia sinfugarholdout, confundir selfjudgeconverdad o inventar métricas. Entradas: referencia adjudicada, corpus/preguntas congelados, corridas ypredicciones, baseline tiempo. Salida: informes numéricos reproducibles y evidencias, criterios failed/passed/not_evaluated por dominio. Actor humano aún solicitado; su falta no impide desarrollo técnico, sí impide afirmar adjudicaciónjurídica.

Alternativas: juecesLLM solos tienen sesgos y noacreditanverdad; elegir capasdeterministas+referenciahumana+juezexplicativoseparado. Las tablas debenchmarkhistórico no se heredan. Holdout nooptimizable; corpuspuedeestarindexado pararesponder, respuestasgold noentran apromptsejemplos ni ajuste.

Riesgos: denominadorcero, promedioocultafamilia, mismaversion/derivado en tuning/test, subset crítico vacío, tiemposretraba joomitidos, goldsintéticopresentadoreal, scorejsonjuezcomoevidenciaautentica. Toda tasalleva numerador/denominador yvaloresnoevaluados. Confianzadeldiseño alta, eficacia nueva pendiente.

EvaluaciónCreator: seis casos y pressureexpertabsent. AssertantesGREEN; generalizaciónstrict, wording, replicación yblind pendientes. Construcción de harness diferente de aceptacióndelagente.
