"""
Source : LeBonCoin — annonces particuliers et agences à Toulon.

LeBonCoin est plus accessible au scraping que les grands portails.
Deux approches possibles :
  A) Scraping HTML avec requests + BeautifulSoup
  B) API interne (inspecter les requêtes réseau sur leboncoin.fr)
"""
import requests
from .base import SourceBase


class LeBonCoinSource(SourceBase):
    name = "leboncoin"

    SEARCH_URL = "https://api.leboncoin.fr/finder/classified/search"

    def fetch_new(self) -> list[dict]:
        # TODO : construire le payload de recherche
        # payload = {
        #     "filters": {
        #         "category": {"id": "9"},   # Immobilier
        #         "location": {"city_zipcodes": [{"city": "Toulon", "zipcode": "83000"}]},
        #     },
        #     "limit": 100,
        # }
        # headers = {"api_key": "...", "Content-Type": "application/json"}
        # response = requests.post(self.SEARCH_URL, json=payload, headers=headers)
        # annonces_brutes = response.json()["ads"]
        # return [self.normalize(self._parse(a)) for a in annonces_brutes]
        raise NotImplementedError

    def _parse(self, raw: dict) -> dict:
        attrs = {a["key"]: a.get("value") for a in raw.get("attributes", [])}
        return {
            "id_source":   str(raw.get("list_id", "")),
            "url_source":  raw.get("url", ""),
            "type":        attrs.get("real_estate_type", ""),
            "surface":     float(attrs["square"]) if "square" in attrs else None,
            "prix":        float(raw.get("price", [None])[0]) if raw.get("price") else None,
            "quartier":    raw.get("location", {}).get("city_label", ""),
            "ville":       raw.get("location", {}).get("city", "Toulon"),
            "description": raw.get("body", ""),
            "photos":      [img["url"] for img in raw.get("images", {}).get("urls_large", [])],
            "nb_pieces":   int(attrs["rooms"]) if "rooms" in attrs else None,
            "dpe":         attrs.get("energy_rate"),
        }