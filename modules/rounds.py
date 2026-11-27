"""Manches Terra Guesser : catalogue contrôlé, état de jeu et correction."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Point, shape

CATALOG = 'data/photos/rounds.json'


def read_member(root, archive, name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Chemin interdit')
    if archive is not None:
        with ZipFile(io.BytesIO(archive)) as z:
            return z.read(name)
    return (Path(root) / name).read_bytes()


def load_rounds(root, archive, geo, matrix):
    records = json.loads(read_member(root, archive, CATALOG))['rounds']
    seen = set()
    project = Transformer.from_crs(4326, 2154, always_xy=True)
    zones = [(str(f['properties']['code_ensem']), shape(f['geometry'])) for f in geo['features']]
    for r in records:
        rid = r['id']
        if rid in seen:
            raise ValueError('Manche dupliquée')
        seen.add(rid)
        lat, lon = r['latitude'], r['longitude']
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Coordonnées invalides')
        pt = Point(*project.transform(lon, lat))
        matches = {c for c, g in zones if g.covers(pt)}
        if matches != {r['code_ensem']}:
            raise ValueError(f'Rattachement ambigu ou incorrect : {rid}')
        if not 1 <= len(r['photos']) <= 4:
            raise ValueError('Nombre de photographies invalide')
        if len({p['sha256'] for p in r['photos']}) != len(r['photos']):
            raise ValueError('Photographie dupliquée')
        present = matrix[(matrix.code_ensem == r['code_ensem']) & matrix.present.eq('True')]
        if not set(r['indices']).issubset(set(present.code_filtre)):
            raise ValueError(f'Indice incompatible avec la matrice : {rid}')
        for p in r['photos']:
            b = read_member(root, archive, p['path'])
            if hashlib.sha256(b).hexdigest() != p['sha256']:
                raise ValueError('Photographie altérée')
            with Image.open(io.BytesIO(b)) as im:
                im.verify()
    return records


def eligible_rounds(records, demo=False):
    return [r for r in records if demo or (len(r['photos']) == 4 and all(p['rights'] == 'autorises' and p['identity_verified'] for p in r['photos']))]


def new_game(records, n):
    if not isinstance(n, int) or not 1 <= n <= len(records):
        raise ValueError('Nombre de manches indisponible')
    return {'order': [r['id'] for r in records[:n]], 'index': 0, 'answers': []}


def submit_answer(game, record, selected, valid_codes):
    if game['index'] >= len(game['order']) or len(game['answers']) != game['index'] or game['order'][game['index']] != record['id']:
        raise ValueError('Manche déjà validée ou incohérente')
    if selected not in valid_codes:
        raise ValueError('Zone non sélectionnable')
    game['answers'].append({'id': record['id'], 'selected': selected, 'correct': selected == record['code_ensem']})


def advance(game):
    if game['index'] >= len(game['order']) or len(game['answers']) != game['index'] + 1:
        raise ValueError('Valider la manche avant de continuer')
    game['index'] += 1
