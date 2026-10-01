# SK06/SK08 protected evidence217

Creator Z, SK06 0.1.17 / SK08 0.1.4 provisional.216 completed33SQL plus certificate/registry, then correctly blocked publication: project writer33b6f37c-7e6a-489f-b313-f886418b0319 has WRITE_VOLUME on entire release_artifacts, granted117 for Job106 sbs-refresh. Keep that grant and owner-only publication boundary unchanged.

Create managed volume neptuno_manuel_arguelles.sbs_radar.genie_evidence_217 as operator, verify owner sociosdosmilveintiseis@gmail.com, grant AppSP a947eccf-5f94-4369-a3d4-8f83b4ea98a1 READ_VOLUME only. Prefix /Volumes/neptuno_manuel_arguelles/sbs_radar/genie_evidence_217/registry. No writer grants, no ownership mutation. Plan limits1create/1additivePATCH/0SQL/0starts; exclusive durable intents and GET reconciliation, no automatic retry. Reject existing unowned volume, partial grants and any nonowner WRITE_VOLUME/ALL_PRIVILEGES/MANAGE including inherited grants. Verify parent metadata and effective privileges before creation; new volume alone does not remove inherited write permissions. Preserve unrelated grants/resources.

Official sources reviewed2026-09-29: https://docs.databricks.com/aws/en/volumes/utility-commands and https://docs.databricks.com/aws/en/volumes/privileges . Create requires USE_CATALOG/USE_SCHEMA/CREATE_VOLUME. SDK0.102.0 create does not accept owner; verify returned owner rather than silently transferring it.

Runtime overlay changes exactly3files: server-template098.evidence_prefix, rotation098.server_template_sha256, bootstrap098.rotation_config_sha256. Existing names avoid app.yaml changes. Packager must update corresponding chunks logical hashes and source manifest. App redeploy required; snapshots, policy invariants, reader identity and TTLs unchanged. Publisher overlay contains equivalent server068 and rotation078 copies with new prefix/path/hash. Root executes metadata plan using existing reviewed SDK session; no new executor framework.

Next publisher must select these reviewed configs explicitly and replace hardcoded old volume check with exact new volume gate BEFORE readback, then recheck before Files publication. Files publish status create-only, immutable generation hash, mutable current pointer with readback using existing validators. No grants or creation inside publisher.

216 effective expiry is min(registry1790723206589, oldestread1790722853966+300000)=1790723153966, 2026-09-29T23:05:53.966Z. No TTL/date extension. Reuse only while RotationReader validates with actual clock; deployment/setup now exceeds this window. Preserve36freshSQL, next33 totals69; legacy99/112 unchanged and separate.

Three offline tests pass for exact config deltas/hash closure, shared publisher/runtime bindings and additive plan. No cloud/auth/grant/create/SQL executed by constructor. Root prerequisite receipt proposed runs/sk06-protected-evidence-217-cloud-verified.json for deployment218 and publisher219. Review plan and configs separately from actual cloud acceptance.
