# Requisitos y riesgos

| Requisito | Riesgo | Verificación |
|---|---|---|
| Preservar spans citables | Truncación silenciosa de disposición | Entrada total contando contexto/prefijos/tokens especiales, error antes de inferencia |
| Bundle inmutable | Mezcla modelos con igual dimensión | Identidad hash modelo/revisión/tokenizer/prefijos/chunking |
| Oferta separada de runtime | Endpoint documentado declarado operativo | Preflight real read-only y ejecución controlada separada |
| Coste explícito | null convertido en cero | Uso/precio/estimación/moneda/fuente separados |
| Comparación atribuible | Cambios de múltiples variables | Congelar corpus/qrels/config y reportar paquete si cambia más de un factor |
| Permisos mínimos | Crear compute o enviar secretos | Configuración normal sin volcar tokens ni cuerpos arbitrarios |

Salida: ModelBundle conforme SK01 e informe de capacidades pendientes/verificadas. No produce Answer ni adjudicación normativa.
