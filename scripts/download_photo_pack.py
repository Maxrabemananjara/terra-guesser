"""Télécharge et valide les huit fichiers indépendamment du paquet cartographique."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from scripts.prepare_public_data import MANIFEST, download

def build_photo_pack(output):
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    seen=set()
    output=Path(output)
    tmp=output.with_suffix('.tmp')
    try:
        with ZipFile(tmp,'w',ZIP_DEFLATED) as z:
            for r in manifest['rounds']:
                for i,p in enumerate(r['photos'],1):
                    raw=download(p)
                    digest=hashlib.sha256(raw).hexdigest()
                    if digest in seen: raise ValueError('Image dupliquée')
                    seen.add(digest)
                    path=f"{r['id']}/{i:02}.jpg"
                    z.writestr(path,raw)
                    p.update(pack_path=path,sha256=digest)
                    print(f"Contrôlé : {p['title']} — {p['license']} — {len(raw)} octets")
            z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        with ZipFile(tmp) as z:
            if z.testzip() is not None or len(seen)!=8: raise ValueError('Archive incomplète')
        tmp.replace(output)
    finally:
        if tmp.exists(): tmp.unlink()
    print(f'{len(seen)} photographies contrôlées')

if __name__=='__main__':
    import sys
    build_photo_pack(sys.argv[1])
