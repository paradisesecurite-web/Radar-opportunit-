# Coût mensuel estimé

## Configuration actuelle : 0 €

| Élément | Coût | Limite gratuite | Consommation estimée |
|---|---|---|---|
| La bonne alternance (offres + entreprises « susceptibles de recruter ») | 0 € | 60 appels / minute | ~40 à 90 appels par passage horaire |
| Annuaire des entreprises | 0 € | 7 appels / seconde | quelques dizaines par heure, quelques milliers le 2 du mois |
| GitHub Actions (dépôt privé) | 0 € | 2 000 min / mois | ~800 à 1 300 min (≈ 26 jours × 14 passages × 2-3 min + ~60 min pour le module B) |
| GitHub Actions (dépôt public) | 0 € | illimité | — |
| Gmail (mot de passe d'application) | 0 € | 500 destinataires / jour | quelques dizaines de mails par jour au maximum |
| Google Sheets API | 0 € | 60 requêtes / minute | ~5 par passage |
| Base de données (SQLite dans le cache GitHub) | 0 € | 10 Go de cache | quelques dizaines de Mo |

Si un jour les 2 000 minutes ne suffisent pas : passer à un lancement toutes
les 2 heures (modifier `5-19` en `5-19/2` dans `.github/workflows/radar.yml`).

## Options payantes possibles plus tard (non installées)

Prix relevés en novembre 2026 sur des sites comparateurs (les pages des
éditeurs n'étaient pas consultables) : **à vérifier avant d'acheter**.

| Option | Apport | Prix indicatif |
|---|---|---|
| TheirStack | annonces LinkedIn / Indeed / sites carrières, stages et CDI juniors IT, parfois le recruteur | gratuit : 200 offres/mois ; 59 $/mois pour 1 500 offres ; 100 $ pour 5 000 |
| Apollo Basic | standard, décideur (DRH, CTO), e-mail pro, page LinkedIn | ~49 $/mois (annuel) à ~59 $/mois (mensuel) par utilisateur |
| Kaspr Business | numéros mobiles (nécessite la page LinkedIn de la personne) | ~79 à 99 €/mois par utilisateur, ~200 numéros/mois ; recharge ~0,21 à 0,36 $ par numéro |

Exemples :
- **Gratuit** (actuel) : 0 €.
- **+ TheirStack 1 500 offres** : ~55 €/mois.
- **+ Apollo Basic** : ~50-55 €/mois de plus.
- **+ Kaspr Business (~200 numéros)** : ~80-100 €/mois de plus, soit
  ~0,40-0,50 € par numéro.

Aurélien utilisant déjà Lusha pour les numéros, ces options ne sont pas utiles
pour l'instant.
