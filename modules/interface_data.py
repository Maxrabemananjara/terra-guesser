"""Lecture et filtrage du paquet Terra Guesser V2, sans modification des sources."""
import gzip
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from pyproj import Transformer
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform

MATRIX = 'data/processed/matrice_filtres_application.csv'
ZONES = 'data/geographic/ensembles_paysagers.geojson.gz'


def load_data(root, archive=None):
    root = Path(root)
    if archive is not None:
        with ZipFile(io.BytesIO(archive)) as z:
            matrix_bytes, zone_bytes = z.read(MATRIX), z.read(ZONES)
    else:
        matrix_bytes, zone_bytes = (root / MATRIX).read_bytes(), (root / ZONES).read_bytes()
    matrix = pd.read_csv(io.BytesIO(matrix_bytes), dtype={'code_ensem': str, 'present': str})
    geo = json.loads(gzip.decompress(zone_bytes))
    ids = {str(f['properties']['code_ensem']) for f in geo['features']}
    if len(geo['features']) != 115 or len(ids) != 115 or set(matrix.code_ensem) != ids:
        raise ValueError('Référentiel incomplet : 115 ensembles attendus.')
    if len(matrix) != 3565 or matrix.code_filtre.nunique() != 31 or matrix.duplicated(['code_ensem', 'code_filtre']).any():
        raise ValueError('Matrice incomplète ou dupliquée : 115 × 31 attendus.')
    if not set(matrix.present.dropna()).issubset({'True', 'False'}):
        raise ValueError('Valeur de présence inconnue.')
    if geo.get('crs', {}).get('properties', {}).get('name', '').split(':')[-1] != '2154':
        raise ValueError('Projection source inattendue : EPSG:2154 requis.')
    return matrix, geo


def filter_zones(matrix, selected):
    """ET entre filtres. Une absence non établie ne constitue pas une exclusion."""
    ids = set(matrix.code_ensem)
    if not set(selected).issubset(set(matrix.code_filtre)):
        raise ValueError('Filtre inconnu.')
    subset = matrix[matrix.code_filtre.isin(selected)]
    excluded = set(subset.loc[subset.present.eq('False'), 'code_ensem'])
    uncertain = set(subset.loc[subset.present.isna(), 'code_ensem']) - excluded
    return ids - excluded, uncertain


def web_geometry(geo, tolerance=75):
    """Simplification uniquement pour le rendu web; conserver les sources pour les calculs."""
    project = Transformer.from_crs(2154, 4326, always_xy=True).transform
    features = []
    for feature in geo['features']:
        geom = shape(feature['geometry'])
        simplified = geom.simplify(tolerance, preserve_topology=True)
        if simplified.is_empty or not simplified.is_valid:
            simplified = geom
        display = transform(project, simplified)
        if not display.is_valid:
            display = display.buffer(0)
        if display.is_empty or not display.is_valid:
            raise ValueError('Géométrie web invalide.')
        p = feature['properties']
        features.append({'type': 'Feature', 'geometry': mapping(display),
                         'properties': {'code_ensem': str(p['code_ensem'])}})
    return {'type': 'FeatureCollection', 'features': features}


def zones_at_point(geo, latitude, longitude, compatible):
    project = Transformer.from_crs(4326, 2154, always_xy=True).transform
    point = Point(*project(longitude, latitude))
    return sorted(str(f['properties']['code_ensem']) for f in geo['features']
                  if str(f['properties']['code_ensem']) in compatible and shape(f['geometry']).covers(point))


def make_map(web_geo, compatible, uncertain, selected=None, center=None, zoom=7):
    import folium
    m = folium.Map(location=center or [45.5, 4.7], zoom_start=zoom, tiles='OpenStreetMap')
    def style(f):
        code = f['properties']['code_ensem']
        color = '#263D59' if code == selected else '#D1D5DB' if code not in compatible else '#D6B447' if code in uncertain else '#43875D'
        return {'fillColor': color, 'color': '#555555', 'weight': 1.1,
                'fillOpacity': 0.24 if code not in compatible else 0.52}
    folium.GeoJson(web_geo, name='Ensembles paysagers', style_function=style,
                   highlight_function=lambda f: {'weight': 3},
                   tooltip=folium.GeoJsonTooltip(fields=['code_ensem'], aliases=['Zone :'])).add_to(m)
    return m
