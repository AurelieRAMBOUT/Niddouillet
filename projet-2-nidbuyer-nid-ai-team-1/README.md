[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/37edVT1_)
# NidBuyer — Votre acheteur IA à Toulon

> **Projet 2 — MBA Data & IA 2026**

## Équipe

### Pôle Produit

| Membre | Rôle |
|--------|------|
| Aurélie RAMBOUT | Lead architecture |
| Aiden Bouaicha | Backend / RAG |
| Julie La Porta | Frontend / UX |
| Emma Ben Boujmaa | Données / DVF + scoring |
| Julien Carcenac | Prompt engineering |

### Pôle R&D Vision

| Membre | Rôle |
|--------|------|
| Prénom NOM | Approche & dataset |
| Prénom NOM | Entraînement / évaluation |

## Demo

URL déployée : **https://TODO**

## Pourquoi NidBuyer ?

|  | BienIci | MeilleursAgents | SeLoger | NidBuyer |
|---|:---:|:---:|:---:|:---:|
| Lister des biens | ✅ | ✅ | ✅ | ✅ |
| Estimer le prix | ❌ | ✅ vendeur | ❌ | ✅ acheteur |
| Détecter sous-évaluations | ❌ | ❌ | ❌ | ✅ |
| Alerter sur profil | ❌ | ❌ | partiel | ✅ |
| Analyser les photos | ❌ | ❌ | ❌ | ✅ |
| Conseiller sur l'offre | ❌ | ❌ | ❌ | ✅ |

## Vision produit

NidBuyer est conçu comme un outil opérationnel
permettant à un conseiller immobilier de :
- identifier rapidement des opportunités
- gagner du temps dans la recherche
- prendre des décisions éclairées

## Lancer en local

```bash
cp .env.example .env
# Remplir les variables dans .env (voir section Configuration)

pip install -r requirements.txt

# Backend
uvicorn backend.main:app --reload

# Frontend (autre terminal)
streamlit run frontend/app.py
```

## Configuration

Copier `.env.example` → `.env` et remplir :

| Variable | Obligatoire | Description |
|---|:---:|---|
| `ANTHROPIC_API_KEY` | ✅ | Clé API Claude |
| `SUPABASE_URL` | ✅ | URL du projet Supabase |
| `SUPABASE_KEY` | ✅ | Clé anon/service Supabase |
| `SMTP_HOST` / `SMTP_USER` / ... | ➕ | Alertes email |
| `SLACK_WEBHOOK_URL` | ➕ | Alertes Slack |

## Architecture

```
nidbuyer/
├── backend/
│   ├── main.py        # FastAPI + scheduler ingestion 7h00
│   ├── rag.py         # ChromaDB — recherche vectorielle
│   ├── scoring.py     # Score opportunité vs médiane DVF
│   ├── ingestion.py   # Scraper → Supabase → ChromaDB
│   ├── alert.py       # Alertes email / Slack
│   └── sources/       # BienIci · LeBonCoin · Générique LLM · ...
├── frontend/          # Streamlit — interface acheteur
├── vision/            # R&D : CNN ou LLM multimodal
│   ├── model.py       # Interface commune (appelée par scoring.py)
│   ├── cnn/           # Piste CNN
│   ├── llm/           # Piste LLM multimodal
│   ├── APPROACH.md    # Choix justifié + résultats mesurés
│   └── benchmark.py   # Script de comparaison
├── prompts/           # System prompts + EXPERIMENTS.md
├── tests/             # Tests scoring, RAG, vision
└── .env               # SUPABASE_URL · SUPABASE_KEY · ANTHROPIC_API_KEY · ...
```

**Les annonces ne transitent pas par GitHub.** Le pipeline écrit directement dans deux bases externes :

```
Scraper (quotidien 7h00)
        ↓
Supabase PostgreSQL   ← données brutes structurées
        ↓
ChromaDB (Railway / HF)  ← vecteurs pour le RAG
        ↓
FastAPI + Streamlit   ← interface acheteur déployée
```

> **Pourquoi pas un CSV dans le repo ?** Les annonces sont des données vivantes — un `git commit` par ingestion n'est pas une pratique prod. GitHub est pour le code ; Supabase est pour la data.

## Tâche J1

**Avant la fin du premier jour :**

1. Importer les annonces P1 dans Supabase (table `annonces`) et lancer une première indexation ChromaDB
2. Vérifier le compte : `GET /admin/status` — si < 300 annonces → scraper immédiatement
3. Lancer `POST /admin/sync` pour valider le pipeline de bout en bout
4. Déclarer les rôles dans ce README et pousser

> *"Vos données P1 sont la fondation. Sans elles, pas de RAG."*

Nombre d'annonces indexées dans la base RAG : **XXX** ← *à mettre à jour J1*

## Prompt Engineering

Voir [`prompts/EXPERIMENTS.md`](prompts/EXPERIMENTS.md) — 3 versions comparées sur le même bien de référence.

## R&D Vision

Voir [`vision/APPROACH.md`](vision/APPROACH.md) — approche retenue, métriques, limites.

## Fonctionnement du produit

1. L'utilisateur renseigne son profil (budget, surface, quartiers, critères)
2. Une requête enrichie est générée côté backend
3. Le moteur RAG (ChromaDB) récupère les biens les plus pertinents
4. Chaque bien est scoré via un score d'opportunité basé sur les données DVF
5. Une fiche décision est générée pour aider à l'achat
6. Des alertes peuvent être envoyées si de nouvelles opportunités apparaissent

## Scoring DVF et score d'opportunité

Le scoring compare chaque annonce aux transactions DVF réelles de Toulon. Le backend utilise en priorité `data/ventes_toulon_avec_quartier.csv`, puis `data/dvf_toulon.csv` en fallback.

Les transactions DVF sont filtrées pour garder les ventes 2024-2026 sur Toulon (`code_commune = 83137`), uniquement pour les appartements et maisons, avec des prix au m² cohérents entre 500 et 20 000 €/m².

Pour chaque quartier, l'application calcule :
- médiane du prix au m² ;
- moyenne du prix au m² ;
- fourchette min / max ;
- nombre de transactions comparées ;
- percentile du bien par rapport aux ventes comparables.

Formules utilisées :

```text
prix_m2 = prix_annonce / surface_annonce
ecart_pct = ((prix_m2 - mediane_quartier) / mediane_quartier) * 100
score = -ecart_pct
```

Interprétation :
- score positif : le bien est sous la médiane du quartier, donc potentiellement intéressant ;
- score proche de 0 : le bien est au prix du marché ;
- score négatif : le bien est au-dessus de la médiane, donc plus cher que le marché comparable.

L'interface affiche aussi un tag de positionnement :
- `Sous-évalué` si le bien est au moins 10 % sous la médiane ;
- `Prix marché` entre -10 % et +10 % ;
- `Surévalué` si le bien est au moins 10 % au-dessus de la médiane.

La fiche décision enrichit ce score avec une recommandation actionnable : opportunité, points forts, points d'attention, marge de négociation estimée et recommandation finale.

## API — principaux endpoints

- `POST /rechercher`  
  Retourne les biens les plus pertinents selon un profil acheteur, avec scoring DVF et fiche décision

- `GET /health`  
  Vérifie que l'API fonctionne

- `POST /chat`  
  Répond aux questions de l'utilisateur avec le contexte RAG, les métriques DVF et le prompt système `prompts/system.txt`

- `GET /marche/quartiers`  
  Retourne les statistiques DVF par quartier : médiane, moyenne, fourchette min/max et nombre de transactions

- `GET /admin/status`  
  Donne le nombre d'annonces indexées

- `POST /admin/sync`  
  Lance une ingestion des nouvelles annonces

- `POST /admin/backfill-supabase`  
  Recharge les annonces Supabase dans ChromaDB pour reconstruire l'index RAG

# Modèle d'embedding

Nous utilisons **all-MiniLM-L6-v2** de Sentence Transformers. 
Ce modèle est léger et rapide à exécuter, ce qui permet d’indexer plusieurs centaines d’annonces sans latence importante et de répondre quasi instantanément aux requêtes utilisateur dans l’application.Ce critère est essentiel dans le cadre d’un produit interactif déployé avec Streamlit.
Il a une qualité suffisante pour des descriptions immobilières et des requêtes simples en langage naturel.
Ce modèle est gratuit et fonctionne en local, sans dépendre d’une API externe.
Même s’il est moins optimisé pour le français que certains modèles spécialisés, il reste performant pour un MVP.

**Pour aller plus loin :** Si nous avions un budget, nous aurions plutôt choisi text-embedding-3-small car il est performant, peu coûteux et meilleur en multilingue que les anciens modèles OpenAI. Et si on placait la priorité à la qualité de recherche, on pourrait utilisé text-embedding-3-large qui est plus performant, mais aussi plus cher.

## Modèle du LLM

Nous avons choisi **Claude via l'API Anthropic** et le modèle **claude-haiku-4-5-20251001** pour générer les fiches décision et enrichir l'analyse des biens.

Ce choix repose sur plusieurs critères :
- **Qualité des réponses** : Claude produit des réponses structurées, nuancées et adaptées à un usage d'aide à la décision.
- **Compréhension du français** : Il gère correctement les descriptions immobilières en français et les critères en langage naturel.
- **Fiabilité du raisonnement** : Il est pertinent pour comparer plusieurs critères d'achat et formuler une recommandation cohérente.
- **Sortie structurée** : il permet de générer facilement des fiches synthétiques avec avantages, risques et conseil sur la négociation.
- **Intégration simple** : l'API Anthropic s'intègre facilement dans le backend en Python.

Limite : l'utilisation d'un LLM externe implique un coût à l'usage et une dépendance à une API tierce. Pour limiter cela, le LLM est utilisé uniquement pour les tâches à forte valeur ajoutée, comme la génération des fiches décision, et non pour toute la recherche de biens.

## Base de données

La base de données est hébergée sur Supabase. Elle permet de stocker les annonces collectées, les données DVF de référence et les alertes envoyées aux profils acheteurs.

Le schéma SQL ci-dessous permet de reconstruire les principales tables utilisées par l’application.


### Fonction de mise à jour automatique

```sql
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;
```

### Table `annonces`

La table `annonces` stocke les biens immobiliers collectés via les sources d’annonces.  
Le champ `url_source` est unique afin d’éviter les doublons lors des synchronisations.

```sql
create table public.annonces (
  id uuid not null default gen_random_uuid(),
  url_source text not null,
  source character varying(50) not null,
  titre character varying(500),
  description text,
  prix numeric(12, 2),
  surface numeric(8, 2),
  prix_m2 numeric(10, 2),
  ville character varying(100) default 'Toulon',
  quartier character varying(100),
  adresse character varying(255),
  type_bien character varying(50),
  nb_pieces integer,
  photos jsonb default '[]'::jsonb,
  date_publication date,
  date_collecte timestamp with time zone default now(),
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now(),
  constraint annonces_pkey primary key (id),
  constraint annonces_url_source_key unique (url_source)
);
```

```sql
create index if not exists idx_annonces_quartier
on public.annonces using btree (quartier);

create index if not exists idx_annonces_prix
on public.annonces using btree (prix);

create index if not exists idx_annonces_surface
on public.annonces using btree (surface);
```

```sql
create trigger update_annonces_updated_at
before update on public.annonces
for each row
execute function update_updated_at_column();
```


### Table `dvf`

La table `dvf` stocke les transactions immobilières issues de la base DVF.  
Elle sert de référence pour calculer les médianes de prix au m² par zone et comparer les annonces au marché réel.

```sql
create table public.dvf (
  id uuid not null default gen_random_uuid(),
  date_mutation date,
  valeur_fonciere numeric,
  prix_m2 numeric,
  code_postal text,
  ville text,
  type_local text,
  surface numeric,
  nb_pieces integer,
  constraint dvf_pkey primary key (id)
);
```

### Table `profils_acheteurs`

La table `profils_acheteurs` stocke les profils des utilisateurs souhaitant recevoir des recommandations ou des alertes.

Elle contient les critères principaux de recherche :
- budget maximum ;
- surface minimale ;
- quartiers souhaités ;
- nombre de pièces minimum ;
- description libre ;
- email de contact.

Le champ `email` est unique afin d’éviter les doublons de profils.

```sql
create table public.profils_acheteurs (
  id uuid not null default gen_random_uuid(),
  nom character varying(100) not null,
  type_profil character varying(50),
  budget_max numeric(12, 2),
  surface_min numeric(6, 2),
  quartiers text[] not null,
  nb_pieces_min integer,
  description_libre text,
  email character varying(255) not null,
  created_at timestamp with time zone default now(),
  constraint profils_acheteurs_pkey primary key (id),
  constraint profils_acheteurs_email_key unique (email)
);
```

### Table `alertes`

La table `alertes` permet de tracer les notifications envoyées lorsqu’un bien correspond à un profil acheteur.

Elle est reliée :
- à la table `profils_acheteurs` ;
- à la table `annonces`.

> La table `profils_acheteurs` doit donc exister avant la création de `alertes`.

```sql
create table public.alertes (
  id uuid not null default gen_random_uuid(),
  profil_id uuid not null,
  annonce_id uuid not null,
  canal character varying(20) default 'email',
  statut character varying(20) default 'envoyee',
  message text,
  sent_at timestamp with time zone default now(),
  constraint alertes_pkey primary key (id),
  constraint alertes_annonce_id_fkey
    foreign key (annonce_id)
    references annonces (id)
    on delete cascade,
  constraint alertes_profil_id_fkey
    foreign key (profil_id)
    references profils_acheteurs (id)
    on delete cascade
);
```

```sql
create index if not exists idx_alertes_profil
on public.alertes using btree (profil_id);

create index if not exists idx_alertes_annonce
on public.alertes using btree (annonce_id);
```

# Rôle des tables

- `annonces` : stocke les biens immobiliers disponibles.
- `dvf` : stocke les transactions réelles utilisées comme référence de marché.
- `profils_acheteurs` : stocke les critères de recherche et les informations de contact des acheteurs.
- `alertes` : historise les notifications envoyées aux profils acheteurs.

Les annonces sont ensuite indexées dans ChromaDB pour permettre la recherche sémantique via le RAG.

# Chat 
Le endpoint /chat utilise un prompt système centralisé dans prompts/system.txt, qui fixe le rôle, les contraintes et le format de réponse de l’IA. Ensuite, à chaque question, le backend construit un prompt utilisateur enrichi avec le profil acheteur, le contexte RAG, les données DVF calculées et la fiche décision. Cela permet au LLM de ne pas répondre seulement de manière générale, mais de s’appuyer sur des chiffres réels : médiane quartier, écart au marché, percentile, nombre de transactions comparées et recommandations de négociation.

# Scraping

Le scraping est lancé automatiquement par le backend tous les jours à 7h via le scheduler FastAPI.

Pour lancer une synchronisation manuelle via l'API :

```bash
curl -X POST "http://127.0.0.1:8000/admin/sync?dry_run=false"
```

Pour tester le scraping sans indexer les nouvelles annonces, utiliser le mode dry-run :

```bash
curl -X POST "http://127.0.0.1:8000/admin/sync?dry_run=true"
```

Pour tester localement les sources actives sans passer par l'API :

```bash
python -m backend.sources.scraping
```

Pour reconstruire l'index ChromaDB depuis les annonces déjà présentes dans Supabase :

```bash
curl -X POST "http://127.0.0.1:8000/admin/backfill-supabase?table_name=annonces&replace=true"
```

Prérequis :
- backend lancé avec `uvicorn backend.main:app --reload` ;
- variables `.env` renseignées (`SUPABASE_URL`, `SUPABASE_KEY`, etc.) ;
- sources actives configurées dans `backend/sources/__init__.py`.
