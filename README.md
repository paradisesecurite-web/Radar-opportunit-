# Radar alternance IT

Outil de prospection pour placer des alternants IT : il repère les entreprises
qui cherchent (ou pourraient chercher) un alternant, les note de 1 à 10 et les
envoie par mail, avec le suivi dans un Google Sheet. 100 % gratuit.

- **Module A – Offres en temps réel** : toutes les heures (7h-20h, lun-sam),
  offres d'alternance IT de toute la France via l'API La bonne alternance
  (qui inclut France Travail et des sites partenaires). Mail 🔥 immédiat dès 8/10.
- **Module B – Prospection à froid** : entreprises du numérique et grandes
  entreprises avec service informatique dans les 10 plus grandes métropoles
  (API Recherche d'entreprises), croisées avec les entreprises « susceptibles
  de recruter » de La bonne alternance. Rafraîchi chaque mois.
- **Récap du matin (8h)** : offres notées 5+ et 40 meilleurs appels à froid.

👉 **Mise en route : [docs/GUIDE.md](docs/GUIDE.md)** · Coûts : [docs/COUTS.md](docs/COUTS.md)
· Réglages : [config.yaml](config.yaml)

## Organisation du code

```
config.yaml              tous les réglages (villes, NAF, ROME, poids de la note…)
radar/__main__.py        commandes : heure, test-offres, test-froid, rafraichir-froid, recap
radar/sources/lba.py     API La bonne alternance
radar/sources/annuaire.py API Recherche d'entreprises
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
