# Guide pas à pas – Radar alternance IT

Ce guide part de zéro. Compte environ **45 minutes** la première fois.
Tout est **gratuit**.

Ce que fait l'outil, en bref :
- **toutes les heures (7h-20h, lundi-samedi)**, il cherche les nouvelles offres
  d'alternance IT dans toute la France et envoie un mail 🔥 dès qu'une
  entreprise est notée 8/10 ou plus ;
- **chaque matin vers 8h**, il envoie un récap : les offres notées 5+ et une
  liste de 40 entreprises à appeler « à froid » ;
- **tout est rangé dans un Google Sheet** où Aurélien coche ce qu'il a vu
  et note le statut de chaque entreprise.

---

## Étape 0 – Mettre le dépôt GitHub en privé (important)

Le dépôt est **public** aujourd'hui. L'outil n'y écrit aucune donnée
personnelle, mais un dépôt privé est plus sûr (les journaux d'exécution
deviennent privés aussi).

1. Ouvrez le dépôt sur github.com → **Settings** (Paramètres).
2. Tout en bas, « Danger Zone » → **Change visibility** → **Make private**.

Un dépôt privé dispose de 2 000 minutes gratuites par mois de lancements
automatiques ; l'outil en utilise environ 800 à 1 300 (voir `docs/COUTS.md`).

## Étape 1 – Vérifier la branche principale

Les lancements automatiques de GitHub ne tournent que sur la branche
principale du dépôt. Aujourd'hui le code est sur l'unique branche, qui est
déjà la branche principale : **rien à faire**. Si vous créez plus tard une
branche `main`, pensez à y fusionner le code (bouton « Compare & pull
request » → « Merge pull request »).

## Étape 2 – La clé La bonne alternance (gratuite)

1. Allez sur https://api.apprentissage.beta.gouv.fr
2. Cliquez sur **Se connecter** / **Créer un compte**, saisissez votre e-mail.
3. Cliquez sur le lien reçu par mail.
4. Dans votre espace, **générez un jeton** (token) et copiez-le.
5. ⚠️ Le jeton est valable **1 an** : mettez un rappel dans votre agenda
   pour le régénérer dans 11 mois. S'il expire, le récap du matin l'indiquera.

## Étape 3 – Le mot de passe d'application Gmail

Les mails partent de **paradise.securite@gmail.com** (le compte qui envoie).

1. Connectez-vous à ce compte Gmail.
2. Activez la **validation en deux étapes** : https://myaccount.google.com/signinoptions/twosv
3. Allez sur https://myaccount.google.com/apppasswords
4. Nom de l'application : `Radar alternance` → **Créer**.
5. Copiez le mot de passe de **16 lettres** affiché (il ne sera plus montré).

## Étape 4 – Le Google Sheet

### 4a. Créer un « compte de service » Google (le robot qui écrit dans le Sheet)

1. Allez sur https://console.cloud.google.com (avec le compte Gmail).
2. En haut, **Sélectionner un projet** → **Nouveau projet** → nom `radar-alternance` → **Créer**.
3. Menu ☰ → **API et services** → **Bibliothèque** → cherchez **Google Sheets API** → **Activer**.
4. Menu ☰ → **API et services** → **Identifiants** → **Créer des identifiants** →
   **Compte de service** → nom `radar` → **Créer et continuer** → **OK**.
5. Cliquez sur le compte de service créé → onglet **Clés** → **Ajouter une clé** →
   **Créer une clé** → **JSON** → un fichier se télécharge.
6. Notez l'adresse du compte de service (du type `radar@radar-alternance.iam.gserviceaccount.com`).

### 4b. Créer le Sheet

1. Sur https://sheets.google.com, créez une feuille vide nommée **Radar alternance IT**.
2. **Partager** → ajoutez l'adresse du compte de service (étape 4a.6) en **Éditeur**.
3. **Partager** → ajoutez **aurelien.wagner@iscod.fr** en **Éditeur**.
   (Si cette adresse n'est pas un compte Google, Aurélien pourra créer un compte
   Google gratuit avec cette même adresse en suivant le lien d'invitation.)
4. Copiez l'**identifiant** du Sheet dans son adresse :
   `https://docs.google.com/spreadsheets/d/`**`CET_IDENTIFIANT`**`/edit`

L'outil crée lui-même les onglets, la liste déroulante « Statut » et les
cases à cocher au premier lancement.

## Étape 5 – Enregistrer les secrets dans GitHub

Les clés ne sont **jamais** écrites dans le code : elles sont rangées dans les
« Secrets » du dépôt.

Sur GitHub : **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**. Créez ces 6 secrets (nom exact à gauche) :

| Nom du secret | Valeur |
|---|---|
| `LBA_API_TOKEN` | le jeton La bonne alternance (étape 2) |
| `GMAIL_ADRESSE` | `paradise.securite@gmail.com` (l'adresse qui envoie, à vérifier) |
| `GMAIL_MOT_DE_PASSE` | le mot de passe de 16 lettres (étape 3) |
| `DESTINATAIRES` | `aurelien.wagner@iscod.fr` (plusieurs adresses : séparées par des virgules) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ouvrez le fichier JSON téléchargé (étape 4a.5) avec le Bloc-notes, copiez **tout** son contenu |
| `GOOGLE_SHEET_ID` | l'identifiant du Sheet (étape 4b.4) |

## Étape 6 – Les tests

Sur GitHub : onglet **Actions** → (si demandé, cliquez sur « I understand my
workflows, go ahead and enable them ») → **Radar alternance IT** à gauche →
bouton **Run workflow** à droite.

1. **Test des offres** : choisissez `test-offres` → **Run workflow**.
   En 2-4 minutes, Aurélien reçoit un mail « TEST – Récap du … » avec les
   offres, et l'onglet **Offres** du Sheet se remplit.
2. **Test du module B sur une ville** : choisissez `test-froid`, ville `Lyon`
   → **Run workflow**. En 5-15 minutes, il reçoit la « Liste d'appels à
   froid » de Lyon et l'onglet **Appels à froid** se remplit.
3. **Base à froid complète** : choisissez `rafraichir-froid` et **videz** le
   champ ville → **Run workflow** (30 à 60 minutes). Ensuite, elle se
   rafraîchit seule le 2 de chaque mois.

Pour suivre un lancement : cliquez dessus dans l'onglet Actions. Une coche
verte = tout va bien ; une croix rouge = ouvrez-le pour lire le message.

C'est tout : les lancements automatiques démarrent seuls.

---

## Utilisation au quotidien (pour Aurélien)

- **Mail 🔥** : `🔥 9/10 – Entreprise – poste – ville`. Le nom de l'entreprise
  est le lien vers l'annonce ; le numéro est cliquable pour appeler.
- **Récap du matin** : `Récap du mardi 04/11 – X offres – Y appels à froid`.
- **Google Sheet** (appli Google Sheets sur téléphone) :
  - colonne **Statut** : Nouveau / Appelé / À rappeler / Pas intéressé / Signé ;
  - colonne **Vu ✓** : case à cocher pour se repérer ;
  - colonne **Notes** : libre ;
  - « **Pas intéressé** » ou « **Signé** » : l'entreprise ne revient plus jamais ;
  - utilisez le filtre (icône entonnoir) pour trier par note, ville, type…
- **Onglet « Ne pas recontacter »** (RGPD) : si une personne demande à ne plus
  être contactée, ajoutez le SIREN ou le nom de l'entreprise en colonne A.
- Une entreprise déjà envoyée n'est **jamais renvoyée**. Exception : une
  entreprise de la liste à froid qui publie une offre déclenche un mail
  « 🔄 Passée en offre ».
- Quand le contact manque, Aurélien le complète avec Lusha.

## Modifier les réglages

Tous les réglages sont dans **`config.yaml`** (sur GitHub : cliquez sur le
fichier → icône crayon → modifiez → **Commit changes**) :
- villes du module B, ou `toute_la_france: true` ;
- codes NAF ciblés (ajouter / retirer une ligne) ;
- codes métiers ROME ;
- poids de la note, seuil d'alerte (8), seuil du récap (5) ;
- nombre d'appels à froid (40), horaires.

## Dépannage

| Problème | Solution |
|---|---|
| Aucun mail | Onglet Actions : le lancement est-il vert ? Vérifiez les secrets Gmail (étapes 3 et 5). Regardez dans les spams. |
| « Jeton La bonne alternance refusé » dans le récap | Le jeton a expiré (1 an) : refaites l'étape 2 et mettez à jour le secret `LBA_API_TOKEN`. |
| Section « ⚠️ Sources en panne » dans le récap | Une source n'a pas répondu ; l'outil a continué avec les autres. Si ça dure plusieurs jours, regardez l'onglet Journal du Sheet. |
| Liste d'appels à froid vide | La base à froid n'est pas encore construite, ou a été perdue : relancez `rafraichir-froid` (étape 6.3). |
| Les lancements automatiques se sont arrêtés | GitHub les met en pause après 60 jours sans modification sur un dépôt public : onglet Actions → **Enable workflow**. |
| Janvier 2027 | L'Insee passe à la nouvelle nomenclature NAF 2025 : il faudra peut-être mettre à jour les codes NAF de `config.yaml`. |

## Données personnelles (RGPD)

- Uniquement des **coordonnées professionnelles** issues de sources publiques
  ou de l'annonce elle-même ; la source de chaque donnée est indiquée dans la
  colonne « Source ».
- Les dirigeants viennent du Registre national des entreprises (public) ; les
  entrepreneurs qui ont demandé à ne pas être diffusés sont exclus.
- Liste d'opposition : onglet « Ne pas recontacter ».
- Aucune donnée personnelle n'est écrite dans le code ni dans les journaux.
- L'outil n'utilise **que des API officielles**, aucun aspirateur de sites.
- Conditions d'utilisation de La bonne alternance :
  https://api.apprentissage.beta.gouv.fr/fr/cgu. L'usage (placer des
  alternants) va dans le sens du service.
