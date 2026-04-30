"""
Alertes acheteur : notifie par email ou Slack quand un nouveau bien
correspond à un profil enregistré.
"""
import os
import json
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

PROFILES_FILE = Path("data/alertes.json")


def charger_profils() -> list[dict]:
    if not PROFILES_FILE.exists():
        return []
    return json.loads(PROFILES_FILE.read_text())


def sauvegarder_profil(email: str, profil: dict) -> None:
    profils = charger_profils()
    profils.append({"email": email, "profil": profil})
    PROFILES_FILE.parent.mkdir(exist_ok=True)
    PROFILES_FILE.write_text(json.dumps(profils, ensure_ascii=False, indent=2))


def notifier_email(email: str, biens: list[dict]) -> None:
    """Envoie un email avec les nouveaux biens correspondants."""
    if not biens:
        return

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM") or os.getenv("ALERT_FROM_EMAIL") or smtp_user

    if not smtp_host or not from_email:
        raise ValueError("Configuration SMTP incomplete")

    lignes = [f"{len(biens)} nouveau(x) bien(s) correspondent a votre profil :"]
    for index, bien in enumerate(biens, start=1):
        details = [
            f"Type: {bien.get('type') or 'N/A'}",
            f"Surface: {bien.get('surface') or 'N/A'} m2",
            f"Prix: {bien.get('prix') or 'N/A'} EUR",
            f"Quartier: {bien.get('quartier') or 'N/A'}",
            f"URL: {bien.get('url_source') or 'N/A'}",
        ]
        description = bien.get("description")
        if description:
            details.append(f"Description: {str(description)[:300]}")
        lignes.append(f"\nBien #{index}\n" + "\n".join(details))

    message = EmailMessage()
    message["Subject"] = f"NidBuyer - {len(biens)} nouveau(x) bien(s)"
    message["From"] = from_email
    message["To"] = email
    message.set_content("\n".join(lignes))

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as smtp:
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        if os.getenv("SMTP_STARTTLS", "true").lower() not in {"0", "false", "no"}:
            smtp.starttls(context=ssl.create_default_context())
        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)


def notifier_slack(webhook_url: str, biens: list[dict]) -> None:
    """Envoie un message Slack avec les nouveaux biens."""
    if not biens:
        return
    if not webhook_url:
        raise ValueError("Webhook Slack manquant")

    lignes = [f"*NidBuyer* - {len(biens)} nouveau(x) bien(s) correspondent a un profil :"]
    for index, bien in enumerate(biens, start=1):
        details = [
            f"*Type:* {bien.get('type') or 'N/A'}",
            f"*Surface:* {bien.get('surface') or 'N/A'} m2",
            f"*Prix:* {bien.get('prix') or 'N/A'} EUR",
            f"*Quartier:* {bien.get('quartier') or 'N/A'}",
            f"*URL:* {bien.get('url_source') or 'N/A'}",
        ]
        description = bien.get("description")
        if description:
            details.append(f"*Description:* {str(description)[:300]}")
        lignes.append(f"\n*Bien #{index}*\n" + "\n".join(details))

    response = requests.post(webhook_url, json={"text": "\n".join(lignes)}, timeout=10)
    response.raise_for_status()


def verifier_nouveaux_biens(nouveaux_biens: list[dict]) -> None:
    """
    Pour chaque profil enregistré, vérifie si un nouveau bien correspond
    et déclenche la notification appropriée.
    """
    if not nouveaux_biens:
        return

    profils = charger_profils()
    if not profils:
        return

    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

    for profil_entry in profils:
        profil = profil_entry.get("profil") or {}
        budget = profil.get("budget_max")
        surface_min = profil.get("surface_min")
        nb_pieces_min = profil.get("nb_pieces_min")
        quartiers = profil.get("quartiers") or ()
        if isinstance(quartiers, str):
            quartiers = (quartiers,)
        quartiers_recherches = {str(q).casefold() for q in quartiers if q}

        biens_matching = []
        for bien in nouveaux_biens:
            prix = bien.get("prix")
            if prix is None:
                prix = bien.get("prix_eur")
            if budget is not None and prix is not None and prix > budget:
                continue

            surface = bien.get("surface")
            if surface is None:
                surface = bien.get("surface_m2")
            if surface_min is not None and surface is not None and surface < surface_min:
                continue

            nb_pieces = bien.get("nb_pieces")
            if nb_pieces is None:
                nb_pieces = bien.get("pieces")
            if nb_pieces_min is not None and nb_pieces is not None and nb_pieces < nb_pieces_min:
                continue

            if quartiers_recherches:
                quartier = bien.get("quartier")
                if not quartier or str(quartier).casefold() not in quartiers_recherches:
                    continue

            biens_matching.append(bien)

        if not biens_matching:
            continue

        email = profil_entry.get("email")
        if email:
            notifier_email(email, biens_matching)

        webhook_url = profil_entry.get("slack_webhook_url") or profil_entry.get("webhook_url") or slack_webhook
        if webhook_url:
            notifier_slack(webhook_url, biens_matching)
