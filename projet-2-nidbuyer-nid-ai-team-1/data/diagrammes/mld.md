@startuml MLD_NidBuyer
!theme plain
skinparam defaultFontName Monospaced

title Modèle Logique de Données — NidBuyer

entity "users" as U {
  * id : UUID <>
  --
  email : VARCHAR <>
  nom : VARCHAR
  mot_de_passe_hash : TEXT NOT NULL
  date_inscription : TIMESTAMPTZ DEFAULT now()
  actif : BOOLEAN DEFAULT true
}

entity "criteres_alertes" as C {
  * id : UUID <>
  --
  * user_id : UUID <>
  budget_max : NUMERIC(12,2)
  surface_min : NUMERIC(6,2)
  type_bien : VARCHAR(50)
  quartier : VARCHAR(100)
  nb_pieces_min : INTEGER
  actif : BOOLEAN DEFAULT true
  created_at : TIMESTAMPTZ DEFAULT now()
  updated_at : TIMESTAMPTZ DEFAULT now()
}

entity "annonces" as A {
  * id : UUID <>
  --
  id_source : VARCHAR <>
  url_source : TEXT NOT NULL
  type : VARCHAR(50)
  surface : NUMERIC(8,2)
  prix : NUMERIC(12,2)
  quartier : VARCHAR(100)
  ville : VARCHAR(100) DEFAULT 'Toulon'
  description : TEXT
  photos : JSONB DEFAULT '[]'
  dpe : VARCHAR(5)
  nb_pieces : INTEGER
  source : VARCHAR(50)
  date_scraping : TIMESTAMPTZ DEFAULT now()
  score_opportunite : NUMERIC(5,2)
}

entity "alertes_envoyees" as E {
  * id : UUID <>
  --
  * user_id : UUID <>
  * annonce_id : UUID <>
  * critere_id : UUID <>
  date_envoi : TIMESTAMPTZ DEFAULT now()
  canal : VARCHAR(20) DEFAULT 'email'
  statut : VARCHAR(20) DEFAULT 'envoyee'
  contenu_resume : TEXT
}

' ── Relations (cardinalités Merise) ──
U ||--o{ C : "1,1 — définit — 0,N"
U ||--o{ E : "1,1 — reçoit — 0,N"
A ||--o{ E : "1,1 — déclenche — 0,N"
C ||--o{ E : "1,1 — matche — 0,N"

@enduml