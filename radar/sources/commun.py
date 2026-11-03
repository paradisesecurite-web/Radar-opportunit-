"""Outils communs aux job boards (Adzuna, Jooble) : filtre IT, type d'offre, école."""
import re
import unicodedata


def normaliser(texte: str | None) -> str:
    """"Société Générale SAS" -> "societe generale"."""
    t = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\b(sas|sasu|sarl|sa|eurl|sci|scop|groupe|group|france)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def est_it(cfg: dict, titre: str) -> bool:
    t = f" {(titre or '').lower()} "
    return any(m in t for m in cfg["module_a"]["mots_cles_it"])


def type_offre(titre: str, description: str = "", defaut: str = "Alternance") -> str:
    t = f"{titre} {description}".lower()
    if re.search(r"alternan|apprenti|contrat pro", t):
        return "Alternance"
    if re.search(r"\bstage|stagiaire|internship", t):
        return "Stage"
    return defaut


def est_ecole(cfg: dict, nom: str) -> bool:
    n = f" {(nom or '').lower()} "
    return any(m in n for m in cfg["module_a"]["mots_ecoles"])


def est_exclue(cfg: dict, nom: str) -> bool:
    n = normaliser(nom)
    return any(normaliser(x) and normaliser(x) in n for x in cfg["module_a"]["exclure_entreprises"])


def offre_generique(*, id_: str, source: str, nom: str | None, ville: str | None, titre: str,
                    lien: str | None, publiee_le: str | None, type_: str, cfg: dict) -> dict:
    """Format commun d'une offre (identique à celui de La bonne alternance)."""
    return {
        "id": id_,
        "entreprise": {"siret": None, "siren": None, "nom": (nom or "Entreprise non précisée").strip(),
                       "code_postal": None, "ville": ville, "site_web": None, "effectif_libelle": None,
                       "effectif_min": None, "naf": None, "secteur": None, "telephone": None, "lien": None},
        "titre": titre,
        "niveau_code": None,
        "niveau": "Non précisé",
        "lien": lien,
        "publiee_le": publiee_le,
        "contrat": type_,
        "type_offre": type_,
        "nb_postes": 1,
        "partenaire": source,
        "via_ecole": est_ecole(cfg, nom or ""),
        "statut": "Active",
    }
