import math
from typing import Any

import pandas as pd


def distance(a: list[float], b: list[float]) -> float:
    """Calcule la distance euclidienne entre deux vecteurs."""
    if len(a) != len(b):
        raise ValueError("Les vecteurs doivent avoir la même longueur")

    total = 0.0
    for i in range(len(a)):
        total += (a[i] - b[i]) ** 2

    return math.sqrt(total)

def knn_similar(
    target: list[float],
    properties: list[list[float]],
    k: int = 5,
) -> list[tuple[float, list[float]]]:
    """
    Retourne les k biens les plus similaires au bien cible.
    Chaque résultat est un tuple (distance, bien).
    """
    distances = []

    for prop in properties:
        d = distance(target, prop)
        distances.append((d, prop))

    distances.sort(key=lambda x: x[0])
    return distances[:k]


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Retourne le premier nom de colonne existant parmi les candidats."""
    lowered = {c.lower(): c for c in df.columns}
    for col in candidates:
        if col.lower() in lowered:
            return lowered[col.lower()]
    return None


def _detect_surface_column(df: pd.DataFrame) -> str | None:
    """Détecte la colonne de surface selon la source."""
    return _first_existing_column(
        df,
        [
            "surface_m2",
            "surface_reelle_bati",
        ],
    )


def _detect_price_column(df: pd.DataFrame) -> str | None:
    """Détecte la colonne de prix selon la source."""
    return _first_existing_column(
        df,
        [
            "prix_eur",
            "valeur_fonciere",
        ],
    )


def _detect_type_column(df: pd.DataFrame) -> str | None:
    """Détecte la colonne de type de bien selon la source."""
    return _first_existing_column(
        df,
        [
            "type_bien",
            "type_local",
        ],
    )


def _normalize_type_value(value: Any) -> str | None:
    """Normalise le type de bien pour comparer annonces et DVF."""
    if value is None or pd.isna(value):
        return None

    text = str(value).strip().lower()

    mapping = {
        "appartement": "appartement",
        "maison": "maison",
        "studio": "appartement",
    }

    return mapping.get(text, text)


def _min_max_scale(value: float, min_value: float, max_value: float) -> float:
    """Normalise une valeur entre 0 et 1."""
    if max_value == min_value:
        return 0.0
    return (value - min_value) / (max_value - min_value)


def prepare_knn_dataset(
    df: pd.DataFrame,
    surface_col: str | None = None,
    price_col: str | None = None,
    type_col: str | None = None,
) -> pd.DataFrame:
    """
    Prépare un dataset exploitable pour le KNN à partir d'annonces.csv ou dvf_toulon.csv.

    Ajoute :
    - feature_surface_norm
    - feature_price_norm
    - type_bien_norm
    """
    data = df.copy()

    if surface_col is None:
        surface_col = _detect_surface_column(data)
    if price_col is None:
        price_col = _detect_price_column(data)
    if type_col is None:
        type_col = _detect_type_column(data)

    if surface_col is None:
        raise ValueError("Aucune colonne de surface détectée.")
    if price_col is None:
        raise ValueError("Aucune colonne de prix détectée.")

    data = data.dropna(subset=[surface_col, price_col]).copy()

    data[surface_col] = pd.to_numeric(data[surface_col], errors="coerce")
    data[price_col] = pd.to_numeric(data[price_col], errors="coerce")
    data = data.dropna(subset=[surface_col, price_col]).copy()

    if type_col is not None:
        data["type_bien_norm"] = data[type_col].apply(_normalize_type_value)
    else:
        data["type_bien_norm"] = None

    surface_min = float(data[surface_col].min())
    surface_max = float(data[surface_col].max())
    price_min = float(data[price_col].min())
    price_max = float(data[price_col].max())

    data["feature_surface_norm"] = data[surface_col].apply(
        lambda x: _min_max_scale(float(x), surface_min, surface_max)
    )
    data["feature_price_norm"] = data[price_col].apply(
        lambda x: _min_max_scale(float(x), price_min, price_max)
    )

    return data


def row_to_feature_vector(
    row: pd.Series,
    surface_feature_col: str = "feature_surface_norm",
    price_feature_col: str = "feature_price_norm",
) -> list[float]:
    """Transforme une ligne préparée en vecteur numérique pour KNN."""
    return [
        float(row[surface_feature_col]),
        float(row[price_feature_col]),
    ]


def find_similar_properties(
    df: pd.DataFrame,
    target_index: int,
    k: int = 5,
    filter_same_type: bool = True,
) -> pd.DataFrame:
    """
    Retourne les k biens les plus similaires à une ligne cible d'un DataFrame.

    Le DataFrame peut provenir de annonces.csv ou dvf_toulon.csv.
    Il est préparé automatiquement si besoin.
    """
    prepared = prepare_knn_dataset(df)

    if target_index not in prepared.index:
        raise ValueError("target_index absent du DataFrame préparé.")

    target_row = prepared.loc[target_index]
    target_vector = row_to_feature_vector(target_row)

    candidates = prepared.drop(index=target_index).copy()

    if filter_same_type and "type_bien_norm" in candidates.columns:
        target_type = target_row.get("type_bien_norm")
        if target_type:
            same_type = candidates["type_bien_norm"] == target_type
            filtered = candidates[same_type].copy()
            if not filtered.empty:
                candidates = filtered

    distances = []
    for idx, row in candidates.iterrows():
        vector = row_to_feature_vector(row)
        d = distance(target_vector, vector)
        distances.append((idx, d))

    distances.sort(key=lambda x: x[1])
    nearest_indices = [idx for idx, _ in distances[:k]]
    nearest_distances = [d for _, d in distances[:k]]

    result = candidates.loc[nearest_indices].copy()
    result["distance_knn"] = nearest_distances
    result = result.sort_values("distance_knn").reset_index(drop=False)

    return result


def find_similar_to_target(
    target: dict[str, Any],
    df: pd.DataFrame,
    k: int = 5,
    filter_same_type: bool = True,
) -> pd.DataFrame:
    """
    Retourne les k biens les plus similaires à une cible externe.

    target attendu :
    {
        "surface_m2": ...,
        "prix_eur": ...,
        "type_bien": ...
    }

    Compatible aussi avec :
    {
        "surface_reelle_bati": ...,
        "valeur_fonciere": ...,
        "type_local": ...
    }
    """
    prepared = prepare_knn_dataset(df)

    surface_col = _detect_surface_column(prepared)
    price_col = _detect_price_column(prepared)
    type_col = _detect_type_column(prepared)

    if surface_col is None or price_col is None:
        raise ValueError("Impossible de détecter les colonnes surface/prix.")

    target_surface = target.get("surface_m2", target.get("surface_reelle_bati"))
    target_price = target.get("prix_eur", target.get("valeur_fonciere"))
    target_type = target.get("type_bien", target.get("type_local"))

    if target_surface is None or target_price is None:
        raise ValueError("La cible doit contenir une surface et un prix.")

    surface_min = float(prepared[surface_col].min())
    surface_max = float(prepared[surface_col].max())
    price_min = float(prepared[price_col].min())
    price_max = float(prepared[price_col].max())

    target_vector = [
        _min_max_scale(float(target_surface), surface_min, surface_max),
        _min_max_scale(float(target_price), price_min, price_max),
    ]

    candidates = prepared.copy()

    if filter_same_type and type_col is not None and target_type is not None:
        normalized_target_type = _normalize_type_value(target_type)
        same_type = candidates["type_bien_norm"] == normalized_target_type
        filtered = candidates[same_type].copy()
        if not filtered.empty:
            candidates = filtered

    distances = []
    for idx, row in candidates.iterrows():
        vector = row_to_feature_vector(row)
        d = distance(target_vector, vector)
        distances.append((idx, d))

    distances.sort(key=lambda x: x[1])
    nearest_indices = [idx for idx, _ in distances[:k]]
    nearest_distances = [d for _, d in distances[:k]]

    result = candidates.loc[nearest_indices].copy()
    result["distance_knn"] = nearest_distances
    result = result.sort_values("distance_knn").reset_index(drop=False)

    return result