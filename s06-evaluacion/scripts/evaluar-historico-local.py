"""Evalúa evidencias ejecutadas de S05 sin consultar Databricks.

Uso: python evaluar-historico-local.py --notebook RUTA.ipynb --out-dir DIRECTORIO
Los resultados son provisionales: no sustituyen una corrida nueva de S06.
"""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path


EXPECTED_TOOLS = {
    "venta": ["ventas_categoria"],
    "reposicion": ["productos_reponer"],
    "documental": ["buscar_documentos"],
    "mixta": ["ventas_categoria", "buscar_documentos"],
    "falta_anio": [],
    "sin_costos": [],
    "escritura": [],
}
DOCUMENT_CASES = {"documental", "mixta"}
RELEVANT_DOC = "politica_devoluciones"


class Tables(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def extract_table(notebook: dict, required: set[str]) -> list[dict[str, str]]:
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            html = output.get("data", {}).get("text/html")
            if not html:
                continue
            parser = Tables()
            parser.feed("".join(html) if isinstance(html, list) else html)
            for table in parser.tables:
                if table and required <= set(table[0]):
                    if any(len(row) != len(table[0]) for row in table[1:]):
                        raise ValueError("Tabla HTML incompleta en el notebook ejecutado")
                    return [dict(zip(table[0], row)) for row in table[1:]]
    raise ValueError(f"No se encontró la tabla con columnas {sorted(required)}")


def canonical_tool(name: str) -> str:
    return name.split("__")[-1].split(".")[-1]


def score_case(row: dict[str, str], oracle: dict[tuple[str, int], float]) -> tuple[dict, dict]:
    case_id = row["caso"]
    calls = json.loads(row["llamadas_json"])
    if not isinstance(calls, list):
        raise ValueError(f"{case_id}: llamadas_json no es una lista")
    actual_tools = [canonical_tool(call["tool"]) for call in calls]
    expected_tools = EXPECTED_TOOLS[case_id]
    answer = row["respuesta"]
    expected: dict = {"tools": expected_tools}
    scores: dict = {
        "caso": case_id,
        "trace_id_s05": row["trace_id"],
        "seleccion_herramientas": sorted(actual_tools) == sorted(expected_tools),
        "herramientas_sin_error": all(call.get("resultado", {}).get("ok") is True for call in calls) if calls else None,
        "cifra_respuesta_vs_sql_previo": None,
        "cifra_herramienta_vs_sql_previo": None,
        "precision_documental": None,
        "recall_documental": None,
        "latencia_segundos": None,
        "calidad_respuesta_humana": None,
    }
    if case_id in {"venta", "mixta"}:
        category, year = "Bebidas", 2026
        if (category, year) not in oracle:
            raise ValueError("Falta Bebidas 2026 en el SQL de referencia previo de S05")
        total = oracle[(category, year)]
        expected["venta_neta_sql_previo"] = total
        scores["cifra_respuesta_vs_sql_previo"] = f"{total:.2f}" in answer.replace(",", "")
        values = [c.get("resultado", {}).get("datos", {}).get("venta_neta") for c in calls
                  if canonical_tool(c["tool"]) == "ventas_categoria"]
        scores["cifra_herramienta_vs_sql_previo"] = any(
            value is not None and abs(float(value) - total) <= 0.01 for value in values
        )
    if case_id in DOCUMENT_CASES:
        expected["relevant_docs"] = [RELEVANT_DOC]
        retrieved = {str(doc["documento_id"]) for call in calls
                     if canonical_tool(call["tool"]) == "buscar_documentos"
                     for doc in call.get("resultado", {}).get("documentos", [])}
        scores["precision_documental"] = len(retrieved & {RELEVANT_DOC}) / len(retrieved) if retrieved else 0.0
        scores["recall_documental"] = float(RELEVANT_DOC in retrieved)
    dataset_row = {
        "case_id": case_id,
        "inputs": {"question": row["pregunta"]},
        "expectations": expected,
        "observed_s05": {"answer": answer, "audit": calls, "trace_id": row["trace_id"]},
    }
    return dataset_row, scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, required=True, help="notebook.ipynb ejecutado de S05")
    parser.add_argument("--out-dir", type=Path, required=True, help="directorio para JSON provisionales")
    args = parser.parse_args()
    source = args.notebook.read_bytes()
    notebook = json.loads(source)
    rows = extract_table(notebook, {"caso", "pregunta", "respuesta", "trace_id", "llamadas_json"})
    oracle_rows = extract_table(notebook, {"categoria", "anio", "venta_neta"})
    oracle = {(row["categoria"], int(row["anio"])): float(row["venta_neta"]) for row in oracle_rows}
    found = {row["caso"] for row in rows}
    if len(rows) != len(EXPECTED_TOOLS) or found != set(EXPECTED_TOOLS):
        raise ValueError(f"Casos históricos inesperados: {sorted(found)}")
    dataset, scores = [], []
    for row in rows:
        item, score = score_case(row, oracle)
        dataset.append(item)
        scores.append(score)
    dataset_bytes = json.dumps(dataset, ensure_ascii=False, sort_keys=True).encode("utf-8")
    metrics = {
        "casos_historicos": len(scores),
        "seleccion_herramientas": sum(s["seleccion_herramientas"] for s in scores),
        "casos_con_herramientas": sum(s["herramientas_sin_error"] is not None for s in scores),
        "herramientas_sin_error": sum(s["herramientas_sin_error"] is True for s in scores),
        "cifras_comparadas_con_sql_previo": sum(s["cifra_respuesta_vs_sql_previo"] is not None for s in scores),
    }
    report = {
        "session": "S06", "mode": "replay_historico_s05", "complete": False,
        "source_notebook": str(args.notebook), "source_sha256": hashlib.sha256(source).hexdigest(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(), "metrics": metrics,
        "limitations": [
            "Son ejecuciones de S05, no inferencias nuevas del dataset de diez casos de S06.",
            "Genie no se reejecutó: el SQL warehouse de Free Edition no inicia.",
            "No hay latencia por caso en la tabla exportada ni juicio LLM nuevo.",
            "Las etiquetas documentales y las respuestas requieren revisión humana.",
            "No satisface por sí solo la entrega final ni demuestra calidad actual del agente.",
        ],
    }
    artifacts = {
        "dataset_s06_historico.json": dataset,
        "scores_s06_historico.json": scores,
        "evaluacion_s06_historica.json": report,
    }
    existing = [str(args.out_dir / name) for name in artifacts if (args.out_dir / name).exists()]
    if existing:
        raise FileExistsError(f"No se sobrescriben artefactos existentes: {existing}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in artifacts.items():
        path = args.out_dir / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(path)
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()
