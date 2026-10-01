# Corrección144: campo requerido rule_set.name

140 falló400 INVALID_PARAMETER_VALUE Missing required field: rule_set.name. Su PUT agotado se conserva, no se reenvía. SDK0.102 RuleSetUpdateRequest declara name requerido, pero from_dict tolera ausencia y serializer lo omite; el constructor140 omitió ese campo.144 añade RULE_NAME exacto en rule_set.name y mantiene también name exterior, etag fresco y todos grants. Fuente primaria SDK local archivada; no nueva búsqueda ni nube por constructor.

Nuevo ledger deployment/state/writer-role144, máximo12HTTP1PUT. Scope writer_role144_user_only y template deployment/writer-role144-review-template.json. Ejecutar PYTHONPATH=src .venv/bin/python -m sbs.operations.writer_role_144 (preflight); tras revisión añadir --execute --review-file deployment/writer-role144-authorization.json --journal deployment/state/writer-role144. Impide overlap106/126/140. Autorización053 persiste; admisión interna <=30min con hashes exactos.

Misma semántica140: OWNER/SPexactos, GETfresh, etag, sólo User aOWNER, preservación demásgrants, GETreadback, intent nunca resend, sin Jobs/tokens/grupos. Cuatrotests PASS; fixtureSDK exige ambosnames y RED reproduce fracaso sinnestedname. No evidencia E2E.143 necesita freshUser observado luego; JobPAUSED/config137/run142 siguen separados. Coste desconocido.
