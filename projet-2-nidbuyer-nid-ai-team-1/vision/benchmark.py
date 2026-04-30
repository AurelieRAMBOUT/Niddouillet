"""
Benchmark — Compare les prédictions du modèle Vision sur un jeu de test.

Usage :
    python vision/benchmark.py --photos data/photos_test/ --labels data/labels_test.csv

Le fichier labels_test.csv doit contenir deux colonnes : filename, etat_reel
"""
import argparse
import csv
import json
from pathlib import Path
from vision.model import evaluer_etat_bien


def run_benchmark(photos_dir: str, labels_file: str) -> dict:
    labels = {}
    with open(labels_file) as f:
        for row in csv.DictReader(f):
            labels[row["filename"]] = row["etat_reel"]

    resultats = []
    for filename, etat_reel in labels.items():
        photo_path = Path(photos_dir) / filename
        if not photo_path.exists():
            print(f"[WARN] Photo introuvable : {photo_path}")
            continue
        try:
            prediction = evaluer_etat_bien([str(photo_path)])
            etat_predit = prediction["etat_general"]
            correct = etat_predit == etat_reel
            resultats.append({"fichier": filename, "reel": etat_reel, "predit": etat_predit, "correct": correct})
        except Exception as e:
            print(f"[ERROR] {filename} : {e}")

    accuracy = sum(r["correct"] for r in resultats) / len(resultats) if resultats else 0
    print(f"\nAccuracy : {accuracy:.1%} ({sum(r['correct'] for r in resultats)}/{len(resultats)})")
    print("\nDétail :")
    for r in resultats:
        status = "✓" if r["correct"] else "✗"
        print(f"  {status}  {r['fichier']:30s}  reel={r['reel']:12s}  predit={r['predit']}")
    return {"accuracy": accuracy, "resultats": resultats}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--photos", required=True)
    parser.add_argument("--labels", required=True)
    args = parser.parse_args()
    run_benchmark(args.photos, args.labels)
