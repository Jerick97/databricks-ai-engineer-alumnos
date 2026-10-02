# Fase S independiente — publicación inicial

Configuración: `deployment/phase-s-017.json`. Publicador revisado: SK06 016, ocho tablas/164 filas del export002, incluida su separación de 135 páginas y 6 artículos. No requiere espacio Genie, Job, app, endpoints de generación ni permiso de los SP. No transfiere propiedad: utiliza el instalador existente `sociosdosmilveintiseis@gmail.com`, ID observado `76826984571984`, perfil normal `databricks-ai-engineer-aws`, host fijado, schema UUID `ff244e9c-7d34-4c2d-8d74-a33292cd5f2c`, warehouse `828756322bedff37`. Todos se revalidan; los GET históricos no son prueba de vigencia.

Comando local reproducible, sin SDK ni red:

```sh
PYTHONPATH=src .venv/bin/python runs/sk12-phase-s-017.py
```

Después de autorización real, el servidor registra en `deployment/phase-s-017-authorization.json` la aceptación exacta usando el esquema de `deployment/phase-s-017-authorization.template.json`: identidad autorizante, hash de configuración, aceptación del coste desconocido, opción de start, inicio y fin de ventana de hasta **30 minutos**. El archivo es capacidad del servidor, no prueba criptográfica ni entrada de la web. El template pendiente no permite ejecutar. No contiene credenciales.

Invocación futura exacta, **no ejecutada en construcción**:

```sh
PYTHONPATH=src .venv/bin/python runs/sk12-phase-s-017.py --execute --authorization deployment/phase-s-017-authorization.json --attempt-id initial
```

Esta invocación guarda un intento local antes del SDK y utiliza `deployment/state/phase-s-017/{journal,certificates,registry}`. Un archivo de intento existente no se sobrescribe. Una recuperación revisada puede usar otro `attempt-id` dentro de una autorización vigente; comparte siempre el mismo journal para impedir repetir mutaciones. Los archivos de journal deben conservarse en almacenamiento local servidor durable; la pérdida no autoriza adoptar tablas existentes.

## Actividad y límites

La autorización puede incluir arrancar **ese mismo warehouse** si se observa STOPPED. Secuencia ejecutable: GET identidad/estado; guardar intención de start exclusiva; un POST `/api/2.0/sql/warehouses/828756322bedff37/start`; hasta tres GET separados por 5 segundos. Un resultado ambiguo no provoca otro start. STARTING permanece pendiente si no alcanza RUNNING; una próxima observación puede continuar si ya está RUNNING. No resize, cambios de auto-stop/ACL, stop/delete ni recursos nuevos. La actividad tiene un límite separado de cuatro GET y un POST, 32 KiB/respuesta y timeout de socket acotado; la publicación conserva sus propios límites.

Ya RUNNING: publicar por el plan exacto `ec0832f9e5eb3dc1acc326d6499b31ad95d1e5d9be5ca363ca1b5eaae0974715`, con CREATE exclusivo e INSERT parametrizada. Camino normal: 80 SQL (16 mutaciones +64 lecturas) y32 GET de historial. Cap por instancia:112 SQL y512 solicitudes HTTP workspace; **hasta5 llamadas adicionales** del control de actividad. OAuth queda fuera de esas cuotas. Los caps se reinician al construir otra instancia, aunque el journal conserva los16 intentos únicos de mutación. No son un límite monetario acumulativo.

La ventana de30 minutos limita la **admisión de nuevos SQL**, incluidos los readbacks. No cancela una consulta ya admitida ni garantiza que compute se detenga al vencimiento. El warehouse es compartido, con auto-stop de10 minutos observado históricamente; se registra su valor actual sin alterarlo. No se envía stop automático que pueda afectar trabajo ajeno. Al cierre se deja el intento/certificado/registro y la actividad observada; queda exposición residual a consultas en curso, actividad ajena y al periodo idle. No atribuir detención ni facturación cero a que el script terminó. Una limpieza o stop requeriría observar actividad y alcance propio; no se improvisa aquí.

## Qué falta decidir

Una sola aprobación concreta de S puede cubrir la publicación de estas ocho tablas y el start opcional del warehouse existente, con ventana de admisión de30 minutos y exposición variable posterior. El precio SQL AWS aplicable no se obtuvo: **coste total desconocido**. Los US$100 del spec no son crédito ni cap autorizado. No hace falta resolver precios de Genie/modelos/apps para esta fase.

Los cuatro textos de `server_policy_assumptions_unobserved` registran la **elección técnica del ejecutor** del perfil piloto `trusted_admin_observed_v1`: administradores confiables, mantenimiento exclusivo de las tablas durante publicación/readback, conservación de versiones y ausencia de ABAC heredada que altere las tablas. Son supuestos no observados, no afirmaciones certificadas ni atestaciones que deba inventar el usuario. No existe un gate adicional de aceptación humana de esos textos. La autorización humana se limita al gasto/start/ventana. Permanecen obligatorios los checks reales de identidad, propietario, filtros/máscaras, filas y versiones/historial; un fallo observado se rechaza, nunca se cubre con el supuesto.

S17-01/02: se comprueba vigencia después de autenticación e inmediatamente antes de despachar start/SQL; no se cancelan solicitudes ya admitidas. La intención de start y cada creación/reemplazo del resultado sincronizan archivo y directorio antes del efecto dependiente. Un fallo de persistencia impide iniciar el POST. Las pruebas verifican secuencia de fsync y fallos inyectados, no simulan pérdida de energía real.

Salida acotada: certificado real y registro local solo si se verifican tablas, versiones, filas e historial real. No se crea Genie, no se concede SELECT al lector, no se mezcla la tabla control ni se afirma E2E. Fallos conservan tablas propias parciales y journal sin DROP/overwrite ni rollback destructivo.
