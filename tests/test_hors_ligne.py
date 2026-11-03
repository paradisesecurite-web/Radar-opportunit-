"""Tests sans réseau : on remplace les API par de fausses réponses.

Lancer : python -m pytest -q
"""
from datetime import datetime, timedelta, timezone

import pytest

from radar import __main__ as cli
from radar import scoring
from radar.config import charger_config
from radar.sources import annuaire, lba

CFG = charger_config()
MAINTENANT = datetime.now(timezone.utc)


def _job(i, siret, nom, heures, niveau="6", tel="0612345678", taille="10-19", postes=1):
    return {
        "identifier": {"id": f"job{i}", "partner_job_id": f"p{i}", "partner_label": "La bonne alternance"},
        "workplace": {"name": nom, "legal_name": nom, "brand": None, "siret": siret,
                      "website": "https://exemple.fr", "size": taille,
                      "location": {"address": "10 rue de la Paix 69002 LYON", "geopoint": {}},
                      "domain": {"naf": {"code": "6201Z", "label": "Programmation informatique"}}},
        "apply": {"url": f"https://labonnealternance.apprentissage.beta.gouv.fr/offre/{i}", "phone": tel},
        "contract": {"type": ["Apprentissage"]},
        "offer": {"title": "Développeur full stack en alternance", "opening_count": postes,
                  "publication": {"creation": (MAINTENANT - timedelta(hours=heures)).isoformat()},
                  "target_diploma": {"european": niveau, "label": ""}, "status": "Active", "rome_codes": ["M1805"]},
        "is_delegated": i == 3,
    }


FAUX_LBA = {
    "jobs": [
        _job(1, "12345678900011", "PetiteTech", 5),                       # fraîche, PME : chaude
        _job(2, "98765432100022", "GrosGroupe", 24 * 20, taille="5000-9999", tel=None),  # ancienne, grande
        _job(3, "11122233300033", "ViaEcole", 30, postes=3),               # via une autre école
        _job(4, "44455566600044", "NiveauBac", 2, niveau="4"),             # exclue (niveau Bac)
    ],
    "recruiters": [], "warnings": [],
}

FAUSSE_FICHE = {
    "siren": "123456789", "nom_complet": "PETITETECH", "activite_principale": "62.01Z",
    "tranche_effectif_salarie": "11", "categorie_entreprise": "PME", "date_creation": "2023-01-10",
    "statut_diffusion": "O", "siege": {"libelle_commune": "LYON", "code_postal": "69002", "epci": "200046977"},
    "dirigeants": [{"type_dirigeant": "personne physique", "nom": "Martin", "prenoms": "Julie Anne",
                    "qualite": "Président"}],
    "finances": {"2023": {"ca": 100000}, "2024": {"ca": 150000}},
    "matching_etablissements": [],
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("RADAR_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("LBA_API_TOKEN", "faux")
    for s in ("GMAIL_MOT_DE_PASSE", "GOOGLE_SHEET_ID"):
        monkeypatch.delenv(s, raising=False)
    monkeypatch.setattr("radar.mailer.RACINE", tmp_path)
    monkeypatch.setattr(lba, "_appeler", lambda params, pause: FAUX_LBA)
    monkeypatch.setattr(annuaire, "_appeler",
                        lambda params, pause: {"results": [FAUSSE_FICHE], "total_results": 1, "total_pages": 1})
    return tmp_path


def test_scoring_reperes():
    n = lambda **k: scoring.noter(CFG, maintenant=MAINTENANT, **k)
    frais = (MAINTENANT - timedelta(hours=3)).isoformat()
    vieux = (MAINTENANT - timedelta(days=40)).isoformat()
    assert n(est_offre=True, publiee_le=frais, effectif_min=10) >= 8                      # PME + offre fraîche
    assert n(est_offre=True, publiee_le=frais, effectif_min=5000, decideur_nomme=True,
             telephone_type="mobile pro") >= 8                                              # gros + frais + direct
    assert n(est_offre=True, publiee_le=vieux, effectif_min=5000) <= 6
    assert 5 <= n(est_offre=False, susceptible=True, effectif_min=10, decideur_nomme=True) <= 7
    assert n(est_offre=False, effectif_min=5000) <= 4


def test_offres_bout_en_bout(env):
    assert cli.main(["test-offres"]) == 0
    apercus = list(env.glob("apercu_*.html"))
    assert len(apercus) == 1
    html = apercus[0].read_text(encoding="utf-8")
    assert "PetiteTech" in html and "GrosGroupe" in html
    assert "NiveauBac" not in html                       # niveau Bac exclu
    assert "via une autre école" in html
    assert "Julie MARTIN" in html                        # dirigeant de l'annuaire (< 20 salariés)
    assert "06 12 34 56 78 (mobile pro)" in html

    # Deuxième passage : rien n'est renvoyé
    for f in apercus:
        f.unlink()
    assert cli.main(["recap"]) == 0
    html2 = next(env.glob("apercu_*.html")).read_text(encoding="utf-8")
    assert "PetiteTech" not in html2


def test_module_b_une_ville(env, monkeypatch):
    monkeypatch.setattr(lba, "_appeler", lambda params, pause: {
        "jobs": [], "warnings": [],
        "recruiters": [{"identifier": {"id": "r1"}, "workplace": FAUX_LBA["jobs"][0]["workplace"],
                        "apply": {"url": "https://lba/fiche/r1", "phone": "0478000000"}}]})
    assert cli.main(["test-froid", "--ville", "Lyon"]) == 0
    html = next(env.glob("apercu_*.html")).read_text(encoding="utf-8")
    assert "appels à froid (1)" in html
    assert "PETITETECH" in html and "04 78 00 00 00 (standard)" in html


def test_alerte_horaire(env, monkeypatch):
    # 1er passage = amorçage : aucune alerte pour les offres déjà en ligne
    assert cli.main(["heure", "--force"]) == 0
    assert not [f for f in env.glob("apercu_*.html") if "_9_10_" in f.name or "10_10" in f.name]
    # 2e passage : une nouvelle offre fraîche dans une PME -> mail 🔥
    nouveau = {**FAUX_LBA, "jobs": FAUX_LBA["jobs"] + [_job(9, "77788899900099", "NouvelleStartup", 1)]}
    monkeypatch.setattr(lba, "_appeler", lambda params, pause: nouveau)
    for f in env.glob("apercu_*.html"):
        f.unlink()
    assert cli.main(["heure", "--force"]) == 0
    alertes = [f.name for f in env.glob("apercu_*.html") if "NouvelleStartup" in f.name]
    assert len(alertes) == 1
    # 3e passage : pas de doublon
    for f in env.glob("apercu_*.html"):
        f.unlink()
    assert cli.main(["heure", "--force"]) == 0
    assert not [f for f in env.glob("apercu_*.html") if "NouvelleStartup" in f.name]


class _Rep:
    def __init__(self, data, code=200):
        self._d, self.status_code = data, code

    def json(self):
        return self._d

    def raise_for_status(self):
        pass


def test_adzuna_jooble(env, monkeypatch):
    from radar.sources import adzuna, jooble
    monkeypatch.setenv("ADZUNA_APP_ID", "x")
    monkeypatch.setenv("ADZUNA_APP_KEY", "y")
    monkeypatch.setenv("JOOBLE_API_KEY", "z")
    monkeypatch.setattr(lba, "_appeler", lambda params, pause: {"jobs": [], "recruiters": [], "warnings": []})
    frais = (MAINTENANT - timedelta(hours=2)).isoformat()
    monkeypatch.setattr(adzuna.requests, "get", lambda *a, **k: _Rep({"results": [
        {"id": "a1", "title": "Alternance Développeur web H/F", "created": frais,
         "redirect_url": "https://www.adzuna.fr/details/a1", "company": {"display_name": "PetiteTech SAS"},
         "location": {"area": ["France", "Auvergne-Rhône-Alpes", "Rhône", "Lyon"]},
         "category": {"tag": "it-jobs"}},
        {"id": "a2", "title": "Alternance technicien réseau", "created": frais,
         "redirect_url": "https://www.adzuna.fr/details/a2", "company": {"display_name": "ISCOD"},
         "location": {"area": ["France", "Île-de-France", "Paris"]}, "category": {"tag": "it-jobs"}},
    ]}))
    monkeypatch.setattr(jooble.requests, "post", lambda *a, **k: _Rep({"jobs": [
        {"id": 7, "title": "Alternance Développeur web H/F", "company": "PetiteTech", "location": "Lyon",
         "link": "https://fr.jooble.org/7", "updated": frais, "source": "indeed.fr", "snippet": ""},
        {"id": 8, "title": "Stage développeur Python", "company": "Campus Numérique", "location": "Nantes",
         "link": "https://fr.jooble.org/8", "updated": frais, "source": "hellowork.com", "snippet": ""},
        {"id": 9, "title": "Alternance commercial", "company": "Boutique", "location": "Nice",
         "link": "https://fr.jooble.org/9", "updated": frais, "snippet": ""},
    ]}))
    assert cli.main(["test-offres"]) == 0
    html = next(env.glob("apercu_*.html")).read_text(encoding="utf-8")
    assert "adzuna.fr/details/a1" in html                 # lien vers l'annonce
    assert "ISCOD" not in html.split("<h3")[1]            # sa propre école est exclue
    assert "Boutique" not in html                         # pas un poste IT
    assert "[Stage]" in html and "via une autre école" in html
    assert html.count("PetiteTech") == 1                  # même annonce sur 2 sites = 1 ligne
    assert "Julie MARTIN" in html                         # SIREN retrouvé par le nom dans l'annuaire
