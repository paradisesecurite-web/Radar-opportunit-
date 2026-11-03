"""Départements français regroupés par région.

La bonne alternance renvoie au plus 150 offres par source et par appel.
On interroge donc la France région par région ; si une région dépasse
la limite, on la redécoupe département par département.
"""

REGIONS = {
    "Île-de-France": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "Auvergne-Rhône-Alpes": ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"],
    "Hauts-de-France": ["02", "59", "60", "62", "80"],
    "Provence-Alpes-Côte d'Azur": ["04", "05", "06", "13", "83", "84"],
    "Occitanie": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
    "Nouvelle-Aquitaine": ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"],
    "Grand Est": ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"],
    "Pays de la Loire": ["44", "49", "53", "72", "85"],
    "Bretagne": ["22", "29", "35", "56"],
    "Normandie": ["14", "27", "50", "61", "76"],
    "Bourgogne-Franche-Comté": ["21", "25", "39", "58", "70", "71", "89", "90"],
    "Centre-Val de Loire": ["18", "28", "36", "37", "41", "45"],
    "Corse": ["2A", "2B"],
    "Outre-mer": ["971", "972", "973", "974", "976"],
}

TOUS_DEPARTEMENTS = [d for ds in REGIONS.values() for d in ds]

# Tranches d'effectif INSEE : code -> (libellé, effectif minimum)
TRANCHES = {
    "NN": ("Sans salarié", 0), "00": ("0 salarié", 0),
    "01": ("1 à 2", 1), "02": ("3 à 5", 3), "03": ("6 à 9", 6),
    "11": ("10 à 19", 10), "12": ("20 à 49", 20), "21": ("50 à 99", 50),
    "22": ("100 à 199", 100), "31": ("200 à 249", 200), "32": ("250 à 499", 250),
    "41": ("500 à 999", 500), "42": ("1 000 à 1 999", 1000), "51": ("2 000 à 4 999", 2000),
    "52": ("5 000 à 9 999", 5000), "53": ("10 000 et +", 10000),
}
ORDRE_TRANCHES = ["01", "02", "03", "11", "12", "21", "22", "31", "32", "41", "42", "51", "52", "53"]


def tranches_a_partir_de(code_min: str) -> list[str]:
    """Liste des tranches d'effectif à partir d'un code (ex. "21" -> 50 salariés et +)."""
    return ORDRE_TRANCHES[ORDRE_TRANCHES.index(code_min):]
