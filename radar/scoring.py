"""Note de 1 (très froid) à 10 (brûlant).

Quatre critères notés de 0 à 10, puis moyenne pondérée (poids dans config.yaml) :
  - besoin  : fraîcheur de l'offre, ou signal "susceptible de recruter"
  - contact : décideur nommé, numéro, type de numéro
  - taille  : les PME décident plus vite que les grands groupes
  - bonus   : plusieurs postes, entreprise jeune, CA en hausse, etc.
La moyenne (0 à 10) est ramenée sur l'échelle 1 à 10.
Aucun critère ne décide seul : une grande entreprise avec une offre toute
fraîche reste bien notée.
"""
from datetime import datetime

from .config import PARIS


def _age_heures(publiee_le: str | None, maintenant: datetime) -> float | None:
    if not publiee_le:
        return None
    try:
        d = datetime.fromisoformat(publiee_le.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=PARIS)
    return max(0.0, (maintenant - d).total_seconds() / 3600)


def note_besoin(cfg_b: dict, publiee_le: str | None, est_offre: bool,
                susceptible: bool, maintenant: datetime, type_offre: str = "Alternance") -> float:
    if est_offre:
        coef = {"Stage": cfg_b.get("coef_stage", 0.7),
                "Emploi junior": cfg_b.get("coef_emploi_junior", 0.6)}.get(type_offre, 1.0)
        return coef * _besoin_offre(cfg_b, publiee_le, maintenant)
    return cfg_b["susceptible_lba"] if susceptible else cfg_b["profil_seul"]


def _besoin_offre(cfg_b: dict, publiee_le: str | None, maintenant: datetime) -> float:
    age = _age_heures(publiee_le, maintenant)
    if age is None:
        return cfg_b["offre_moins_30j"]
    if age <= 48:
        return cfg_b["offre_moins_48h"]
    if age <= 24 * 7:
        return cfg_b["offre_moins_7j"]
    if age <= 24 * 30:
        return cfg_b["offre_moins_30j"]
    return cfg_b["offre_ancienne"]


def note_contact(cfg_c: dict, decideur_nomme: bool, telephone_type: str | None) -> float:
    if decideur_nomme and telephone_type in ("mobile pro", "direct"):
        return cfg_c["decideur_mobile"]
    if decideur_nomme and telephone_type:
        return cfg_c["nom_et_numero"]
    if decideur_nomme:
        return cfg_c["nom_seul"]
    if telephone_type:
        return cfg_c["numero_seul"]
    return cfg_c["rien"]


def note_taille(cfg_t: dict, effectif_min: int | None) -> float:
    if effectif_min is None:
        return cfg_t["inconnue"]
    if effectif_min < 20:
        return cfg_t["moins_20"]
    if effectif_min < 250:
        return cfg_t["de_20_a_249"]
    if effectif_min < 2000:
        return cfg_t["de_250_a_1999"]
    return cfg_t["plus_2000"]


def note_bonus(cfg_x: dict, plusieurs_postes=False, jeune=False, ca_hausse=False,
               numerique=False, gros_service_info=False) -> float:
    pts = 0
    pts += cfg_x["plusieurs_postes"] if plusieurs_postes else 0
    pts += cfg_x["entreprise_jeune"] if jeune else 0
    pts += cfg_x["chiffre_affaires_en_hausse"] if ca_hausse else 0
    pts += cfg_x["entreprise_numerique"] if numerique else 0
    pts += cfg_x["gros_service_info"] if gros_service_info else 0
    return min(10, pts)


def noter(cfg: dict, *, est_offre: bool, publiee_le: str | None = None,
          susceptible: bool = False, decideur_nomme: bool = False,
          telephone_type: str | None = None, effectif_min: int | None = None,
          plusieurs_postes: bool = False, jeune: bool = False, ca_hausse: bool = False,
          numerique: bool = False, maintenant: datetime | None = None,
          type_offre: str = "Alternance") -> int:
    """Calcule la note finale de 1 à 10."""
    n = cfg["note"]
    p = n["poids"]
    maintenant = maintenant or datetime.now(PARIS)
    gros_si = (not numerique) and effectif_min is not None and effectif_min >= 250
    sous_notes = {
        "besoin": note_besoin(n["besoin"], publiee_le, est_offre, susceptible, maintenant, type_offre),
        "contact": note_contact(n["contact"], decideur_nomme, telephone_type),
        "taille": note_taille(n["taille"], effectif_min),
        "bonus": note_bonus(n["bonus"], plusieurs_postes, jeune, ca_hausse, numerique, gros_si),
    }
    moyenne = sum(p[k] * v for k, v in sous_notes.items()) / sum(p.values())  # 0 à 10
    return max(1, min(10, round(1 + 0.9 * moyenne)))
