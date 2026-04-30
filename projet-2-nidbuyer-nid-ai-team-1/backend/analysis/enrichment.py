import json
import re
from typing import Any

import pandas as pd
import requests

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_URL = f"{DEFAULT_OLLAMA_BASE_URL}/api/generate"

def is_ollama_available(
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout: int = 3,
) -> bool:
    """Vérifie si un serveur Ollama répond."""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False


def ask_llm(
    prompt: str,
    model: str = "llama3",
    url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 60,
) -> str:
    """Appelle un LLM local via Ollama et retourne la réponse texte."""
    response = requests.post(
        url,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extrait le premier objet JSON trouvé dans un texte."""
    text = text.strip()

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Aucun objet JSON détecté dans la réponse LLM.")

    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Le JSON extrait n'est pas un objet.")
    return obj


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Retourne le premier nom de colonne existant parmi une liste de candidats."""
    lowered = {c.lower(): c for c in df.columns}
    for col in candidates:
        if col.lower() in lowered:
            return lowered[col.lower()]
    return None


def _detect_quartier_column(df: pd.DataFrame) -> str | None:
    """Détecte une colonne représentant le quartier."""
    return _first_existing_column(
        df,
        [
            "quartier",
            "district",
            "arrondissement",
            "zone",
            "secteur",
            "localisation",
            "ville_quartier",
        ],
    )


def _detect_text_columns(df: pd.DataFrame) -> list[str]:
    """Détecte les colonnes textuelles potentielles d'une annonce."""
    candidates = [
        "description",
        "texte",
        "titre",
        "title",
        "annonce",
        "resume_annonce",
    ]
    result = []
    lowered = {c.lower(): c for c in df.columns}
    for col in candidates:
        if col.lower() in lowered:
            result.append(lowered[col.lower()])
    return result


def _non_empty_count(series: pd.Series) -> int:
    """Compte le nombre de valeurs texte non vides."""
    return int(series.fillna("").astype(str).str.strip().ne("").sum())


def _choose_best_text_column(df: pd.DataFrame) -> str:
    """
    Choisit la meilleure colonne texte disponible.
    Préfère la colonne la plus remplie parmi les candidates détectées.
    """
    text_cols = _detect_text_columns(df)
    if not text_cols:
        raise ValueError("Aucune colonne texte détectée. Passe text_col explicitement.")

    best_col = text_cols[0]
    best_count = -1

    for col in text_cols:
        count = _non_empty_count(df[col])
        if count > best_count:
            best_count = count
            best_col = col

    return best_col


def _normalize_text(value: Any) -> str:
    """Normalise une valeur en texte propre."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _build_listing_text(
    row: pd.Series,
    preferred_text_col: str | None = None,
) -> str:
    """
    Construit le meilleur texte possible pour une annonce.
    Utilise d'abord la colonne texte préférée, puis complète avec titre/description.
    """
    parts: list[str] = []

    if preferred_text_col and preferred_text_col in row.index:
        preferred_value = _normalize_text(row.get(preferred_text_col))
        if preferred_value:
            parts.append(preferred_value)

    for fallback_col in ["titre", "description", "texte", "annonce", "title", "resume_annonce"]:
        if fallback_col in row.index:
            value = _normalize_text(row.get(fallback_col))
            if value and value not in parts:
                parts.append(value)

    return "\n".join(parts).strip()


def _extract_quartier_from_text(text: str) -> str | None:
    """
    Tente d'extraire un quartier depuis le titre/texte.
    Exemple visé : 'La Serinette, Toulon (83000)' -> 'La Serinette'
    """
    if not text:
        return None

    patterns = [
        r"([A-Za-zÀ-ÿ0-9' -]+),\s*Toulon\s*\(\d{5}\)",
        r"([A-Za-zÀ-ÿ0-9' -]+),\s*Toulon\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            quartier = match.group(1).strip(" -")
            if quartier:
                return quartier

    return None


def add_quartier_fallback(
    df_annonces: pd.DataFrame,
    quartier_col: str | None = None,
    text_col: str | None = None,
    output_col: str = "quartier_source",
) -> pd.DataFrame:
    """
    Ajoute une colonne de quartier robuste :
    - prend la colonne quartier si elle existe et est remplie,
    - sinon tente d'extraire le quartier depuis le texte/titre.
    """
    df = df_annonces.copy()

    if text_col is None:
        text_col = _choose_best_text_column(df)

    if quartier_col is None:
        quartier_col = _detect_quartier_column(df)

    values = []
    for _, row in df.iterrows():
        quartier_value = None
        if quartier_col is not None and quartier_col in df.columns:
            raw_quartier = _normalize_text(row.get(quartier_col))
            if raw_quartier:
                quartier_value = raw_quartier

        if not quartier_value:
            full_text = _build_listing_text(row, preferred_text_col=text_col)
            quartier_value = _extract_quartier_from_text(full_text)

        values.append(quartier_value)

    df[output_col] = values
    return df


def extract_structured_from_text(
    texte_annonce: str,
    model: str = "llama3",
    llm_available: bool | None = None,
) -> dict[str, Any]:
    """
    Extrait des champs structurés depuis le texte d'une annonce.

    Retourne un dict avec des valeurs typées.
    Si le backend LLM est indisponible, retourne une structure vide cohérente.
    """
    defaults: dict[str, Any] = {
        "type_bien": None,
        "surface_m2": None,
        "pieces": None,
        "chambres": None,
        "etage": None,
        "ascenseur": None,
        "balcon_ou_terrasse": None,
        "parking": None,
        "travaux_a_prevoir": None,
        "dpe": None,
        "prix_eur": None,
        "charges_eur_mois": None,
        "quartier": None,
        "atouts": [],
        "inconvenients": [],
    }

    if not isinstance(texte_annonce, str) or not texte_annonce.strip():
        return defaults.copy()

    if llm_available is None:
        llm_available = is_ollama_available()

    if not llm_available:
        return defaults.copy()

    prompt = f"""
Tu es un extracteur d'informations immobilières.
Réponds UNIQUEMENT avec un objet JSON valide.
Pas de markdown. Pas d'explication. Pas de texte avant ou après.
Si l'information est absente, mets null.

Schéma attendu :
{{
  "type_bien": "appartement|maison|studio|autre|null",
  "surface_m2": number|null,
  "pieces": integer|null,
  "chambres": integer|null,
  "etage": integer|null,
  "ascenseur": boolean|null,
  "balcon_ou_terrasse": boolean|null,
  "parking": boolean|null,
  "travaux_a_prevoir": boolean|null,
  "dpe": "A|B|C|D|E|F|G|null",
  "prix_eur": number|null,
  "charges_eur_mois": number|null,
  "quartier": string|null,
  "atouts": [string],
  "inconvenients": [string]
}}

Texte annonce :
\"\"\"{texte_annonce}\"\"\"
""".strip()

    try:
        raw = ask_llm(prompt, model=model)
        data = _extract_json_object(raw)
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        data = {}

    for key, value in defaults.items():
        data.setdefault(key, value)

    if not isinstance(data.get("atouts"), list):
        data["atouts"] = []
    if not isinstance(data.get("inconvenients"), list):
        data["inconvenients"] = []

    return data


def enrich_annonces_structured(
    df_annonces: pd.DataFrame,
    text_col: str | None = None,
    model: str = "llama3",
) -> pd.DataFrame:
    """
    Ajoute des colonnes structurées extraites du texte d'annonce.

    Si text_col n'est pas fourni, choisit automatiquement la colonne texte
    la plus remplie. Le texte effectif utilisé combine la colonne principale
    et des fallbacks utiles comme le titre.
    """
    df = df_annonces.copy()
    if df.empty:
        return df

    if text_col is None:
        text_col = _choose_best_text_column(df)

    llm_available = is_ollama_available()

    extracted_rows = []
    for _, row in df.iterrows():
        full_text = _build_listing_text(row, preferred_text_col=text_col)
        try:
            extracted = extract_structured_from_text(
                full_text,
                model=model,
                llm_available=llm_available,
            )
        except TypeError:
            extracted = extract_structured_from_text(full_text, model=model)
        extracted_rows.append(extracted)

    extracted_df = pd.DataFrame(extracted_rows)
    return pd.concat(
        [df.reset_index(drop=True), extracted_df.reset_index(drop=True)],
        axis=1,
    )


def summarize_by_quartier(
    df_annonces: pd.DataFrame,
    quartier_col: str | None = None,
    text_col: str | None = None,
    max_annonces_per_quartier: int = 30,
    model: str = "llama3",
) -> pd.DataFrame:
    """
    Génère un résumé IA par quartier à partir des annonces.

    Retourne une DataFrame avec :
    - quartier
    - nb_annonces
    - resume
    - profil_acheteur
    - points_forts
    - points_faibles
    """
    df = df_annonces.copy()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "quartier",
                "nb_annonces",
                "resume",
                "profil_acheteur",
                "points_forts",
                "points_faibles",
            ]
        )

    if text_col is None:
        text_col = _choose_best_text_column(df)

    if quartier_col is None:
        quartier_col = _detect_quartier_column(df)
    if quartier_col is None:
        raise ValueError("Aucune colonne quartier détectée. Passe quartier_col explicitement.")

    df = add_quartier_fallback(
        df,
        quartier_col=quartier_col,
        text_col=text_col,
        output_col="quartier_source",
    )
    quartier_group_col = "quartier_source"

    llm_available = is_ollama_available()

    results: list[dict[str, Any]] = []

    grouped = df.groupby(quartier_group_col, dropna=False)
    for quartier, group in grouped:
        q_name = str(quartier).strip() if pd.notna(quartier) and str(quartier).strip() else "Inconnu"

        texts = []
        for _, row in group.head(max_annonces_per_quartier).iterrows():
            full_text = _build_listing_text(row, preferred_text_col=text_col)
            if full_text:
                texts.append(full_text)

        corpus = "\n\n---\n\n".join(texts)

        if not corpus:
            results.append(
                {
                    "quartier": q_name,
                    "nb_annonces": len(group),
                    "resume": "Aucune description exploitable.",
                    "profil_acheteur": None,
                    "points_forts": [],
                    "points_faibles": [],
                }
            )
            continue

        if not llm_available:
            results.append(
                {
                    "quartier": q_name,
                    "nb_annonces": len(group),
                    "resume": "Résumé IA indisponible : backend Ollama non accessible.",
                    "profil_acheteur": None,
                    "points_forts": [],
                    "points_faibles": [],
                }
            )
            continue

        prompt = f"""
Tu es analyste immobilier local.
À partir des annonces ci-dessous pour un quartier, génère UNIQUEMENT un JSON valide.
Pas de markdown. Pas de texte autour.

Schéma :
{{
  "resume": "3 à 5 phrases factuelles",
  "profil_acheteur": "profil acheteur ou investisseur le plus adapté",
  "points_forts": ["..."],
  "points_faibles": ["..."]
}}

Quartier : {q_name}

Annonces :
\"\"\"{corpus}\"\"\"
""".strip()

        try:
            raw = ask_llm(prompt, model=model)
            data = _extract_json_object(raw)
        except (requests.RequestException, ValueError, json.JSONDecodeError):
            data = {
                "resume": "Résumé indisponible (réponse LLM non structurée).",
                "profil_acheteur": None,
                "points_forts": [],
                "points_faibles": [],
            }

        points_forts = data.get("points_forts", [])
        points_faibles = data.get("points_faibles", [])

        if not isinstance(points_forts, list):
            points_forts = []
        if not isinstance(points_faibles, list):
            points_faibles = []

        results.append(
            {
                "quartier": q_name,
                "nb_annonces": len(group),
                "resume": data.get("resume"),
                "profil_acheteur": data.get("profil_acheteur"),
                "points_forts": points_forts,
                "points_faibles": points_faibles,
            }
        )

    return pd.DataFrame(results)
