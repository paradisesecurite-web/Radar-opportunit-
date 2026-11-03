"""Choix de la bonne personne à appeler et type de numéro (sources gratuites).

Règle de choix selon la taille :
  - moins de 20 salariés          -> le dirigeant
  - entreprise tech (numérique)   -> CTO / DSI / responsable technique
  - plus de 200 salariés          -> chargé(e) de recrutement / resp. alternance / DRH
Sources, dans l'ordre : contact de l'annonce, dirigeants de l'annuaire.
Aurélien complète lui-même avec Lusha si besoin.
"""
import re


def type_numero(numero: str | None) -> str | None:
    """Mobile pro si 06/07, sinon standard (on ne peut pas savoir si c'est une ligne directe)."""
    if not numero:
        return None
    chiffres = re.sub(r"\D", "", numero)
    if chiffres.startswith("33"):
        chiffres = "0" + chiffres[2:]
    return "mobile pro" if chiffres[:2] in ("06", "07") else "standard"


def formater_numero(numero: str | None) -> str | None:
    """"0612345678" -> "06 12 34 56 78"."""
    if not numero:
        return None
    chiffres = re.sub(r"\D", "", numero)
    if chiffres.startswith("33") and len(chiffres) == 11:
        chiffres = "0" + chiffres[2:]
    if len(chiffres) == 10:
        return " ".join(chiffres[i:i + 2] for i in range(0, 10, 2))
    return numero.strip()


def choisir_decideur(effectif_min: int | None, est_numerique: bool,
                     dirigeant: str | None) -> tuple[str, bool, str | None]:
    """Renvoie (texte à afficher, personne nommée ?, source)."""
    if effectif_min is not None and effectif_min > 200:
        return "À demander : chargé(e) de recrutement / resp. alternance / DRH", False, None
    if effectif_min is not None and effectif_min < 20 and dirigeant:
        return dirigeant, True, "Annuaire des entreprises (RNE)"
    if est_numerique:
        texte = "À demander : CTO / DSI / resp. technique"
        if dirigeant:
            texte += f" (dirigeant : {dirigeant})"
        return texte, bool(dirigeant), "Annuaire des entreprises (RNE)" if dirigeant else None
    if dirigeant:
        return dirigeant, True, "Annuaire des entreprises (RNE)"
    return "À demander : responsable du recrutement", False, None
