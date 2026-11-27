# Préparation du déploiement
## Démonstration privée locale
Installer Python 3.12, puis pip install -r requirements.txt. Définir TERRA_ALLOW_DEMO=1 dans l'environnement, puis lancer streamlit run app.py. Importer le paquet V4 depuis l'interface (ou décompresser ses données à la racine). Ne pas partager les photographies de démonstration sans autorisation. Le mode collectif nécessite une seule instance et des données identiques dans toutes les sessions.

## Déploiement public : prérequis non satisfaits
- Quatre photographies distinctes et identifiées par manche ; droits de diffusion documentés.
- Contrôle des libellés exacts du Canva, non accessibles sous forme de texte.
- Tests du parcours dans un navigateur et sur plusieurs appareils.
- Stockage durable des parties sur serveur (SQLite sur volume persistant pour une seule instance ; PostgreSQL pour plusieurs instances).
- Authentification des enseignants, contrôle d'accès à l'import de données, supervision et protection des données avant ouverture publique.
- Optimiser et tester les performances lorsque de nombreux calques sont activés.

Ne jamais activer TERRA_ALLOW_DEMO sur un serveur ouvert au public. Aucun fichier photo privé n'est poussé sur GitHub.

## CI
Le workflow teste la compilation, le moteur de notation et la protection contre les commandes périmées, puis le démarrage Streamlit sans données privées. Les tests avec données restent à lancer avec TERRA_DATA_ZIP pointant vers le V4 : python -m unittest tests.test_interface_data tests.test_thematic_layers tests.test_rounds tests.test_parties tests.test_scoring tests.test_release -v.

## Validation responsive et provisionnement
Le workflow inclut un parcours réel sur cinq tailles Chromium avec une fixture strictement synthétique, sans photos privées. Exécuter aussi les tests tactiles et de performances avec les données autorisées avant diffusion. Pour éviter tout import côté joueur, placer le paquet autorisé dans un emplacement serveur et définir TERRA_DATA_ZIP sur son chemin, ou décompresser data/ à la racine. Ce fichier doit être fourni au serveur lors du déploiement, jamais téléchargé par chaque élève.

## Paquet de diffusion et contrôle des accès
La base publique V4 sans les photographies privées doit être transférée au serveur. Deux manches candidates (Aiguebelette, Bourget) de quatre vues distinctes, coordonnées et licences documentées dans assets/photo_candidates.json. Exécuter python -m scripts.prepare_public_data BASE.zip PUBLIC.zip sur une machine connectée. L'outil vérifie les huit coordonnées contre les contours exacts, les licences via l'API Commons, les empreintes des images et le catalogue complet. Il échoue si une vérification échoue ; le fichier n'est pas produit avant validation. Les crédits apparaissent dans la correction. Pour diffusion définir TERRA_PUBLIC=1, TERRA_DATA_ZIP sur PUBLIC.zip et TERRA_TEACHER_SECRET sur un secret fort, et TERRA_PARTIES_DB sur un volume persistant. Aucun import de données côté joueur dans ce mode. Ne pas diffuser le V4 privé. Les vues représentent un ensemble paysager, pas un point GPS unique.
