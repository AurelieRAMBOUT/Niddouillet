"""Tests unitaires — module scoring"""
import pytest
from backend.scoring import score_opportunite, fiche_decision


BIEN_TEST = {
    "id": "test-001",
    "type": "T3",
    "surface": 68,
    "quartier": "Mourillon",
    "prix": 215_000,
    "description": "Bel appartement lumineux, balcon vue mer partielle.",
}

DVF_MOURILLON = {"mediane_prix_m2": 3_400}


def test_score_sous_evalue():
    """Un bien sous la médiane doit avoir un score positif (bonne affaire)."""
    result = score_opportunite(BIEN_TEST, DVF_MOURILLON["mediane_prix_m2"], profil="rp")
    assert result["ecart_pct"] < 0, "Bien sous-évalué → écart négatif"
    assert result["score"] > 0, "Bien sous-évalué → score positif"


def test_score_sur_evalue():
    """Un bien au-dessus de la médiane doit avoir un score négatif."""
    bien_cher = {**BIEN_TEST, "prix": 280_000}  # ~4 118 €/m²
    result = score_opportunite(bien_cher, DVF_MOURILLON["mediane_prix_m2"], profil="rp")
    assert result["ecart_pct"] > 0
    assert result["score"] < 0


def test_malus_travaux_investisseur():
    """L'investisseur ne subit pas de malus travaux."""
    vision = {"travaux_score": 1.0}
    r_investisseur = score_opportunite(BIEN_TEST, DVF_MOURILLON["mediane_prix_m2"], "investissement", vision)
    r_famille = score_opportunite(BIEN_TEST, DVF_MOURILLON["mediane_prix_m2"], "rp", vision)
    assert r_investisseur["score"] >= r_famille["score"]


def test_fiche_decision_contient_ecart():
    """La fiche décision doit mentionner l'écart au marché."""
    fiche = fiche_decision(BIEN_TEST, DVF_MOURILLON)
    assert "%" in fiche or "médiane" in fiche.lower()
