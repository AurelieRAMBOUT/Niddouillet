"""
Interface commune R&D Vision — à implémenter par l'équipe.

Chaque équipe choisit son approche (CNN ou LLM multimodal) et implémente
cette fonction. Le reste du produit l'appelle sans savoir comment c'est fait.
"""


def evaluer_etat_bien(photos: list) -> dict:
    """
    Analyse les photos d'un bien et retourne une estimation de son état.

    Args:
        photos: liste de chemins locaux ou d'URLs vers les photos du bien

    Returns:
        {
            "etat_general":       "excellent" | "bon" | "correct" | "a_renover",
            "travaux_detectes":   ["peinture", "cuisine", "salle_de_bain", ...],
            "estimation_travaux": "0-5k" | "5-20k" | "20-50k" | ">50k",
            "luminosite":         1-5,
            "score_presentation": 1-10
        }

    Raises:
        NotImplementedError si l'équipe n'a pas encore implémenté son approche.
        ValueError si photos est vide.
    """
    if not photos:
        raise ValueError("Au moins une photo est requise.")
    raise NotImplementedError("Choisissez votre approche dans vision/cnn/ ou vision/llm/")
