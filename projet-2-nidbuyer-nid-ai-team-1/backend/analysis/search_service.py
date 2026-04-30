from __future__ import annotations

from typing import Any

from backend.rag import search_similar
from backend.scoring import score_opportunite, fiche_decision


def build_profile_query(profil: Any) -> str:
    return (
        f"{profil.intention} "
        f"budget maximum {profil.budget_max} euros "
        f"surface minimum {profil.surface_min or ''} m² "
        f"quartiers {' '.join(profil.quartiers or [])} "
        f"{profil.description_libre or ''}"
    ).strip()


def get_reference(bien: dict[str, Any], index: int) -> str:
    return str(
        bien.get("reference")
        or bien.get("id")
        or bien.get("id_source")
        or bien.get("url_source")
        or index
    )


def build_tags(score: float | None, quartier: str | None) -> list[str]:
    if score is None:
        return ["A analyser"]

    tags = []
    quartier_normalise = str(quartier or "").lower()

    if score >= 7.5:
        tags.append("Investissement")
    if score >= 7.0:
        tags.append("Residence principale")
    if score >= 8.0 or quartier_normalise in {"le mourillon", "cap brun", "centre-ville"}:
        tags.append("Residence secondaire")
    if score >= 7.2:
        tags.append("Mixte")

    return tags or ["A surveiller"]


def prepare_resultat_bien(
    bien: dict[str, Any],
    profil: Any,
    index: int,
) -> dict[str, Any]:
    mediane_quartier = float(bien.get("mediane_prix_m2", 3400))

    scoring = score_opportunite(
        bien=bien,
        mediane_quartier=mediane_quartier,
        profil=profil.intention,
    )

    fiche = fiche_decision(
        bien=bien,
        dvf_quartier={"mediane_prix_m2": mediane_quartier},
    )

    reference = get_reference(bien, index)
    score = scoring.get("score")

    return {
        "reference": reference,
        "bien": {
            **bien,
            "reference": reference,
        },
        "scoring": scoring,
        "fiche_decision": fiche,
        "tags": build_tags(score, bien.get("quartier")),
    }


def rechercher_biens_pour_profil(profil: Any, n_results: int = 5) -> dict[str, Any]:
    query = build_profile_query(profil)
    biens = search_similar(query, n_results=n_results)

    resultats = [
        prepare_resultat_bien(bien=bien, profil=profil, index=index)
        for index, bien in enumerate(biens, start=1001)
    ]

    return {
        "profil": profil,
        "query": query,
        "resultats": resultats,
    }