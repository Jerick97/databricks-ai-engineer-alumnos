# SK12 / CreatorZ — puerto explícito y clasificación state203

Antecedente observado por coordinador:202falló con mensaje genérico callback/exchange antes de navegar su URL recién publicada; no empezó199. Un callback anterior sobre8022es hipótesis, no causa probada. No se inspeccionaron códigos, tokens ni state reales.

Cambio acotado: `authenticate(publish_authorization_url, timeout_seconds=180, *, callback_port=8023)` valida entero no booleano en8020..8040, intervalo oficial CLI documentado201. Construye bind127.0.0.1:puerto y redirecthttp://localhost:puerto desde el mismo valor. No escanea ni ocupa puertos por import. Coordinador confirmó8023libre antes de un posible intento; no implica reserva.

La excepción pública exacta `ValueError('state mismatch')` del SDK ahora produce únicamente mensaje fijo `OAuth state mismatch`; las demás conservan genérico seguro. No se transmite texto arbitrario de excepción ni se modifica/elude state. El primer callback con forma válida conserva política failclosed si el SDK lo rechaza. Issuer opcional exacto y demás garantías202intactas; no nuevo retry automático.

Evidencia:18tests offline PASS, incluyen5puertos inválidos, coherencia bind/redirect para8024con discoverydoble sin red, state inválido rechazado por SDKsinexchange, issueryresto de contratos anteriores. No authreal/listenerreal en pruebas.200/201/202yfreezes preservados. Causa de202continúa sin determinar; autenticación y E2Ependientes.
