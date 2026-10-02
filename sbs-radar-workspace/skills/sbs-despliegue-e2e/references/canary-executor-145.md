# Ejecutor acotado145

Nueva admisión para canary141, independiente del gate final133. Reutilizar ScopedApi/services080 y serializers SDK0.102.0: host/App/prefix cerrados, multipartRAW sin overwrite, cero retries, timeout15/180s y lectura acotada. El ejecutor145 añade límites por tipo de efecto y HTTPtotal, sin copiar un clienteHTTP distinto.

Preflight verifica freeze141 y sus entradas, los218archivos del paquete held y autonomía053. Antes de Config/auth o efectos exigir revisión145 ligada al freeze145. Autenticar normalmente antes de crear admisión; error de caché no gasta un estado nuevo ni autoriza bypass. Una admisión exclusiva impide reiniciar intentos/resets.

Materializar la copia con expiry absoluto de30min. Permitir únicamente el cambio de canary141-config.json que expresa ese expiry; cualquier otro drift impide subir. Ligarlo al manifest y path remoto exclusivo. Verificar App/SP/client y ausencia de despliegue activo antes de mutar; con despliegue activo se necesita un plan de rollback separado, no sustitución silenciosa.

Una intención durable antes de cada mkdir/upload/start/deploy. Subida ambigua sólo permite readbackRAW por hash, nunca reenvío. Start/deploy ambiguos sólo permiten GETreconciliación. Máximo218uploads, unmkdir por directorio derivado,1startcondicional,1deploy,1600HTTPtotal,20observaciones de start y20deploy. Ningún API de grants/SQL/recursosnuevos o stop está habilitado en ScopedApi080; root coordina stop explícito y evidencias tras deploy.

Resultado deployed_linux_evidence_pending no declara saludLinux ni calidad. Capturar root /health,/evidence/logs por separado, mantener resultados fallidos y control del compute. El watchdogcanary acaba el proceso, no garantiza que Apps deje de facturar. La revisión145 y esta admisión nunca sustituyen Astra125, revisión destino final, identidad real, permisos o UI.
