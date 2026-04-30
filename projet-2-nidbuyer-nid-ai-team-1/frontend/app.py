"""
NidBuyer — Frontend Streamlit V2
Lancement:
streamlit run frontend/app.py
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

_carte_import_error = None
try:
    from carte_quartiers import afficher_carte
except Exception as exc:
    _carte_import_error = exc

    def afficher_carte():
        st.error("La carte interactive n'a pas pu etre chargee.")
        st.caption(f"Detail technique: {_carte_import_error}")


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

API_URL = os.getenv("NIDBUYER_API_URL") or os.getenv("API_URL") or "http://127.0.0.1:8000"
API_FALLBACK_URLS = (
    API_URL,
    "http://127.0.0.1:8000",
    "http://localhost:8000",
)
LOGO_PATH = Path(__file__).resolve().parent / "logo_niddouillet.png"

INTENTION_TO_API = {
    "Residence principale": "rp",
    "Residence secondaire": "rs",
    "Investissement": "investissement",
    "Mixte": "mixte",
}


st.set_page_config(
    page_title="NidBuyer",
    page_icon="🏠",
    layout="wide",
)


def normalize_api_url(value: Any) -> str:
    return str(value or API_URL).strip().rstrip("/")


def api_url() -> str:
    return normalize_api_url(
        st.session_state.get("api_url_input")
        or st.session_state.get("api_url")
        or API_URL
    )


def active_api_url() -> str:
    return normalize_api_url(st.session_state.get("api_active_url") or api_url())


def api_url_candidates() -> list[str]:
    current = api_url()
    active = st.session_state.get("api_active_url")
    candidates = [current, *API_FALLBACK_URLS]

    if current == "http://localhost:8000" and API_URL != current:
        candidates = [API_URL, current, *API_FALLBACK_URLS]

    if active:
        candidates.insert(1, active)

    normalized: list[str] = []

    for candidate in candidates:
        url = normalize_api_url(candidate)
        if url and url not in normalized:
            normalized.append(url)

    return normalized


def request_api(method: str, path: str, base_url: str | None = None, **kwargs: Any) -> Any:
    candidates = [normalize_api_url(base_url)] if base_url else api_url_candidates()
    connection_errors = []

    for candidate in candidates:
        url = f"{candidate}{path}"

        try:
            response = requests.request(method, url, timeout=45, **kwargs)
            response.raise_for_status()
            st.session_state["api_active_url"] = candidate
            return response.json()

        except requests.exceptions.ConnectionError as exc:
            connection_errors.append(candidate)
            if candidate != candidates[-1]:
                continue
            tested = ", ".join(connection_errors)
            raise RuntimeError(
                f"API indisponible. URLs testees: {tested}. "
                "Demarre le backend FastAPI avec: uvicorn backend.main:app --reload"
            ) from exc

        except requests.exceptions.Timeout as exc:
            connection_errors.append(f"{candidate} (timeout)")
            if method.upper() in {"GET", "HEAD", "OPTIONS"} and candidate != candidates[-1]:
                continue
            raise RuntimeError(f"Timeout API sur {candidate}") from exc

        except requests.exceptions.HTTPError as exc:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = response.text

            raise RuntimeError(f"{response.status_code} - {detail or 'Erreur API'}") from exc

        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Erreur reseau sur {candidate}: {exc}") from exc

    raise RuntimeError("API indisponible.")


def render_brand_header(title: str) -> None:
    col_logo, col_title = st.columns([1, 6])

    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=90)

    with col_title:
        st.title(title)


def format_price(value: Any) -> str:
    try:
        return f"{float(value):,.0f} €".replace(",", " ")
    except (TypeError, ValueError):
        return "Prix non renseigné"


def format_area(value: Any) -> str:
    try:
        return f"{float(value):.0f} m²"
    except (TypeError, ValueError):
        return "Surface n/a"


def photo_urls_from_value(value: Any) -> list[str]:
    if value in (None, ""):
        return []

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                return photo_urls_from_value(json.loads(text))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return [text]

    if isinstance(value, dict):
        for key in ("url", "src", "href", "large", "medium", "small"):
            url = value.get(key)
            if isinstance(url, str) and url.strip():
                return [url.strip()]
        return []

    if isinstance(value, (list, tuple)):
        urls = []
        for item in value:
            urls.extend(photo_urls_from_value(item))
        return urls

    return []


def annonce_photo_urls(bien: dict[str, Any]) -> list[str]:
    urls = []
    for key in (
        "photos",
        "photo_urls",
        "images",
        "image_urls",
        "pictures",
        "photo_url",
        "image_url",
        "photo",
        "image",
    ):
        urls.extend(photo_urls_from_value(bien.get(key)))

    uniques = []
    for url in urls:
        if url and url not in uniques:
            uniques.append(url)

    return uniques


def render_photo_gallery(photo_urls: list[str]) -> None:
    if not photo_urls:
        st.info("Photo non disponible pour cette annonce.")
        return

    st.caption(f"{len(photo_urls)} photo{'s' if len(photo_urls) > 1 else ''} disponible{'s' if len(photo_urls) > 1 else ''}")
    cols = st.columns(2)

    for index, photo_url in enumerate(photo_urls[:6]):
        with cols[index % 2]:
            st.image(photo_url, use_container_width=True)

    if len(photo_urls) > 6:
        st.caption(f"+ {len(photo_urls) - 6} photos sur l'annonce source")


def only_real_values(values: list[str]) -> list[str]:
    return [value for value in values if value != "Indifférent"]


def profil_payload() -> dict[str, Any]:
    quartiers = only_real_values(st.session_state.get("quartier_critere", []))

    budget_max = int(st.session_state.get("prix_max_input", 0) or 0)
    if not budget_max:
        budget_max = 2_000_000

    surface_min = int(st.session_state.get("surface_min_input", 0) or 0)

    pieces = only_real_values(st.session_state.get("pieces_critere", []))
    nb_pieces_min = None

    if pieces:
        nums = []
        for piece in pieces:
            if piece == "5+":
                nums.append(5)
            elif piece.isdigit():
                nums.append(int(piece))
        nb_pieces_min = min(nums) if nums else None

    description = st.session_state.get("description", "")

    return {
        "intention": INTENTION_TO_API.get(st.session_state.get("intention"), "rp"),
        "budget_max": float(budget_max),
        "surface_min": float(surface_min) if surface_min else None,
        "quartiers": quartiers,
        "nb_pieces_min": nb_pieces_min,
        "description_libre": description,
        "ville": st.session_state.get("ville", "Toulon"),
    }


def load_health() -> dict[str, Any] | None:
    try:
        health = request_api("GET", "/health")
        st.session_state["api_last_error"] = ""
        return health
    except RuntimeError as health_exc:
        try:
            request_api("GET", "/admin/status")
            st.session_state["api_last_error"] = ""
            return {"status": "ok", "fallback": "/admin/status"}
        except RuntimeError as status_exc:
            st.session_state["api_last_error"] = (
                f"/health: {health_exc} | /admin/status: {status_exc}"
            )
            return None


def load_status() -> dict[str, Any] | None:
    try:
        st.session_state["api_status_error"] = ""
        return request_api("GET", "/admin/status")
    except RuntimeError as exc:
        st.session_state["api_status_error"] = str(exc)
        return None


def build_reco_message(intention: str, score: float | None) -> str:
    if score is None:
        return "Score d'opportunité non disponible."

    if intention == "Investissement":
        if score >= 8:
            return "Bonne opportunité d'investissement: potentiel locatif et marge de negociation interessants."
        if score >= 6:
            return "A analyser pour investissement: verifier rendement net, charges et tension locative."
        return "Plutot risque pour investissement: rentabilite possiblement insuffisante."

    if intention == "Residence principale":
        if score >= 8:
            return "Bonne opportunité pour residence principale: rapport qualite/prix attractif."
        if score >= 6:
            return "A analyser pour residence principale: comparer confort, emplacement et budget."
        return "Bien moins adapte a une residence principale au regard du prix."

    if intention == "Residence secondaire":
        if score >= 8:
            return "Bonne opportunité pour residence secondaire: potentiel de valorisation interessant."
        if score >= 6:
            return "A analyser pour residence secondaire: verifier usage saisonnier et cout d'entretien."
        return "Peu attractif pour une residence secondaire avec les criteres actuels."

    if score >= 8:
        return "Bonne opportunite pour une strategie mixte."
    if score >= 6:
        return "A analyser pour strategie mixte: equilibrer confort d'usage et rendement."
    return "Moins pertinent pour une strategie mixte avec les criteres actuels."


def build_positionnement_tag(ecart_pct: Any) -> tuple[str, str] | None:
    try:
        ecart = float(ecart_pct)
    except (TypeError, ValueError):
        return None

    if ecart <= -10:
        return "Sous-&eacute;valu&eacute;", "under"
    if ecart >= 10:
        return "Sur&eacute;valu&eacute;", "over"
    return "Prix march&eacute;", "market"


def build_percentile_message(percentile: Any) -> str | None:
    try:
        value = float(percentile)
    except (TypeError, ValueError):
        return None

    moins_chers = max(0, min(100, round(value)))
    if value <= 50:
        return f"Dans les {moins_chers}% les moins chers"
    return f"Plus cher que {moins_chers}% des ventes comparees"


def render_fiche_decision(fiche_decision: Any) -> None:
    text = str(fiche_decision or "").strip()
    if not text:
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return

    st.markdown("##### Fiche décision")
    st.info(lines[0])

    for line in lines[1:]:
        if " : " in line:
            title, content = line.split(" : ", 1)
            st.markdown(f"**{title.strip()}**  \n{content.strip()}")
        else:
            st.markdown(line)


def render_annonce_card(result: dict[str, Any]) -> None:
    bien = result.get("bien", {})
    scoring = result.get("scoring", {})
    reference = result.get("reference") or bien.get("reference", "N/A")
    tags = result.get("tags", [])
    fiche_decision = result.get("fiche_decision")

    titre = (
        bien.get("titre")
        or bien.get("title")
        or f"{bien.get('type', 'Bien')} — {bien.get('quartier', 'Quartier non précisé')}"
    )

    prix = bien.get("prix")
    surface = bien.get("surface")
    description = bien.get("description")
    photo_urls = annonce_photo_urls(bien)
    url_source = bien.get("url_source") or bien.get("url")

    score = scoring.get("score")
    prix_m2 = scoring.get("prix_m2")
    mediane_prix_m2 = scoring.get("mediane_prix_m2")
    ecart_pct = scoring.get("ecart_pct")
    min_prix_m2 = scoring.get("min_prix_m2")
    max_prix_m2 = scoring.get("max_prix_m2")
    nb_transactions = scoring.get("nb_transactions")
    percentile_prix_m2 = scoring.get("percentile_prix_m2")
    quartier_comparaison = scoring.get("quartier_comparaison")
    positionnement = build_positionnement_tag(ecart_pct)

    with st.container(border=True):
        render_photo_gallery(photo_urls)

        st.subheader(f"{titre} — {format_price(prix)}")
        st.caption(f"Reference annonce: {reference}")

        meta = []
        if surface:
            meta.append(format_area(surface))
        if bien.get("quartier"):
            meta.append(str(bien.get("quartier")))
        if bien.get("nb_pieces"):
            meta.append(f"{bien.get('nb_pieces')} pièces")
        if bien.get("dpe"):
            meta.append(f"DPE {bien.get('dpe')}")

        if meta:
            st.caption(" · ".join(meta))

        if positionnement:
            label, variant = positionnement
            st.markdown(
                f"<span class='position-tag position-tag-{variant}'>{label}</span>",
                unsafe_allow_html=True,
            )

        if description:
            st.write(str(description)[:650])
        else:
            st.caption("Description non disponible pour cette annonce.")

        if tags:
            tags_html = "".join(
                f"<span class='interest-tag'>{tag}</span>" for tag in tags
            )
            st.markdown(
                f"<div class='interest-tags'>{tags_html}</div>",
                unsafe_allow_html=True,
            )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Prix/m²",
            f"{float(prix_m2):.0f} €" if prix_m2 is not None else "A impl.",
        )

        c2.metric(
            "Médiane quartier",
            f"{float(mediane_prix_m2):.0f} €" if mediane_prix_m2 is not None else "A impl.",
            f"{float(ecart_pct):.1f}%" if ecart_pct is not None else None,
        )

        c3.metric(
            "Score",
            f"{float(score):.1f}" if score is not None else "A impl.",
        )

        c4.metric(
            "Ventes comparees",
            f"{int(nb_transactions)}" if nb_transactions is not None else "n/a",
        )

        comparison_bits = []
        if min_prix_m2 is not None and max_prix_m2 is not None:
            comparison_bits.append(
                f"Fourchette quartier: {float(min_prix_m2):.0f} - {float(max_prix_m2):.0f} €/m²"
            )
        percentile_message = build_percentile_message(percentile_prix_m2)
        if percentile_message:
            comparison_bits.append(percentile_message)
        if quartier_comparaison:
            comparison_bits.append(f"Comparaison: {quartier_comparaison}")

        if comparison_bits:
            st.caption(" · ".join(comparison_bits))

        score_float = float(score) if score is not None else None
        reco_msg = build_reco_message(st.session_state.get("intention"), score_float)

        if score_float is not None and score_float >= 8:
            st.success(reco_msg)
        elif score_float is not None and score_float >= 6:
            st.warning(reco_msg)
        else:
            st.error(reco_msg)

        render_fiche_decision(fiche_decision)

        if url_source:
            st.link_button("Voir l'annonce source", url_source)

        if st.button(f"Analyser {titre}", key=f"analyse-{reference}"):
            question = f"Analyse la reference {reference} pour mon profil {st.session_state.get('intention')}."

            with st.spinner("Analyse IA en cours..."):
                try:
                    chat_response = request_api(
                        "POST",
                        "/chat",
                        params={"question": question},
                        json=profil_payload(),
                    )
                    st.write(chat_response.get("reponse") or "Réponse vide")
                except RuntimeError as exc:
                    st.error(str(exc))


defaults = {
    "messages": [],
    "saved_alerts": [],
    "last_results": [],
    "quartier_selectionne": None,
    "reference_index": {},
    "api_url_input": st.session_state.get("api_url", API_URL),
    "api_active_url": "",
    "api_last_error": "",
    "api_status_error": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


render_brand_header("NidDouillet")

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        padding: 0.25rem 0.4rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.05rem;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.75rem;
    }
    .interest-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin: 0.25rem 0 0.5rem 0;
    }
    .interest-tag {
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.15rem 0.45rem;
        border-radius: 999px;
        background: #eef3fa;
        color: #24456b;
        border: 1px solid #d4e0ef;
    }
    .position-tag {
        display: inline-flex;
        align-items: center;
        width: fit-content;
        margin: 0.15rem 0 0.55rem 0;
        padding: 0.22rem 0.55rem;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 700;
        border: 1px solid transparent;
    }
    .position-tag-under {
        background: #eaf7ef;
        color: #11612f;
        border-color: #bfe6cc;
    }
    .position-tag-market {
        background: #eef3fa;
        color: #24456b;
        border-color: #d4e0ef;
    }
    .position-tag-over {
        background: #fdecec;
        color: #8f2f2f;
        border-color: #f4c9c9;
    }
    .score-footer {
        color: #64748b;
        font-size: 0.82rem;
        line-height: 1.45;
        margin: 0.4rem 0 0.25rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    widget_defaults = {
        "intention": "Residence principale",
        "ville": "Toulon",
        "quartier_critere": [],
        "prix_max_input": 500000,
        "surface_min_input": 0,
        "pieces_critere": [],
        "description": "",
        "email": "",
    }

    for key, value in widget_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    st.subheader("Critères de recherche")

    intention = st.selectbox(
        "Projet",
        [
            "Residence principale",
            "Residence secondaire",
            "Investissement",
            "Mixte",
        ],
        key="intention",
    )

    ville = st.text_input(
        "Ville",
        key="ville",
    )

    quartier_critere = st.multiselect(
    "Quartier",
    [
        "Toulon - Beaulieu",
        "Toulon - Le Cap Brun - Le Petit Bois",
        "Toulon - Porte d'Italie",
        "Toulon - La Rode",
        "Toulon - Beaulieu",
        "Toulon - Porte d'Italie",
        "Toulon - Le Mourillon La Mitre - Fort",
        "Toulon - Haute ville",
        "Toulon - La Palasse",
        "Toulon - Champs de Mars",
        "Toulon - Aguillon",
        "Toulon - Ubc - Dardennes - Barbanne",
        "Toulon",
    ],
    key="quartier_critere",
)

    st.number_input(
        "Budget maximum (€)",
        min_value=0,
        step=10000,
        key="prix_max_input",
    )

    st.number_input(
        "Surface minimum (m²)",
        min_value=0,
        step=5,
        key="surface_min_input",
    )

    pieces_critere = st.multiselect(
    "Nombre de pièces minimum",
    ["1", "2", "3", "4", "5+"],
    key="pieces_critere",
)

    st.divider()
    st.subheader("🔔 Alerte")

    description = st.text_area(
        "Description libre",
        placeholder="T3 calme, vue dégagée, proche transports...",
        key="description",
    )

    email = st.text_input("Email", key="email")

    if st.button("Enregistrer l'alerte"):
        if not email:
            st.warning("Email requis")
        else:
            alert_payload = {
                "email": email,
                "profil": profil_payload(),
            }

            try:
                request_api("POST", "/alerte", json=alert_payload)

                st.session_state.saved_alerts.append(
                    {
                        "title": f"Alerte {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                        "email": email,
                        "intention": intention,
                        "quartier": st.session_state.quartier_critere,
                        "prix_max": int(st.session_state.get("prix_max_input", 0) or 0),
                        "surface_min": int(st.session_state.get("surface_min_input", 0) or 0),
                        "pieces": st.session_state.pieces_critere,
                        "description": description,
                        "date": datetime.now().strftime("%d/%m/%Y"),
                    }
                )

                st.success("Alerte enregistrée.")

            except RuntimeError as exc:
                st.error(str(exc))

tabs = st.tabs(
    [
        "🏠 Annonces",
        "🤖 Conseiller IA",
        "📍 Quartiers",
        "⚙️ Admin",
    ]
)


with tabs[0]:
    st.subheader("Trouver des annonces")

    if st.button("Trouver mes biens", type="primary"):
        with st.spinner("Recherche RAG et scoring en cours..."):
            try:
                data = request_api("POST", "/rechercher", json=profil_payload())
                results = data.get("resultats", [])

                st.session_state.last_results = results
                st.session_state.reference_index = {
                    str(result.get("reference")): result for result in results
                }

            except RuntimeError as exc:
                st.error(str(exc))

    if st.session_state.last_results:
        for result in st.session_state.last_results:
            render_annonce_card(result)
    else:
        st.info("Lance une recherche pour afficher les annonces réelles indexées.")


with tabs[1]:
    st.subheader("Conseiller immobilier IA")
    st.caption("Tu peux citer une annonce par sa reference, ex: 'Analyse la reference 1001'.")

    suggestions = st.pills(
        "Questions rapides",
        [
            "Dois-je négocier ce bien ?",
            "Quel quartier pour 300k ?",
            "Bon rendement locatif ?",
        ],
    )

    if suggestions:
        prompt = suggestions

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.spinner("Analyse IA en cours..."):
            try:
                data = request_api(
                    "POST",
                    "/chat",
                    params={"question": prompt},
                    json=profil_payload(),
                )
                rep = data.get("reponse") or "Réponse vide."
            except RuntimeError as exc:
                rep = str(exc)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": rep,
            }
        )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_prompt = st.chat_input("Posez une question...")

    if user_prompt:
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )

        with st.spinner("Analyse IA en cours..."):
            try:
                data = request_api(
                    "POST",
                    "/chat",
                    params={"question": user_prompt},
                    json=profil_payload(),
                )
                rep = data.get("reponse") or "Réponse vide."
            except RuntimeError as exc:
                rep = str(exc)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": rep,
            }
        )

        st.rerun()


with tabs[2]:
    afficher_carte()

    st.divider()
    st.subheader("Données marché par quartier")

    if st.button("Charger les médianes DVF", type="primary"):
        with st.spinner("Chargement des données DVF..."):
            try:
                st.session_state["market_data"] = request_api("GET", "/marche/quartiers")
            except RuntimeError as exc:
                st.error(str(exc))

    market_data = st.session_state.get("market_data")

    if market_data:
        quartiers = market_data.get("quartiers", [])

        c1, c2 = st.columns(2)
        c1.metric("Transactions", market_data.get("total_transactions", 0))
        c2.metric("Groupement", market_data.get("source_groupement", "quartier"))

        if quartiers:
            df = pd.DataFrame(quartiers)
            st.dataframe(df, use_container_width=True, hide_index=True)

            if "quartier" in df.columns and "mediane_prix_m2" in df.columns:
                st.bar_chart(df.set_index("quartier")["mediane_prix_m2"])
        else:
            st.info("Aucune donnée DVF disponible.")
    else:
        st.caption("Objectif: afficher les médianes DVF réelles par quartier.")


with tabs[3]:
    st.subheader("Administration")

    st.text_input("URL API", key="api_url_input")

    health = load_health()
    status = load_status() if health else None

    if health:
        st.success(f"API connectee ({active_api_url()})")

        if status:
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Annonces indexees",
                    status.get("annonces_indexees", 0),
                )

            with col2:
                st.metric(
                    "Derniere sync",
                    status.get("derniere_sync", "jamais"),
                )
        else:
            st.warning("API connectee, mais statut admin indisponible")
            if st.session_state.get("api_status_error"):
                st.caption(st.session_state["api_status_error"])
    else:
        st.warning("API non joignable")
        if st.session_state.get("api_last_error"):
            st.caption(st.session_state["api_last_error"])

    st.divider()

    col_sync, col_refresh = st.columns(2)

    with col_sync:
        dry_run = st.checkbox("Dry run", value=True)

        if st.button("Lancer la sync", type="primary", use_container_width=True):
            try:
                result = request_api(
                    "POST",
                    "/admin/sync",
                    params={"dry_run": dry_run},
                )
                st.success(result.get("status", "Sync lancee"))
                st.json(result)
            except RuntimeError as exc:
                st.error(str(exc))

    with col_refresh:
        if st.button("Rafraichir le statut", use_container_width=True):
            health = load_health()
            status = load_status() if health else None

            if health and status:
                st.json(status)
            elif health:
                st.warning("API connectee, mais statut admin indisponible")
                if st.session_state.get("api_status_error"):
                    st.caption(st.session_state["api_status_error"])
            else:
                st.warning("API non joignable")
                if st.session_state.get("api_last_error"):
                    st.caption(st.session_state["api_last_error"])

    st.divider()

    st.markdown("### Backfill Supabase vers ChromaDB")

    b1, b2, b3, b4 = st.columns(
        [0.28, 0.18, 0.18, 0.36],
        vertical_alignment="bottom",
    )

    with b1:
        table_name = st.text_input("Table Supabase", value="annonces")

    with b2:
        backfill_limit = st.number_input(
            "Limite",
            min_value=0,
            max_value=10000,
            value=0,
            step=100,
        )

    with b3:
        replace_index = st.checkbox("Remplacer ChromaDB", value=True)

    with b4:
        if st.button("Indexer Supabase", type="primary", use_container_width=True):
            params = {
                "table_name": table_name.strip() or "annonces",
                "replace": replace_index,
                "dry_run": False,
            }

            if backfill_limit:
                params["limit"] = backfill_limit

            with st.spinner("Indexation des annonces Supabase..."):
                try:
                    result = request_api(
                        "POST",
                        "/admin/backfill-supabase",
                        params=params,
                    )
                    st.success("Backfill termine")
                    st.json(result)
                except RuntimeError as exc:
                    st.error(str(exc))


st.divider()
st.markdown(
    """
    <div class="score-footer">
        Score d'opportunit&eacute; : comparaison du prix/m2 de l'annonce avec la
        m&eacute;diane DVF du quartier. Un score positif indique un bien sous la
        m&eacute;diane, un score proche de 0 indique un prix march&eacute;, un score
        n&eacute;gatif indique un bien au-dessus de la m&eacute;diane. Le tag
        Sous-&eacute;valu&eacute; / Prix march&eacute; / Sur&eacute;valu&eacute; est
        bas&eacute; sur un seuil de 10% autour de cette m&eacute;diane.
    </div>
    """,
    unsafe_allow_html=True,
)
