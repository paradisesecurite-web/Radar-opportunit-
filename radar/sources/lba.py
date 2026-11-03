"""Source : API La bonne alternance (API Apprentissage, gratuite).

Doc : https://api.apprentissage.beta.gouv.fr/fr/explorer/recherche-offre
Clé : jeton personnel gratuit (valable 1 an) -> secret LBA_API_TOKEN.

Une recherche renvoie :
  - jobs       : offres d'apprentissage / professionnalisation. Elles viennent de
                 La bonne alternance, de France Travail et de sites partenaires
                 (150 max par provenance et par appel)
  - recruiters : entreprises "susceptibles de recruter" selon leur algorithme
                 (aucune offre publiée), 150 max par appel
Limite : 60 appels par minute.
"""
import re
import time

import requests

from ..config import secret
from ..geo import REGIONS

URL = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"
PLAFOND = 150
NIVEAUX = {"3": "CAP", "4": "Bac", "5": "Bac+2", "6": "Bac+3/4", "7": "Bac+5"}
ENTETES = {"User-Agent": "radar-alternance-it/1.0"}


class ErreurCodeRome(Exception):
    """L'API a refusé la liste de codes ROME."""


def _appeler(params: dict, pause: float) -> dict:
    """Un appel à l'API, avec 3 nouvelles tentatives si le serveur sature."""
    jeton = secret("LBA_API_TOKEN", obligatoire=True)
    entetes = {**ENTETES, "Authorization": f"Bearer {jeton}"}
    for essai in range(4):
        time.sleep(pause)
        r = requests.get(URL, params=params, headers=entetes, timeout=60)
        if r.status_code in (419, 429, 500, 502, 503, 504):
            time.sleep(int(r.headers.get("Retry-After", 0) or 0) or 10 * (essai + 1))
            continue
        if r.status_code == 400 and "rome" in r.text.lower():
            raise ErreurCodeRome(r.text[:300])
        if r.status_code in (401, 403):
            raise RuntimeError("Jeton La bonne alternance refusé (expiré ? il dure 1 an). "
                               "Régénérez-le et mettez à jour le secret LBA_API_TOKEN.")
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"La bonne alternance ne répond pas (dernier code HTTP {r.status_code}).")


def _sature(reponse: dict) -> bool:
    """Vrai si une provenance d'offres a atteint le plafond de 150 (il en manque peut-être)."""
    compte = {"lba": 0, "ft": 0, "partenaires": 0}
    for job in reponse.get("jobs", []):
        label = (job.get("identifier", {}).get("partner_label") or "").lower()
        if "france travail" in label:
            compte["ft"] += 1
        elif "bonne alternance" in label or label in ("lba", "offres_emploi_lba"):
            compte["lba"] += 1
        else:
            compte["partenaires"] += 1
    return max(compte.values()) >= PLAFOND


def rechercher_france(cfg: dict) -> tuple[list, list, list[str]]:
    """Toutes les offres IT de France. Renvoie (offres, recruteurs, avertissements)."""
    mod = cfg["module_a"]
    pause = cfg.get("pause_entre_appels_lba_s", 1.1)
    romes = ",".join(mod["codes_rome"])
    avert: list[str] = []
    offres, recruteurs = {}, {}

    def chercher(departements, romes_txt):
        nonlocal romes
        params = {"romes": romes_txt, "departements": departements}
        try:
            rep = _appeler(params, pause)
        except ErreurCodeRome as e:
            # Un code ROME récent n'est pas reconnu : on repasse sur la liste sûre.
            avert.append(f"Codes ROME refusés, liste réduite utilisée ({e})")
            romes = ",".join(mod["codes_rome_surs"])
            params["romes"] = romes
            rep = _appeler(params, pause)
        for w in rep.get("warnings", []):
            avert.append(f"{w.get('code')}: {w.get('message')}")
        return rep

    def ranger(rep):
        for j in rep.get("jobs", []):
            offres[j["identifier"]["id"]] = j
        for r in rep.get("recruiters", []):
            recruteurs[r["identifier"]["id"]] = r

    for region, deps in REGIONS.items():
        rep = chercher(deps, romes)
        ranger(rep)
        if not _sature(rep):
            continue
        # Trop d'offres pour un seul appel : département par département...
        for dep in deps:
            rep_dep = chercher([dep], romes)
            ranger(rep_dep)
            if _sature(rep_dep):
                # ... puis métier par métier si besoin (ex. Paris).
                for rome in romes.split(","):
                    ranger(chercher([dep], rome))
    return list(offres.values()), list(recruteurs.values()), avert


def rechercher_autour(cfg: dict, lat: float, lon: float, rayon_km: int) -> tuple[list, list]:
    """Offres et entreprises "susceptibles de recruter" autour d'un point (module B)."""
    pause = cfg.get("pause_entre_appels_lba_s", 1.1)
    offres, recruteurs = {}, {}
    for rome in cfg["module_a"]["codes_rome_surs"]:
        rep = _appeler({"romes": rome, "latitude": lat, "longitude": lon,
                        "radius": min(int(rayon_km), 200)}, pause)
        for j in rep.get("jobs", []):
            offres[j["identifier"]["id"]] = j
        for r in rep.get("recruiters", []):
            recruteurs[r["identifier"]["id"]] = r
    return list(offres.values()), list(recruteurs.values())


# ---------------------------------------------------------------------------
# Transformation des réponses en dictionnaires simples
# ---------------------------------------------------------------------------

def _cp_ville(adresse: str | None) -> tuple[str | None, str | None]:
    """Extrait code postal et ville de "12 rue X 75011 Paris"."""
    if not adresse:
        return None, None
    m = re.search(r"\b(\d{5})\s+([^,\d][^,]*)", adresse)
    if m:
        return m.group(1), m.group(2).strip().title()
    return None, adresse.split(",")[-1].strip().title() or None


def _effectif_min(taille: str | None) -> int | None:
    """"10-19" -> 10 ; "0 salarié" -> 0 ; None -> None."""
    if not taille:
        return None
    nombres = re.findall(r"\d[\d\s]*", str(taille))
    return int(nombres[0].replace(" ", "")) if nombres else None


def lire_entreprise(element: dict) -> dict:
    """Partie "entreprise" commune aux offres et aux recruteurs."""
    w = element.get("workplace") or {}
    siret = w.get("siret")
    cp, ville = _cp_ville((w.get("location") or {}).get("address"))
    naf = ((w.get("domain") or {}).get("naf")) or {}
    nom = w.get("brand") or w.get("name") or w.get("legal_name") or "Entreprise inconnue"
    return {
        "siret": siret,
        "siren": siret[:9] if siret else None,
        "nom": nom.strip(),
        "code_postal": cp,
        "ville": ville,
        "site_web": w.get("website"),
        "effectif_libelle": w.get("size"),
        "effectif_min": _effectif_min(w.get("size")),
        "naf": naf.get("code"),
        "secteur": naf.get("label"),
        "telephone": (element.get("apply") or {}).get("phone"),
        "lien": (element.get("apply") or {}).get("url"),
    }


def lire_offre(job: dict) -> dict:
    """Une offre au format de l'outil."""
    o = job.get("offer") or {}
    diplome = o.get("target_diploma") or {}
    niveau = diplome.get("european")
    contrat = job.get("contract") or {}
    return {
        "id": "lba:" + job["identifier"]["id"],
        "entreprise": lire_entreprise(job),
        "titre": o.get("title") or "Alternance IT",
        "niveau_code": niveau,
        "niveau": NIVEAUX.get(niveau or "", diplome.get("label") or "Non précisé"),
        "lien": (job.get("apply") or {}).get("url"),
        "publiee_le": (o.get("publication") or {}).get("creation"),
        "contrat": ", ".join(contrat.get("type") or []) or "Alternance",
        "nb_postes": o.get("opening_count") or 1,
        "partenaire": job["identifier"].get("partner_label") or "La bonne alternance",
        "via_ecole": bool(job.get("is_delegated")),
        "statut": o.get("status") or "Active",
    }
