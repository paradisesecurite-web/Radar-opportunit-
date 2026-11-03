"""Source : API Jooble (agrégateur de sites d'emploi), clé gratuite.

Demande de clé : https://jooble.org/api/about -> secret JOOBLE_API_KEY.
Appel : POST https://fr.jooble.org/api/<clé> avec {"keywords", "location", "page"}.
"""
import time
from datetime import timedelta

import requests

from ..config import maintenant, secret
from .commun import est_it, offre_generique, type_offre


def actif() -> bool:
    return bool(secret("JOOBLE_API_KEY"))


def rechercher(cfg: dict) -> list[dict]:
    reglages = cfg["jooble"]
    cle = secret("JOOBLE_API_KEY")
    url = reglages["url"].rstrip("/") + "/" + cle
    depuis = (maintenant() - timedelta(days=3)).strftime("%Y-%m-%d")
    offres = {}
    for r in reglages["recherches"]:
        corps = {"keywords": r["mots"], "location": "France", "page": "1", "datecreatedfrom": depuis}
        rep = requests.post(url, json=corps, timeout=60, headers={"User-Agent": "radar-alternance-it/1.0"})
        if rep.status_code == 404 and "fr.jooble" in url:   # adresse internationale en secours
            url = "https://jooble.org/api/" + cle
            rep = requests.post(url, json=corps, timeout=60)
        if rep.status_code in (401, 403):
            raise RuntimeError("Clé Jooble refusée ou quota dépassé.")
        rep.raise_for_status()
        for j in rep.json().get("jobs", []):
            titre = j.get("title") or ""
            if not est_it(cfg, titre):
                continue
            t = type_offre(titre, j.get("snippet") or "", defaut=r["type"])
            offres[str(j.get("id"))] = offre_generique(
                id_=f"jooble:{j.get('id')}", cfg=cfg,
                source="Jooble" + (f" ({j['source']})" if j.get("source") else ""),
                nom=j.get("company"), ville=(j.get("location") or "").split(",")[0].strip() or None,
                titre=titre, lien=j.get("link"), publiee_le=j.get("updated"), type_=t)
        time.sleep(1)
    return list(offres.values())
