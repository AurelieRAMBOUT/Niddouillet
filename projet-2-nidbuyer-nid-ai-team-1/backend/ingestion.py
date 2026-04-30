"""
Pipeline ingestion FINAL (robuste + upsert)
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client
from .rag import indexer_annonces, get_collection
from .sources import SOURCES_ACTIVES

# 🔥 CHARGE LE .env (IMPORTANT)
load_dotenv()

# 🔧 CONFIG LOG
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LAST_RUN_FILE = Path("data/.last_sync")
DEFAULT_SUPABASE_TABLE = "annonces"
SUPABASE_TABLE_ALIASES = {
    "annonce": DEFAULT_SUPABASE_TABLE,
}

# 🔐 CONFIG SUPABASE
SUPABASE_URL = "https://rxvcfvpbixmcazdinysm.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 🔍 DEBUG TEMPORAIRE (tu peux supprimer après)
print("SUPABASE_KEY:", "OK" if SUPABASE_KEY else "NONE")

if not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_KEY manquante (vérifie ton .env)")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def _first_value(row: dict, *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:[\s.,]\d+)*", str(value))
    if not match:
        return None
    normalized = match.group(0).replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    number = _to_float(value)
    return int(number) if number is not None else None


def _text_from_fields(row: dict, *keys: str) -> str:
    parts = []
    seen = set()
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        text = str(value).strip()
        if text and text not in seen:
            parts.append(text)
            seen.add(text)
    return " - ".join(parts)


def _photo_urls_from_value(value: Any) -> list[str]:
    if value in (None, ""):
        return []

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []

        if text.startswith("["):
            try:
                return _photo_urls_from_value(json.loads(text))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass

        return [text]

    if isinstance(value, dict):
        for key in ("url", "src", "href", "large", "medium", "small"):
            url = value.get(key)
            if isinstance(url, str) and url.strip():
                return [url.strip()]
        return []

    if isinstance(value, (list, tuple, set)):
        urls = []
        for item in value:
            urls.extend(_photo_urls_from_value(item))
        return urls

    return []


def _normaliser_photos(row: dict) -> list[str]:
    photos = []
    for key in (
        "photos",
        "photo_urls",
        "images",
        "image_urls",
        "pictures",
        "photos_url",
        "url_photos",
        "photo_url",
        "image_url",
        "photo",
        "image",
    ):
        photos.extend(_photo_urls_from_value(row.get(key)))

    uniques = []
    for photo in photos:
        if photo and photo not in uniques:
            uniques.append(photo)
    return uniques


def _normaliser_annonce_supabase(row: dict, table_name: str) -> dict:
    annonce_id = _first_value(
        row,
        "id",
        "id_source",
        "annonce_id",
        "id_annonce",
        "source_id",
        "external_id",
        "uuid",
    )
    url_source = _first_value(
        row,
        "url_source",
        "source_url",
        "url",
        "lien",
        "link",
        "annonce_url",
    )
    if not url_source and annonce_id is not None:
        url_source = f"supabase://{table_name}/{annonce_id}"

    description = _text_from_fields(
        row,
        "titre",
        "title",
        "description",
        "texte",
        "annonce",
        "resume_annonce",
        "body",
    )
    photos = _normaliser_photos(row)

    annonce = {
        "id": str(annonce_id or url_source),
        "id_source": str(_first_value(row, "id_source", "source_id", "external_id") or annonce_id or ""),
        "url_source": str(url_source or ""),
        "type": _first_value(row, "type", "type_bien", "property_type", "typologie", "type_local"),
        "surface": _to_float(_first_value(row, "surface", "surface_m2", "surface_habitable", "surface_reelle_bati")),
        "prix": _to_float(_first_value(row, "prix", "price", "prix_vente", "valeur", "valeur_fonciere")),
        "quartier": _first_value(row, "quartier", "quartier_final", "quartier_source", "secteur", "localisation"),
        "ville": _first_value(row, "ville", "city", "commune") or "Toulon",
        "description": description,
        "nb_pieces": _to_int(_first_value(row, "nb_pieces", "pieces", "nombre_pieces", "rooms")),
        "dpe": _first_value(row, "dpe", "energy_rate", "classe_energie"),
        "photo_url": photos[0] if photos else "",
        "photos": json.dumps(photos, ensure_ascii=False),
        "source": _first_value(row, "source") or "supabase",
        "table_source": table_name,
    }

    for key, value in row.items():
        if key not in annonce and isinstance(value, (str, int, float, bool)):
            annonce[key] = value

    return annonce


def _clear_collection() -> int:
    collection = get_collection(with_embedding=False)
    results = collection.get(include=[])
    ids = results.get("ids") or []
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def backfill_supabase_annonces(
    table_name: str = DEFAULT_SUPABASE_TABLE,
    batch_size: int = 500,
    limit: int | None = None,
    dry_run: bool = False,
    replace: bool = True,
) -> dict:
    """
    Charge les annonces depuis Supabase puis les indexe dans ChromaDB.
    """
    import requests

    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL") or SUPABASE_URL
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL et SUPABASE_KEY doivent etre definies dans l'environnement")

    if batch_size <= 0:
        raise ValueError("batch_size doit etre positif")

    requested_table_name = (table_name or DEFAULT_SUPABASE_TABLE).strip()
    table_name = SUPABASE_TABLE_ALIASES.get(requested_table_name, requested_table_name)

    annonces = []
    offset = 0
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{table_name}"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept": "application/json",
        "Range-Unit": "items",
    }

    while True:
        remaining = None if limit is None else limit - len(annonces)
        if remaining is not None and remaining <= 0:
            break

        page_size = min(batch_size, remaining) if remaining is not None else batch_size
        response = requests.get(
            endpoint,
            params={"select": "*"},
            headers={**headers, "Range": f"{offset}-{offset + page_size - 1}"},
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            if response.status_code == 404:
                raise RuntimeError(
                    f"Table Supabase '{requested_table_name}' introuvable. "
                    f"Table utilisee: '{table_name}'. Verifie le nom dans Supabase "
                    "ou saisis 'annonces' dans l'admin."
                ) from exc
            raise

        rows = response.json() or []
        if not rows:
            break

        annonces.extend(_normaliser_annonce_supabase(row, table_name) for row in rows)
        if len(rows) < page_size:
            break
        offset += page_size

    sans_id = [a for a in annonces if not a.get("id")]
    indexables = [a for a in annonces if a.get("id")]

    rapport = {
        "table": table_name,
        "table_demandee": requested_table_name,
        "lues": len(annonces),
        "indexables": len(indexables),
        "ignorees_sans_id": len(sans_id),
        "replace": replace,
        "dry_run": dry_run,
        "supprimees_avant_indexation": 0,
        "annonces_indexees": get_collection(with_embedding=False).count(),
    }

    if dry_run or not indexables:
        return rapport

    if replace:
        rapport["supprimees_avant_indexation"] = _clear_collection()

    indexer_annonces(indexables)
    rapport["annonces_indexees"] = get_collection(with_embedding=False).count()
    LAST_RUN_FILE.write_text(datetime.now().isoformat())
    return rapport


# 🔥 UPSERT
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


def sync(dry_run: bool = False):
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

    if dry_run:
        return {"nouvelles": len(uniques), "dry_run": True}

    # 📦 INSERTION
    insert_supabase(uniques)

    # 🕒 LOG DERNIÈRE EXEC
    LAST_RUN_FILE.write_text(datetime.now().isoformat())

    logger.info("🎯 Sync terminée")


if __name__ == "__main__":
    sync()
