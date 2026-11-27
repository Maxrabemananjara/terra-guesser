# Terra Guesser
Défis Datable — équipe MEE. Jeu pédagogique de déduction géographique.

## Prototype cartographique (étape 6)
- 115 ensembles paysagers et 31 filtres pédagogiques V2.
- Moteur ET : absence constatée = élimination ; donnée inconnue = incertitude.
- Carte Folium, sélection spatiale sur les contours originaux.
- Quatre emplacements photographiques réservés. Calques détaillés CLC, banque photo, équipes, score et classement à venir.

## Lancer
```bash
pip install -r requirements.txt
streamlit run app.py
```
Décompresser le ZIP de données V2 à la racine pour ajouter le dossier data/ ou importer le ZIP V2 depuis l'interface.

Tests : `python -m unittest tests.test_interface_data` (données V2 présentes), ou définir TERRA_DATA_ZIP vers le ZIP V2.
Les géométries sources sont conservées. La simplification de 75 m concerne seulement l'affichage web.
Sources : DatARA / DREAL Auvergne-Rhône-Alpes, CORINE Land Cover 2018.
