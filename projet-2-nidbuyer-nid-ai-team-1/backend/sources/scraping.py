"""
Scraping orchestrator.

Rôle :
- Appelle toutes les sources actives
- Agrège les annonces
- Filtre uniquement les annonces sur Toulon
- Supprime les doublons

Utilisé par ingestion.py
"""

import logging
from datetime import datetime

from . import SOURCES_ACTIVES

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def filtrer_annonces_toulon(annonces: list[dict]) -> list[dict]:
    """
    Garde uniquement les annonces situées à Toulon.
    """

    annonces_toulon = []

    for annonce in annonces:
        ville = str(annonce.get("ville", "")).lower()
        code_postal = str(annonce.get("code_postal", ""))
        adresse = str(annonce.get("adresse", "")).lower()
        titre = str(annonce.get("titre", "")).lower()
        description = str(annonce.get("description", "")).lower()
        quartier = str(annonce.get("quartier", "")).lower()

        est_toulon = (
            "toulon" in ville
            or "toulon" in adresse
            or "toulon" in titre
            or "toulon" in description
            or "toulon" in quartier
            or code_postal in ["83000", "83100", "83200"]
        )

        if est_toulon:
            annonce["ville"] = annonce.get("ville") or "Toulon"
            annonces_toulon.append(annonce)

    logger.info(f"📍 {len(annonces_toulon)} annonce(s) conservée(s) sur Toulon")

    return annonces_toulon


def scrape_all_sources() -> list[dict]:
    """
    Lance le scraping de toutes les sources actives.

    Returns:
        Liste d'annonces normalisées situées à Toulon
    """

    if not SOURCES_ACTIVES:
        logger.warning("⚠️ Aucune source active.")
        return []

    toutes_annonces = []

    logger.info(f"🔎 Scraping démarré — {len(SOURCES_ACTIVES)} source(s)")

    for source in SOURCES_ACTIVES:
        try:
            logger.info(f"➡️ Source : {source.name}")

            annonces = source.fetch_new()
            annonces = filtrer_annonces_toulon(annonces)

            logger.info(
                f"✅ {source.name} → {len(annonces)} annonce(s) Toulon récupérée(s)"
            )

            toutes_annonces.extend(annonces)

        except NotImplementedError:
            logger.warning(f"⚠️ {source.name} non implémenté")

        except Exception as e:
            logger.error(f"❌ {source.name} erreur : {e}")

    logger.info(f"📦 Total annonces Toulon récupérées : {len(toutes_annonces)}")

    return toutes_annonces


def deduplicate_annonces(annonces: list[dict]) -> list[dict]:
    """
    Supprime les doublons basés sur url_source.
    """

    vues = set()
    uniques = []

    for annonce in annonces:
        url = annonce.get("url_source")

        if not url:
            continue

        if url not in vues:
            vues.add(url)
            uniques.append(annonce)

    logger.info(f"🧹 {len(annonces) - len(uniques)} doublon(s) supprimé(s)")

    return uniques


# ─────────────────────────────────────────────
# ▶️ Test local
# ─────────────────────────────────────────────
if __name__ == "__main__":
    start = datetime.now()

    annonces = scrape_all_sources()
    annonces = deduplicate_annonces(annonces)

    print(f"\n📊 {len(annonces)} annonce(s) unique(s) sur Toulon\n")

    for i, annonce in enumerate(annonces[:5], start=1):
        print(f"--- Annonce {i} ---")
        print(f"Titre : {annonce.get('titre')}")
        print(f"Prix : {annonce.get('prix')}")
        print(f"Surface : {annonce.get('surface')}")
        print(f"Ville : {annonce.get('ville')}")
        print(f"Code postal : {annonce.get('code_postal')}")
        print(f"Quartier : {annonce.get('quartier')}")
        print(f"URL : {annonce.get('url_source')}\n")

    print(f"⏱️ Temps total : {(datetime.now() - start).seconds}s")
