"""Source : API Recherche d'entreprises (annuaire-entreprises.data.gouv.fr).

Gratuite, sans clé. Doc : https://recherche-entreprises.api.gouv.fr/docs/
Limites : 7 appels/seconde, 25 résultats par page, 10 000 résultats max par
recherche (au-delà on découpe par tranche d'effectif).

Sert à :
  - compléter une entreprise vue dans une offre (effectif, secteur, dirigeants)
  - lister les entreprises du module B (par métropole et code NAF)
"""
import time
from datetime import date

import requests

from ..geo import TRANCHES

URL = "https://recherche-entreprises.api.gouv.fr/search"
ENTETES = {"User-Agent": "radar-alternance-it/1.0"}
INCLURE = "siege,dirigeants,complements,finances,matching_etablissements"
FICHE = "https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}"

# Fonctions de dirigeant, de la plus pertinente à la moins pertinente
QUALITES_PRIORITAIRES = ["président", "gérant", "directeur général", "dirigeant"]


def _appeler(params: dict, pause: float) -> dict:
    for essai in range(5):
        time.sleep(pause)
        r = requests.get(URL, params=params, headers=ENTETES, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(int(r.headers.get("Retry-After", 0) or 0) or 2 * (essai + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Annuaire des entreprises indisponible (HTTP {r.status_code}).")


def fiche(siren: str, pause: float = 0.2) -> dict | None:
    """Fiche d'une entreprise par son SIREN (None si introuvable)."""
    rep = _appeler({"q": siren, "minimal": "true", "include": INCLURE, "per_page": 5}, pause)
    for res in rep.get("results", []):
        if res.get("siren") == siren:
            return res
    return None


def lister(pause: float, naf: str, tranches: list[str], epci: str | None = None,
           departement: str | None = None):
    """Toutes les entreprises actives d'un code NAF dans une métropole (ou un département).

    Génère les résultats bruts. Si une recherche dépasse 10 000 résultats,
    on la redécoupe tranche d'effectif par tranche d'effectif.
    """
    base = {"activite_principale": naf, "etat_administratif": "A", "minimal": "true",
            "include": INCLURE, "limite_matching_etablissements": 3, "per_page": 25}
    if epci:
        base["epci"] = epci
    if departement:
        base["departement"] = departement

    def pages(params):
        page = 1
        while True:
            rep = _appeler({**params, "page": page}, pause)
            yield from rep.get("results", [])
            if page >= min(rep.get("total_pages", 1), 400):
                break
            page += 1

    premier = _appeler({**base, "tranche_effectif_salarie": ",".join(tranches), "page": 1}, pause)
    if premier.get("total_results", 0) < 10000:
        yield from pages({**base, "tranche_effectif_salarie": ",".join(tranches)})
    else:
        for t in tranches:
            yield from pages({**base, "tranche_effectif_salarie": t})


def lire_fiche(res: dict) -> dict:
    """Transforme une fiche de l'annuaire en champs simples pour l'outil."""
    siege = res.get("siege") or {}
    tranche = res.get("tranche_effectif_salarie") or siege.get("tranche_effectif_salarie")
    libelle, eff_min = TRANCHES.get(tranche or "", (None, None))

    # Chiffre d'affaires en hausse (> +10 %) sur les deux dernières années publiées
    hausse = False
    fin = res.get("finances") or {}
    annees = sorted(a for a in fin if (fin[a] or {}).get("ca"))
    if len(annees) >= 2:
        avant, apres = fin[annees[-2]]["ca"], fin[annees[-1]]["ca"]
        hausse = bool(avant and apres and apres > avant * 1.10)

    # Dirigeant personne physique le plus pertinent (données publiques du RNE)
    dirigeant = None
    personnes = [d for d in res.get("dirigeants") or [] if d.get("type_dirigeant") == "personne physique"]
    personnes.sort(key=lambda d: next((i for i, q in enumerate(QUALITES_PRIORITAIRES)
                                       if q in (d.get("qualite") or "").lower()), 99))
    if personnes and res.get("statut_diffusion", "O") == "O":
        d = personnes[0]
        prenom = (d.get("prenoms") or "").split(" ")[0].title()
        dirigeant = f"{prenom} {(d.get('nom') or '').upper()} – {d.get('qualite') or 'Dirigeant'}".strip()

    # Ville : celle de l'établissement trouvé dans la zone, sinon celle du siège
    etab = next((e for e in res.get("matching_etablissements") or []
                 if e.get("etat_administratif") == "A"), siege)
    return {
        "siren": res.get("siren"),
        "nom": res.get("nom_complet") or res.get("nom_raison_sociale"),
        "ville": (etab.get("libelle_commune") or siege.get("libelle_commune") or "").title() or None,
        "code_postal": etab.get("code_postal") or siege.get("code_postal"),
        "epci_siege": siege.get("epci"),
        "naf": res.get("activite_principale"),
        "tranche_effectif": tranche,
        "effectif_libelle": libelle,
        "effectif_min": eff_min,
        "categorie": res.get("categorie_entreprise"),
        "date_creation": res.get("date_creation"),
        "ca_en_hausse": 1 if hausse else 0,
        "dirigeant": dirigeant,
        "diffusible": res.get("statut_diffusion", "O") == "O",
        "lien": FICHE.format(siren=res.get("siren")),
    }


def age_ans(date_creation: str | None) -> float | None:
    if not date_creation:
        return None
    try:
        return (date.today() - date.fromisoformat(date_creation[:10])).days / 365.25
    except ValueError:
        return None
