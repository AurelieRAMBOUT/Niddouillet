from pathlib import Path
from functools import lru_cache
import os
import re
import unicodedata

import pandas as pd
import requests


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DVF_PATHS = (
    DATA_DIR / "ventes_toulon_avec_quartier.csv",
    DATA_DIR / "dvf_toulon.csv",
)


def _charger_stats_depuis_supabase() -> dict[str, dict]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key:
        return {}
    try:
        headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
        resp = requests.get(
            f"{supabase_url.rstrip('/')}/rest/v1/dvf_quartiers",
            headers=headers,
            params={"select": "*", "limit": "1000"},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
        stats = {}
        for row in rows:
            quartier = str(row.get("quartier") or "")
            if not quartier:
                continue
            key = normaliser_quartier(quartier)
            stats[key] = {
                "quartier": quartier,
                "source_groupement": "quartier",
                "mediane_prix_m2": float(row.get("mediane_prix_m2") or 3400),
                "moyenne_prix_m2": float(row.get("moyenne_prix_m2") or 3400),
                "min_prix_m2": float(row.get("min_prix_m2") or 0),
                "max_prix_m2": float(row.get("max_prix_m2") or 0),
                "nb_transactions": int(row.get("nb_transactions") or 0),
                "prix_m2_values": [],
            }
        return stats
    except Exception:
        return {}


def normaliser_texte(value: str | None) -> str:
    return str(value or "").strip().lower()


def normaliser_quartier(value: str | None) -> str:
    text = normaliser_texte(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\btoulon\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\b(le|la|les|l|de|du|des|d)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normaliser_code_postal(value: str | int | float | None) -> str:
    code = pd.to_numeric(value, errors="coerce")
    if pd.isna(code):
        return normaliser_texte(str(value) if value is not None else None)
    return str(int(code)).zfill(5)


def dvf_path_disponible() -> Path | None:
    return next((path for path in DVF_PATHS if path.exists()), None)


@lru_cache(maxsize=1)
def charger_stats_toulon() -> dict[str, dict[str, float | int | str]]:
    dvf_path = dvf_path_disponible()
    if dvf_path is None:
        return _charger_stats_depuis_supabase()

    df = pd.read_csv(dvf_path)

    if "date_mutation" in df.columns:
        dates = pd.to_datetime(df["date_mutation"], errors="coerce")
        df = df[(dates >= "2024-01-01") & (dates < "2027-01-01")]

    if "nature_mutation" in df.columns:
        df = df[df["nature_mutation"].astype(str).str.strip().eq("Vente")]

    if "code_commune" in df.columns:
        codes = pd.to_numeric(df["code_commune"], errors="coerce").astype("Int64").astype(str).str.zfill(5)
        df = df[codes.eq("83137")]

    if "type_local" in df.columns:
        df = df[df["type_local"].astype(str).str.strip().isin(["Appartement", "Maison"])]

    if "prix_m2" in df.columns:
        df["prix_m2"] = pd.to_numeric(df["prix_m2"], errors="coerce")
    elif {"valeur_fonciere", "surface_reelle_bati"}.issubset(df.columns):
        valeurs = pd.to_numeric(df["valeur_fonciere"], errors="coerce")
        surfaces = pd.to_numeric(df["surface_reelle_bati"], errors="coerce")
        df["prix_m2"] = valeurs / surfaces.where(surfaces > 0)
    else:
        return {}

    df = df[df["prix_m2"].between(500, 20_000)]

    if df.empty:
        return {}

    stats: dict[str, dict[str, float | int | str]] = {}

    for group_col in ("quartier", "quartier_final", "quartier_source", "code_postal"):
        if group_col not in df.columns:
            continue

        df[group_col] = df[group_col].astype(str).str.strip()
        grouped = df[df[group_col].ne("")].groupby(group_col)["prix_m2"].agg(["median", "mean", "min", "max", "count"])

        for group, row in grouped.iterrows():
            key = normaliser_quartier(group) if group_col != "code_postal" else normaliser_code_postal(group)
            if not key:
                continue
            values = (
                df.loc[df[group_col].eq(str(group)), "prix_m2"]
                .dropna()
                .astype(float)
                .sort_values()
                .tolist()
            )

            stats[key] = {
                "quartier": str(group),
                "source_groupement": "code_postal" if group_col == "code_postal" else "quartier",
                "mediane_prix_m2": float(row["median"]),
                "moyenne_prix_m2": float(row["mean"]),
                "min_prix_m2": float(row["min"]),
                "max_prix_m2": float(row["max"]),
                "nb_transactions": int(row["count"]),
                "prix_m2_values": values,
            }

    stats["toulon"] = {
        "quartier": "Toulon",
        "source_groupement": "ville",
        "mediane_prix_m2": float(df["prix_m2"].median()),
        "moyenne_prix_m2": float(df["prix_m2"].mean()),
        "min_prix_m2": float(df["prix_m2"].min()),
        "max_prix_m2": float(df["prix_m2"].max()),
        "nb_transactions": int(df["prix_m2"].count()),
        "prix_m2_values": df["prix_m2"].dropna().astype(float).sort_values().tolist(),
    }

    return stats


def charger_medianes_toulon() -> dict[str, float]:
    stats = charger_stats_toulon()
    return {
        key: float(value["mediane_prix_m2"])
        for key, value in stats.items()
    }


def get_mediane_quartier(bien: dict) -> float | None:
    stats = get_stats_bien(bien)
    if not stats:
        return None
    return float(stats["mediane_prix_m2"])


def get_stats_bien(bien: dict) -> dict | None:
    ville = normaliser_texte(
        bien.get("ville")
        or bien.get("city")
        or bien.get("commune")
        or bien.get("localisation")
    )

    if "toulon" not in ville:
        return None

    quartier = normaliser_texte(
        bien.get("quartier")
        or bien.get("quartier_final")
        or bien.get("quartier_source")
    )

    if not quartier:
        return None

    stats = charger_stats_toulon()
    quartier_normalise = normaliser_quartier(quartier)

    if quartier_normalise in stats:
        return stats[quartier_normalise]

    for quartier_dvf, item in stats.items():
        if quartier_normalise in quartier_dvf or quartier_dvf in quartier_normalise:
            return item

    code_postal = normaliser_code_postal(bien.get("code_postal") or bien.get("postal_code"))
    if code_postal in stats:
        return stats[code_postal]

    return stats.get("toulon")

def get_stats_quartiers_toulon() -> list[dict]:
    stats = charger_stats_toulon()
    stats_affichees = {
        key: item
        for key, item in stats.items()
        if item.get("source_groupement") == "quartier"
    }
    if not stats_affichees:
        stats_affichees = {
            key: item
            for key, item in stats.items()
            if key != "toulon" or len(stats) == 1
        }

    return [
        {
            "quartier": str(item["quartier"]),
            "mediane_prix_m2": round(float(item["mediane_prix_m2"]), 2),
            "moyenne_prix_m2": round(float(item["moyenne_prix_m2"]), 2),
            "min_prix_m2": round(float(item["min_prix_m2"]), 2),
            "max_prix_m2": round(float(item["max_prix_m2"]), 2),
            "nb_transactions": int(item["nb_transactions"]),
        }
        for _, item in sorted(stats_affichees.items())
    ]
