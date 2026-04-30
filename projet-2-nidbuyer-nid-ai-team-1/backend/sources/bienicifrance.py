"""
Source Bien'ici — FRANCE (300 annonces clean)
"""

import json
import time
import random
import logging
import requests

from .base import SourceBase

logger = logging.getLogger(__name__)


class BienIciFranceSource(SourceBase):
    name = "bienicifrance"

    API_URL = "https://www.bienici.com/realEstateAds.json"

    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    def fetch_new(self, max_pages: int = 30, page_size: int = 100):

        annonces_finales = []
        deja_vues = set()

        logger.info("[BienIci FR] 🔎 Scraping France démarré")

        property_types = [["house"], ["flat"]]
        sort_options = ["publicationDate", "price"]

        for property_type in property_types:
            for sort in sort_options:

                for page in range(max_pages):
                    try:
                        payload = {
                            "size": page_size,
                            "from": page * page_size,
                            "filterType": "buy",
                            "propertyType": property_type,
                            "sortBy": sort,
                            "sortOrder": "desc",
                            "onTheMarket": [True],
                            "places": [
                                {
                                    "label": "France"
                                }
                            ]
                        }

                        params = {"filters": json.dumps(payload)}

                        res = requests.get(
                            self.API_URL,
                            params=params,
                            headers=self.HEADERS,
                            timeout=20
                        )

                        data = res.json()
                        annonces = data.get("realEstateAds", [])

                        if not annonces:
                            break

                        for raw in annonces:

                            url = f"https://www.bienici.com/annonce/achat/{raw.get('id')}"

                            if url in deja_vues:
                                continue

                            deja_vues.add(url)

                            # 🔥 FIX DATA
                            prix = raw.get("price")
                            surface = raw.get("surfaceArea")

                            if isinstance(prix, list):
                                prix = prix[0] if prix else None

                            if isinstance(surface, list):
                                surface = surface[0] if surface else None

                            try:
                                prix = float(prix) if prix else None
                            except:
                                prix = None

                            try:
                                surface = float(surface) if surface else None
                            except:
                                surface = None

                            prix_m2 = None
                            if prix and surface:
                                prix_m2 = round(prix / surface, 2)

                            quartier = ""
                            if isinstance(raw.get("district"), dict):
                                quartier = raw["district"].get("name")

                            annonces_finales.append({
                                "url_source": url,
                                "source": "bienici_france",
                                "titre": raw.get("title"),
                                "description": raw.get("description"),
                                "prix": prix,
                                "surface": surface,
                                "prix_m2": prix_m2,
                                "ville": raw.get("city"),
                                "quartier": quartier,
                                "type_bien": raw.get("propertyType"),
                                "nb_pieces": raw.get("roomsQuantity"),
                                "photos": [
                                    p.get("url")
                                    for p in raw.get("photos", [])
                                    if isinstance(p, dict) and p.get("url")
                                ]
                            })

                            # 🎯 STOP à 300
                            if len(annonces_finales) >= 300:
                                logger.info("🎯 300 annonces atteintes")
                                return annonces_finales

                        time.sleep(random.uniform(0.5, 1.5))

                    except Exception as e:
                        logger.error(f"[BienIci FR] ❌ {e}")

        logger.info(f"[BienIci FR] ✅ TOTAL FINAL : {len(annonces_finales)} annonces")
        return annonces_finales