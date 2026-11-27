# Terra Guesser
Défis Datable — équipe MEE. Jeu pédagogique de déduction géographique.

## Version V5
115 ensembles, 31 calques et filtres, deux manches publiques de quatre photos sous licence libre, validation et correction géographique.
Les photos de démonstration ne sont pas publiées dans le dépôt. Leur identité originale et les droits de diffusion ne sont pas validés. Le mode normal exige quatre photos distinctes, identifiées et autorisées par manche.

## Lancer
```bash
pip install -r requirements.txt
streamlit run app.py
```
Pour une démonstration privée, définir TERRA_ALLOW_DEMO=1 avant le lancement. Importer le ZIP Terra Guesser V4 depuis l'interface ou décompresser les données autorisées à la racine. Conserver le V2 comme source intégrale. Les contours d'affichage sont simplifiés (75 m) ; les réponses sont validées sur les contours originaux. Ne pas diffuser les photos de démonstration sans autorisation.

Tests : définir TERRA_DATA_ZIP vers le ZIP V4, puis `python -m unittest tests.test_interface_data tests.test_thematic_layers tests.test_rounds`.
Sources : DatARA / DREAL Auvergne-Rhône-Alpes, CORINE Land Cover 2018 et CAUE 73.

## Parties collectives
L’enseignant crée une partie, communique le code à six caractères, puis lance avec au moins deux équipes. Les équipes de 4 à 5 élèves rejoignent avec un pseudonyme. Chaque équipe conserve sa clé personnelle de reprise. L’enseignant révèle après toutes les réponses et déclenche la manche suivante. Actualisation manuelle par bouton. Toutes les sessions doivent utiliser les mêmes données et la même instance de l'application. SQLite stocke les réponses transactionnellement, dans .terra/parties.sqlite par défaut (TERRA_PARTIES_DB configurable). Le stockage local peut être éphémère en hébergement cloud ; migration vers PostgreSQL prévue avant déploiement durable. Ne pas publier les photos non autorisées. Tests : python -m unittest tests.test_parties avec TERRA_DATA_ZIP.

## Barème et classement
100 points par bonne réponse, 0 sinon. Aucun bonus de vitesse. Classement cumulé après chaque correction révélée, ex æquo en cas d'égalité (rang 1, 1, 3). Tous les vainqueurs sont affichés à la fin. Export CSV final réservé à l'enseignant dans l'interface. Tests indépendants des données : python -m unittest tests.test_scoring (64 scénarios de trois équipes sur deux manches).

Voir [préparation du déploiement](DEPLOYMENT.md). Le mode démonstration est désactivé par défaut.

## Étape 12 — Responsive
Mise en page verticale jusqu'à 1024 px, grille photo 2 × 2, commandes tactiles, filtres accessibles sur la page, hauteur de carte réglable, sélection alternative par code et classement en cartes. Tests Chromium de référence et test navigateur réel automatisé pour 360, 390, 768, 1024, 1920 px. Le parcours Chromium a passé les cinq tailles et le test collectif à trois sessions. Le serveur peut fournir le paquet de données via TERRA_DATA_ZIP ; aucun import n'est nécessaire pour les joueurs dans ce cas.


## Déploiement gratuit — Streamlit Community Cloud
1. Ajouter à la racine les deux fichiers terra_v5.part1 et terra_v5.part2 du paquet V5 vérifié (ou le ZIP complet avec Git). Ils sont chargés automatiquement et vérifiés par SHA-256 au démarrage. Aucun import côté joueur.
2. Sur https://share.streamlit.io/, connecter GitHub, créer une application depuis Maxrabemananjara/terra-guesser, branche main, fichier app.py. Choisir une URL disponible. Dans les secrets avancés, définir TERRA_TEACHER_SECRET avec une clé personnelle forte, et TERRA_PUBLIC = "1". Ne jamais placer cette clé dans le dépôt.
3. Le stockage SQLite est local à l'instance et peut disparaître après un redémarrage. Export CSV des résultats en fin de partie. Aucun service payant configuré.
