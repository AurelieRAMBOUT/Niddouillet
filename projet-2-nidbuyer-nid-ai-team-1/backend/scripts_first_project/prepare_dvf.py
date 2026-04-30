"""Prepare a clean Toulon DVF dataset from raw yearly files.

Usage:
    python analysis/prepare_dvf.py

Expected input files:
    donnees/ValeursFoncieres-2024.txt
    donnees/ValeursFoncieres-2025-S1.txt

Output:
    data/dvf_toulon.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


RAW_FILES = [
    Path("donnees/ValeursFoncieres-2024.txt"),
    Path("donnees/ValeursFoncieres-2025-S1.txt"),
]

OUTPUT_PATH = Path("data/dvf_toulon.csv")
INSEE_TOULON = "83137"
ALLOWED_TYPES = {"Appartement", "Maison"}


def parse_french_float(series: pd.Series) -> pd.Series:
    """Convert French decimal strings like '123456,78' to float."""
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def load_and_filter_raw(path: Path) -> pd.DataFrame:
    """Load one raw DVF file and apply assignment filters."""
    if not path.exists():
        raise FileNotFoundError(f"Raw DVF file not found: {path}")

    usecols = [
        "Date mutation",
        "Nature mutation",
        "Valeur fonciere",
        "Code postal",
        "Commune",
        "Code departement",
        "Code commune",
        "Type local",
        "Surface reelle bati",
        "Nombre pieces principales",
        "Surface terrain",
    ]

    chunks = []
    for chunk in pd.read_csv(path, sep="|", dtype=str, low_memory=False, chunksize=200_000):
        c = chunk[usecols].copy()
        c["Code departement"] = c["Code departement"].astype(str).str.strip().str.zfill(2)
        c["Code commune"] = c["Code commune"].astype(str).str.strip().str.zfill(3)
        c["code_commune_full"] = c["Code departement"] + c["Code commune"]
        c["Type local"] = c["Type local"].astype(str).str.strip()

        mask = (c["code_commune_full"] == INSEE_TOULON) & (c["Type local"].isin(ALLOWED_TYPES))
        filtered = c.loc[mask].copy()
        if not filtered.empty:
            chunks.append(filtered)

    if not chunks:
        return pd.DataFrame(columns=usecols + ["code_commune_full"])
    return pd.concat(chunks, ignore_index=True)


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types, remove bad rows, and compute derived metrics."""
    renamed = df.rename(
        columns={
            "Date mutation": "date_mutation",
            "Nature mutation": "nature_mutation",
            "Valeur fonciere": "valeur_fonciere",
            "Code postal": "code_postal",
            "Commune": "nom_commune",
            "Code departement": "code_departement",
            "Code commune": "code_commune_suffix",
            "Type local": "type_local",
            "Surface reelle bati": "surface_reelle_bati",
            "Nombre pieces principales": "nombre_pieces_principales",
            "Surface terrain": "surface_terrain",
        }
    ).copy()

    renamed["code_commune"] = INSEE_TOULON
    renamed["date_mutation"] = pd.to_datetime(renamed["date_mutation"], format="%d/%m/%Y", errors="coerce")
    renamed["valeur_fonciere"] = parse_french_float(renamed["valeur_fonciere"])
    renamed["surface_reelle_bati"] = pd.to_numeric(renamed["surface_reelle_bati"], errors="coerce")
    renamed["nombre_pieces_principales"] = pd.to_numeric(
        renamed["nombre_pieces_principales"], errors="coerce"
    )
    renamed["surface_terrain"] = pd.to_numeric(renamed["surface_terrain"], errors="coerce")

    # Keep sales with enough information for price analysis.
    cleaned = renamed[(renamed["nature_mutation"] == "Vente")].copy()
    cleaned = cleaned.dropna(subset=["date_mutation", "valeur_fonciere", "surface_reelle_bati"])
    cleaned = cleaned[cleaned["surface_reelle_bati"] > 0]

    cleaned["prix_m2"] = cleaned["valeur_fonciere"] / cleaned["surface_reelle_bati"]

    # Simple outlier filter for robust visualizations.
    cleaned = cleaned[(cleaned["prix_m2"] >= 500) & (cleaned["prix_m2"] <= 20_000)]
    cleaned = cleaned[(cleaned["valeur_fonciere"] >= 20_000) & (cleaned["valeur_fonciere"] <= 2_000_000)]

    cleaned = cleaned.drop_duplicates(
        subset=["date_mutation", "valeur_fonciere", "code_postal", "type_local", "surface_reelle_bati"]
    )

    cleaned = cleaned.sort_values("date_mutation").reset_index(drop=True)

    final_cols = [
        "date_mutation",
        "nature_mutation",
        "valeur_fonciere",
        "prix_m2",
        "code_postal",
        "nom_commune",
        "code_departement",
        "code_commune",
        "type_local",
        "surface_reelle_bati",
        "nombre_pieces_principales",
        "surface_terrain",
    ]
    return cleaned[final_cols]


def main() -> None:
    frames = [load_and_filter_raw(path) for path in RAW_FILES]
    merged = pd.concat(frames, ignore_index=True)
    cleaned = clean_dataset(merged)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows: {len(cleaned)}")
    print(f"Type repartition: {cleaned['type_local'].value_counts().to_dict()}")
    print(f"Prix/m2 median: {cleaned['prix_m2'].median():.2f}")


if __name__ == "__main__":
    main()

# ..venv\Scripts\python.exe analysis/prepare_dvf.py