"""Alertes immédiates (🔥) et récapitulatif du matin.

Règle d'or : une entreprise déjà envoyée n'est jamais renvoyée
(une fois comme offre, une fois comme appel à froid au maximum).
Exception voulue : une entreprise déjà envoyée "à froid" qui publie une offre
déclenche une alerte (passage du module B au module A).
"""
from datetime import datetime, timedelta

from . import db, mailer
from . import sheet as gsheet
from .config import PARIS
from .geo import TRANCHES
from .module_b import noter_froid
from .rapport import ligne_froid, ligne_offre, page
from .suivi import deja_envoye

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _meilleure_offre_par_entreprise(con, ids: list[str] | None, note_min: int, frais_h: int | None):
    """Une ligne par entreprise : sa meilleure offre non encore envoyée."""
    sql = """SELECT o.*, e.cle AS ecle FROM offres o JOIN entreprises e ON e.cle=o.cle_entreprise
             WHERE o.envoyee_le IS NULL AND o.note >= ?"""
    params: list = [note_min]
    if ids is not None:
        sql += f" AND o.id IN ({','.join('?' * len(ids))})"
        params += ids
    rows = con.execute(sql + " ORDER BY o.note DESC, o.publiee_le DESC", params).fetchall()
    limite = datetime.now(PARIS) - timedelta(hours=frais_h) if frais_h else None
    choisies = {}
    for o in rows:
        cle = o["cle_entreprise"]
        if cle in choisies or db.est_bloquee(con, cle) or deja_envoye(con, cle, "offre"):
            continue
        if o["amorcage"] and limite and o["publiee_le"]:
            # Offres déjà en ligne au tout premier lancement : seulement les très récentes
            try:
                if datetime.fromisoformat(o["publiee_le"].replace("Z", "+00:00")) < limite:
                    continue
            except ValueError:
                continue
        choisies[cle] = o
    return list(choisies.values())


def _marquer_offre(con, sh, offres, onglet_lignes: list):
    maintenant = db.maintenant_iso()
    for o in offres:
        con.execute("UPDATE offres SET envoyee_le=? WHERE cle_entreprise=? AND envoyee_le IS NULL",
                    (maintenant, o["cle_entreprise"]))
        con.execute("UPDATE entreprises SET envoye_offre_le=?, module='A' WHERE cle=?",
                    (maintenant, o["cle_entreprise"]))
    con.commit()
    if sh is not None and onglet_lignes:
        try:
            gsheet.ajouter(sh, gsheet.ONGLET_OFFRES, onglet_lignes)
        except Exception as e:
            db.journaliser(con, "Google Sheet", f"ajout des offres : {e}")


def _ligne(con, o):
    ent = con.execute("SELECT * FROM entreprises WHERE cle=?", (o["cle_entreprise"],)).fetchone()
    return ligne_offre(ent, o, ex_froid=deja_envoye(con, o["cle_entreprise"], "froid"))


def alertes(cfg: dict, con, sh, nouvelles: list[str]) -> int:
    """Mail immédiat pour chaque entreprise notée 8+ (ou passée du froid à l'offre)."""
    if not nouvelles:
        return 0
    seuil = cfg["mails"]["seuil_alerte"]
    candidates = _meilleure_offre_par_entreprise(con, nouvelles, 1, None)
    retenues = [o for o in candidates
                if o["note"] >= seuil or deja_envoye(con, o["cle_entreprise"], "froid")]
    retenues = [o for o in retenues if not o["amorcage"]]
    if not retenues:
        return 0
    lignes = [_ligne(con, o) for o in retenues]
    maxi = cfg["mails"]["max_alertes_par_heure"]
    for l in lignes[:maxi]:
        prefixe = "🔥" if l["Note /10"] >= seuil else "🔄 Passée en offre"
        sujet = f"{prefixe} {l['Note /10']}/10 – {l['Entreprise']} – {l['Poste recherché']} – {l['Ville']}"
        mailer.envoyer(sujet[:180], page(sujet, [("Offre", [l])]))
    if len(lignes) > maxi:
        reste = lignes[maxi:]
        sujet = f"🔥 {len(reste)} autres offres chaudes"
        mailer.envoyer(sujet, page(sujet, [("Offres chaudes", reste)]))
    maintenant = db.maintenant_iso()
    for o in retenues:
        con.execute("UPDATE offres SET alerte_le=? WHERE id=?", (maintenant, o["id"]))
    _marquer_offre(con, sh, retenues, lignes)
    return len(retenues)


def recap(cfg: dict, con, sh, test: bool = False, avec_froid: bool = True,
          ville: str | None = None, nom: str = "Récap") -> tuple[int, int]:
    """Mail récapitulatif : les offres notées 5+ puis, le matin, la liste d'appels à froid."""
    m = cfg["mails"]
    offres = []
    if not ville:   # test d'une ville = liste d'appels à froid seulement
        offres = _meilleure_offre_par_entreprise(con, None, m["seuil_recap_offres"], 48)
        if test and len(offres) < 5:   # test : on montre au moins quelques offres
            offres = _meilleure_offre_par_entreprise(con, None, 1, None)[:20]
    lignes_offres = [_ligne(con, o) for o in offres]
    lignes_offres.sort(key=lambda l: -l["Note /10"])

    lignes_froid, froids = [], []
    if avec_froid:
        noter_froid(cfg, con, ville)
        mb = cfg["module_b"]
        eff_max = TRANCHES[mb["effectif_max_numerique"]][1]
        villes = [ville] if ville else list(mb["villes"])
        sql = f"""SELECT * FROM entreprises WHERE module='B' AND note_froid IS NOT NULL
                 AND envoye_froid_le IS NULL AND envoye_offre_le IS NULL AND statut='Nouveau'
                 AND (effectif_min IS NULL OR effectif_min BETWEEN 1 AND ?)
                 AND lower(metropole) IN ({','.join('lower(?)' for _ in villes)})"""
        params: tuple = (eff_max, *villes)
        sql += " ORDER BY note_froid DESC, lba_susceptible DESC, effectif_min ASC"
        for e in con.execute(sql, params):
            if len(froids) >= m["nb_appels_a_froid"]:
                break
            if db.est_bloquee(con, e["cle"]) or deja_envoye(con, e["cle"], "froid"):
                continue
            froids.append(e)
        lignes_froid = [ligne_froid(e) for e in froids]

    # Pannes de sources depuis le dernier récap
    pannes = con.execute("SELECT * FROM journal WHERE signale=0 ORDER BY quand").fetchall()
    pied = ""
    if pannes:
        items = "".join(f"<li>{p['quand'][:16].replace('T', ' ')} – {p['source']} : {p['message'][:200]}</li>"
                        for p in pannes[-15:])
        pied = f'<h3 style="font-size:15px;color:#c5221f">⚠️ Sources en panne</h3><ul style="font-size:12px">{items}</ul>'

    aujourd_hui = datetime.now(PARIS)
    date_txt = f"{JOURS[aujourd_hui.weekday()]} {aujourd_hui:%d/%m}"
    maxi = m["max_offres_dans_recap"]
    affichees = lignes_offres[:maxi]
    if len(lignes_offres) > maxi:
        pied = f"<p>+ {len(lignes_offres) - maxi} autres offres dans le Google Sheet.</p>" + pied
    sujet = f"{nom} du {date_txt} – {len(lignes_offres)} offres"
    if avec_froid:
        sujet += f" – {len(lignes_froid)} appels à froid"
    if test:
        sujet = "TEST – " + sujet
    sections = []
    if not ville:
        sections.append(("Offres", affichees))
    if avec_froid:
        sections.append(("Liste d'appels à froid", lignes_froid))
    mailer.envoyer(sujet, page(sujet, sections, pied))

    # Marquage "envoyé" + ajout dans le Google Sheet
    _marquer_offre(con, sh, offres, lignes_offres)
    maintenant = db.maintenant_iso()
    for e in froids:
        con.execute("UPDATE entreprises SET envoye_froid_le=? WHERE cle=?", (maintenant, e["cle"]))
    con.execute("UPDATE journal SET signale=1 WHERE signale=0")
    con.commit()
    if sh is not None:
        try:
            gsheet.ajouter(sh, gsheet.ONGLET_FROID, lignes_froid)
            gsheet.journal(sh, [(p["quand"], p["source"], p["message"]) for p in pannes])
        except Exception as e:
            db.journaliser(con, "Google Sheet", f"ajout de la liste d'appels : {e}")
    return len(lignes_offres), len(lignes_froid)
