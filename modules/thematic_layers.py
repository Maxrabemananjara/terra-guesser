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


def visible_zones(web_geo, compatible, selected=None, answer=None):
    """Ne dessiner que les hypothèses restantes et, après validation, la correction."""
    ids = set(compatible) if answer is None else {str(answer), str(selected)}
    return {'type': 'FeatureCollection',
            'features': [f for f in web_geo['features']
                         if str(f['properties']['code_ensem']) in ids]}


def make_thematic_map(web_geo, compatible, uncertain, selected, layers, center=None, zoom=7, answer=None):
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union
    from shapely.prepared import prep

    visible = visible_zones(web_geo, compatible, selected, answer)
    m = folium.Map(location=center or [45.5, 4.7], zoom_start=zoom,
                   tiles='OpenStreetMap', prefer_canvas=True, max_zoom=14)
    # Bounds and overlays use display geometries only; original polygons
    # remain authoritative for point-in-polygon selection.
    geoms = [shape(f['geometry']) for f in visible['features']]
    if geoms:
        minx = min(g.bounds[0] for g in geoms)
        miny = min(g.bounds[1] for g in geoms)
        maxx = max(g.bounds[2] for g in geoms)
        maxy = max(g.bounds[3] for g in geoms)
        m.fit_bounds([[miny, minx], [maxy, maxx]], padding=(20, 20), max_zoom=11)
    # Restrict observation overlays to the remaining territory, so a
    # thematic layer cannot repaint an excluded area.
    if layers and geoms and answer is None:
        restrict = len(visible['features']) < len(web_geo['features'])
        boundary = unary_union(geoms) if restrict else None
        prepared = prep(boundary) if restrict else None
        for code, entry, data in sorted(layers, key=lambda item: (0 if item[0].startswith('grand_') else 1 if item[0].startswith('typo_') else 2, item[0])):
            color = entry['color']
            if restrict:
                features = []
                for f in data['features']:
                    g = shape(f['geometry'])
                    if not prepared.intersects(g):
                        continue
                    if not prepared.covers(g):
                        g = g.intersection(boundary)
                    if not g.is_empty:
                        features.append({**f, 'geometry': mapping(g)})
                data = {'type': 'FeatureCollection', 'features': features}
            if data['features']:
                folium.GeoJson(data, name=entry['label'], style_function=lambda f, color=color: {'fillColor': color, 'color': color, 'weight': 0.6, 'fillOpacity': 0.62}, interactive=False).add_to(m)

    def style(f):
        code = str(f['properties']['code_ensem'])
        chosen = code == selected
        correct = answer is not None and code == str(answer)
        unsure = code in uncertain and answer is None
        color = '#009E73' if correct else '#D63384' if chosen else '#F59E0B' if unsure else '#007FBE'
        return {'fillColor': color, 'color': color, 'weight': 4 if chosen or correct else 2.3,
                'dashArray': '6 4' if unsure else None,
                'fillOpacity': 0.62 if chosen or correct else 0.12 if layers else 0.52}
    if visible['features']:
        folium.GeoJson(visible, name='Territoires restants', control=False, style_function=style,
                       highlight_function=lambda f: {'weight': 4, 'fillOpacity': 0.7},
                       tooltip=folium.GeoJsonTooltip(fields=['code_ensem'], aliases=['Territoire :'])).add_to(m)
    return m
