import pandas as pd
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://rxvcfvpbixmcazdinysm.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_PATH = "backend/dvf_toulon.csv"


def main():
    print("📂 Lecture DVF...")

    df = pd.read_csv(CSV_PATH, sep=",")

    print("🧹 Nettoyage...")

    df = df[df["nature_mutation"] == "Vente"]
    df = df.dropna(subset=["prix_m2"])

    df = df[df["nom_commune"].str.upper() == "TOULON"]

    # mapping vers ta DB
    df_clean = pd.DataFrame({
        "date_mutation": df["date_mutation"],
        "valeur_fonciere": df["valeur_fonciere"],
        "prix_m2": df["prix_m2"],
        "code_postal": df["code_postal"],
        "ville": df["nom_commune"],
        "type_local": df["type_local"],
        "surface": df["surface_reelle_bati"],
        "nb_pieces": df["nombre_pieces_principales"]
    })

    data = df_clean.to_dict(orient="records")

    print(f"📦 {len(data)} lignes à insérer")

    # batch insert
    batch_size = 500

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]

        supabase.table("dvf").insert(batch).execute()

        print(f"✅ Batch {i//batch_size + 1}")

    print("🎯 DVF FULL import terminé")


if __name__ == "__main__":
    main()