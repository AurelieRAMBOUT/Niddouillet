"""
Indexation et recherche sémantique sur les annonces immobilières.
Utilise ChromaDB comme base vectorielle.
"""
import json

import chromadb
from chromadb.utils import embedding_functions


# TODO : choisir le modèle d'embedding (all-MiniLM-L6-v2, text-embedding-3-small, etc.)
# Justifier votre choix dans le README (vitesse vs qualité, coût, langue)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "annonces_toulon"

_client = None
_ef = None


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path="./chroma_db")
    return _client


def get_embedding_function():
    global _ef
    if _ef is None:
        _ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return _ef


def get_collection(with_embedding: bool = True):
    kwargs = {"name": COLLECTION_NAME}
    if with_embedding:
        kwargs["embedding_function"] = get_embedding_function()
    return get_client().get_or_create_collection(**kwargs)


def _metadata_value(key: str, value):
    if isinstance(value, (str, int, float, bool)):
        return value
    if key in {"photos", "photo_urls", "images", "image_urls", "pictures"} and isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return None


def _photo_urls_from_value(value) -> list[str]:
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
    if isinstance(value, list):
        urls = []
        for item in value:
            urls.extend(_photo_urls_from_value(item))
        return urls
    return []


def _photo_urls_from_annonce(annonce: dict) -> list[str]:
    urls = []
    for key in ("photos", "photo_urls", "images", "image_urls", "pictures", "photo_url", "image_url"):
        urls.extend(_photo_urls_from_value(annonce.get(key)))

    uniques = []
    for url in urls:
        if url and url not in uniques:
            uniques.append(url)
    return uniques


def _metadata_from_annonce(annonce: dict) -> dict:
    metadata = {}

    for key, value in annonce.items():
        metadata_value = _metadata_value(key, value)
        if metadata_value is not None:
            metadata[key] = metadata_value

    photos = _photo_urls_from_annonce(annonce)
    if photos:
        metadata.setdefault("photo_url", str(photos[0]))
        metadata["photos"] = json.dumps(photos, ensure_ascii=False)

    return metadata


def indexer_annonces(annonces: list[dict]) -> None:
    """
    Indexe une liste d'annonces dans ChromaDB.

    Chaque annonce doit contenir au minimum :
    id, type, surface, quartier, prix, description
    """
    collection = get_collection()
    if not annonces:
        return

    ids = []
    documents = []
    metadatas = []

    for annonce in annonces:
        annonce_id = annonce.get("id") or annonce.get("id_source") or annonce.get("url_source")
        if not annonce_id:
            continue

        documents.append(
            " ".join(
                str(value)
                for value in (
                    annonce.get("type"),
                    annonce.get("surface"),
                    annonce.get("quartier"),
                    annonce.get("prix"),
                    annonce.get("description"),
                )
                if value not in (None, "")
            )
        )
        ids.append(str(annonce_id))
        metadatas.append(_metadata_from_annonce(annonce))

    if documents:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)


def search_similar(query: str, n_results: int = 5, filtre_meta: dict | None = None) -> list[dict]:
    """
    Recherche sémantique : retourne les n_results biens les plus proches de la requête.

    Args:
        query: description en langage naturel du bien recherché
        n_results: nombre de résultats à retourner
        filtre_meta: filtres optionnels sur les métadonnées (ex: {"quartier": "Mourillon"})

    Returns:
        Liste de dicts avec les métadonnées des biens
    """
    collection = get_collection()
    query_kwargs = {
        "query_texts": [query],
        "n_results": n_results,
    }
    if filtre_meta:
        query_kwargs["where"] = filtre_meta

    results = collection.query(**query_kwargs)
    metadatas = results.get("metadatas") or [[]]
    ids = results.get("ids") or [[]]
    result_metadatas = metadatas[0]
    result_ids = ids[0]

    return [
        {**metadata, "id": metadata.get("id") or result_ids[index]}
        for index, metadata in enumerate(result_metadatas)
    ]
