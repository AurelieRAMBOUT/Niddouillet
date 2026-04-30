"""
Calcul du score d'opportunité d'un bien immobilier.
Compare le prix au m² du bien à la médiane DVF du quartier."""


MALUS_TRAVAUX = {
    "investissement": 0.0,  # travaux = opportunité de négociation
    "rp":             0.3,  # travaux = contrainte pour une famille
    "rs":             0.15, # peut accepter  des travaux mais pas des chantiers lourds
    "mixte":          0.1,  # peut accepter un peu de travaux
}

TRAVAUX_SCORE_PAR_ETAT = {
    "excellent": 0.0,
    "bon": 0.0,
    "correct": 0.3,
    "a_renover": 1.0,
}

TRAVAUX_SCORE_PAR_ESTIMATION = {
    "0-5k": 0.1,
    "5-20k": 0.4,
    "20-50k": 0.7,
    ">50k": 1.0,
}

from typing import Optional


def percentile_prix_m2(prix_m2: float, valeurs_prix_m2: list[float]) -> float | None:
    valeurs = [float(value) for value in valeurs_prix_m2 if value is not None]
    if not valeurs:
        return None

    nb_inferieurs_ou_egaux = sum(1 for value in valeurs if value <= prix_m2)
    return nb_inferieurs_ou_egaux / len(valeurs) * 100


def score_opportunite(
    bien: dict,
    mediane_quartier: float,
    profil: str = "rp",
    vision_result: Optional[dict] = None,
    dvf_stats: Optional[dict] = None,
) -> dict:
    surface = float(bien["surface"])
    prix = float(bien["prix"])

    if surface <= 0:
        raise ValueError("La surface doit être positive")
    if mediane_quartier <= 0:
        raise ValueError("La médiane prix/m2 doit être positive")

    prix_m2 = prix / surface
    ecart_pct = ((prix_m2 - mediane_quartier) / mediane_quartier) * 100
    score = -ecart_pct

    if vision_result:
        travaux_score = float(vision_result.get("travaux_score", 0) or 0)
        if profil != "investissement":
            score -= travaux_score * 0.3

    result = {
        "prix_m2": prix_m2,
        "mediane_prix_m2": mediane_quartier,
        "ecart_pct": ecart_pct,
        "score": score,
    }

    if dvf_stats:
        result.update(
            {
                "quartier_comparaison": dvf_stats.get("quartier"),
                "source_groupement": dvf_stats.get("source_groupement"),
                "min_prix_m2": dvf_stats.get("min_prix_m2"),
                "max_prix_m2": dvf_stats.get("max_prix_m2"),
                "nb_transactions": dvf_stats.get("nb_transactions"),
                "percentile_prix_m2": percentile_prix_m2(
                    prix_m2,
                    dvf_stats.get("prix_m2_values") or [],
                ),
            }
        )

    return result

def fiche_decision(bien: dict, dvf_quartier: dict) -> str:
    mediane = float(dvf_quartier["mediane_prix_m2"])
    result = score_opportunite(bien, mediane, profil="rp")

    prix_m2 = result["prix_m2"]
    ecart = result["ecart_pct"]

    if ecart < 0:
        position = "SOUS"
    elif ecart > 0:
        position = "AU-DESSUS DE"
    else:
        position = "AU NIVEAU DE"

    if ecart <= -10:
        opportunite = "Le bien semble sous-évalué par rapport aux ventes comparables."
        marge_negociation = "faible a modérée, sauf defaut visible ou urgence vendeur"
        recommandation = "Prioriser une vérification rapide du bien et se positionner sans trop tirer le prix vers le bas."
    elif ecart <= 5:
        opportunite = "Le bien est proche du prix marche du quartier."
        marge_negociation = "moderee, autour de 2-5% selon l'état du bien et la concurrence"
        recommandation = "Négocier surtout sur les travaux, les diagnostics, les charges et les délais de vente."
    elif ecart <= 20:
        opportunite = "Le bien est au-dessus de la médiane du quartier."
        marge_negociation = "significative, autour de 5-10% si aucun avantage rare ne justifie le prix"
        recommandation = "Demander des comparables, vérifier les prestations et formuler une offre argumentée sous le prix affiche."
    else:
        opportunite = "Le bien est nettement au-dessus de la médiane du quartier."
        marge_negociation = "forte, souvent superieure a 10% si le prix n'est pas justifie par un emplacement ou des prestations rares"
        recommandation = "Ne pas se précipiter: comparer avec d'autres biens, chiffrer les écarts et négocier fermement."

    points_forts = []
    points_attention = []

    if ecart <= 0:
        points_forts.append("prix/m2 favorable par rapport à la médiane DVF")
    else:
        points_attention.append("prix/m2 superieur a la médiane DVF")

    if bien.get("quartier"):
        points_forts.append(f"quartier identifie: {bien.get('quartier')}")

    try:
        surface = float(bien.get("surface") or 0)
        if surface >= 80:
            points_forts.append("surface confortable")
        elif surface and surface < 30:
            points_attention.append("petite surface: verifier l'usage reel et la liquidite a la revente")
    except (TypeError, ValueError):
        pass

    if not points_attention:
        points_attention.append("verifier diagnostics, charges, travaux et nuisances avant offre")

    return (
        f"Ce {bien.get('type', 'bien')} de {bien.get('surface')} m2 "
        f"au {bien.get('quartier', 'quartier indique')} est a {prix_m2:.0f} EUR/m2, "
        f"soit {abs(ecart):.1f}% {position} la médiane du quartier "
        f"({mediane:.0f} EUR/m2).\n\n"
        f"Opportunite : {opportunite}\n"
        f"Points forts : {'; '.join(points_forts)}.\n"
        f"Points d'attention : {'; '.join(points_attention)}.\n"
        f"Negociation : marge {marge_negociation}.\n"
        f"Recommandation : {recommandation}"
    )
def rendement_locatif(bien: dict, loyer_estime: float) -> dict:
    """
    Calcule le rendement brut et net estimé (bonus investissement).

    Args:
        bien: dict avec 'prix'
        loyer_estime: loyer mensuel estimé en €

    Returns:
        dict avec 'rendement_brut_pct', 'rendement_net_pct'
    """
    prix = float(bien["prix"])
    loyer_annuel = float(loyer_estime) * 12
    if prix <= 0 or loyer_annuel < 0:
        raise ValueError("Le prix doit etre positif et le loyer estime ne peut pas etre negatif.")

    rendement_brut_pct = loyer_annuel / prix * 100
    return {
        "rendement_brut_pct": rendement_brut_pct,
        "rendement_net_pct": rendement_brut_pct * 0.7,
    }
