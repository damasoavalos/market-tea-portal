from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from django.db import connection


@dataclass
class ReportConfig:
    excel_column_map: dict[str, str]
    db_sql: str
    output_excel_name: str


def generate_report(excel_path: Path, output_dir: Path, cfg: ReportConfig) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    df_excel = (
        pd.read_excel(
            excel_path,
            usecols=list(cfg.excel_column_map.keys()),
            engine="openpyxl",
        )
        .rename(columns=cfg.excel_column_map)
        .assign(weight_g=lambda df_n: pd.to_numeric(df_n["weight_g"], errors="coerce"))
        .dropna(subset=["weight_g"])
        .assign(weight_g=lambda df_i: df_i["weight_g"].astype(int))
    )
    df_excel["tea_id"] = (
        df_excel["tea_id"]
        .astype(str)
        .str.split("-", n=1)
        .str[0]
        .str.strip()
        .astype(int)
    )
    df_db = pd.read_sql_query(cfg.db_sql, connection)

    df_joined = df_excel.merge(df_db, on="tea_id", how="inner")
    df_ludify_whole_package = df_joined[
        (df_joined["package_type"] == "Ludify") &
        (df_joined["weight_g"] == df_joined["package_grams"])
        ].copy()
    df_ludify_whole_package = df_ludify_whole_package[[
        "tea_id",
        "tea_name",
        "weight_g",
        "quantity_sold",
        "package_type",
        "package_grams",
    ]].sort_values("tea_name")
    df_sold_by_grams = df_joined.loc[
        ~df_joined.index.isin(df_ludify_whole_package.index)
    ].copy()
    df_sold_by_grams["sold"] = (
            df_sold_by_grams["weight_g"] * df_sold_by_grams["quantity_sold"]
    )
    df_by_grams_agg = (
        df_sold_by_grams
        .groupby([
            "tea_id",
            "tea_name",
            "category",
            "jar_capacity_g",
            "package_type",
            "package_grams"
        ], as_index=False)
        .agg(
            sold=("sold", "sum"),
            record_count=("tea_id", "count"),
        )
    )

    EXCEL_COLUMN_LABELS = {
        "tea_id": "Tea ID",
        "tea_name": "Tea Name",
        "weight_g": "Weight (g)",
        "quantity_sold": "Quantity Sold",
        "sold": "Total Sold (g)",
        "record_count": "Number of Records",
        "category": "Category",
        "package_type": "Package Type",
        "package_grams": "Package Size (g)",
        "jar_capacity_g": "Jar Capacity (g)",
    }
    EXPORT_COLUMNS_WHOLE_PACKAGES = [
        "tea_id",
        "tea_name",
        "package_grams",
        "quantity_sold",
    ]
    EXPORT_COLUMNS_SOLD_BY_GRAMS = [
        "tea_id",
        "tea_name",
        "category",
        "package_type",
        "sold",
        "jar_capacity_g",
    ]

    df_ludify_export = (df_ludify_whole_package[EXPORT_COLUMNS_WHOLE_PACKAGES]
    .rename(columns=EXCEL_COLUMN_LABELS)
    )
    df_by_grams_export = (df_by_grams_agg[EXPORT_COLUMNS_SOLD_BY_GRAMS]
    .rename(columns=EXCEL_COLUMN_LABELS)
    )




    out_path = output_dir / "report.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_ludify_export.to_excel(writer, sheet_name="Whole Packages", index=False)
        df_by_grams_export.to_excel(writer, sheet_name="Sold by grams", index=False)

        for sheet_name, df in {
            "Whole Packages": df_ludify_export,
            "Sold by grams": df_by_grams_export,
        }.items():
            worksheet = writer.sheets[sheet_name]
            for i, col in enumerate(df.columns, start=1):
                max_len = max(
                    df[col].astype(str).map(len).max(),
                    len(col),
                )
                worksheet.column_dimensions[
                    worksheet.cell(row=1, column=i).column_letter
                ].width = max_len + 2

    return out_path
