"""
Source Bien'ici — TOULON (clean)
"""

import json
import time
import random
import logging
import requests

from .base import SourceBase

logger = logging.getLogger(__name__)


class BienIciSource(SourceBase):
    name = "bienici"

    API_URL = "https://www.bienici.com/realEstateAds.json"

    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    def fetch_new(self, max_pages: int = 20, page_size: int = 100):

        annonces_finales = []
        deja_vues = set()

        logger.info("[BienIci] 🔎 Scraping Toulon démarré")

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
                                    "inseeCodes": ["83137", "83126", "83500"],
                                    "label": "Toulon"
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

                            ville = (raw.get("city") or "").lower()

                            if "toulon" not in ville:
                                continue

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
                                "source": "bienici",
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

                        time.sleep(random.uniform(0.5, 1.5))

                    except Exception as e:
                        logger.error(f"[BienIci] ❌ {e}")

        logger.info(f"[BienIci] ✅ TOTAL FINAL : {len(annonces_finales)} annonces")
        return annonces_finales