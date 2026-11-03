# Coût mensuel estimé

## Configuration actuelle : 0 €

| Élément | Coût | Limite gratuite | Consommation estimée |
|---|---|---|---|
| La bonne alternance (offres + entreprises « susceptibles de recruter ») | 0 € | 60 appels / minute | ~40 à 90 appels par passage |
| Adzuna (clé gratuite) | 0 € | quotas affichés dans votre espace | ~4 appels toutes les 2 h |
| Jooble (clé gratuite) | 0 € | quotas fixés par clé | ~5 appels par heure |
| Annuaire des entreprises | 0 € | 7 appels / seconde | quelques dizaines par heure, quelques milliers le 2 du mois |
| GitHub Actions (dépôt public) | 0 € | illimité | ~1 500 à 2 200 min (≈ 26 jours × 28 passages × 2-3 min + ~40 min pour le module B) |
| GitHub Actions (dépôt privé) | 0 € | 2 000 min / mois | même consommation : risque de dépasser → passer à une veille horaire |
| Gmail (mot de passe d'application) | 0 € | 500 destinataires / jour | quelques dizaines de mails par jour au maximum |
| Google Sheets API | 0 € | 60 requêtes / minute | ~5 par passage |
| Base de données (SQLite dans le cache GitHub) | 0 € | 10 Go de cache | quelques dizaines de Mo |

En dépôt privé, pour rester sous 2 000 minutes : remplacer `7,37 5-19 * * 1-6`
par `7 5-19 * * 1-6` dans `.github/workflows/radar.yml` (une veille par heure,
~1 100 min/mois ; le récap de 13h30 partira alors vers 14h).

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
pour l'instant. Adzuna et Jooble suffisent pour couvrir une grande partie des
annonces des autres sites d'emploi.
