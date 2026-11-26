"""Vérifier l'intégrité du paquet de données importé."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data"
manifest = ROOT / "manifest.json"
if not manifest.is_file():
    raise SystemExit("Import incomplet : data/manifest.json absent.")
data = json.loads(manifest.read_text(encoding="utf-8"))
errors = []
for name, expected in data["files"].items():
    path = ROOT / name
    if not path.is_file():
        errors.append(f"Absent : {name}")
        continue
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    if path.stat().st_size != expected["bytes"] or sha != expected["sha256"]:
        errors.append(f"Intégrité incorrecte : {name}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"{len(data['files'])} fichiers contrôlés : aucune différence.")
