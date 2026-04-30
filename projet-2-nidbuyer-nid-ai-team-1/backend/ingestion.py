"""
Pipeline ingestion FINAL (robuste + upsert)
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client
from .sources import SOURCES_ACTIVES

# 🔥 CHARGE LE .env (IMPORTANT)
load_dotenv()

# 🔧 CONFIG LOG
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LAST_RUN_FILE = Path("data/.last_sync")

# 🔐 CONFIG SUPABASE
SUPABASE_URL = "https://rxvcfvpbixmcazdinysm.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 🔍 DEBUG TEMPORAIRE (tu peux supprimer après)
print("SUPABASE_KEY:", "OK" if SUPABASE_KEY else "NONE")

if not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_KEY manquante (vérifie ton .env)")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# 🔥 UPSERT (corrige ton bug 409)
def insert_supabase(annonces):
    try:
        batch_size = 100

        for i in range(0, len(annonces), batch_size):
            batch = annonces[i:i + batch_size]

            supabase.table("annonces").upsert(
                batch,
                on_conflict="url_source"
            ).execute()

            logger.info(f"✅ Batch {i//batch_size + 1} : {len(batch)} annonces upserted")

    except Exception as e:
        logger.error(f"❌ Supabase: {e}")


def sync():
    logger.info("🚀 Sync démarrée")

    toutes_annonces = []

    # 🔎 SCRAPING
    for source in SOURCES_ACTIVES:
        try:
            annonces = source.fetch_new()
            logger.info(f"{source.name} → {len(annonces)} annonces")
            toutes_annonces.extend(annonces)
        except Exception as e:
            logger.error(f"❌ Source {source.name}: {e}")

    print("SCRAPED:", len(toutes_annonces))

    # 🔁 DÉDUPLICATION
    uniques = []
    vues = set()

    for a in toutes_annonces:
        url = a.get("url_source")

        if not url:
            continue

        if url not in vues:
            vues.add(url)
            uniques.append(a)

    print("UNIQUE:", len(uniques))

    if not uniques:
        print("❌ Rien à insérer")
        return

    # 📦 INSERTION
    insert_supabase(uniques)

    # 🕒 LOG DERNIÈRE EXEC
    LAST_RUN_FILE.write_text(datetime.now().isoformat())

    logger.info("🎯 Sync terminée")


if __name__ == "__main__":
    sync()