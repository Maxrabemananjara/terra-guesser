# Terra Guesser
Défis Datable — équipe MEE. Jeu pédagogique de déduction géographique.

## Prototype cartographique (étape 7)
- 115 ensembles paysagers, 31 filtres et 31 calques réels issus du mapping V2.
- Les calques d'observation sont indépendants du moteur de déduction.
- Moteur ET : absence constatée = élimination ; donnée inconnue = incertitude.
- Carte Folium, sélection spatiale sur les contours originaux.
- Quatre emplacements photographiques réservés. Banque photo, équipes, score et classement à venir.

## Lancer
```bash
pip install -r requirements.txt
streamlit run app.py
```
Importer le ZIP cartographique V3 depuis l'interface ou décompresser son dossier data/ à la racine. Conserver le paquet V2 comme source complète. Le paquet V3 est dérivé pour l'affichage (75 m), et ne remplace pas les données originales. Aucun fichier source n'est simplifié pour le calcul de déduction.

Tests : `python -m unittest tests.test_interface_data tests.test_thematic_layers` avec TERRA_DATA_ZIP pointant vers le ZIP V3 ou les données décompressées.

Sources : DatARA / DREAL Auvergne-Rhône-Alpes, CORINE Land Cover 2018.
