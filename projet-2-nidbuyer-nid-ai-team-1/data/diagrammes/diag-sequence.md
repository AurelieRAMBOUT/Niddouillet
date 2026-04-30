@startuml Pipeline_NidBuyer
!theme plain
skinparam defaultFontName Monospaced
skinparam sequenceArrowThickness 1.5
skinparam sequenceParticipantBorderThickness 1
skinparam sequenceLifeLineBorderThickness 1

title Pipeline d'ingestion quotidienne — NidBuyer

actor "APScheduler\n(7h00)" as SCHED
participant "ingestion.py" as ING
participant "BienIciSource\nPAPSource" as SCRAPER
database "Supabase\n(annonces)" as SUPA
database "ChromaDB\n(vecteurs RAG)" as CHROMA
database "Supabase\n(criteres_alertes)" as CRIT
participant "alert.py\n(SMTP)" as ALERT
actor "Utilisateur" as USER

SCHED -> ING : sync()
activate ING

ING -> SCRAPER : fetch_new()
activate SCRAPER
SCRAPER --> ING : liste annonces brutes\n(≥ 300)
deactivate SCRAPER

ING -> SUPA : SELECT id_source\n(déduplique)
SUPA --> ING : URLs déjà connues

loop Pour chaque nouvelle annonce
  ING -> SUPA : INSERT INTO annonces\n(upsert on id_source)
  SUPA --> ING : OK
end

ING -> CHROMA : indexer_annonces(nouvelles)
CHROMA --> ING : OK (vecteurs stockés)

ING -> CRIT : SELECT criteres_alertes\nWHERE actif = true
CRIT --> ING : profils utilisateurs

loop Pour chaque profil
  ING -> ING : _filtrer_pour_profil()\n(budget, surface, type)

  alt Des biens correspondent
    ING -> ALERT : notifier_email(user, biens)
    activate ALERT
    ALERT -> USER : Email HTML\n(biens sous-évalués)
    ALERT -> SUPA : INSERT INTO alertes_envoyees
    deactivate ALERT
  end
end

ING --> SCHED : rapport\n{nouvelles, alertes_envoyees}
deactivate ING

@enduml