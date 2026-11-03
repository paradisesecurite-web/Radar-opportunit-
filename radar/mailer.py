"""Envoi des mails via Gmail (mot de passe d'application).

Secrets nécessaires :
  GMAIL_ADRESSE        : l'adresse Gmail qui envoie
  GMAIL_MOT_DE_PASSE   : le mot de passe d'application (16 lettres)
  DESTINATAIRES        : une ou plusieurs adresses, séparées par des virgules

Sans GMAIL_MOT_DE_PASSE, le mail est enregistré en fichier HTML (apercu_*.html)
au lieu d'être envoyé : pratique pour tester.
"""
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from .config import RACINE, secret


def envoyer(sujet: str, html_corps: str) -> bool:
    adresse = secret("GMAIL_ADRESSE")
    mdp = secret("GMAIL_MOT_DE_PASSE")
    dest = [d.strip() for d in (secret("DESTINATAIRES") or "").split(",") if d.strip()]

    if not (adresse and mdp and dest):
        nom = "apercu_" + re.sub(r"[^a-zA-Z0-9]+", "_", sujet)[:60] + ".html"
        (RACINE / nom).write_text(html_corps, encoding="utf-8")
        print(f"✉️  (pas de secrets Gmail : mail enregistré dans {nom}) — {sujet}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = sujet
    msg["From"] = formataddr(("Radar alternance IT", adresse))
    msg["To"] = ", ".join(dest)
    msg.attach(MIMEText("Ce mail s'affiche en HTML.", "plain", "utf-8"))
    msg.attach(MIMEText(html_corps, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(adresse, mdp.replace(" ", ""))
        s.sendmail(adresse, dest, msg.as_string())
    print(f"✉️  Mail envoyé : {sujet[:20]}…")  # pas de nom d'entreprise dans les journaux
    return True
