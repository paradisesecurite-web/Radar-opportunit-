"""Construction des lignes du tableau et des mails HTML (lisibles sur téléphone).

Une ligne = une entreprise. Colonnes, dans l'ordre demandé :
Note /10 | Type | Entreprise | Ville | Poste recherché | Niveau | Lien |
Date de publication | Décideur et fonction | Numéro et son type | E-mail pro |
Effectif | Secteur | Source
(+ dans le Google Sheet : Statut | Vu ✓ | Notes | ID)
"""
import html
from datetime import datetime

from .config import PARIS

COLONNES = ["Note /10", "Type", "Entreprise", "Ville", "Poste recherché", "Niveau", "Lien",
            "Date de publication", "Décideur et fonction", "Numéro et son type", "E-mail pro",
            "Effectif", "Secteur", "Source"]
COLONNES_SUIVI = ["Statut", "Vu ✓", "Notes", "ID"]


def _date_fr(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if d.tzinfo:
            d = d.astimezone(PARIS)
        return d.strftime("%d/%m/%Y %Hh%M") if (d.hour or d.minute) else d.strftime("%d/%m/%Y")
    except ValueError:
        return iso[:10]


def _numero(ent) -> str:
    if not ent["telephone"]:
        return ""
    return f"{ent['telephone']} ({ent['telephone_type'] or 'standard'})"


def ligne_offre(ent, offre, ex_froid: bool = False) -> dict:
    """Ligne du tableau pour une offre (ent et offre sont des lignes SQLite)."""
    sources = [offre["partenaire"] or "La bonne alternance"]
    if offre["via_ecole"]:
        sources.append("via une autre école")
    if ent["decideur_source"]:
        sources.append(f"décideur : {ent['decideur_source']}")
    if ent["telephone_source"]:
        sources.append(f"numéro : {ent['telephone_source']}")
    return {
        "Note /10": offre["note"],
        "Type": "Offre (ex-froid)" if ex_froid else "Offre",
        "Entreprise": ent["nom"],
        "Ville": offre["ville"] or ent["ville"] or "",
        "Poste recherché": offre["titre"] + (f" ({offre['nb_postes']} postes)" if (offre["nb_postes"] or 1) > 1 else "")
                           + (f" [{offre['type_offre']}]" if offre["type_offre"] and offre["type_offre"] != "Alternance" else ""),
        "Niveau": offre["niveau"] or "",
        "Lien": offre["lien"] or ent["lien"] or "",
        "Date de publication": _date_fr(offre["publiee_le"]),
        "Décideur et fonction": ent["decideur"] or "",
        "Numéro et son type": _numero(ent),
        "E-mail pro": ent["email"] or "",
        "Effectif": ent["effectif_libelle"] or "",
        "Secteur": ent["secteur"] or "",
        "Source": " ; ".join(sources),
        "ID": ent["cle"],
        "via_ecole": bool(offre["via_ecole"]),
    }


def ligne_froid(ent) -> dict:
    """Ligne du tableau pour une entreprise du module B (sans offre)."""
    signal = "susceptible de recruter (La bonne alternance)" if ent["lba_susceptible"] else "profil IT"
    sources = ["Annuaire des entreprises", signal]
    if ent["decideur_source"]:
        sources.append(f"décideur : {ent['decideur_source']}")
    return {
        "Note /10": ent["note_froid"],
        "Type": "À froid",
        "Entreprise": ent["nom"],
        "Ville": ent["ville"] or ent["metropole"] or "",
        "Poste recherché": "Alternant IT (aucune offre publiée)",
        "Niveau": "Bac+2 à Bac+5",
        "Lien": ent["lien"] or ent["site_web"] or "",
        "Date de publication": "",
        "Décideur et fonction": ent["decideur"] or "",
        "Numéro et son type": _numero(ent),
        "E-mail pro": ent["email"] or "",
        "Effectif": ent["effectif_libelle"] or "",
        "Secteur": ent["secteur"] or "",
        "Source": " ; ".join(sources),
        "ID": ent["cle"],
        "via_ecole": False,
    }


# ---------------------------------------------------------------------------
# Mails HTML : une "carte" par entreprise, plus lisible qu'un tableau large
# sur téléphone. Note, entreprise, lien et numéro sont en tête de carte.
# ---------------------------------------------------------------------------

def _couleur(note: int) -> str:
    return "#d93025" if note >= 8 else ("#e8710a" if note >= 5 else "#5f6368")


def carte(l: dict) -> str:
    e = html.escape
    lien = e(l["Lien"])
    numero = e(l["Numéro et son type"]) or "<i>pas de numéro</i>"
    tel = "".join(c for c in l["Numéro et son type"].split("(")[0] if c.isdigit() or c == "+")
    if tel:
        numero = f'<a href="tel:{tel}" style="color:#1a73e8">{numero}</a>'
    details = " · ".join(x for x in [e(l["Poste recherché"]), e(l["Niveau"]), e(l["Ville"])] if x)
    infos = " · ".join(x for x in [e(l["Décideur et fonction"]), e(l["Effectif"] and l["Effectif"] + " sal."),
                                   e(l["Secteur"])] if x)
    pub = f"Publiée le {e(l['Date de publication'])} · " if l["Date de publication"] else ""
    badge = ' <span style="background:#fce8e6;color:#c5221f;font-size:11px;padding:1px 5px;border-radius:4px">via une autre école</span>' if l.get("via_ecole") else ""
    return f"""
<div style="border:1px solid #dadce0;border-radius:8px;padding:10px 12px;margin:0 0 10px 0">
  <div style="font-size:16px"><b style="color:{_couleur(l['Note /10'])}">{l['Note /10']}/10</b> ·
    <a href="{lien}" style="color:#1a73e8;font-weight:bold">{e(l['Entreprise'])}</a>{badge}</div>
  <div style="font-size:15px;margin-top:4px">📞 {numero}</div>
  <div style="font-size:13px;color:#3c4043;margin-top:4px">{details}</div>
  <div style="font-size:12px;color:#5f6368;margin-top:2px">{infos}</div>
  <div style="font-size:11px;color:#80868b;margin-top:2px">{pub}{e(l['Type'])} · Source : {e(l['Source'])}</div>
</div>"""


def page(titre: str, sections: list[tuple[str, list[dict]]], pied: str = "") -> str:
    corps = f'<h2 style="font-size:18px;margin:0 0 12px 0">{html.escape(titre)}</h2>'
    for nom, lignes in sections:
        corps += f'<h3 style="font-size:16px;margin:16px 0 8px 0">{html.escape(nom)} ({len(lignes)})</h3>'
        corps += "".join(carte(l) for l in lignes) or "<p><i>Rien de nouveau.</i></p>"
    return f"""<!doctype html><html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;padding:8px">
{corps}{pied}
<p style="font-size:11px;color:#80868b;margin-top:20px">Radar alternance IT · données professionnelles publiques,
source indiquée sur chaque ligne. Suivi des statuts dans le Google Sheet.</p></body></html>"""
