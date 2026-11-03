# Radar alternance IT

Outil de prospection pour placer des alternants IT : il repère les entreprises
qui cherchent (ou pourraient chercher) un alternant, les note de 1 à 10 et les
envoie par mail, avec le suivi dans un Google Sheet. 100 % gratuit.

- **Module A – Offres en temps réel** : toutes les 30 min (7h-20h, lun-sam),
  offres d'alternance et de stage IT de toute la France via les API
  La bonne alternance (avec France Travail et ses sites partenaires),
  Adzuna et Jooble. Mail 🔥 immédiat dès 8/10.
- **Module B – Prospection à froid** : entreprises du numérique de 1 à 49
  salariés dans les 6 plus grandes métropoles (API Recherche d'entreprises),
  croisées avec les entreprises « susceptibles de recruter » de
  La bonne alternance. Rafraîchi chaque mois.
- **Récaps à 8h et 13h30** : offres notées 5+ avec le lien de l'annonce ;
  à 8h, en plus, les 20 meilleurs appels à froid.

👉 **Mise en route : [docs/GUIDE.md](docs/GUIDE.md)** · Coûts : [docs/COUTS.md](docs/COUTS.md)
· Réglages : [config.yaml](config.yaml)

## Organisation du code

```
config.yaml              tous les réglages (villes, NAF, ROME, poids de la note…)
radar/__main__.py        commandes : heure, test-offres, test-froid, rafraichir-froid, recap
radar/sources/lba.py     API La bonne alternance
radar/sources/annuaire.py API Recherche d'entreprises
radar/sources/adzuna.py  API Adzuna
radar/sources/jooble.py  API Jooble
radar/module_a.py        collecte et notation des offres
radar/module_b.py        base à froid
radar/scoring.py         note de 1 à 10
radar/contacts.py        choix de l'interlocuteur, type de numéro
radar/envois.py          alertes 🔥 et récap du matin
radar/rapport.py         mise en forme (tableau, mails lisibles sur téléphone)
radar/sheet.py           Google Sheet (statuts, cases à cocher)
radar/suivi.py           relecture des statuts du Sheet
.github/workflows/radar.yml  lancement automatique
```

## En local (facultatif)

```bash
pip install -r requirements.txt pytest
python -m pytest -q                      # tests sans réseau
LBA_API_TOKEN=... python -m radar test-offres   # sans secrets Gmail : le mail est enregistré en apercu_*.html
```
