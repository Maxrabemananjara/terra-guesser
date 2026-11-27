"""Calques d'observation indépendants de la déduction."""
import gzip
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile
import folium

CATALOG = 'data/layers/catalog.json'


def read_bytes(root, archive, path):
    if archive is not None:
        with ZipFile(io.BytesIO(archive)) as z:
            return z.read(path)
    return (Path(root) / path).read_bytes()


def load_catalog(root, archive, matrix):
    c = json.loads(read_bytes(root, archive, CATALOG))
    if c['version'] != 3 or c['crs'] != 'EPSG:4326':
        raise ValueError('Version ou projection des calques incorrecte.')
    rows = matrix[['code_filtre', 'filtre_canva', 'couleur_hex']].drop_duplicates().set_index('code_filtre')
    if len(rows) != 31 or set(c['layers']) != set(rows.index):
        raise ValueError('Catalogue incomplet ou différent de la matrice.')
    for code, entry in c['layers'].items():
        if entry['path'] != f'data/layers/{code}.geojson.gz' or entry['count'] <= 0 or entry['label'] != rows.loc[code, 'filtre_canva'] or entry['color'] != rows.loc[code, 'couleur_hex']:
            raise ValueError(f'Mapping incorrect : {code}')
    return c['layers']


def load_layer(root, archive, code, entry):
    b = read_bytes(root, archive, entry['path'])
    if len(b) != entry['bytes'] or hashlib.sha256(b).hexdigest() != entry['sha256']:
        raise ValueError(f'Intégrité incorrecte : {code}')
    data = json.loads(gzip.decompress(b))
    fs = data['features']
    if data['type'] != 'FeatureCollection' or len(fs) != entry['count'] or any(f['properties']['code_filtre'] != code for f in fs):
        raise ValueError(f'Calque incohérent : {code}')
    return data


def make_thematic_map(web_geo, compatible, uncertain, selected, layers, center=None, zoom=7):
    m = folium.Map(location=center or [45.5, 4.7], zoom_start=zoom, tiles='OpenStreetMap', prefer_canvas=True)
    for code, entry, data in sorted(layers, key=lambda item: (0 if item[0].startswith('grand_') else 1 if item[0].startswith('typo_') else 2, item[0])):
        color = entry['color']
        folium.GeoJson(data, name=entry['label'], style_function=lambda f, color=color: {'fillColor': color, 'color': color, 'weight': 0.35, 'fillOpacity': 0.58}, interactive=False).add_to(m)
    def style(f):
        code = f['properties']['code_ensem']
        chosen = code == selected
        excluded = code not in compatible
        unsure = code in uncertain
        color = '#263D59' if chosen else '#7C8189' if excluded else '#B28316' if unsure else '#43875D'
        fill = '#D1D5DB' if excluded else color
        opacity = 0.45 if excluded else 0.10 if layers else 0.48
        return {'fillColor': fill, 'color': color, 'weight': 3 if chosen else 1.4, 'dashArray': '5 4' if unsure else None, 'fillOpacity': opacity}
    folium.GeoJson(web_geo, name='Zones de déduction', control=False, style_function=style, highlight_function=lambda f: {'weight': 3}, tooltip=folium.GeoJsonTooltip(fields=['code_ensem'], aliases=['Zone :'])).add_to(m)
    return m
