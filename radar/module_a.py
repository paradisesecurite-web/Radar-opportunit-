"""MODULE A – Offres en temps réel.

1. Récupère toutes les offres d'alternance IT de France (La bonne alternance,
   qui inclut les offres France Travail et celles de sites partenaires).
2. Enregistre les nouvelles offres et leurs entreprises.
3. Complète les entreprises avec l'annuaire (effectif, secteur, dirigeant).
4. Calcule la note de chaque nouvelle offre.
Renvoie les identifiants des offres nouvelles de ce passage.
"""
import re
from datetime import datetime, timedelta

from . import db
from .config import PARIS
from .contacts import choisir_decideur, formater_numero, type_numero
from .scoring import noter
from .sources import annuaire, lba

MAX_FICHES_PAR_PASSAGE = 400   # le reste est complété au passage suivant


def cle_entreprise(ent: dict) -> str:
    if ent.get("siren"):
        return ent["siren"]
    nom = re.sub(r"[^a-z0-9]+", " ", (ent.get("nom") or "").lower()).strip()
    return f"nom:{nom}|{ent.get('code_postal') or ''}"


def est_numerique(cfg: dict, naf: str | None) -> bool:
    if not naf:
        return False
    naf = naf if "." in naf else f"{naf[:2]}.{naf[2:]}"   # "6201Z" -> "62.01Z"
    return naf in cfg["module_b"]["naf_numerique"] or naf.startswith(("58.2", "62.", "63.1", "61."))


def collecter(cfg: dict, con, amorcage: bool) -> list[str]:
    """Interroge La bonne alternance et enregistre les nouveautés."""
    maintenant = datetime.now(PARIS)
    limite = maintenant - timedelta(days=cfg["module_a"]["age_max_offre_jours"])
    exclus = set(cfg["module_a"]["niveaux_exclus"])

    jobs, recruteurs, avertissements = lba.rechercher_france(cfg)
    for a in sorted(set(avertissements))[:5]:
        db.journaliser(con, "La bonne alternance", a)
    print(f"📥 La bonne alternance : {len(jobs)} offres, {len(recruteurs)} entreprises susceptibles.")

    nouvelles = []
    for job in jobs:
        o = lba.lire_offre(job)
        if o["statut"] != "Active" or (o["niveau_code"] or "") in exclus:
            continue
        if o["publiee_le"]:
            try:
                if datetime.fromisoformat(o["publiee_le"].replace("Z", "+00:00")) < limite:
                    continue
            except ValueError:
                pass
        if con.execute("SELECT 1 FROM offres WHERE id=?", (o["id"],)).fetchone():
            continue
        ent = o["entreprise"]
        cle = cle_entreprise(ent)
        if db.est_bloquee(con, cle):
            continue
        numero = formater_numero(ent["telephone"])
        db.enregistrer_entreprise(con, cle, {
            "siren": ent["siren"], "nom": ent["nom"], "ville": ent["ville"],
            "code_postal": ent["code_postal"], "naf": ent["naf"], "secteur": ent["secteur"],
            "site_web": ent["site_web"], "effectif_libelle": ent["effectif_libelle"],
            "effectif_min": ent["effectif_min"], "est_numerique": int(est_numerique(cfg, ent["naf"])),
            "module": "A",   # une entreprise du module B qui publie une offre passe dans le A
        })
        ligne = con.execute("SELECT telephone, lien FROM entreprises WHERE cle=?", (cle,)).fetchone()
        if numero and not ligne["telephone"]:
            db.enregistrer_entreprise(con, cle, {"telephone": numero, "telephone_type": type_numero(numero),
                                                 "telephone_source": "annonce La bonne alternance"})
        if not ligne["lien"]:
            db.enregistrer_entreprise(con, cle, {"lien": ent["site_web"] or (
                annuaire.FICHE.format(siren=ent["siren"]) if ent["siren"] else None)})
        con.execute("""INSERT INTO offres (id, cle_entreprise, titre, niveau, lien, publiee_le, ville, contrat,
                       nb_postes, partenaire, via_ecole, telephone, premiere_vue, amorcage)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (o["id"], cle, o["titre"], o["niveau"], o["lien"] or ent["lien"], o["publiee_le"],
                     ent["ville"], o["contrat"], o["nb_postes"], o["partenaire"], int(o["via_ecole"]),
                     numero, db.maintenant_iso(), int(amorcage)))
        nouvelles.append(o["id"])
    con.commit()

    # Entreprises "susceptibles de recruter" : on marque celles déjà connues
    for r in recruteurs:
        e = lba.lire_entreprise(r)
        if e["siren"]:
            con.execute("UPDATE entreprises SET lba_susceptible=1 WHERE cle=?", (e["siren"],))
    con.commit()

    completer_annuaire(cfg, con)
    noter_offres(cfg, con, nouvelles)
    print(f"🆕 {len(nouvelles)} nouvelles offres enregistrées.")
    return nouvelles


def completer_annuaire(cfg: dict, con) -> None:
    """Ajoute effectif, secteur et dirigeant depuis l'annuaire (gratuit)."""
    pause = cfg.get("pause_entre_appels_annuaire_s", 0.2)
    a_faire = con.execute("""SELECT cle, siren FROM entreprises WHERE annuaire_ok=0 AND siren IS NOT NULL
                             LIMIT ?""", (MAX_FICHES_PAR_PASSAGE,)).fetchall()
    for r in a_faire:
        try:
            res = annuaire.fiche(r["siren"], pause)
        except Exception as e:  # une fiche en échec ne bloque pas les autres
            db.journaliser(con, "Annuaire des entreprises", str(e))
            break
        champs = {"annuaire_ok": 1}
        if res:
            f = annuaire.lire_fiche(res)
            naf = f["naf"]
            champs.update({
                "naf": naf, "tranche_effectif": f["tranche_effectif"], "categorie": f["categorie"],
                "date_creation": f["date_creation"], "ca_en_hausse": f["ca_en_hausse"],
                "est_numerique": int(est_numerique(cfg, naf)),
            })
            if f["effectif_libelle"]:
                champs.update({"effectif_libelle": f["effectif_libelle"], "effectif_min": f["effectif_min"]})
            secteur = cfg["module_b"]["naf_numerique"].get(naf) or cfg["module_b"]["naf_hors_numerique"].get(naf)
            if secteur:
                champs["secteur"] = secteur
            champs["_dirigeant"] = f["dirigeant"]
        dirigeant = champs.pop("_dirigeant", None)
        db.enregistrer_entreprise(con, r["cle"], champs)
        ent = con.execute("SELECT effectif_min, est_numerique FROM entreprises WHERE cle=?", (r["cle"],)).fetchone()
        texte, nomme, source = choisir_decideur(ent["effectif_min"], bool(ent["est_numerique"]), dirigeant)
        db.enregistrer_entreprise(con, r["cle"], {"decideur": texte, "decideur_nomme": int(nomme),
                                                  "decideur_source": source})
    con.commit()


def _jeune(date_creation: str | None) -> bool:
    age = annuaire.age_ans(date_creation)
    return age is not None and age < 5


def noter_offres(cfg: dict, con, ids: list[str]) -> None:
    for oid in ids:
        o = con.execute("SELECT * FROM offres WHERE id=?", (oid,)).fetchone()
        e = con.execute("SELECT * FROM entreprises WHERE cle=?", (o["cle_entreprise"],)).fetchone()
        if not e["decideur"]:   # entreprise sans SIREN : pas de fiche annuaire
            texte, nomme, source = choisir_decideur(e["effectif_min"], bool(e["est_numerique"]), None)
            db.enregistrer_entreprise(con, e["cle"], {"decideur": texte, "decideur_nomme": int(nomme)})
            e = con.execute("SELECT * FROM entreprises WHERE cle=?", (e["cle"],)).fetchone()
        nb_offres = con.execute("SELECT COUNT(*) n FROM offres WHERE cle_entreprise=?", (e["cle"],)).fetchone()["n"]
        note = noter(cfg, est_offre=True, publiee_le=o["publiee_le"],
                     decideur_nomme=bool(e["decideur_nomme"]), telephone_type=e["telephone_type"],
                     effectif_min=e["effectif_min"], plusieurs_postes=(o["nb_postes"] or 1) > 1 or nb_offres > 1,
                     jeune=_jeune(e["date_creation"]), ca_hausse=bool(e["ca_en_hausse"]),
                     numerique=bool(e["est_numerique"]))
        con.execute("UPDATE offres SET note=? WHERE id=?", (note, oid))
    con.commit()
