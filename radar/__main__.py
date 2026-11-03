"""Point d'entrée : python -m radar <commande>

Commandes :
  heure              passage horaire (7h-20h, lun-sam) : nouvelles offres, alertes 🔥,
                     et récap du matin au premier passage à partir de 8h
  test-offres        TEST : cherche les offres maintenant et envoie tout de suite un mail
  rafraichir-froid   reconstruit la base du module B (toutes les villes, ou --ville X)
  test-froid         TEST : module B sur une seule ville (--ville Lyon) + mail d'appels à froid
  recap              envoie le récap du matin maintenant

Option : --force  (ignore les horaires pour la commande "heure")
"""
import argparse
import sys
import traceback

from . import db, envois, module_a, module_b, suivi
from . import sheet as gsheet
from .config import charger_config, maintenant


def _ouvrir_sheet(con):
    try:
        sh = gsheet.ouvrir()
        if sh is None:
            print("ℹ️  Google Sheet non configuré : on continue sans.")
        return sh
    except Exception as e:
        db.journaliser(con, "Google Sheet", f"ouverture impossible : {e}")
        return None


def _collecter(cfg, con, sh) -> list[str]:
    """Synchronise les statuts puis récupère les offres. Une panne n'arrête pas tout."""
    try:
        suivi.synchroniser(con, sh)
    except Exception as e:
        db.journaliser(con, "Google Sheet", f"lecture des statuts : {e}")
    amorcage = db.get_meta(con, "amorce") is None
    try:
        nouvelles = module_a.collecter(cfg, con, amorcage)
    except Exception as e:
        db.journaliser(con, "La bonne alternance", str(e))
        traceback.print_exc()
        nouvelles = []
    else:
        db.set_meta(con, "amorce", maintenant().isoformat())
    return nouvelles


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar")
    p.add_argument("commande", choices=["heure", "test-offres", "rafraichir-froid", "test-froid", "recap"])
    p.add_argument("--ville", default=None)
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    cfg = charger_config()
    con = db.connexion()
    h = cfg["horaires"]
    now = maintenant()

    if args.commande == "heure":
        dans_creneau = now.weekday() in h["jours"] and h["heure_debut"] <= now.hour <= h["heure_fin"]
        if not (dans_creneau or args.force):
            print(f"⏸️  {now:%A %H:%M} (Paris) : hors des horaires, rien à faire.")
            return 0
        sh = _ouvrir_sheet(con)
        nouvelles = _collecter(cfg, con, sh)
        n = envois.alertes(cfg, con, sh, nouvelles)
        print(f"🔥 {n} alerte(s) envoyée(s).")
        if now.hour >= h["heure_recap"] and db.get_meta(con, "dernier_recap") != now.date().isoformat():
            o, f = envois.recap(cfg, con, sh)
            db.set_meta(con, "dernier_recap", now.date().isoformat())
            print(f"📬 Récap envoyé : {o} offres, {f} appels à froid.")

    elif args.commande == "test-offres":
        sh = _ouvrir_sheet(con)
        _collecter(cfg, con, sh)
        o, _ = envois.recap(cfg, con, sh, test=True, avec_froid=False)
        print(f"📬 Mail de test envoyé : {o} offres.")

    elif args.commande == "rafraichir-froid":
        sh = _ouvrir_sheet(con)
        suivi.synchroniser(con, sh) if sh else None
        n = module_b.rafraichir(cfg, con, args.ville)
        db.set_meta(con, "dernier_rafraichissement_b", now.isoformat())
        print(f"✅ Module B : {n} entreprises.")

    elif args.commande == "test-froid":
        ville = args.ville or "Lyon"
        sh = _ouvrir_sheet(con)
        suivi.synchroniser(con, sh) if sh else None
        n = module_b.rafraichir(cfg, con, ville)
        _, f = envois.recap(cfg, con, sh, test=True, ville=ville)
        print(f"✅ Test module B ({ville}) : {n} entreprises, {f} dans la liste d'appels.")

    elif args.commande == "recap":
        sh = _ouvrir_sheet(con)
        suivi.synchroniser(con, sh) if sh else None
        envois.recap(cfg, con, sh)
        db.set_meta(con, "dernier_recap", now.date().isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())
