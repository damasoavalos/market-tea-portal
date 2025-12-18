from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from django.db import connection


@dataclass
class ReportConfig:
    excel_key_col: str = "code"
    db_table: str = "inventory.tea_products"
    db_key_col: str = "code"
    db_value_col: str = "tea_name"


def generate_report(excel_path: Path, output_dir: Path, cfg: ReportConfig) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    df_excel = pd.read_excel(excel_path, engine="openpyxl")
    if cfg.excel_key_col not in df_excel.columns:
        raise ValueError(
            f"Excel must contain column '{cfg.excel_key_col}'. "
            f"Found: {list(df_excel.columns)}"
        )

    df_excel = df_excel[[cfg.excel_key_col]].dropna().drop_duplicates()
    df_excel[cfg.excel_key_col] = df_excel[cfg.excel_key_col].astype(str).str.strip()

    sql = (
        f"SELECT {cfg.db_key_col}::text AS code, "
        f"{cfg.db_value_col}::text AS tea_name "
        f"FROM {cfg.db_table};"
    )
    df_db = pd.read_sql_query(sql, connection)
    df_db["code"] = df_db["code"].astype(str).str.strip()

    excel_codes = set(df_excel[cfg.excel_key_col])
    db_codes = set(df_db["code"])

    missing_in_db = sorted(excel_codes - db_codes)
    missing_in_excel = sorted(db_codes - excel_codes)
    matched = sorted(excel_codes & db_codes)

    summary = pd.DataFrame(
        {
            "metric": ["excel_unique_codes", "db_unique_codes", "matched", "missing_in_db", "missing_in_excel"],
            "value": [len(excel_codes), len(db_codes), len(matched), len(missing_in_db), len(missing_in_excel)],
        }
    )

    df_missing_in_db = pd.DataFrame({"code": missing_in_db})
    df_missing_in_excel = pd.DataFrame({"code": missing_in_excel})
    df_matched = df_db[df_db["code"].isin(matched)].sort_values("code")

    out_path = output_dir / "report.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="summary")
        df_missing_in_db.to_excel(writer, index=False, sheet_name="missing_in_db")
        df_missing_in_excel.to_excel(writer, index=False, sheet_name="missing_in_excel")
        df_matched.to_excel(writer, index=False, sheet_name="matched")

    return out_path
