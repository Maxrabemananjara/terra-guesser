from pathlib import Path
import hashlib
import folium
import streamlit as st
from streamlit_folium import st_folium
from modules.interface_data import load_data, filter_zones, web_geometry, zones_at_point
from modules.thematic_layers import CATALOG, load_catalog, load_layer, make_thematic_map
from modules.rounds import CATALOG as PHOTO_CATALOG, read_member, load_rounds, eligible_rounds, new_game, submit_answer, advance

st.set_page_config(page_title='Terra Guesser', page_icon='🌍', layout='wide')
ROOT = Path(__file__).resolve().parent
st.markdown('''<style>
[data-testid="stSidebar"] {background:#f7f3ed;}
.terra-banner {background:#FEDCB5;padding:1.1rem 1.4rem;border-radius:14px;color:#263D59;margin-bottom:1rem;}
.terra-banner h1 {margin:0;font-size:2.1rem;}
</style><div class="terra-banner"><h1>Terra Guesser</h1>Observe · Récolte · Superpose · Interprète · Restitue</div>''', unsafe_allow_html=True)
st.caption('Défis Datable · Équipe MEE | Prototype de l’interface cartographique')

@st.cache_data(show_spinner='Chargement des données vérifiées…')
def cached_data(archive):
    matrix, geo = load_data(ROOT, archive)
    return matrix, geo, web_geometry(geo), load_catalog(ROOT, archive, matrix), load_rounds(ROOT, archive, geo, matrix)

@st.cache_data(show_spinner=False, max_entries=8)
def cached_layer(archive, code, entry):
    return load_layer(ROOT, archive, code, entry)

archive = None
if not all((ROOT / p).exists() for p in ('data/processed/matrice_filtres_application.csv', 'data/geographic/ensembles_paysagers.geojson.gz', CATALOG, PHOTO_CATALOG)):
    upload = st.file_uploader('Importer le paquet Terra Guesser V4', type=['zip'])
    if upload is None:
        st.info('Le dépôt ne contient pas encore les données. Importe le ZIP V4 pour ouvrir la carte réelle.')
        st.stop()
    archive = upload.getvalue()
try:
    matrix, geo, web_geo, layers_catalog, records = cached_data(archive)
except Exception as exc:
    st.error(f'Impossible de lire les données : {exc}')
    st.stop()

catalog = matrix[['code_filtre','theme_canva','categorie_canva','filtre_canva','couleur_hex']].drop_duplicates()
def clear_round():
    for code in catalog.code_filtre:
        st.session_state.pop('filter_' + code, None)
    for theme in catalog.theme_canva.unique():
        st.session_state.pop('observe_' + theme, None)
    st.session_state.pop('terra_zone', None)

def restart():
    clear_round()
    st.session_state.pop('terra_game', None)

def next_round():
    advance(st.session_state['terra_game'])
    clear_round()

dataset_id = hashlib.sha256(archive if archive is not None else read_member(ROOT, None, PHOTO_CATALOG)).hexdigest()
if st.session_state.get('terra_dataset') != dataset_id:
    restart()
    st.session_state['terra_dataset'] = dataset_id
by_id = {r['id']: r for r in records}
zone_props = {str(f['properties']['code_ensem']): f['properties'] for f in geo['features']}
if 'terra_game' not in st.session_state:
    st.subheader('Nouvelle partie')
    demo = st.checkbox('Mode démonstration privée : images fournies, droits et identité originale non confirmés')
    available = eligible_rounds(records, demo)
    if not available:
        st.info('Aucune manche de diffusion validée : quatre images distinctes, identité et droits vérifiés sont requis.')
        st.stop()
    n = st.selectbox('Nombre de manches', list(range(1, len(available) + 1)), index=len(available)-1)
    if st.button('Commencer la partie', type='primary'):
        st.session_state['terra_game'] = new_game(available, n)
        st.rerun()
    st.stop()

game = st.session_state['terra_game']
if game['index'] >= len(game['order']):
    st.header('Partie terminée')
    st.metric('Bonnes réponses', f"{sum(a['correct'] for a in game['answers'])} / {len(game['order'])}")
    for answer in game['answers']:
        st.write(by_id[answer['id']]['place'], '—', 'Correct' if answer['correct'] else 'Incorrect')
    st.button('Nouvelle partie', on_click=restart)
    st.stop()
record = by_id[game['order'][game['index']]]
answered = len(game['answers']) > game['index']
st.subheader(f"Manche {game['index'] + 1} / {len(game['order'])}")
st.button('Quitter la partie', on_click=restart)
if len(record['photos']) < 4:
    st.caption(f"Démonstration privée : {len(record['photos'])}/4 photos disponibles pour ce lieu.")

with st.sidebar:
    st.header('Calques d’observation')
    st.caption('Afficher une couche ne modifie pas les zones compatibles.')
    observed = []
    for theme, rows in catalog.groupby('theme_canva', sort=True):
        codes = rows.code_filtre.tolist()
        observed.extend(st.multiselect(theme, codes, format_func=lambda c: layers_catalog[c]['label'], key='observe_' + theme))
    st.divider()
    st.header('Filtres de déduction')
    st.caption('Les critères sélectionnés se cumulent (ET).')
    if st.button('Réinitialiser les filtres', use_container_width=True, disabled=answered):
        for code in catalog.code_filtre:
            st.session_state['filter_' + code] = False
        st.session_state.pop('terra_zone', None)
    chosen = []
    for theme, rows in catalog.groupby('theme_canva', sort=True):
        with st.expander(theme, expanded=True):
            for category, items in rows.groupby('categorie_canva', sort=True):
                st.markdown('**' + category + '**')
                for row in items.itertuples():
                    if st.checkbox(row.filtre_canva, key='filter_' + row.code_filtre, disabled=answered):
                        chosen.append(row.code_filtre)

compatible, uncertain = filter_zones(matrix, chosen)
a,b,c = st.columns(3)
a.metric('Zones encore possibles', len(compatible))
b.metric('Zones éliminées', 115-len(compatible))
c.metric('Compatibilité incertaine', len(uncertain))
left, right = st.columns([1,2])
with left:
    st.subheader('Observer le paysage')
    for row in range(2):
        for i,col in enumerate(st.columns(2)):
            with col:
                j = row * 2 + i
                if j < len(record['photos']):
                    st.image(read_member(ROOT, archive, record['photos'][j]['path']), caption=f'Photo {j+1}', use_container_width=True)
                else:
                    st.container(border=True).caption(f'Photo {j+1} — non disponible')
    st.subheader('Indices sélectionnés')
    for item in catalog[catalog.code_filtre.isin(chosen)].itertuples():
        st.markdown(f'<span style="color:{item.couleur_hex}">●</span> {item.filtre_canva}', unsafe_allow_html=True)
    if not chosen:
        st.caption('Aucun filtre actif.')
with right:
    st.subheader('Explorer la carte')
    st.caption('Contours : vert = compatible · ocre pointillé = incertain · gris = éliminé · bleu foncé = sélection')
    for code in observed:
        entry = layers_catalog[code]
        st.markdown(f'<span style="color:{entry["color"]}">●</span> {entry["label"]}', unsafe_allow_html=True)
    if st.session_state.get('terra_zone') not in compatible:
        st.session_state.pop('terra_zone', None)
    try:
        active_layers = [(code, layers_catalog[code], cached_layer(archive, code, layers_catalog[code])) for code in observed]
        m = make_thematic_map(web_geo, compatible, uncertain, st.session_state.get('terra_zone'), active_layers)
    except Exception as exc:
        st.error(f'Impossible de charger un calque : {exc}')
        st.stop()
    if answered:
        folium.Marker([record['latitude'], record['longitude']], tooltip='Localisation réelle', icon=folium.Icon(color='red')).add_to(m)
    result = st_folium(m, key='terra_map_' + record['id'] + ('_answer' if answered else ''), height=560, use_container_width=True, returned_objects=['last_clicked'])
    click = result.get('last_clicked')
    if click and not answered:
        matches = zones_at_point(geo, click['lat'], click['lng'], compatible)
        if matches:
            picked = st.selectbox('Zone au point sélectionné', matches, format_func=lambda x: 'Zone '+x)
            if st.button('Retenir cette zone'):
                st.session_state['terra_zone'] = picked
                st.rerun()
        else:
            st.caption('Ce point ne correspond à aucune zone encore compatible.')
    if not compatible:
        st.warning('Aucune zone restante : retire un critère pour revoir ton hypothèse.')
    if st.session_state.get('terra_zone'):
        st.success('Zone retenue : ' + st.session_state['terra_zone'])
    st.caption('Contours simplifiés uniquement pour l’affichage ; sélection calculée sur les contours originaux.')
if not answered and st.session_state.get('terra_zone') in compatible:
    if st.button('Valider ma réponse', type='primary'):
        submit_answer(game, record, st.session_state['terra_zone'], compatible)
        st.rerun()

if answered:
    answer = game['answers'][game['index']]
    props = zone_props[record['code_ensem']]
    st.header('Correction géographique')
    if answer['correct']:
        st.success('Bonne réponse !')
    else:
        st.error('Ce n’est pas le bon ensemble paysager.')
    st.write('Lieu :', record['place'])
    st.write('Ensemble paysager :', props['nom_ensemb'])
    st.write('Grand paysage :', props['nom_grandp'])
    st.write('Coordonnées :', record['latitude'], record['longitude'])
    st.write('Observations sur la photo :', record['observation'])
    labels = catalog.set_index('code_filtre').filtre_canva.to_dict()
    st.write('Indices observables et compatibles :', ', '.join(labels[c] for c in record['indices']))
    st.markdown('[Fiche de l’ensemble paysager](' + props['url_fiche'] + ')')
    st.markdown('[Source du point photographique](' + record['source'] + ')')
    st.button('Manche suivante' if game['index']+1 < len(game['order']) else 'Voir les résultats', on_click=next_round, type='primary')
st.caption('Sources : DatARA / DREAL Auvergne-Rhône-Alpes · CORINE Land Cover 2018. Les équipes et le classement partagé seront ajoutés ultérieurement.')
