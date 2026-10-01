# SK07 / CreatorZ — relaciones entre cláusulas212

Estado provisional: corrección de instrucciones, no mejora semántica demostrada. CreatorZ exacto exigido por AGENTS.md leído; propietario SK07, constructor deployment_lifecycle210 y revisión independiente root/SK09.

## Baseline y causa

Fuente y respuesta real se conservan en `runs/ui210/turn3-rendered.json`. La respuesta a la propuesta, después de la comparación extractiva, describe una obligación como «condicionada a que no resulten exigibles trámites adicionales». El pasaje completo aportado exige disponibilidad mínima de canales y expresa que no resulten exigibles trámites adicionales. Astra detectó la conversión material de una restricción concurrente en una condición. No se modifican fuente, respuesta, gold, umbral ni evaluación histórica.

El generador125 separa comparación literal de propuesta generada y pide una «actuación condicionada» para el proceso ficticio. La instrucción no distingue expresamente ese supuesto de aplicabilidad de las relaciones lógicas internas de la fuente. Esta es una hipótesis causal del prompt, no una causa del comportamiento del modelo demostrada.

Investigación acotada: `src/sbs/conversation/hybrid_125.py` (PROPOSAL_POLICY + único POST de propuesta); `focal_packet_115.py` (evidencia y política focal); `skills/sbs-conversacion-orquestacion/assets/generator-instructions.md` (modalidades y condiciones); evidencia real210. No se necesita reconstruir derecho vigente: se compara la salida con el texto exacto proporcionado. No se reemplaza esta evidencia por fuentes externas ni una interpretación institucional.

## Corrección mínima

Un único archivo candidato `deployment/overlay212/src/sbs/conversation/hybrid_125.py`: añade un párrafo al PROPOSAL_POLICY125. Separar supuesto de aplicabilidad de la propuesta y condición normativa; conservar sujeto, mandato/permiso, negación y concurrencia. Si «sin que» restringe exigencias al destinatario, no convertirlo en condición del mandato. Mantener condiciones genuinas y no clasificar toda aparición de «sin que» automáticamente. Ante ambigüedad, citar literalmente y declararla.

No filtra ni reescribe respuestas con reglas léxicas; no añade otra llamada, reintento o verificador modelo. No incorpora artículos, IDs ni respuesta correcta prediseñada. Conserva temperatura, esquema, modelo, evidencia, citas y comparación extractiva. Se prefiere esta corrección general a un detector rígido de la frase errónea, que podría ocultar casos o rechazar condiciones válidas.

## Evaluación y límites

Tres pruebas técnicas: A/B del request real de propuesta demuestra la nueva instrucción en el mensaje system y el resto de payload idéntico; rama extractiva devuelve el mismo texto sin POST; fallo real permanece como caso. Reproducir fixture no prueba obediencia del modelo ni entailment. `runs/sk07-proposal-relations-212-eval.json` prepara casos discriminantes sin modificar gold existente.

Revisión requerida antes de combinar con211: inspección de diff y hash, prueba de transmisión, luego regeneración real de la misma propuesta en UI con asignación ya revisada. SK09 debe verificar que obligación y restricción no se subordinan, sin premiar coincidencia de palabras; comprobar además una condición genuina para no invertir el error. Mantener fallo210 hasta nueva evidencia real. No nuevo presupuesto ni firma emitidos durante preparación.
