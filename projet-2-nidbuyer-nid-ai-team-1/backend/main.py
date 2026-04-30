from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel
from .ingestion import sync

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(sync, "cron", hour=7, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="NidBuyerAI API", version="0.1.0", lifespan=lifespan)


@app.get("/")
def accueil():
    return {
        "message": "Bienvenue sur l'API NidBuyerAI",
        "documentation": "/docs",
        "status": "/admin/status",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "NidBuyerAI API",
        "version": app.version,
    }


class ProfilAcheteur(BaseModel):
    intention: str
    budget_max: float
    surface_min: float | None = None
    quartiers: list[str] = []
    nb_pieces_min: int | None = None
    description_libre: str = ""
    ville: str | None = "Toulon"


class AlerteProfil(BaseModel):
    email: str
    profil: ProfilAcheteur


def scoring_indisponible(message: str) -> dict:
    return {
        "prix_m2": None,
        "mediane_prix_m2": None,
        "ecart_pct": None,
        "score": None,
        "statut": "donnees_indisponibles",
        "message": message,
    }


def construire_scoring_et_fiche(bien: dict, profil_intention: str = "rp") -> tuple[dict, str]:
    from .analysis.dvf_services import get_stats_bien
    from .scoring import score_opportunite, fiche_decision

    dvf_stats = get_stats_bien(bien)
    mediane_quartier = float(dvf_stats["mediane_prix_m2"]) if dvf_stats else None

    if mediane_quartier is None:
        message = (
            "DonnÃ©es DVF indisponibles pour ce bien : "
            "le score est calculÃ© uniquement pour les biens situÃ©s Ã  Toulon "
            "avec un quartier reconnu dans le fichier DVF."
        )
        return scoring_indisponible(message), message

    try:
        scoring = score_opportunite(
            bien=bien,
            mediane_quartier=mediane_quartier,
            profil=profil_intention,
            dvf_stats=dvf_stats,
        )

        fiche = fiche_decision(
            bien=bien,
            dvf_quartier={"mediane_prix_m2": mediane_quartier},
        )

        return scoring, fiche

    except Exception as exc:
        message = f"Score indisponible : {exc}"
        return scoring_indisponible(message), message


@app.get("/biens")
def liste_biens(
    budget_max: float | None = None,
    surface_min: float | None = None,
    quartier: str | None = None,
):
    from .rag import get_collection

    filtres = []
    if budget_max is not None:
        filtres.append({"prix": {"$lte": budget_max}})
    if surface_min is not None:
        filtres.append({"surface": {"$gte": surface_min}})
    if quartier:
        filtres.append({"quartier": {"$eq": quartier}})

    query = {"include": ["metadatas"]}
    if len(filtres) == 1:
        query["where"] = filtres[0]
    elif filtres:
        query["where"] = {"$and": filtres}

    try:
        results = get_collection(with_embedding=False).get(**query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lecture des biens impossible: {exc}") from exc

    ids = results.get("ids") or []
    metadatas = results.get("metadatas") or []

    biens = [
        {**(metadata or {}), "id": (metadata or {}).get("id") or ids[index]}
        for index, metadata in enumerate(metadatas)
    ]

    return {"total": len(biens), "biens": biens}


@app.get("/biens/{bien_id}")
def detail_bien(bien_id: str):
    from .rag import get_collection

    results = get_collection(with_embedding=False).get(ids=[bien_id], include=["metadatas"])
    ids = results.get("ids") or []
    metadatas = results.get("metadatas") or []

    if not ids or not metadatas:
        raise HTTPException(status_code=404, detail="Bien introuvable")

    bien = {**(metadatas[0] or {}), "id": (metadatas[0] or {}).get("id") or ids[0]}
    scoring, fiche = construire_scoring_et_fiche(bien)

    return {
        "bien": bien,
        "scoring": scoring,
        "fiche_decision": fiche,
    }


@app.post("/rechercher")
def rechercher(profil: ProfilAcheteur):
    from .rag import search_similar

    query = (
        f"{profil.intention} "
        f"ville {profil.ville or 'Toulon'} "
        f"budget maximum {profil.budget_max} euros "
        f"surface minimum {profil.surface_min or ''} m² "
        f"quartiers {' '.join([q for q in profil.quartiers if q != 'Indifférent'])} "
        f"nombre de pièces minimum {profil.nb_pieces_min or ''} "
        f"{profil.description_libre}"
    )

    biens = search_similar(query, n_results=50)
    biens_filtres = []

    ville_demandee = str(profil.ville or "Toulon").strip().lower()

    for bien in biens:
        try:
            prix = float(bien.get("prix") or 0)
            surface = float(bien.get("surface") or 0)

            nb_pieces_raw = (
                bien.get("nb_pieces")
                or bien.get("pieces")
                or bien.get("nombre_pieces")
                or 0
            )
            nb_pieces = int(float(nb_pieces_raw or 0))

            ville_bien = str(
                bien.get("ville")
                or bien.get("city")
                or bien.get("commune")
                or bien.get("localisation")
                or ""
            ).strip().lower()

            quartier = str(bien.get("quartier") or "").strip().lower()

            if ville_demandee:
                if not ville_bien or ville_demandee not in ville_bien:
                    continue

            if prix > profil.budget_max:
                continue

            if profil.surface_min and surface < profil.surface_min:
                continue

            if profil.nb_pieces_min and nb_pieces < profil.nb_pieces_min:
                continue

            if profil.quartiers:
                quartiers_ok = [
                    q.strip().lower()
                    for q in profil.quartiers
                    if q
                    and q.strip().lower() != "indifférent"
                    and q.strip().lower() != "toulon"
                ]

                if quartiers_ok:
                    if not quartier:
                        continue

                    quartier_match = any(
                        q == quartier
                        or q in quartier
                        or quartier in q
                        for q in quartiers_ok
                    )

                    if not quartier_match:
                        continue

            biens_filtres.append(bien)

        except Exception:
            continue

    resultats = []

    for i, bien in enumerate(biens_filtres[:5]):
        scoring, fiche = construire_scoring_et_fiche(
            bien=bien,
            profil_intention=profil.intention,
        )

        reference = bien.get("id") or bien.get("reference") or str(i)

        resultats.append(
            {
                "reference": reference,
                "bien": {
                    **bien,
                    "reference": reference,
                },
                "scoring": scoring,
                "fiche_decision": fiche,
                "tags": [],
            }
        )

    return {
        "profil": profil,
        "query": query,
        "criteres_appliques": {
            "ville": profil.ville or "Toulon",
            "budget_max": profil.budget_max,
            "surface_min": profil.surface_min,
            "quartiers": profil.quartiers,
            "nb_pieces_min": profil.nb_pieces_min,
        },
        "total_rag": len(biens),
        "total_apres_filtre": len(biens_filtres),
        "resultats": resultats,
    }


@app.post("/chat")
def chat(question: str, profil: ProfilAcheteur | None = None):
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    import re
    import anthropic
    from pathlib import Path
    from .rag import search_similar, get_collection
    from .analysis.dvf_services import get_stats_quartiers_toulon

    profil_texte = ""
    if profil:
        profil_texte = (
            f"Intention: {profil.intention}. "
            f"Budget maximum: {profil.budget_max} EUR. "
            f"Surface minimum: {profil.surface_min or 'non precisee'} m2. "
            f"Quartiers: {', '.join(profil.quartiers) or 'non precise'}. "
            f"Pieces minimum: {profil.nb_pieces_min or 'non precise'}. "
            f"Description libre: {profil.description_libre or 'non precisee'}."
        )

    reference_detectee = None
    match = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        question,
    )
    if match:
        reference_detectee = match.group(0)

    biens = []

    try:
        if reference_detectee:
            collection = get_collection(with_embedding=False)
            result = collection.get(
                ids=[reference_detectee],
                include=["metadatas", "documents"],
            )

            ids = result.get("ids") or []
            metadatas = result.get("metadatas") or []
            documents = result.get("documents") or []

            if ids:
                metadata = metadatas[0] or {}
                document = documents[0] if documents else ""

                bien = {
                    **metadata,
                    "id": metadata.get("id") or ids[0],
                    "description": metadata.get("description") or document,
                }
                biens = [bien]

        if not biens:
            requete_rag = f"{question} {profil_texte}".strip()
            biens = search_similar(requete_rag, n_results=5)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Recherche RAG impossible: {exc}") from exc

    lignes_contexte = []
    for index, bien in enumerate(biens, start=1):
        prix = bien.get("prix")
        surface = bien.get("surface")
        prix_m2 = ""
        scoring_texte = ""
        fiche_texte = ""

        try:
            if prix is not None and surface:
                prix_m2 = f" | prix_m2={float(prix) / float(surface):.0f} EUR/m2"
        except (TypeError, ValueError, ZeroDivisionError):
            prix_m2 = ""

        try:
            scoring, fiche = construire_scoring_et_fiche(
                bien=bien,
                profil_intention=profil.intention if profil else "rp",
            )
            scoring_texte = (
                f" | mediane_dvf={scoring.get('mediane_prix_m2')} EUR/m2"
                f" | ecart_pct={scoring.get('ecart_pct')}"
                f" | score={scoring.get('score')}"
                f" | fourchette_dvf={scoring.get('min_prix_m2')}-{scoring.get('max_prix_m2')} EUR/m2"
                f" | percentile_prix_m2={scoring.get('percentile_prix_m2')}"
                f" | nb_ventes_comparees={scoring.get('nb_transactions')}"
                f" | quartier_comparaison={scoring.get('quartier_comparaison')}"
            )
            fiche_texte = f"\nFiche decision:\n{fiche}"
        except Exception as exc:
            scoring_texte = f" | scoring_dvf=indisponible ({exc})"

        lignes_contexte.append(
            (
                f"[Bien {index}] id={bien.get('id', 'n/a')} | "
                f"type={bien.get('type', 'n/a')} | "
                f"quartier={bien.get('quartier', 'n/a')} | "
                f"surface={surface or 'n/a'} m2 | "
                f"prix={prix or 'n/a'} EUR{prix_m2}{scoring_texte} | "
                f"description={str(bien.get('description', ''))[:1200]}"
                f"{fiche_texte}"
            )
        )

    contexte_biens = "\n".join(lignes_contexte) or "Aucun bien pertinent trouve dans la base RAG."

    question_normalisee = question.casefold()
    demande_quartier = any(
        terme in question_normalisee
        for terme in ("quartier", "secteur", "invest", "investir", "marche", "marchÃ©")
    )
    contexte_marche = ""

    if demande_quartier:
        try:
            quartiers = get_stats_quartiers_toulon()
            lignes_marche = []
            for item in quartiers:
                lignes_marche.append(
                    (
                        f"- {item.get('quartier')}: "
                        f"mediane={item.get('mediane_prix_m2')} EUR/m2, "
                        f"moyenne={item.get('moyenne_prix_m2')} EUR/m2, "
                        f"fourchette={item.get('min_prix_m2')}-{item.get('max_prix_m2')} EUR/m2, "
                        f"transactions={item.get('nb_transactions')}"
                    )
                )
            contexte_marche = "\n".join(lignes_marche)
        except Exception as exc:
            contexte_marche = f"Donnees marche quartiers indisponibles: {exc}"

    system_prompt = getattr(chat, "_system_prompt", None)
    if system_prompt is None:
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "system.txt"
        system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else (
            "Tu es NidBuyer, un conseiller immobilier IA specialise sur le marche de Toulon."
        )
        chat._system_prompt = system_prompt

    message = (
        "Reponds a la question de l'acheteur en t'appuyant uniquement sur les contextes fournis. "
        "Pour une question sur les quartiers ou le marche, utilise d'abord le contexte marche quartiers DVF, "
        "puis les biens RAG seulement comme exemples d'annonces. "
        "Si une rÃ©fÃ©rence prÃ©cise est demandÃ©e et qu'elle est prÃ©sente dans le contexte, analyse ce bien. "
        "Ne dis pas que la rÃ©fÃ©rence est absente si elle apparait dans le contexte.\n\n"
        f"Profil acheteur:\n{profil_texte or 'Non fourni'}\n\n"
        f"Reference detectee:\n{reference_detectee or 'Aucune'}\n\n"
        f"Contexte marche quartiers DVF:\n{contexte_marche or 'Non demande ou indisponible'}\n\n"
        f"Contexte biens RAG:\n{contexte_biens}\n\n"
        f"Question:\n{question}"
    )

    try:
        client = getattr(chat, "_anthropic_client", None)
        if client is None:
            client = anthropic.Anthropic()
            chat._anthropic_client = client

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": message}],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Appel Anthropic impossible: {exc}") from exc

    reponse = "".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ).strip()

    return {
        "question": question,
        "reference_detectee": reference_detectee,
        "reponse": reponse,
        "sources": biens,
    }

@app.post("/alerte")
def creer_alerte(alerte: AlerteProfil):
    from .alert import sauvegarder_profil

    sauvegarder_profil(alerte.email, alerte.profil.model_dump())
    return {"message": "Alerte creee", "email": alerte.email}


@app.get("/marche/quartiers")
def marche_quartiers():
    from .analysis.dvf_services import get_stats_quartiers_toulon

    stats = get_stats_quartiers_toulon()

    return {
        "source_groupement": "quartier",
        "total_transactions": sum(item["nb_transactions"] for item in stats),
        "quartiers": stats,
    }


@app.post("/admin/sync")
def admin_sync(background_tasks: BackgroundTasks, dry_run: bool = False):
    background_tasks.add_task(sync, dry_run=dry_run)
    return {"status": "sync lancée en arrière-plan", "dry_run": dry_run}


@app.post("/admin/backfill-supabase")
def admin_backfill_supabase(
    table_name: str = "annonces",
    batch_size: int = 500,
    limit: int | None = None,
    dry_run: bool = False,
    replace: bool = True,
):
    from .ingestion import backfill_supabase_annonces

    try:
        return backfill_supabase_annonces(
            table_name=table_name,
            batch_size=batch_size,
            limit=limit,
            dry_run=dry_run,
            replace=replace,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backfill Supabase impossible: {exc}") from exc


@app.get("/admin/status")
def admin_status():
    from pathlib import Path
    from .rag import get_collection

    try:
        n = get_collection(with_embedding=False).count()
    except Exception:
        n = 0

    last_sync = Path("data/.last_sync")

    return {
        "annonces_indexees": n,
        "derniere_sync": last_sync.read_text() if last_sync.exists() else "jamais",
    }
