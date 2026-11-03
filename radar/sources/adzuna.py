"""Source : API Adzuna (agrégateur de sites d'emploi), clé gratuite.

Inscription : https://developer.adzuna.com -> secrets ADZUNA_APP_ID et ADZUNA_APP_KEY.
La clé gratuite a des quotas limités (visibles dans votre espace Adzuna) :
on n'interroge Adzuna que toutes les 2 heures (réglable dans config.yaml).
"""
import time

import requests

from ..config import secret
from .commun import est_it, offre_generique, type_offre

URL = "https://api.adzuna.com/v1/api/jobs/fr/search/{page}"


def actif() -> bool:
    return bool(secret("ADZUNA_APP_ID") and secret("ADZUNA_APP_KEY"))


def rechercher(cfg: dict) -> list[dict]:
    reglages = cfg["adzuna"]
    offres = {}
    for r in reglages["recherches"]:
        for page in range(1, reglages["pages_max"] + 1):
            params = {"app_id": secret("ADZUNA_APP_ID"), "app_key": secret("ADZUNA_APP_KEY"),
                      "results_per_page": 50, "what_or": r["mots_ou"], "category": "it-jobs",
                      "max_days_old": 3, "sort_by": "date", "content-type": "application/json"}
            rep = requests.get(URL.format(page=page), params=params, timeout=60,
                               headers={"User-Agent": "radar-alternance-it/1.0"})
            if rep.status_code in (401, 403):
                raise RuntimeError("Clé Adzuna refusée ou quota dépassé.")
            rep.raise_for_status()
            resultats = rep.json().get("results", [])
            for j in resultats:
                if not est_it(cfg, j.get("title", "")) and (j.get("category") or {}).get("tag") != "it-jobs":
                    continue
                zone = (j.get("location") or {}).get("area") or []
                ville = zone[-1] if len(zone) > 1 else None   # [pays, région, département, ville]
                offres[j["id"]] = offre_generique(
                    id_=f"adzuna:{j['id']}", source="Adzuna", cfg=cfg,
                    nom=(j.get("company") or {}).get("display_name"), ville=ville,
                    titre=j.get("title", "Offre IT"), lien=j.get("redirect_url"),
                    publiee_le=j.get("created"),
                    type_=type_offre(j.get("title", ""), j.get("description", ""), defaut=r["type"]))
            if len(resultats) < 50:
                break
            time.sleep(2)
    return list(offres.values())
