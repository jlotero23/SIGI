"""Carga, limpieza y preparación del dataset de ventas."""

from pathlib import Path
import shutil

import pandas as pd

from ..config import DEFAULT_DATASET, DATA_DIR


REQUIRED_COLUMNS = {
    "fecha",
    "tienda",
    "categoria de producto",
    "vendedor",
    "producto",
    "cantidad",
    "precio",
    "total",
}


def ensure_default_dataset() -> Path:
    """Copia el dataset académico a data/ventas.csv si no existe."""
    if DEFAULT_DATASET.exists():
        return DEFAULT_DATASET

    source = (
        DATA_DIR.parent
        / "Dataset"
        / "extracted"
        / "Productos_vendidos_portienda .csv"
    )
    if not source.exists():
        zip_path = DATA_DIR.parent / "Dataset" / "archive.zip"
        if zip_path.exists():
            import zipfile

            extract_dir = DATA_DIR.parent / "Dataset" / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            source = next(extract_dir.glob("*.csv"), source)

    if source.exists():
        shutil.copy2(source, DEFAULT_DATASET)
    return DEFAULT_DATASET


def load_sales_data(file_path: Path | None = None) -> pd.DataFrame:
    """
    Carga y limpia el CSV de ventas.

    Pasos de limpieza:
    - Normalización de nombres de columnas
    - Parseo flexible de fechas (formatos mixtos en el dataset)
    - Eliminación de filas inválidas
    - Conversión numérica de cantidad y precio
    """
    path = file_path or ensure_default_dataset()
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el dataset en {path}")

    # El dataset académico puede venir en UTF-8 o Latin-1 (caracteres especiales)
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, encoding=encoding, on_bad_lines="skip")
            break
        except UnicodeDecodeError:
            continue
    else:
        df = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")

    # Normalizar encabezados
    df.columns = [c.strip().lower() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes en el dataset: {missing}")

    # Limpiar fechas (el dataset mezcla 01/02/2026 y 1/13/2026)
    df["fecha"] = pd.to_datetime(df["fecha"], format="mixed", dayfirst=False, errors="coerce")
    df = df.dropna(subset=["fecha", "producto", "cantidad"])

    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(float)
    df["precio"] = pd.to_numeric(df["precio"], errors="coerce").fillna(0).astype(float)
    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0).astype(float)

    # Texto limpio
    for col in ["tienda", "categoria de producto", "producto", "vendedor"]:
        df[col] = df[col].astype(str).str.strip()

    df = df[df["cantidad"] > 0]
    df = df.sort_values("fecha")
    return df.reset_index(drop=True)


def aggregate_daily_demand(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega la demanda diaria por producto (suma de cantidades vendidas)."""
    daily = (
        df.groupby(["fecha", "producto", "categoria de producto"], as_index=False)["cantidad"]
        .sum()
        .rename(columns={"categoria de producto": "categoria", "cantidad": "demanda"})
    )
    return daily


def upload_dataset(content: bytes, filename: str) -> Path:
    """Guarda un nuevo dataset cargado manualmente."""
    dest = DATA_DIR / filename
    dest.write_bytes(content)
    # Validar que se puede leer
    load_sales_data(dest)
    # Si es válido, reemplazar ventas principal
    shutil.copy2(dest, DEFAULT_DATASET)
    return DEFAULT_DATASET


def get_dataset_summary(df: pd.DataFrame) -> dict:
    """Resumen KPI del dataset para el dashboard."""
    return {
        "total_registros": int(len(df)),
        "fecha_inicio": df["fecha"].min().strftime("%Y-%m-%d"),
        "fecha_fin": df["fecha"].max().strftime("%Y-%m-%d"),
        "productos_unicos": int(df["producto"].nunique()),
        "tiendas": int(df["tienda"].nunique()),
        "categorias": int(df["categoria de producto"].nunique()),
        "demanda_total": float(df["cantidad"].sum()),
        "ventas_totales": float(df["total"].sum()),
    }
