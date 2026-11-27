#!/bin/sh
set -eu
export TERRA_PUBLIC=1
export TERRA_ALLOW_DEMO=0
: "${TERRA_TEACHER_SECRET:?Définir le secret enseignant dans les variables de l’hébergeur}"
: "${TERRA_PARTIES_DB:?Définir la base SQLite sur un volume persistant}"
if [ -z "${TERRA_DATA_ZIP:-}" ]; then
  : "${TERRA_BASE_ZIP:?Fournir la base cartographique publique sur le serveur}"
  export TERRA_DATA_ZIP="/app/terra-public.zip"
  python -m scripts.prepare_public_data "$TERRA_BASE_ZIP" "$TERRA_DATA_ZIP"
fi
python -c "import os; from pathlib import Path; from modules.interface_data import load_data; from modules.rounds import load_rounds,eligible_rounds; from modules.thematic_layers import load_catalog; b=Path(os.environ['TERRA_DATA_ZIP']).read_bytes(); m,g=load_data('.',b); load_catalog('.',b,m); assert len(eligible_rounds(load_rounds('.',b,g,m)))>=2, 'Deux manches autorisées requises'"
exec streamlit run app.py --server.address=0.0.0.0 --server.port="${PORT:-8501}" --server.headless=true
