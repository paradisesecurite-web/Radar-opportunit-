"""Lecture des réglages (config.yaml) et des secrets (variables d'environnement).

Les secrets ne sont JAMAIS dans le code : GitHub Actions les injecte comme
variables d'environnement à partir des "Secrets" du dépôt.
"""
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

RACINE = Path(__file__).resolve().parent.parent
PARIS = ZoneInfo("Europe/Paris")


def charger_config(chemin: Path | None = None) -> dict:
    with open(chemin or RACINE / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def secret(nom: str, obligatoire: bool = False) -> str | None:
    """Lit un secret. Renvoie None s'il n'est pas renseigné."""
    valeur = os.environ.get(nom, "").strip()
    if not valeur and obligatoire:
        raise RuntimeError(f"Le secret {nom} n'est pas renseigné (voir docs/GUIDE.md).")
    return valeur or None


def maintenant() -> datetime:
    """Date et heure actuelles à Paris."""
    return datetime.now(PARIS)


def chemin_base() -> Path:
    """Fichier SQLite local (jamais commité : il est gardé dans le cache GitHub Actions)."""
    p = Path(os.environ.get("RADAR_DB", RACINE / "data" / "radar.db"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
