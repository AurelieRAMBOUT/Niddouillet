"""
Import DVF → agrégation + insertion Supabase (version propre)
"""

import pandas as pd
import os
from supabase import create_client
from dotenv import load_dotenv

# 🔐 Charger .env
load_dotenv()

SUPABASE_URL = "https://rxvcfvpbixmcazdinysm.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_KEY manquante dans .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 📂 Chemin CSV
CSV_PATH = "backend/dvf_toulon.csv"


def load_data():
    print("📂 Lecture DVF...")
    df = pd.read_csv(CSV_PATH, sep=",")
    return df


def clean_data(df):
    print("🧹 Nettoyage...")

    # garder uniquement les ventes
    df = df[df["nature_mutation"] == "Vente"]

    # supprimer valeurs nulles
    df = df.dropna(subset=["prix_m2"])

    # sécurité : garder Toulon
    df = df[df["nom_commune"].str.upper() == "TOULON"]

    return df


def aggregate(df):
    print("📊 Agrégation...")

    grouped = df.groupby("code_postal").agg(
        prix_m2_moyen=("prix_m2", "mean"),
        mediane_prix_m2=("prix_m2", "median"),
        nb_transactions=("prix_m2", "count"),
        date_min=("date_mutation", "min"),
        date_max=("date_mutation", "max"),
    ).reset_index()

    # correspond à ta table
    grouped = grouped.rename(columns={
        "code_postal": "quartier"
    })

    grouped["ville"] = "Toulon"

    # arrondir
    grouped["prix_m2_moyen"] = grouped["prix_m2_moyen"].round(2)
    grouped["mediane_prix_m2"] = grouped["mediane_prix_m2"].round(2)

    return grouped


def insert_supabase(df):
    print("🚀 Insertion Supabase...")

    data = df.to_dict(orient="records")

    supabase.table("dvf_quartiers").insert(data).execute()

    print(f"✅ {len(data)} quartiers insérés")


def main():
    df = load_data()
    df = clean_data(df)
    df = aggregate(df)

    print("\n📊 Résultat final :")
    print(df)

    insert_supabase(df)

    print("🎯 DVF import terminé")


if __name__ == "__main__":
    main()