"""Charge le paquet public V5 livré, sans import utilisateur."""
import hashlib
from pathlib import Path

V5_SHA256 = '05ff8bbda7569cc4dbe9eed7ed5f530ac925c887f5282c50bcfbe9664f99337f'

DEPLOY_SHA256 = 'badbd6535bfefaa87d2813c06f49cf692e346fa38ac592f59738587bafe331d6'

def load_bundled(root):
    root = Path(root)
    full = root / 'terra_guesser_public_v5.zip'
    parts = [root / 'terra_v5.part1', root / 'terra_v5.part2']
    compact = root / 'terra_guesser_v5_deploiement.zip'
    expected = V5_SHA256
    if compact.is_file():
        data = compact.read_bytes()
        expected = DEPLOY_SHA256
    elif full.is_file():
        data = full.read_bytes()
    elif all(p.is_file() for p in parts):
        data = b''.join(p.read_bytes() for p in parts)
    elif any(p.exists() for p in parts):
        raise ValueError('Paquet V5 incomplet : deux parties requises.')
    else:
        return None
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Empreinte du paquet V5 incorrecte.')
    return data
