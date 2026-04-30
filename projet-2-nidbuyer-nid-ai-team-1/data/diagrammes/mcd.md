@startuml MCD_NidBuyer
!theme plain
skinparam defaultFontName Monospaced
skinparam EntityBackgroundColor #F8F8F8
skinparam EntityBorderColor #888888
skinparam ArrowColor #555555

title Modèle Conceptuel de Données — NidBuyer

entity "USER" as U {
  id
  email
  nom
  mot_de_passe_hash
  date_inscription
  actif
}

entity "CRITERE_ALERTE" as C {
  id
  budget_max
  surface_min
  type_bien
  quartier
  nb_pieces_min
  actif
}

entity "ANNONCE" as A {
  id
  id_source
  url_source
  type
  surface
  prix
  quartier
  ville
  description
  photos
  dpe
  nb_pieces
  source
  date_scraping
  score_opportunite
}

entity "ALERTE_ENVOYEE" as E {
  id
  date_envoi
  canal
  statut
  contenu_resume
}

' ── Relations ──
U "1,1" -- "0,N" C : définit >
U "1,1" -- "0,N" E : reçoit >
A "1,1" -- "0,N" E : déclenche >
C "1,1" -- "0,N" E : matche >

@enduml