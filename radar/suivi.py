"""Synchronisation des statuts entre le Google Sheet et la base locale.

Le Sheet fait foi : à chaque lancement on relit les statuts (Appelé, Signé...),
la liste "Ne pas recontacter", et ce qui a déjà été envoyé (utile si la base
locale a été perdue : rien ne sera renvoyé en double).
"""
from . import db
from . import sheet as gsheet


def synchroniser(con, sh) -> None:
    if sh is None:
        return
    statuts, offres_envoyees, froids_envoyes, opposition = gsheet.lire_suivi(sh)
    maintenant = db.maintenant_iso()
    for cle, statut in statuts.items():
        con.execute("UPDATE entreprises SET statut=? WHERE cle=?", (statut, cle))
    for cle in offres_envoyees:
        con.execute("UPDATE entreprises SET envoye_offre_le=COALESCE(envoye_offre_le, ?) WHERE cle=?",
                    (maintenant, cle))
        con.execute("INSERT OR IGNORE INTO meta VALUES (?, ?)", (f"envoye_offre:{cle}", maintenant))
    for cle in froids_envoyes:
        con.execute("UPDATE entreprises SET envoye_froid_le=COALESCE(envoye_froid_le, ?) WHERE cle=?",
                    (maintenant, cle))
        con.execute("INSERT OR IGNORE INTO meta VALUES (?, ?)", (f"envoye_froid:{cle}", maintenant))
    # RGPD : "Ne pas recontacter" (SIREN ou nom d'entreprise)
    for valeur in opposition:
        con.execute("INSERT OR IGNORE INTO opposition VALUES (?)", (valeur,))
        for r in con.execute("SELECT cle FROM entreprises WHERE siren=? OR lower(nom)=?", (valeur, valeur)):
            con.execute("INSERT OR IGNORE INTO opposition VALUES (?)", (r["cle"],))
    con.commit()
    print(f"🔄 Sheet relu : {len(statuts)} statuts, {len(opposition)} oppositions.")


def deja_envoye(con, cle: str, type_envoi: str) -> bool:
    """type_envoi = "offre" ou "froid". Vérifie aussi la trace gardée si l'entreprise
    n'était pas encore dans la base locale au moment de la synchronisation."""
    col = "envoye_offre_le" if type_envoi == "offre" else "envoye_froid_le"
    r = con.execute(f"SELECT {col} FROM entreprises WHERE cle=?", (cle,)).fetchone()
    if r and r[col]:
        return True
    return db.get_meta(con, f"envoye_{type_envoi}:{cle}") is not None
