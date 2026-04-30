"""
Source générique — LLM-assistée.

Pour toute source non structurée : page HTML, post Facebook, PDF,
liste WhatsApp, fichier Excel d'agence...

Le LLM extrait les informations pertinentes depuis n'importe quel format.
Idéal pour : groupes Facebook, sites d'agences locales, PAP, SeLoger...

Usage :
    source = SourceGenerique()
    annonces = source.fetch_from_urls([
        "https://www.facebook.com/groups/girlsoftoulon/posts/...",
        "https://agence-xyz-toulon.fr/vente/appartement-mourillon",
    ])
"""
import json
import anthropic
from .base import SourceBase

client = anthropic.Anthropic()

PROMPT_EXTRACTION = """Extrais les informations immobilières depuis ce contenu.
Retourne UNIQUEMENT du JSON valide, sans texte autour :
{
  "id_source": "identifiant unique si présent, sinon null",
  "url_source": "url de la page si connue, sinon null",
  "type": "T1/T2/T3/T4/maison/immeuble ou null",
  "surface": nombre ou null,
  "prix": nombre ou null,
  "quartier": "nom du quartier à Toulon ou null",
  "ville": "Toulon",
  "description": "description complète du bien",
  "photos": [],
  "nb_pieces": nombre ou null,
  "dpe": "A/B/C/D/E/F/G ou null"
}
Si ce n'est pas une annonce immobilière, retourne null."""


class SourceGenerique(SourceBase):
    name = "generique"

    def fetch_new(self) -> list[dict]:
        # Cette source est appelée manuellement avec fetch_from_urls()
        return []

    def fetch_from_urls(self, urls: list[str], model: str = "claude-haiku-4-5-20251001") -> list[dict]:
        """
        Extrait des annonces depuis une liste d'URLs quelconques.

        Args:
            urls: liste d'URLs (pages HTML, posts Facebook publics, etc.)
            model: modèle Claude à utiliser (haiku = rapide et économique)

        Returns:
            Liste d'annonces normalisées
        """
        import requests
        annonces = []
        for url in urls:
            try:
                html = requests.get(url, timeout=10).text[:8000]
                response = client.messages.create(
                    model=model,
                    max_tokens=512,
                    messages=[{"role": "user", "content": f"{PROMPT_EXTRACTION}\n\nContenu :\n{html}"}],
                )
                data = json.loads(response.content[0].text)
                if data:
                    data["url_source"] = data.get("url_source") or url
                    annonces.append(self.normalize(data))
            except Exception as e:
                print(f"[WARN] {url} ignorée : {e}")
        return annonces

    def fetch_from_text(self, texte: str, url_source: str = "", model: str = "claude-haiku-4-5-20251001") -> dict | None:
        """
        Extrait une annonce depuis un texte brut (copié-collé d'un post Facebook, SMS d'agence...).
        """
        try:
            response = client.messages.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "user", "content": f"{PROMPT_EXTRACTION}\n\nContenu :\n{texte}"}],
            )
            data = json.loads(response.content[0].text)
            if data:
                data["url_source"] = url_source
                return self.normalize(data)
        except Exception as e:
            print(f"[WARN] Extraction échouée : {e}")
        return None
