# Terra Guesser
Défis Datable — équipe MEE. Jeu pédagogique de déduction géographique.

## Prototype (étape 9)
115 ensembles, 31 calques et filtres, 2 manches de démonstration avec une photo chacune, validation et correction géographique.
Les photos de démonstration ne sont pas publiées dans le dépôt. Leur identité originale et les droits de diffusion ne sont pas validés. Le mode normal exige quatre photos distinctes, identifiées et autorisées par manche.

## Lancer
```bash
pip install -r requirements.txt
streamlit run app.py
```
Importer le ZIP Terra Guesser V4 depuis l'interface ou décompresser les données autorisées à la racine. Conserver le V2 comme source intégrale. Les contours d'affichage sont simplifiés (75 m) ; les réponses sont validées sur les contours originaux. Ne pas diffuser les photos de démonstration sans autorisation.

Tests : définir TERRA_DATA_ZIP vers le ZIP V4, puis `python -m unittest tests.test_interface_data tests.test_thematic_layers tests.test_rounds`.
Le classement partagé reste à développer. Sources : DatARA / DREAL Auvergne-Rhône-Alpes, CORINE Land Cover 2018 et CAUE 73.

## Parties collectives
L’enseignant crée une partie, communique le code à six caractères, puis lance avec au moins deux équipes. Les équipes de 4 à 5 élèves rejoignent avec un pseudonyme. Chaque équipe conserve sa clé personnelle de reprise. L’enseignant révèle après toutes les réponses et déclenche la manche suivante. Actualisation manuelle par bouton. Toutes les sessions doivent utiliser les mêmes données V4 et la même instance de l'application. SQLite stocke les réponses transactionnellement, dans .terra/parties.sqlite par défaut (TERRA_PARTIES_DB configurable). Le stockage local peut être éphémère en hébergement cloud ; migration vers PostgreSQL prévue avant déploiement durable. Ne pas publier les photos non autorisées. Tests : python -m unittest tests.test_parties avec TERRA_DATA_ZIP.
