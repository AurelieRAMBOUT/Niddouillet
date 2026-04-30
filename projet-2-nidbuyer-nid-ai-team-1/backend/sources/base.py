"""
Interface commune pour toutes les sources d'annonces.

Pour ajouter une source, créez un fichier dans ce dossier et héritez de SourceBase.
L'ingestion appellera automatiquement toutes les sources enregistrées.

Exemple minimal :
    class MaSource(SourceBase):
        name = "ma_source"
        def fetch_new(self) -> list[dict]:
            ...
"""
from abc import ABC, abstractmethod


class SourceBase(ABC):
    # Nom de la source — apparaît dans les logs et les métadonnées
    name: str = "source_inconnue"

    @abstractmethod
    def fetch_new(self) -> list[dict]:
        """
        Récupère les annonces nouvelles ou mises à jour depuis la dernière exécution.

        Returns:
            Liste de dicts. Chaque annonce doit contenir au minimum :
            {
                "id_source":   str,   # identifiant unique côté source
                "url_source":  str,   # URL de l'annonce originale
                "type":        str,   # "T1", "T2", "T3", "T4", "maison", "immeuble"...
                "surface":     float,
                "prix":        float,
                "quartier":    str,
                "ville":       str,
                "description": str,
                "photos":      list[str],  # URLs des photos (peut être vide)
                "nb_pieces":   int | None,
                "dpe":         str | None,
            }
            Les champs manquants seront remplis avec None — pas d'erreur levée.
        """
        ...

    def normalize(self, raw: dict) -> dict:
        """Normalise un dict brut vers le format standard. Peut être surchargé."""
        defaults = {
            "id_source": None, "url_source": None, "type": None,
            "surface": None, "prix": None, "quartier": None,
            "ville": "Toulon", "description": "", "photos": [],
            "nb_pieces": None, "dpe": None, "source": self.name,
        }
        return {**defaults, **raw, "source": self.name}
