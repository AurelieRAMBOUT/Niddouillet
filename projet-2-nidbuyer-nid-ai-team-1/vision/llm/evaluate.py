"""
Piste LLM multimodal — Analyse des photos via un modèle de vision.

Compatible avec tout modèle acceptant des images en entrée :
- Claude (claude-opus-4-6, claude-haiku-4-5-20251001...)
- GPT-4o
- LLaVA (open source, hébergeable soi-même)

Conseil coût : tester d'abord avec claude-haiku-4-5-20251001 (10x moins cher que opus),
puis comparer la qualité dans votre APPROACH.md.
"""
import os
import base64
from pathlib import Path

# TODO : choisir et implémenter une des options ci-dessous

# --- Option A : Claude (Anthropic) ---
# import anthropic
#
# def evaluer_photos_claude(photos: list, model: str = "claude-haiku-4-5-20251001") -> dict:
#     client = anthropic.Anthropic()
#     content = []
#     for photo in photos[:4]:  # limiter pour maîtriser les coûts
#         ...  # encoder en base64 ou passer une URL
#     content.append({"type": "text", "text": PROMPT_VISION})
#     response = client.messages.create(model=model, max_tokens=512, messages=[{"role": "user", "content": content}])
#     return json.loads(response.content[0].text)

# --- Option B : GPT-4o (OpenAI) ---
# from openai import OpenAI
# ...

# --- Option C : LLaVA local (open source) ---
# import requests
# ...

PROMPT_VISION = """Analyse ces photos d'un bien immobilier.
Retourne uniquement du JSON valide, sans texte autour :
{
  "etat_general": "excellent"|"bon"|"correct"|"a_renover",
  "travaux_detectes": ["peinture", "cuisine", ...],
  "estimation_travaux": "0-5k"|"5-20k"|"20-50k"|">50k",
  "luminosite": 1-5,
  "score_presentation": 1-10
}"""


raise NotImplementedError("À implémenter par l'équipe R&D Vision")
