"""
Carte interactive des quartiers toulonnais — NidDouillet
Lancement : streamlit run app/carte_quartiers.py

Règle : stats via analysis.stats uniquement — aucun numpy/pandas.mean/sklearn.
"""

import sys
import re
import json
from pathlib import Path

# Permet de trouver analysis/ depuis app/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from backend.analysis.stats import mean, median, standard_deviation


# ═══════════════════════════════════════════════════════════════════════════
#  DONNÉES QUARTIERS
#  → Modifie ici : desc, tags, tendance (%)
# ═══════════════════════════════════════════════════════════════════════════

QUARTIERS_META: dict[str, dict] = {
    "Les Routes": {
        "desc": "Quartier calme et verdoyant aux portes de la montagne. Idéal pour les familles cherchant de l'espace.",
        "tags": ["Résidentiel", "Familial", "Calme"],
        "tendance": 2.1,
    },
    "Le Faron": {
        "desc": "Zone en hauteur, panorama exceptionnel sur la rade. Peu d'appartements, surtout des maisons.",
        "tags": ["Vue mer", "Maisons", "Exclusif"],
        "tendance": 1.8,
    },
    "Le Pont du Las": {
        "desc": "Quartier populaire bien desservi par les transports. Prix accessibles, forte densité.",
        "tags": ["Abordable", "Bien desservi", "Dynamique"],
        "tendance": 3.2,
    },
    "La Serinette": {
        "desc": "Secteur mixte entre habitat et commerces. Bon rapport qualité-prix pour les primo-accédants.",
        "tags": ["Mixte", "Commerce", "Accessible"],
        "tendance": 1.5,
    },
    "Sainte-Musse": {
        "desc": "Quartier en pleine transformation avec de nombreux programmes neufs. Prix encore accessibles mais en forte hausse. Bon potentiel.",
        "tags": ["En développement", "Abordable", "Pratique"],
        "tendance": 5.3,
    },
    "Centre-Ville": {
        "desc": "Hypercentre animé, commerces, restaurants, culture. Fort marché locatif, idéal pour investisseurs.",
        "tags": ["Central", "Animé", "Investissement"],
        "tendance": 2.8,
    },
    "Cap Brun": {
        "desc": "Le quartier le plus prisé de Toulon. Résidences de luxe, vue mer exceptionnelle, calme absolu.",
        "tags": ["Luxe", "Vue mer", "Prestige"],
        "tendance": 4.1,
    },
    "Saint-Jean du Var": {
        "desc": "Quartier résidentiel avec bonnes écoles et espaces verts. Plébiscité par les familles.",
        "tags": ["Écoles", "Familial", "Résidentiel"],
        "tendance": 2.4,
    },
    "Le Mourillon": {
        "desc": "Balnéaire et vivant, à deux pas des plages. Le quartier le plus coté après Cap Brun.",
        "tags": ["Balnéaire", "Plages", "Vivant"],
        "tendance": 3.7,
    },
    "La Rode": {
        "desc": "Quartier tranquille à dominante pavillonnaire. Bonne qualité de vie, bien relié au centre.",
        "tags": ["Pavillonnaire", "Tranquille", "Verdure"],
        "tendance": 1.9,
    },
    "Claret": {
        "desc": "Secteur résidentiel calme, maisons individuelles avec jardins. Apprécié pour sa tranquillité.",
        "tags": ["Maisons", "Jardins", "Calme"],
        "tendance": 2.2,
    },
    "Brunet": {
        "desc": "Quartier populaire dynamique avec un fort tissu associatif. Prix parmi les plus bas de Toulon.",
        "tags": ["Populaire", "Prix bas", "Dynamique"],
        "tendance": 1.2,
    },
}

# ═══════════════════════════════════════════════════════════════════════════
#  POLYGONES SVG
#  → Modifie "points" pour ajuster les formes (viewBox 0 0 480 395)
#  → "lx","ly" = position du label texte
# ═══════════════════════════════════════════════════════════════════════════

POLYGONES: dict[str, dict] = {
  "Les Routes":        {"points": "24,68 128,68 128,196 24,196",                               "lx": 44,  "ly": 136},
  "Le Faron":          {"points": "130,42 432,42 426,70 414,196 246,196 172,168 130,126",     "lx": 250, "ly": 102},
  "Le Pont du Las":    {"points": "24,198 126,198 126,266 24,266",                             "lx": 34,  "ly": 236},
  "La Serinette":      {"points": "128,198 246,198 246,266 128,266",                           "lx": 160, "ly": 236},
  "Sainte-Musse":      {"points": "248,168 412,168 412,248 248,248",                           "lx": 302, "ly": 214},
  "Cap Brun":          {"points": "414,168 476,180 476,336 402,348 316,334 316,262 414,248",   "lx": 420, "ly": 246},
  "Saint-Jean du Var": {"points": "24,268 126,268 126,340 24,340",                             "lx": 34,  "ly": 304},
  "Centre-Ville":      {"points": "128,268 316,268 316,334 128,334",                           "lx": 186, "ly": 306},
  "Brunet":            {"points": "24,342 126,342 120,380 24,380",                             "lx": 46,  "ly": 366},
  "La Rode":           {"points": "128,336 286,336 280,380 122,380",                           "lx": 176, "ly": 364},
  "Claret":            {"points": "286,336 334,332 330,380 280,380",                           "lx": 292, "ly": 364},
  "Le Mourillon":      {"points": "334,332 476,356 476,380 328,380",                           "lx": 374, "ly": 364},
}

# ═══════════════════════════════════════════════════════════════════════════
#  NORMALISATION noms de quartiers (CSV → clés QUARTIERS_META)
# ═══════════════════════════════════════════════════════════════════════════

NORMALISATION: dict[str, str] = {
    # Mourillon
    "mourillon": "Le Mourillon",
    "le mourillon": "Le Mourillon",
    "mourillon centre": "Le Mourillon",
    "mourillon sud": "Le Mourillon",
    "le mourillon - la mitre - fort lamalgue": "Le Mourillon",
    # Centre
    "centre": "Centre-Ville",
    "centre ville": "Centre-Ville",
    "centre-ville": "Centre-Ville",
    # Pont du Las
    "pont du las": "Le Pont du Las",
    "pont-du-las": "Le Pont du Las",
    # Sainte-Musse
    "sainte musse": "Sainte-Musse",
    "sainte-musse": "Sainte-Musse",
    # Cap Brun
    "cap brun": "Cap Brun",
    "cap-brun": "Cap Brun",
    "le cap brun - le petit bois": "Cap Brun",
    # Saint-Jean du Var (toutes variantes, tirets inclus)
    "saint jean du var": "Saint-Jean du Var",
    "saint-jean-du-var": "Saint-Jean du Var",
    "saint-jean du var": "Saint-Jean du Var",
    # La Serinette
    "la serinette": "La Serinette",
    "la serinette - la barre": "La Serinette",
    # La Rode
    "la rode": "La Rode",
    # Les Routes
    "les routes": "Les Routes",
    # Brunet
    "brunet": "Brunet",
    # Claret
    "claret": "Claret",
    # Le Faron
    "le faron": "Le Faron",
    "le faron fort rouge": "Le Faron",
}


def _extraire_quartier(row: pd.Series) -> str:
    """Extrait le quartier depuis l'URL (SeLoger) ou le titre (Bienici)."""
    url = str(row.get("url", ""))
    titre = str(row.get("titre", ""))

    # SeLoger : .../toulon-83/NOM-QUARTIER/123...
    m = re.search(r"toulon-83[_/]([a-z][a-z0-9\-]+)[_/]\d", url.lower())
    if m:
        slug = m.group(1).replace("-", " ").strip()
        return NORMALISATION.get(slug, "")

    # Bienici : "83000 Toulon (Quartier)"
    m2 = re.search(r"\d{5}\s+toulon\s*\(([^)]+)\)", titre.lower())
    if m2:
        slug = m2.group(1).strip()
        return NORMALISATION.get(slug, "")

    return ""


# ═══════════════════════════════════════════════════════════════════════════
#  CHARGEMENT & CALCUL STATS — listes Python pures (analysis.stats)
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data
def charger_stats() -> dict[str, dict]:
    """Retourne {quartier: {pm2_median, pm2_mean, pm2_std, n_annonces}}
    Toutes les stats via analysis.stats — aucun numpy/pandas.mean."""
    try:
        df = pd.read_csv(
            Path(__file__).resolve().parent.parent / "data" / "annonces.csv"
        )
    except FileNotFoundError:
        return {}

    # Extraction quartier
    df["_q"] = df.apply(_extraire_quartier, axis=1)

    # Calcul prix/m²
    groupes: dict[str, list[float]] = {}
    for _, row in df.iterrows():
        q = row["_q"].strip()
        if not q:
            continue
        try:
            prix = float(row["prix_eur"])
            surf = float(row["surface_m2"])
        except (ValueError, TypeError):
            continue
        if surf <= 0 or prix <= 0:
            continue
        pm2 = prix / surf
        if pm2 < 500 or pm2 > 20000:
            continue
        groupes.setdefault(q, []).append(pm2)

    result: dict[str, dict] = {}
    for q, vals in groupes.items():
        if not vals:
            continue
        result[q] = {
            "pm2_median":  median(vals),
            "pm2_mean":    mean(vals),
            "pm2_std":     standard_deviation(vals) if len(vals) > 1 else 0.0,
            "n_annonces":  len(vals),
        }
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  CONSTRUCTION HTML
# ═══════════════════════════════════════════════════════════════════════════

# Labels longs → coupés sur 2 lignes pour les polygones étroits
LABELS_2_LIGNES: dict[str, tuple[str, str]] = {
    "Le Pont du Las":    ("Le Pont", "du Las"),
    "Saint-Jean du Var": ("St-Jean", "du Var"),
    "Cap Brun":          ("Cap", "Brun"),
  "Centre-Ville":      ("Centre", "Ville"),
  "Le Mourillon":      ("Le", "Mourillon"),
}


def _build_html(data_json: str) -> str:
    svg_lines = []
    for nom, p in POLYGONES.items():
        poly = f'<polygon class="q-poly" data-name="{nom}" points="{p["points"]}"/>'
        if nom in LABELS_2_LIGNES:
            l1, l2 = LABELS_2_LIGNES[nom]
            label = (
                f'<text class="q-label" x="{p["lx"]}" y="{p["ly"] - 5}">'
                f'<tspan x="{p["lx"]}" dy="0">{l1}</tspan>'
                f'<tspan x="{p["lx"]}" dy="11">{l2}</tspan>'
                f'</text>'
            )
        else:
            label = f'<text class="q-label" x="{p["lx"]}" y="{p["ly"]}">{nom}</text>'
        svg_lines.append(poly + label)
    polygons_svg = "\n        ".join(svg_lines)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif;background:transparent}}
  .wrapper{{background:linear-gradient(180deg,#fffdf9 0%,#f7f2ea 100%);border:1px solid #ebe3d8;border-radius:14px;overflow:hidden;box-shadow:0 8px 24px rgba(57,37,17,.08)}}
  .header{{padding:18px 22px 6px;display:flex;align-items:center;gap:8px}}
  .header h2{{font-size:17px;font-weight:700;color:#1e1e1e}}
  .pin{{color:#d4654e;font-size:18px}}
  .body{{display:flex;gap:14px;padding:10px 16px 16px;align-items:stretch}}
  .map-wrap{{flex:1.25;min-width:0;background:radial-gradient(circle at 18% 20%,#fff7ef 0%,#f6ecdf 55%,#f4e8da 100%);border-radius:12px;padding:8px}}
  svg{{width:100%;height:auto;display:block;max-height:560px}}
  .q-poly{{fill:#f2b9a7;stroke:#fff8f1;stroke-width:2.6;stroke-linejoin:round;cursor:pointer;transition:fill .18s,transform .18s,filter .18s}}
  .q-poly:hover{{fill:#e79078;filter:drop-shadow(0 2px 2px rgba(83,43,23,.22))}}
  .q-poly.selected{{fill:#cd5f48;stroke:#ffe8dc;stroke-width:3.2;filter:drop-shadow(0 3px 3px rgba(71,35,18,.32))}}
  .sea{{fill:#d8eaf4;stroke:none;cursor:default}}
  .q-label{{font-size:10.5px;fill:#5a2f22;font-weight:600;pointer-events:none;user-select:none;paint-order:stroke;stroke:#fff9f2;stroke-width:.8}}
  .sea-label{{font-size:11.5px;fill:#6e9ab0;font-style:italic;pointer-events:none;user-select:none}}
  .panel{{flex:1;min-width:260px;padding:8px 0 0 20px;display:flex;flex-direction:column;justify-content:center}}
  .panel-empty{{text-align:center;padding:30px 10px}}
  .big-pin{{font-size:38px;margin-bottom:10px;opacity:.35}}
  .panel-empty p{{font-size:13px;color:#aaa;line-height:1.5}}
  .panel-empty .sub{{font-size:11px;color:#ccc;margin-top:4px}}
  .panel-detail{{display:none}}
  .panel-detail.active{{display:block}}
  .q-name{{font-size:21px;font-weight:700;color:#1e1e1e;margin-bottom:7px}}
  .q-desc{{font-size:12.5px;color:#666;line-height:1.55;margin-bottom:14px}}
  .tags{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:16px}}
  .tag{{font-size:11px;padding:3px 10px;border-radius:20px;background:#f0ede8;color:#5a5a5a;border:1px solid #e3ddd7;font-weight:500}}
  .stat-row{{display:flex;gap:10px}}
  .stat-card{{flex:1;background:#f3f0eb;border-radius:9px;padding:11px 13px}}
  .stat-ico{{font-size:10.5px;color:#999;margin-bottom:5px}}
  .stat-val{{font-size:19px;font-weight:700;color:#1e1e1e}}
  .stat-val.up{{color:#1fa855}}
  .stat-val.down{{color:#d4654e}}
  @media (max-width: 980px) {{
    .body{{flex-direction:column}}
    .panel{{min-width:0;padding:10px 2px 0 2px}}
    svg{{max-height:460px}}
  }}
</style>
</head><body>
<div class="wrapper">
  <div class="header">
    <span class="pin">📍</span>
    <h2>Carte des quartiers de Toulon</h2>
  </div>
  <div class="body">
    <div class="map-wrap">
      <svg viewBox="0 0 500 390" preserveAspectRatio="xMidYMid meet">
        <path class="sea" d="M18,332 C120,336 240,324 352,330 C418,334 458,350 484,346 L484,390 L18,390 Z"/>
        <text class="sea-label" x="194" y="368">Rade de Toulon</text>
        {polygons_svg}
      </svg>
    </div>
    <div class="panel">
      <div id="panel-empty" class="panel-empty">
        <div class="big-pin">📍</div>
        <p>Cliquez sur les quartiers<br>pour les sélectionner</p>
        <p class="sub">Passez la souris pour l'ambiance</p>
      </div>
      <div id="panel-detail" class="panel-detail">
        <div id="qname" class="q-name"></div>
        <div id="qdesc" class="q-desc"></div>
        <div id="qtags" class="tags"></div>
        <div class="stat-row">
          <div class="stat-card">
            <div class="stat-ico">€ Prix m²</div>
            <div id="qprix" class="stat-val">—</div>
          </div>
          <div class="stat-card">
            <div class="stat-ico">↗ Tendance</div>
            <div id="qtend" class="stat-val up">—</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
const DATA = {data_json};

function showQuartier(name) {{
  const d = DATA[name] || {{}};
  document.getElementById('panel-empty').style.display = 'none';
  document.getElementById('panel-detail').classList.add('active');
  document.getElementById('qname').textContent = name;
  document.getElementById('qdesc').textContent = d.desc || '';
  document.getElementById('qtags').innerHTML =
    (d.tags || []).map(t => '<span class="tag">' + t + '</span>').join('');
  const pEl = document.getElementById('qprix');
  pEl.textContent = d.pm2_median
    ? Math.round(d.pm2_median).toLocaleString('fr-FR') + '\u00a0\u20ac'
    : 'N/A';
  const tEl = document.getElementById('qtend');
  const tend = d.tendance;
  tEl.textContent = tend !== undefined
    ? (tend >= 0 ? '+' : '') + tend.toFixed(1) + '\u00a0%' : 'N/A';
  tEl.className = 'stat-val ' + (tend >= 0 ? 'up' : 'down');
  document.querySelectorAll('.q-poly').forEach(p => p.classList.remove('selected'));
  const poly = document.querySelector('.q-poly[data-name="' + name + '"]');
  if (poly) poly.classList.add('selected');
}}

const emptyP = document.querySelector('#panel-empty p');
const origText = emptyP ? emptyP.innerHTML : '';

document.querySelectorAll('.q-poly').forEach(poly => {{
  const name = poly.getAttribute('data-name');
  poly.addEventListener('click', () => showQuartier(name));
  poly.addEventListener('mouseenter', () => {{
    const d = DATA[name] || {{}};
    if (emptyP && !document.getElementById('panel-detail').classList.contains('active')) {{
      emptyP.innerHTML = '<strong>' + name + '</strong><br>'
        + '<em style="font-size:11px;color:#999">' + (d.desc || '') + '</em>';
    }}
  }});
  poly.addEventListener('mouseleave', () => {{
    if (emptyP && !document.getElementById('panel-detail').classList.contains('active')) {{
      emptyP.innerHTML = origText;
    }}
  }});
}});
</script>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════════
#  AFFICHAGE STREAMLIT
# ═══════════════════════════════════════════════════════════════════════════

def afficher_carte(annonces=None) -> None:
    """Affiche la carte interactive des quartiers de Toulon."""
    st.title("📍 Carte des quartiers de Toulon")
    st.caption("Cliquez sur un quartier · Prix/m² calculé depuis les annonces · Stats from scratch")

    # Calcul stats (analysis.stats — aucun numpy)
    q_stats = charger_stats()

    # Assemblage JSON pour le JS
    data_carte: dict[str, dict] = {}
    for nom, meta in QUARTIERS_META.items():
        s = q_stats.get(nom, {})
        data_carte[nom] = {
            "desc":       meta["desc"],
            "tags":       meta["tags"],
            "tendance":   meta["tendance"],
            "pm2_median": s.get("pm2_median"),
            "n_annonces": s.get("n_annonces", 0),
        }
    data_json = json.dumps(data_carte, ensure_ascii=False)

    # Composant HTML interactif
    components.html(_build_html(data_json), height=880, scrolling=False)

    # ── Tableau récapitulatif sous la carte ────────────────────────────────────
    if q_stats:
        st.divider()
        st.subheader("Détail par quartier")
        rows = []
        for nom in sorted(q_stats, key=lambda x: q_stats[x].get("pm2_median", 9999)):
            s = q_stats[nom]
            rows.append({
                "Quartier":        nom,
                "Prix/m² médian":  f"{s['pm2_median']:,.0f} €",
                "Prix/m² moyen":   f"{s['pm2_mean']:,.0f} €",
                "Écart-type":      f"{s['pm2_std']:,.0f} €",
                "Annonces":        s["n_annonces"],
                "Ambiance":        QUARTIERS_META.get(nom, {}).get("tags", []),
            })
        import pandas as _pd
        st.dataframe(_pd.DataFrame(rows).set_index("Quartier"), use_container_width=True)
