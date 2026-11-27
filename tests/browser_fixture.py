"""Génère un jeu de données strictement synthétique pour les tests navigateur."""
import gzip
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile
import pandas as pd
from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform

def create_fixture(path):
    src = []
    rows = []
    proj = Transformer.from_crs(2154, 4326, always_xy=True)
    codes = [f'filtre_{i:02}' for i in range(31)]
    for i in range(115):
        x, y = 820000 + (i % 12)*12000, 6450000 + (i//12)*12000
        geom = box(x,y,x+10000,y+10000)
        src.append({'type':'Feature','geometry':mapping(geom),'properties':{'code_ensem':str(i+100),'nom_ensemb':f'Zone test {i}','nom_grandp':'Paysage de test','url_fiche':'https://example.invalid'}})
        for code in codes:
            rows.append({'code_ensem':str(i+100),'code_filtre':code,'present':str(i%2==0 or code!=codes[0]),'theme_canva':'Thème test','categorie_canva':'Catégorie test','filtre_canva':code,'couleur_hex':'#43875D'})
    def j(obj): return json.dumps(obj).encode()
    def fc(features): return {'type':'FeatureCollection','features':features}
    geo=fc(src); geo['crs']={'type':'name','properties':{'name':'EPSG:2154'}}
    catalog={'version':3,'crs':'EPSG:4326','layers':{}}
    with ZipFile(path,'w') as z:
        z.writestr('data/processed/matrice_filtres_application.csv',pd.DataFrame(rows).to_csv(index=False))
        z.writestr('data/geographic/ensembles_paysagers.geojson.gz',gzip.compress(j(geo)))
        for code in codes:
            features=[{'type':'Feature','geometry':mapping(transform(proj.transform,box(820000,6450000,830000,6460000))),'properties':{'code_filtre':code}}]
            raw=gzip.compress(j(fc(features))); p=f'data/layers/{code}.geojson.gz'
            z.writestr(p,raw); catalog['layers'][code]={'path':p,'count':1,'label':code,'color':'#43875D','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        z.writestr('data/layers/catalog.json',j(catalog))
        photos=[]
        for i in range(4):
            im=Image.new('RGB',(640,420),(200,210,210-i*20)); ImageDraw.Draw(im).text((20,20),f'FIXTURE {i}',fill='black')
            buf=io.BytesIO(); im.save(buf,format='PNG'); raw=buf.getvalue()
            p=f'data/photos/test{i}.png'; z.writestr(p,raw)
            photos.append({'path':p,'sha256':hashlib.sha256(raw).hexdigest(),'rights':'autorises','identity_verified':True})
        lon,lat=proj.transform(825000,6455000)
        z.writestr('data/photos/rounds.json',j({'rounds':[{'id':'test1','latitude':lat,'longitude':lon,'code_ensem':'100','photos':photos,'indices':[codes[0]],'place':'Lieu de test fictif','source':'https://example.invalid','observation':'Fixture technique'}]}))

if __name__=='__main__':
    import sys
    create_fixture(Path(sys.argv[1]))
