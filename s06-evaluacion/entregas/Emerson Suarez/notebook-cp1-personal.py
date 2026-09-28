# Databricks notebook source
# MAGIC %md
# MAGIC # S06 · CP1 personal · Preparación sin SQL warehouse
# MAGIC Este notebook lee un **borrador local** de once casos: los diez de la consigna y uno adicional.
# MAGIC No ejecuta `%run`, no llama al agente y no consulta Genie. La referencia numérica de Genie
# MAGIC queda pendiente hasta poder calcular un SQL independiente sobre el catálogo personal.
# MAGIC Ejecuta las celdas en orden y revisa las referencias antes de inferir respuestas nuevas.

# COMMAND ----------
from pathlib import Path
import hashlib
import json

carpeta = Path.cwd() / "provisional-local"
dataset_path = carpeta / "dataset_s06_cp1_borrador.json"
referencias_path = carpeta / "referencias_s06_cp1.json"
if not dataset_path.is_file() or not referencias_path.is_file():
    raise FileNotFoundError(
        f"Faltan los JSON de CP1 en {carpeta}. Confirma que hiciste Pull en el Git Folder correcto."
    )
DATA = json.loads(dataset_path.read_text(encoding="utf-8"))
REFS = json.loads(referencias_path.read_text(encoding="utf-8"))
DATASET_HASH = hashlib.sha256(
    json.dumps(DATA, ensure_ascii=False, sort_keys=True).encode("utf-8")
).hexdigest()
assert len(DATA) == 11
assert DATASET_HASH == REFS["dataset_sha256"], "Cambió el dataset: revisa la procedencia y congela un hash nuevo"
assert [d["expectations"]["case_id"] for d in DATA].count("genie") == 1
print("CP1 borrador: 10 casos base + 1 caso propio")
print("Dataset SHA256:", DATASET_HASH)
print("Referencia Genie:", DATA[7]["expectations"]["reference_status"])

# COMMAND ----------
# MAGIC %md
# MAGIC ## CP1.1 · Revisar preguntas y etiquetas antes de inferir
# MAGIC Comprueba las preguntas, las herramientas esperadas y la fuente de cada referencia.
# MAGIC `pending` indica una referencia incompleta; no la puntúes como error ni como cero.

# COMMAND ----------
for row in DATA:
    exp = row["expectations"]
    print(f"{exp['case_id']:<20} | {row['inputs']['question']}")
    print(f"  tools={exp['tools']} | referencia={exp['reference_source']} | estado={exp['reference_status']}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## CP1.2 · Revisar oracles y corpus
# MAGIC La cifra de ventas proviene del SQL de CP0 de S05, ejecutado **antes** de las respuestas
# MAGIC del agente. El texto documental proviene del corpus fuente de S04. Compara ambos con los
# MAGIC datos actuales cuando vuelva el cómputo. El caso adicional usa la ficha de Lácteos.

# COMMAND ----------
print("Ventas:", json.dumps(REFS["sales_reference"], ensure_ascii=False, indent=2))
print("Política:", json.dumps(REFS["document_reference"], ensure_ascii=False, indent=2))
print("Caso propio:", json.dumps(REFS["own_case_reference"], ensure_ascii=False, indent=2))
print("Pendiente:")
for item in REFS["pending"]:
    print("-", item)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Siguiente checkpoint
# MAGIC CP1 está **preparado, no cerrado**. El caso Genie necesita un oracle SQL independiente
# MAGIC del resultado de Genie. Cuando el warehouse vuelva a iniciar, recalcula ese oracle sobre
# MAGIC el catálogo personal, confirma los documentos actuales y congela otra vez el hash. Luego
# MAGIC ejecuta el agente en CP2. El notebook principal del docente permanece intacto.
