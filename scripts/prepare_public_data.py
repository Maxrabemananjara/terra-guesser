"""Télécharger uniquement les fichiers Commons recensés et construire un ZIP.
Le paquet final doit passer le contrôle spatial sur la base originale.
Usage : python -m scripts.prepare_public_data BASE.zip SORTIE.zip
"""
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image, ImageOps
from modules.interface_data import load_data
from modules.rounds import load_rounds
from modules.thematic_layers import load_catalog
from shapely.geometry import Point, shape
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'assets/photo_candidates.json'
UA = 'TerraGuesser-Educational/1.0 (https://github.com/Maxrabemananjara/terra-guesser)'
LICENSES = {'CC BY-SA 3.0':'https://creativecommons.org/licenses/by-sa/3.0/',
            'CC BY-SA 4.0':'https://creativecommons.org/licenses/by-sa/4.0/',
            'CC BY 4.0':'https://creativecommons.org/licenses/by/4.0/'}

def request(url, max_size):
    with urlopen(Request(url, headers={'User-Agent':UA}),timeout=45) as r:
        raw = r.read(max_size+1)
        if len(raw)>max_size:
            raise ValueError('Fichier trop volumineux')
        return raw

def download(p):
    query = urlencode({'action':'query','format':'json','formatversion':'2','titles':'File:'+p['title'],
                       'prop':'imageinfo','iiprop':'url|extmetadata|mime','iiurlwidth':'1280'})
    pages=json.loads(request('https://commons.wikimedia.org/w/api.php?'+query,2_000_000))['query']['pages']
    if len(pages)!=1 or 'missing' in pages[0]:
        raise ValueError('Fiche Commons introuvable : '+p['title'])
    info=pages[0]['imageinfo'][0]
    license=info['extmetadata']['LicenseShortName']['value']
    if license!=p['license'] or license not in LICENSES:
        raise ValueError('Licence différente de la fiche vérifiée : '+p['title'])
    url=info['url']
    if urlparse(url).scheme!='https' or urlparse(url).hostname!='upload.wikimedia.org' or info['mime']!='image/jpeg':
        raise ValueError('Source ou format inattendu')
    raw=request(url,25_000_000)
    with Image.open(io.BytesIO(raw)) as im:
        # Retirer EXIF/GPS et limiter la résolution. Transformation indiquée dans les crédits.
        im=ImageOps.exif_transpose(im).convert('RGB')
        im.thumbnail((1280,1280))
        out=io.BytesIO()
        im.save(out,format='JPEG',quality=88,optimize=True)
    return out.getvalue()

def validate_locations(records, geo, matrix):
    project=Transformer.from_crs(4326,2154,always_xy=True)
    zones=[(str(f['properties']['code_ensem']),shape(f['geometry'])) for f in geo['features']]
    for r in records:
        present=set(matrix.loc[(matrix.code_ensem==r['code_ensem']) & matrix.present.eq('True'),'code_filtre'])
        if len(r['photos'])!=4 or not set(r['indices']).issubset(present):
            raise ValueError('Manche incomplète ou indices incohérents')
        for p in r['photos']:
            point=Point(*project.transform(p['longitude'],p['latitude']))
            if {c for c,g in zones if g.covers(point)}!={r['code_ensem']}:
                raise ValueError('Rattachement incorrect : '+p['title'])

def build(base, output, downloader=download):
    records=json.loads(MANIFEST.read_text(encoding='utf-8'))['rounds']
    archive=Path(base).read_bytes()
    matrix,geo=load_data(ROOT,archive)
    load_catalog(ROOT,archive,matrix)
    validate_locations(records,geo,matrix)
    photo_files={}
    seen=set()
    for r in records:
        for i,p in enumerate(r['photos'],1):
            raw=downloader(p)
            digest=hashlib.sha256(raw).hexdigest()
            if digest in seen: raise ValueError('Image dupliquée')
            seen.add(digest)
            path=f"data/photos/{r['id']}/{i:02}.jpg"
            p.update(path=path,sha256=digest,rights='autorises',identity_verified=True,
                     license_url=LICENSES[p['license']],modifications='Redimensionnée, réencodée, métadonnées retirées.')
            photo_files[path]=raw
        p=r['photos'][0]
        r.update(latitude=p['latitude'],longitude=p['longitude'],source=p['source'])
    output=Path(output)
    if output.resolve()==Path(base).resolve(): raise ValueError('La source ne doit pas être écrasée')
    temporary=output.with_suffix('.tmp')
    try:
        with ZipFile(io.BytesIO(archive)) as src, ZipFile(temporary,'w',ZIP_DEFLATED) as dst:
            for name in src.namelist():
                if not name.startswith('data/photos/'):
                    dst.writestr(name,src.read(name))
            for name,raw in photo_files.items(): dst.writestr(name,raw)
            dst.writestr('data/photos/rounds.json',json.dumps({'rounds':records},ensure_ascii=False,indent=2))
        raw=temporary.read_bytes()
        load_rounds(ROOT,raw,geo,matrix)
        with ZipFile(temporary) as z:
            if z.testzip(): raise ValueError('Archive corrompue')
        temporary.replace(output)
    finally:
        if temporary.exists(): temporary.unlink()
    print(f'{len(records)} manches et {len(seen)} photos contrôlées : {output}')

if __name__=='__main__':
    build(*sys.argv[1:])
