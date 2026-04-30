"""Tests unitaires — module RAG"""
import pytest
from backend.rag import indexer_annonces, search_similar


ANNONCES_SAMPLE = [
    {
        "id": "001",
        "type": "T3",
        "surface": 68,
        "quartier": "Mourillon",
        "prix": 215_000,
        "description": "Bel appartement lumineux, balcon vue mer partielle, cuisine rénovée.",
        "dpe": "C",
        "nb_pieces": 3,
    },
    {
        "id": "002",
        "type": "T2",
        "surface": 45,
        "quartier": "Cap Brun",
        "prix": 180_000,
        "description": "Studio lumineux proche plage, idéal investissement locatif.",
        "dpe": "D",
        "nb_pieces": 2,
    },
    {
        "id": "003",
        "type": "T4",
        "surface": 95,
        "quartier": "Mourillon",
        "prix": 350_000,
        "description": "Grand appartement familial, 4 chambres, parking sous-sol.",
        "dpe": "B",
        "nb_pieces": 4,
    },
]


@pytest.fixture(autouse=True)
def setup_index(tmp_path, monkeypatch):
    """Indexe les annonces de test dans une base temporaire."""
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    indexer_annonces(ANNONCES_SAMPLE)


def test_search_retourne_resultats():
    results = search_similar("appartement vue mer Mourillon", n_results=2)
    assert len(results) == 2


def test_search_pertinence_famille():
    """Une recherche famille doit retourner le T4 en priorité."""
    results = search_similar("grand appartement familial 4 chambres", n_results=1)
    assert results[0]["id"] == "003"


def test_search_pertinence_investissement():
    """Une recherche investissement locatif doit favoriser le T2 studio."""
    results = search_similar("studio investissement locatif rentable", n_results=1)
    assert results[0]["id"] == "002"
