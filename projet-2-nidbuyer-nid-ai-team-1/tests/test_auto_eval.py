"""
Tests d'auto-évaluation — Projet 2 NidBuyer
Lancés automatiquement à chaque push via GitHub Actions.

Points couverts ici :
  - Fichiers obligatoires (5 pts)
  - Démarrage API + /docs + /admin/status (5 pts)

Les tests scoring (10 pts) et RAG (10 pts) sont dans test_scoring.py / test_rag.py.
"""
import os
import subprocess
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).parent.parent


# ── Fichiers obligatoires ─────────────────────────────────────────────────────

class TestFichiersObligatoires:
    """5 pts — présence et contenu minimal des livrables non-code."""

    def test_readme_url_deployee(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "https://TODO" not in readme, (
            "README.md : remplacer 'https://TODO' par l'URL déployée"
        )
        assert any(s in readme for s in ("https://", "http://")), (
            "README.md : aucune URL déployée trouvée"
        )

    def test_experiments_md_existe(self):
        path = ROOT / "prompts" / "EXPERIMENTS.md"
        assert path.exists(), "prompts/EXPERIMENTS.md manquant"

    def test_experiments_md_contient_trois_versions(self):
        content = (ROOT / "prompts" / "EXPERIMENTS.md").read_text(encoding="utf-8")
        assert len(content) > 300, (
            "EXPERIMENTS.md trop court — documenter les 3 versions de prompt"
        )
        assert content.count("V") >= 3 or content.count("#") >= 3, (
            "EXPERIMENTS.md : au moins 3 sections attendues (V1, V2, V3)"
        )

    def test_approach_md_existe(self):
        path = ROOT / "vision" / "APPROACH.md"
        assert path.exists(), "vision/APPROACH.md manquant"

    def test_approach_md_a_du_contenu(self):
        content = (ROOT / "vision" / "APPROACH.md").read_text(encoding="utf-8")
        assert len(content) > 300, (
            "APPROACH.md trop court — documenter l'approche Vision (métriques, limites)"
        )

    def test_env_example_a_supabase(self):
        env = (ROOT / ".env.example").read_text(encoding="utf-8")
        assert "SUPABASE_URL" in env, ".env.example : SUPABASE_URL manquant"
        assert "SUPABASE_KEY" in env, ".env.example : SUPABASE_KEY manquant"

    def test_readme_mentionne_nb_annonces(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "XXX" not in readme, (
            "README.md : mettre à jour le nombre d'annonces indexées (remplacer XXX)"
        )


# ── API démarre ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_process():
    """Démarre l'API sur le port 18765 avec des variables d'env de test."""
    env = os.environ.copy()
    env.update({
        "ANTHROPIC_API_KEY": "sk-ant-test-00000000",
        "SUPABASE_URL": "https://placeholder.supabase.co",
        "SUPABASE_KEY": "placeholder-key",
        "CHROMA_PATH": "/tmp/chroma_autoeval",
    })
    proc = subprocess.Popen(
        ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "18765",
         "--log-level", "warning"],
        env=env,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(5)
    yield proc
    proc.terminate()
    proc.wait()


class TestAPIDemarre:
    """5 pts — l'API FastAPI doit démarrer et exposer les endpoints de base."""

    def test_docs_accessible(self, api_process):
        try:
            resp = requests.get("http://127.0.0.1:18765/docs", timeout=6)
        except requests.ConnectionError:
            pytest.fail("L'API ne répond pas — vérifier que uvicorn démarre sans erreur")
        assert resp.status_code == 200, f"/docs retourne {resp.status_code}"

    def test_openapi_json(self, api_process):
        resp = requests.get("http://127.0.0.1:18765/openapi.json", timeout=6)
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data, "openapi.json invalide"

    def test_admin_status_retourne_json(self, api_process):
        resp = requests.get("http://127.0.0.1:18765/admin/status", timeout=6)
        assert resp.status_code == 200, f"/admin/status retourne {resp.status_code}"
        data = resp.json()
        assert "annonces_indexees" in data, (
            "/admin/status doit contenir 'annonces_indexees'"
        )

    def test_admin_status_champ_derniere_sync(self, api_process):
        resp = requests.get("http://127.0.0.1:18765/admin/status", timeout=6)
        data = resp.json()
        assert "derniere_sync" in data, (
            "/admin/status doit contenir 'derniere_sync'"
        )
