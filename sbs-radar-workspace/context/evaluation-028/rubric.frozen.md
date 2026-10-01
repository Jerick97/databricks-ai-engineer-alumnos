# Rúbrica congelada SK09 028

Modelo designado: GPT-6 Astra, high. Revisión IA independiente de relevancia; no aprobación humana. Se aplica diseño018: 0 irrelevante, 1 contexto relevante, 2 sustento directo. Congelada antes de emitir juicios; no se leerán rankings, scores ni juicios anteriores.

Elegibilidad: identidad exacta document_id/version_id de before o after del pair de cada pregunta, sin filtrar por artículo ni resultado de recuperación. Cada pasaje elegible se lee entero; los que comparten documento se juzgan por separado para ambas preguntas. No basta pertenecer a la misma norma ni mencionar palabras similares.

2: el pasaje contiene regla explícita del punto consultado (responsabilidad por pérdidas sin autenticación reforzada; contratación independiente/seguro adicional/consentimiento en art27; canal para pagos anticipados/adelantos en29.1.4), incluida su contraparte anterior aunque no contenga la adición posterior. Debe permitir citar sustento directo en ese lado. Contenido idéntico o complementario en otro pasaje también puede sostener directamente el punto, sin restringir por título.

1: aporta contexto específico necesario o útil para interpretar ese punto, por ejemplo excepción de autenticación, definición de autenticación reforzada, información/condiciones concretas del seguro adicional, modalidad de pago anticipado o adelanto, o alcance/canal estrechamente relacionado. No se extiende a todo gobierno, seguridad, conducta, contratación o transparencia generales. Razón debe explicitar el vínculo interpretativo y la limitación.

0: tema distinto o regla demasiado general para contribuir a la comparación específica. Un extracto temático representativo ancla la razón, sin afirmar que demuestra ausencia jurídica global. No se asigna por defecto ni por regex.

no_juzgable: texto ilegible/incompleto de forma material para decidir relevancia, fuente/identidad sin resolver o cita no verificable. Se conserva fuera de qrels numéricos y se declara denominador faltante; no se transforma en0.

Antes/después son lados documentales declarados por el par, no vigencia inferida. Citas exactas con offsets Unicode0/end-exclusive contra raw local; no limpieza silenciosa. Grados1/2 conservan toda evidencia pertinente no recuperada. Exhaustividad significa358 relaciones de inventario si los conteos coinciden; no exhaustividad jurídica ni certificación de fragmentación. Umbrales018 permanecen intactos, sin evaluarlos aquí. No rounds repetidos para obtener acuerdo.
