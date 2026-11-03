"""Base de données locale (SQLite, gratuite, un seul fichier).

Elle contient :
  - entreprises : une ligne par entreprise, partagée par les modules A et B
  - offres      : les annonces du module A
  - meta        : petites informations (date du dernier récap, etc.)
  - journal     : les pannes de sources, reprises dans le récap du matin

Le Google Sheet reste la référence pour les statuts (Nouveau, Appelé...) :
ils sont relus à chaque lancement. Si cette base est perdue, rien de grave :
l'historique des envois est reconstruit depuis le Sheet.
"""
import sqlite3
from datetime import datetime

from .config import PARIS, chemin_base

SCHEMA = """
CREATE TABLE IF NOT EXISTS entreprises (
    cle TEXT PRIMARY KEY,           -- SIREN, ou "nom:<nom>|<cp>" si pas de SIRET
    siren TEXT,
    nom TEXT,
    ville TEXT,
    code_postal TEXT,
    metropole TEXT,                 -- ville du module B (Paris, Lyon...)
    naf TEXT,
    secteur TEXT,
    tranche_effectif TEXT,          -- code INSEE (01, 12, 21...)
    effectif_libelle TEXT,
    effectif_min INTEGER,
    categorie TEXT,                 -- PME / ETI / GE
    date_creation TEXT,
    ca_en_hausse INTEGER DEFAULT 0,
    est_numerique INTEGER DEFAULT 0,
    site_web TEXT,
    decideur TEXT,                  -- "Prénom NOM – fonction" ou "À demander : DRH..."
    decideur_nomme INTEGER DEFAULT 0,
    decideur_source TEXT,
    telephone TEXT,
    telephone_type TEXT,            -- direct / mobile pro / standard
    telephone_source TEXT,
    email TEXT,
    email_source TEXT,
    lba_susceptible INTEGER DEFAULT 0,   -- "susceptible de recruter" (La bonne alternance)
    lien TEXT,                      -- fiche LBA, annuaire ou site web
    module TEXT DEFAULT 'B',        -- 'A' dès qu'une offre est vue
    note_froid INTEGER,
    annuaire_ok INTEGER DEFAULT 0,  -- fiche annuaire déjà récupérée
    statut TEXT DEFAULT 'Nouveau',
    envoye_offre_le TEXT,
    envoye_froid_le TEXT,
    premiere_vue TEXT,
    maj TEXT
);
CREATE TABLE IF NOT EXISTS offres (
    id TEXT PRIMARY KEY,
    cle_entreprise TEXT,
    titre TEXT,
    niveau TEXT,
    lien TEXT,
    publiee_le TEXT,
    ville TEXT,
    contrat TEXT,
    nb_postes INTEGER,
    partenaire TEXT,
    via_ecole INTEGER DEFAULT 0,
    telephone TEXT,
    note INTEGER,
    premiere_vue TEXT,
    amorcage INTEGER DEFAULT 0,     -- vue lors du tout premier lancement
    envoyee_le TEXT,
    alerte_le TEXT
);
CREATE INDEX IF NOT EXISTS idx_offres_ent ON offres(cle_entreprise);
CREATE TABLE IF NOT EXISTS meta (cle TEXT PRIMARY KEY, valeur TEXT);
CREATE TABLE IF NOT EXISTS journal (quand TEXT, source TEXT, message TEXT, signale INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS opposition (cle TEXT PRIMARY KEY);  -- RGPD : ne plus recontacter
"""

STATUTS_BLOQUANTS = ("Pas intéressé", "Signé")


def connexion(chemin=None) -> sqlite3.Connection:
    con = sqlite3.connect(chemin or chemin_base())
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def maintenant_iso() -> str:
    return datetime.now(PARIS).isoformat(timespec="seconds")


def get_meta(con, cle, defaut=None):
    r = con.execute("SELECT valeur FROM meta WHERE cle=?", (cle,)).fetchone()
    return r["valeur"] if r else defaut


def set_meta(con, cle, valeur):
    con.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (cle, str(valeur)))
    con.commit()


def journaliser(con, source: str, message: str):
    """Note une panne de source (elle apparaîtra dans le récap du matin)."""
    con.execute("INSERT INTO journal (quand, source, message) VALUES (?, ?, ?)",
                (maintenant_iso(), source, message[:500]))
    con.commit()
    print(f"⚠️  {source} : {message[:200]}")


def enregistrer_entreprise(con, cle: str, champs: dict):
    """Crée ou complète une entreprise. Les champs vides n'écrasent pas les existants."""
    champs = {k: v for k, v in champs.items() if v not in (None, "")}
    existe = con.execute("SELECT 1 FROM entreprises WHERE cle=?", (cle,)).fetchone()
    champs["maj"] = maintenant_iso()
    if existe:
        sets = ", ".join(f"{k}=?" for k in champs)
        con.execute(f"UPDATE entreprises SET {sets} WHERE cle=?", (*champs.values(), cle))
    else:
        champs.setdefault("premiere_vue", maintenant_iso())
        champs["cle"] = cle
        cols = ", ".join(champs)
        con.execute(f"INSERT INTO entreprises ({cols}) VALUES ({','.join('?' * len(champs))})",
                    tuple(champs.values()))


def est_bloquee(con, cle: str) -> bool:
    """Vrai si l'entreprise ne doit plus jamais revenir (statut ou opposition RGPD)."""
    r = con.execute("SELECT statut FROM entreprises WHERE cle=?", (cle,)).fetchone()
    if r and r["statut"] in STATUTS_BLOQUANTS:
        return True
    return con.execute("SELECT 1 FROM opposition WHERE cle=?", (cle,)).fetchone() is not None
