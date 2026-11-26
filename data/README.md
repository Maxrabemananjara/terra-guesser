# Données Terra Guesser

Décompresser le paquet de données préparé dans la racine du dépôt, en conservant le dossier `data/`.

- raw/ : quatre CSV originaux DatARA.
- geographic/ : GeoJSON gzip, EPSG:2154. CLC réparti par famille thématique, sans suppression ni simplification.
- processed/ : matrice 115 × 33, dictionnaire CLC, points GPS et résultats de validation des filtres.
- audit/ : résultats de contrôle et anomalies à prendre en compte.
- photos/ : banque photographique, à intégrer après contrôle des droits.
- manifest.json : empreintes SHA-256 et inventaire des fichiers.

Pour contrôler les fichiers après import : `python scripts/verify_data.py`.
Les géométries doivent être reprojetées vers EPSG:4326 pour un affichage web, sans modifier les fichiers sources.
