"""MODULE B – Prospection à froid.

Rafraîchi une fois par mois (et à la demande pour une seule ville) :
1. Liste les entreprises actives des codes NAF ciblés dans chaque métropole
   (annuaire des entreprises, gratuit).
2. Croise avec La bonne alternance : les entreprises que leur algorithme juge
   "susceptibles de recruter" un alternant sont marquées (signal moyen).
3. Calcule la note "à froid" de chaque entreprise.
"""
from . import db
from .contacts import choisir_decideur, formater_numero, type_numero
from .geo import TOUS_DEPARTEMENTS, TRANCHES, tranches_entre
from .module_a import cle_entreprise, est_numerique
from .scoring import noter
from .sources import annuaire, lba


def _zones(cfg: dict, ville: str | None) -> list[tuple[str, dict]]:
    mb = cfg["module_b"]
    if ville:
        trouvees = {k: v for k, v in mb["villes"].items() if k.lower() == ville.lower()}
        if not trouvees:
            raise SystemExit(f"Ville inconnue : {ville}. Villes possibles : {', '.join(mb['villes'])}")
        return list(trouvees.items())
    if mb.get("toute_la_france"):
        return [(f"Dép. {d}", {"departement": d}) for d in TOUS_DEPARTEMENTS]
    return list(mb["villes"].items())


def rafraichir(cfg: dict, con, ville: str | None = None) -> int:
    """Reconstruit la base à froid (toutes les villes, ou une seule). Renvoie le nombre d'entreprises."""
    mb = cfg["module_b"]
    pause = cfg.get("pause_entre_appels_annuaire_s", 0.2)
    total = 0
    for nom_zone, zone in _zones(cfg, ville):
        vues = set()
        familles = [(mb["naf_numerique"], mb["effectif_min_numerique"], mb["effectif_max_numerique"])]
        if mb.get("inclure_hors_numerique"):
            familles.append((mb["naf_hors_numerique"], mb["effectif_min_hors_numerique"],
                             mb["effectif_max_hors_numerique"]))
        for codes, eff_min, eff_max in familles:
            for naf, libelle in codes.items():
                try:
                    for res in annuaire.lister(pause, naf, tranches_entre(eff_min, eff_max),
                                               epci=zone.get("epci"), departement=zone.get("departement")):
                        if _enregistrer(cfg, con, res, nom_zone, libelle):
                            vues.add(res["siren"])
                except Exception as e:
                    db.journaliser(con, "Annuaire des entreprises", f"{nom_zone} / {naf} : {e}")
                con.commit()
        print(f"🏢 {nom_zone} : {len(vues)} entreprises ciblées.")
        total += len(vues)
        if "lat" in zone:
            croiser_lba(cfg, con, nom_zone, zone)
        noter_froid(cfg, con, nom_zone)
    return total


def _enregistrer(cfg, con, res: dict, metropole: str, secteur: str) -> bool:
    f = annuaire.lire_fiche(res)
    if not f["diffusible"] or not f["siren"]:
        return False
    cle = f["siren"]
    if db.est_bloquee(con, cle):
        return False
    num = est_numerique(cfg, f["naf"])
    texte, nomme, source = choisir_decideur(f["effectif_min"], num, f["dirigeant"])
    db.enregistrer_entreprise(con, cle, {
        "siren": cle, "nom": f["nom"], "ville": f["ville"], "code_postal": f["code_postal"],
        "metropole": metropole, "naf": f["naf"], "secteur": secteur,
        "tranche_effectif": f["tranche_effectif"], "effectif_libelle": f["effectif_libelle"],
        "effectif_min": f["effectif_min"], "categorie": f["categorie"], "date_creation": f["date_creation"],
        "ca_en_hausse": f["ca_en_hausse"], "est_numerique": int(num), "decideur": texte,
        "decideur_nomme": int(nomme), "decideur_source": source, "annuaire_ok": 1,
    })
    ligne = con.execute("SELECT lien FROM entreprises WHERE cle=?", (cle,)).fetchone()
    if not ligne["lien"]:
        db.enregistrer_entreprise(con, cle, {"lien": f["lien"]})
    return True


def croiser_lba(cfg: dict, con, nom_zone: str, zone: dict) -> None:
    """Marque les entreprises "susceptibles de recruter" selon La bonne alternance."""
    try:
        _, recruteurs = lba.rechercher_autour(cfg, zone["lat"], zone["lon"], cfg["module_b"]["rayon_lba_km"])
    except Exception as e:
        db.journaliser(con, "La bonne alternance (croisement)", f"{nom_zone} : {e}")
        return
    marquees = 0
    eff_max = TRANCHES[cfg["module_b"]["effectif_max_numerique"]][1]   # ex. "12" -> 20 (tranche 20-49)
    for r in recruteurs:
        e = lba.lire_entreprise(r)
        if e["effectif_min"] is not None and (e["effectif_min"] > eff_max or e["effectif_min"] < 1):
            continue   # hors de la taille ciblée
        cle = cle_entreprise(e)
        if db.est_bloquee(con, cle):
            continue
        existe = con.execute("SELECT telephone FROM entreprises WHERE cle=?", (cle,)).fetchone()
        champs = {"lba_susceptible": 1, "lien": e["lien"], "metropole": nom_zone}
        if not existe:   # entreprise hors des codes NAF ciblés : on l'ajoute quand même (bon signal)
            champs.update({"siren": e["siren"], "nom": e["nom"], "ville": e["ville"],
                           "code_postal": e["code_postal"], "naf": e["naf"], "secteur": e["secteur"],
                           "site_web": e["site_web"], "effectif_libelle": e["effectif_libelle"],
                           "effectif_min": e["effectif_min"]})
        num = formater_numero(e["telephone"])
        if num and not (existe and existe["telephone"]):
            champs.update({"telephone": num, "telephone_type": type_numero(num),
                           "telephone_source": "La bonne alternance"})
        db.enregistrer_entreprise(con, cle, champs)
        marquees += 1
    con.commit()
    print(f"🎯 {nom_zone} : {marquees} entreprises susceptibles de recruter (La bonne alternance).")


def noter_froid(cfg: dict, con, metropole: str | None = None) -> None:
    """Note "à froid" des entreprises sans offre (module B)."""
    sql = "SELECT * FROM entreprises WHERE module='B'"
    params: tuple = ()
    if metropole:
        sql += " AND metropole=?"
        params = (metropole,)
    for e in con.execute(sql, params).fetchall():
        if not e["decideur"]:
            texte, nomme, _ = choisir_decideur(e["effectif_min"], bool(e["est_numerique"]), None)
            con.execute("UPDATE entreprises SET decideur=?, decideur_nomme=? WHERE cle=?",
                        (texte, int(nomme), e["cle"]))
        age = annuaire.age_ans(e["date_creation"])
        note = noter(cfg, est_offre=False, susceptible=bool(e["lba_susceptible"]),
                     decideur_nomme=bool(e["decideur_nomme"]), telephone_type=e["telephone_type"],
                     effectif_min=e["effectif_min"], jeune=age is not None and age < 5,
                     ca_hausse=bool(e["ca_en_hausse"]), numerique=bool(e["est_numerique"]))
        con.execute("UPDATE entreprises SET note_froid=? WHERE cle=?", (note, e["cle"]))
    con.commit()
