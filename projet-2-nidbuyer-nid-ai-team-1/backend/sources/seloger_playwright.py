"""
Source SeLoger — Playwright (version finale clean)
"""

import re
import logging
import time
import random
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError

from .base import SourceBase

logger = logging.getLogger(__name__)


class SeLogerPlaywrightSource(SourceBase):
    name = "seloger_playwright"

    BASE_URL = "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD08FR34378"

    def fetch_new(self, max_pages=12):

        annonces = []
        seen = set()

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir="playwright_profile",
                headless=False,
                locale="fr-FR"
            )
            page = context.new_page()

            for page_num in range(1, max_pages + 1):

                url = f"{self.BASE_URL}&page={page_num}"
                logger.info(f"[SeLoger] 🔎 Page {page_num}")

                try:
                    page.goto(url, timeout=90000)

                    # 🍪 cookies
                    try:
                        page.get_by_role("button", name="Tout accepter").click(timeout=3000)
                    except:
                        pass

                    # 🔥 attendre les annonces
                    try:
                        page.wait_for_selector("a[href*='/annonces/']", timeout=10000)
                    except TimeoutError:
                        logger.warning("[SeLoger] aucune annonce trouvée")
                        continue

                    # 🔥 scroll progressif
                    for _ in range(20):
                        page.mouse.wheel(0, 2000)
                        page.wait_for_timeout(1200)

                    page.wait_for_timeout(3000)

                    cards = page.query_selector_all("a[href*='/annonces/']")
                    logger.info(f"[SeLoger] cards trouvées: {len(cards)}")

                    for card in cards:
                        try:
                            href = card.get_attribute("href")
                            if not href:
                                continue

                            full_url = urljoin("https://www.seloger.com", href)

                            if not full_url.startswith("http"):
                                continue

                            if full_url in seen:
                                continue
                            seen.add(full_url)

                            parent = card.evaluate_handle("el => el.closest('div')")
                            text = parent.inner_text()

                            prix = self.extract_price(text)
                            surface = self.extract_surface(text)

                            annonces.append({
                                "url_source": full_url,
                                "source": "seloger",
                                "titre": self.build_title(text),
                                "description": text,
                                "prix": prix,
                                "surface": surface,
                                "prix_m2": round(prix / surface, 2) if prix and surface else None,
                                "ville": "Toulon",
                                "quartier": "",
                                "type_bien": self.extract_type(text),
                                "nb_pieces": self.extract_pieces(text),
                                "photos": []
                            })

                        except Exception:
                            continue

                    time.sleep(random.uniform(2, 4))

                except Exception as e:
                    logger.error(f"[SeLoger] ❌ {e}")

            context.close()

        logger.info(f"[SeLoger] ✅ TOTAL : {len(annonces)} annonces")
        return annonces

    # -----------------------
    # EXTRACTIONS
    # -----------------------

    def extract_price(self, text):
        try:
            m = re.search(r"(\d[\d\s]+)€", text.replace("\xa0", " "))
            if not m:
                return None
            return int(re.sub(r"\D", "", m.group(1)))
        except:
            return None

    def extract_surface(self, text):
        try:
            m = re.search(r"(\d+)\s*m", text.lower())
            if not m:
                return None
            return float(m.group(1))
        except:
            return None

    def extract_pieces(self, text):
        try:
            m = re.search(r"(\d+)\s*pi", text.lower())
            if not m:
                return None
            return int(m.group(1))
        except:
            return None

    def extract_type(self, text):
        t = text.lower()
        if "appartement" in t:
            return "Appartement"
        if "maison" in t:
            return "Maison"
        return None

    # -----------------------
    # TITRE PROPRE
    # -----------------------

    def build_title(self, text):

        text_lower = text.lower()

        type_bien = self.extract_type(text) or "Bien"
        pieces = self.extract_pieces(text)
        surface = self.extract_surface(text)

        titre = type_bien

        if pieces:
            titre += f" {pieces} pièces"

        if surface:
            titre += f" {int(surface)} m²"

        titre += " - Toulon"

        return titre