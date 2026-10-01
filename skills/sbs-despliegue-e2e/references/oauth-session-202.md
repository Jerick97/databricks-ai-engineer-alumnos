# SK12 / CreatorZ — issuer de callback202

Causa real informada por coordinador mediante CUA: callback201incluye claves `code`, `iss`, `state`; la vista AX inicial truncada mostraba solamente code. Issuer público observado: `https://dbc-0410b264-20c7.cloud.databricks.com/oidc`. El parser201exigía exactamente code/state, por lo que rechazó ese callback antes del exchange. No se guardaron valores de código o state; no se omite validación state.

Corrección mínima: aceptar code/state y opcionalmente iss, este último sólo si coincide exactamente con HOST + `/oidc`. Rechazar issuer vacío/ajeno/con slash adicional, claves desconocidas, duplicados y parámetros faltantes. Entregar únicamente code/state al Consent.exchange_callback_parameters del SDK; éste sigue validando state antes de llamar al token endpoint. Host, cliente, scopes, callback8022, límites y API de llamada permanecen iguales a201. Sin nuevo diagnóstico general ni cambio de permisos.

Evidencia oficial: PythonSDK0.102.0 `Consent.exchange_callback_parameters` exige code/state pero ignora campos adicionales; GoSDK0.104.0 `credentials/u2m/callback.go` extrae r.FormValue(code/state) sin imponer conjunto exacto. Validar issuer adicional es específico y acotado al workspace aprobado.

Código202 independiente;200/201yfreezes intactos. Doce pruebas offline PASS, incluidas issuer exacto, incorrecto/vacío, duplicados/unknown/missingstate y rechazo SDK de state erróneo sin token exchange. Primer RED202sobre diagnóstico sin módulo se conserva como historia; coordinador identificó issuer antes de implementarlo y scope final cambió a esta corrección. REDissuer202por módulo ausente conservado. No se ejecutó nueva autenticación ni browser/HTTP real por constructor. Login real y aceptaciónE2E siguen pendientes del coordinador.
