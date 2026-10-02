# SK12 / CreatorZ — callback alternativo201

Cambio mínimo sobre200 preservado: puerto8022 explícito, URL http://localhost:8022, y diagnóstico seguro stage/errno sin texto proveedor. El coordinador observó200fallar antes de publicar URL porque8020 estaba ocupado por un CLIexistente;8021 también ocupado,8022 disponible en su probe. Este módulo no detiene ni modifica esos procesos. No se inspeccionaron credenciales.

Fuente primaria: https://github.com/databricks/databricks-sdk-go/blob/v0.104.0/credentials/u2m/persistent_auth.go: defaultPort8020, maxPortFallback8040, startListenerWithFallback prueba el intervalo inclusivo y construye RedirectURL http://localhost:puerto. Por tanto8022 pertenece al fallback normal oficial del CLI. Python OAuthClient admite redirect_url público. No se cambia host receptor, cliente, scopes ni duración; se conservan restricciones, CUA, contexto de archivo0600 y sesión en memoria de referencia200.

Código201 independiente conserva200yfreeze200intactos. Contrato igual: authenticate(publicador) devuelve Config para el mismo proceso. Diez pruebas offline PASS: ocho contratos200, puerto oficial8022, bind fallido informa únicamente stage callback-bind/errno48. RED registrado antes del módulo201; tests no ejecutan OAuthreal ni listenerreal. Estado componente: localmente probado; auth/UI/E2E pendientes de coordinador.
