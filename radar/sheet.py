"""Google Sheet : l'écran de travail d'Aurélien (lisible dans l'appli Google Sheets).

Onglets :
  - "Offres"              : chaque offre envoyée par mail (module A)
  - "Appels à froid"      : chaque entreprise de la liste d'appels (module B)
  - "Ne pas recontacter"  : RGPD, une entreprise ou personne par ligne (SIREN ou nom)
  - "Journal"             : pannes de sources

Colonnes "Statut" (liste : Nouveau / Appelé / À rappeler / Pas intéressé / Signé)
et "Vu ✓" (case à cocher) : Aurélien les remplit, l'outil les relit à chaque
lancement. "Pas intéressé" ou "Signé" = l'entreprise ne revient jamais.

Secrets : GOOGLE_SERVICE_ACCOUNT_JSON (contenu du fichier JSON du compte de
service) et GOOGLE_SHEET_ID (l'identifiant dans l'adresse du Sheet).
"""
import json

from .config import secret
from .rapport import COLONNES, COLONNES_SUIVI

ONGLET_OFFRES = "Offres"
ONGLET_FROID = "Appels à froid"
ONGLET_OPPOSITION = "Ne pas recontacter"
ONGLET_JOURNAL = "Journal"
STATUTS = ["Nouveau", "Appelé", "À rappeler", "Pas intéressé", "Signé"]
ENTETES = COLONNES + COLONNES_SUIVI
COL_STATUT = len(COLONNES)          # index 0-based de "Statut"
COL_ID = len(ENTETES) - 1


def ouvrir():
    """Ouvre le Google Sheet, ou renvoie None si les secrets ne sont pas renseignés."""
    cle_json, sheet_id = secret("GOOGLE_SERVICE_ACCOUNT_JSON"), secret("GOOGLE_SHEET_ID")
    if not (cle_json and sheet_id):
        return None
    import gspread
    client = gspread.service_account_from_dict(json.loads(cle_json))
    sh = client.open_by_key(sheet_id)
    _preparer(sh)
    return sh


def _preparer(sh):
    """Crée les onglets, les en-têtes, la liste déroulante et les cases à cocher (une seule fois)."""
    existants = {ws.title: ws for ws in sh.worksheets()}
    requetes = []
    for titre in (ONGLET_OFFRES, ONGLET_FROID):
        if titre in existants:
            continue
        ws = sh.add_worksheet(titre, rows=2000, cols=len(ENTETES))
        ws.update([ENTETES], "A1")
        sid = ws.id
        requetes += [
            {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {
                "frozenRowCount": 1, "frozenColumnCount": 3}},
                "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}},
            {"setDataValidation": {"range": _plage(sid, COL_STATUT), "rule": {
                "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": s} for s in STATUTS]},
                "showCustomUi": True, "strict": False}}},
            {"setDataValidation": {"range": _plage(sid, COL_STATUT + 1),
                                   "rule": {"condition": {"type": "BOOLEAN"}}}},
            {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
                            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                            "fields": "userEnteredFormat.textFormat.bold"}},
        ]
    if ONGLET_OPPOSITION not in existants:
        ws = sh.add_worksheet(ONGLET_OPPOSITION, rows=500, cols=3)
        ws.update([["SIREN ou nom de l'entreprise", "Personne", "Date de la demande"]], "A1")
    if ONGLET_JOURNAL not in existants:
        ws = sh.add_worksheet(ONGLET_JOURNAL, rows=1000, cols=3)
        ws.update([["Date", "Source", "Problème"]], "A1")
    if requetes:
        sh.batch_update({"requests": requetes})
        # Supprime l'onglet vide créé par défaut ("Feuille 1" / "Sheet1")
        for ws in sh.worksheets():
            if ws.title in ("Feuille 1", "Sheet1", "Feuille1") and not any(ws.get_all_values()):
                sh.del_worksheet(ws)


def _plage(sheet_id: int, col: int) -> dict:
    return {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 20000,
            "startColumnIndex": col, "endColumnIndex": col + 1}


def lire_suivi(sh) -> tuple[dict, set, set, set]:
    """Renvoie (statuts par ID, IDs déjà envoyés en offre, IDs déjà envoyés à froid, oppositions)."""
    statuts, offres, froids = {}, set(), set()
    for titre, ensemble in ((ONGLET_OFFRES, offres), (ONGLET_FROID, froids)):
        for ligne in sh.worksheet(titre).get_all_values()[1:]:
            if len(ligne) > COL_ID and ligne[COL_ID]:
                cle = ligne[COL_ID]
                ensemble.add(cle)
                statut = ligne[COL_STATUT].strip()
                # Le statut le plus "avancé" l'emporte si l'entreprise est dans les deux onglets
                if statut in STATUTS and STATUTS.index(statut) >= STATUTS.index(statuts.get(cle, "Nouveau")):
                    statuts[cle] = statut
    opposition = {l[0].strip().lower() for l in sh.worksheet(ONGLET_OPPOSITION).get_all_values()[1:]
                  if l and l[0].strip()}
    return statuts, offres, froids, opposition


def _texte(v):
    """Empêche Google Sheets d'interpréter "+33..." ou "=..." comme une formule."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
        return "'" + v
    return v


def ajouter(sh, onglet: str, lignes: list[dict]):
    if not lignes:
        return
    valeurs = [[_texte(l.get(c, "")) for c in COLONNES] + ["Nouveau", False, "", l["ID"]] for l in lignes]
    sh.worksheet(onglet).append_rows(valeurs, value_input_option="USER_ENTERED")


def journal(sh, entrees: list[tuple[str, str, str]]):
    if entrees:
        sh.worksheet(ONGLET_JOURNAL).append_rows([list(e) for e in entrees])
