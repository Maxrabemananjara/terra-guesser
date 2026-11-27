from pathlib import Path
import hashlib
import os
from modules.party_ui import party_screen
from modules.parties import PartyError
from modules.scoring import points, POINTS_PER_CORRECT
import folium
import streamlit as st
from streamlit_folium import st_folium
from modules.interface_data import load_data, filter_zones, web_geometry, zones_at_point
from modules.thematic_layers import CATALOG, load_catalog, load_layer, make_thematic_map
from modules.rounds import CATALOG as PHOTO_CATALOG, read_member, load_rounds, eligible_rounds, new_game, submit_answer, advance

st.set_page_config(page_title='Terra Guesser', page_icon='🌍', layout='wide', initial_sidebar_state='collapsed')
ROOT = Path(__file__).resolve().parent
st.markdown('<style>' + (ROOT / 'assets/mobile.css').read_text(encoding='utf-8') + '</style><div class="terra-banner"><h1>Terra Guesser</h1>Observe · Récolte · Superpose · Interprète · Restitue</div>', unsafe_allow_html=True)
st.caption('Défis Datable · Équipe MEE | Prototype de l’interface cartographique')

@st.cache_data(show_spinner='Chargement des données vérifiées…')
def cached_data(archive):
    matrix, geo = load_data(ROOT, archive)
    return matrix, geo, web_geometry(geo), load_catalog(ROOT, archive, matrix), load_rounds(ROOT, archive, geo, matrix)

@st.cache_data(show_spinner=False, max_entries=8)
def cached_layer(archive, code, entry):
    return load_layer(ROOT, archive, code, entry)

archive = None
server_archive = os.environ.get('TERRA_DATA_ZIP')
if server_archive:
    try:
        archive = Path(server_archive).read_bytes()
    except OSError as exc:
        st.error(f'Paquet serveur inaccessible : {exc}')
        st.stop()
elif not all((ROOT / p).exists() for p in ('data/processed/matrice_filtres_application.csv', 'data/geographic/ensembles_paysagers.geojson.gz', CATALOG, PHOTO_CATALOG)):
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
    st.session_state.pop('terra_party', None)
    st.session_state.pop('terra_party_round', None)

def next_round():
    advance(st.session_state['terra_game'])
    clear_round()

dataset_id = hashlib.sha256(b''.join(hashlib.sha256(read_member(ROOT, archive, path)).digest() for path in ('data/processed/matrice_filtres_application.csv','data/geographic/ensembles_paysagers.geojson.gz',CATALOG,PHOTO_CATALOG))).hexdigest()
if st.session_state.get('terra_dataset') != dataset_id:
    restart()
    st.session_state['terra_dataset'] = dataset_id
by_id = {r['id']: r for r in records}
zone_props = {str(f['properties']['code_ensem']): f['properties'] for f in geo['features']}
collective = 'terra_party' in st.session_state
if not collective and 'terra_game' not in st.session_state:
    collective = st.radio('Mode de jeu', ['Collectif', 'Individuel'], horizontal=True) == 'Collectif'
if collective:
    store, shared, token = party_screen(records, dataset_id, clear_round)
    record = by_id[shared['order'][shared['index']]]
    answered = shared['phase'] == 'revealed'
    game = shared
    if answered and shared['own']:
        st.session_state['terra_zone'] = shared['own']['selected']
elif 'terra_game' not in st.session_state:
    st.subheader('Nouvelle partie')
    demo = os.environ.get('TERRA_ALLOW_DEMO') == '1' and st.checkbox('Mode démonstration privée : images fournies, droits et identité originale non confirmés')
    available = eligible_rounds(records, demo)
    if not available:
        st.info('Aucune manche de diffusion validée : quatre images distinctes, identité et droits vérifiés sont requis.')
        st.stop()
    n = st.selectbox('Nombre de manches', list(range(1, len(available) + 1)), index=len(available)-1)
    if st.button('Commencer la partie', type='primary'):
        st.session_state['terra_game'] = new_game(available, n)
        st.rerun()
    st.stop()

if not collective:
    game = st.session_state['terra_game']
if not collective and game['index'] >= len(game['order']):
    st.header('Partie terminée')
    st.metric('Bonnes réponses', f"{sum(a['correct'] for a in game['answers'])} / {len(game['order'])}")
    st.metric('Score total', f"{sum(points(a['correct']) for a in game['answers'])} / {len(game['order'])*POINTS_PER_CORRECT} points")
    for answer in game['answers']:
        st.write(by_id[answer['id']]['place'], '—', 'Correct' if answer['correct'] else 'Incorrect')
    st.button('Nouvelle partie', on_click=restart)
    st.stop()
if not collective:
    record = by_id[game['order'][game['index']]]
    answered = len(game['answers']) > game['index']
st.subheader(f"Manche {game['index'] + 1} / {len(game['order'])}")
if not collective:
    st.button('Quitter la partie', on_click=restart)
if len(record['photos']) < 4:
    st.caption(f"Démonstration privée : {len(record['photos'])}/4 photos disponibles pour ce lieu.")

with st.expander('Filtres et calques d’observation', expanded=False):
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
        with st.container():
            st.subheader(theme)
            for category, items in rows.groupby('categorie_canva', sort=True):
                st.markdown('**' + category + '**')
                for row in items.itertuples():
                    if st.checkbox(row.filtre_canva, key='filter_' + row.code_filtre, disabled=answered):
                        chosen.append(row.code_filtre)

compatible, uncertain = filter_zones(matrix, chosen)
with st.container(key='terra_metrics'):
    a,b,c = st.columns(3)
    a.metric('Zones encore possibles', len(compatible))
    b.metric('Zones éliminées', 115-len(compatible))
    c.metric('Compatibilité incertaine', len(uncertain))
with st.container(key='terra_workspace'):
    left, right = st.columns([1,2])
    with left:
        st.subheader('Observer le paysage')
        with st.container(key='terra_photo_grid'):
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
        with st.container(key='terra_map'):
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
            map_height = 650 if st.toggle('Agrandir la carte', value=False, key='terra_large_map') else 440
            result = st_folium(m, key='terra_map_' + record['id'] + ('_answer' if answered else ''), height=map_height, use_container_width=True, returned_objects=['last_clicked'])
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
            if not answered and compatible:
                with st.expander('Sélection alternative par code de zone'):
                    alternative = st.selectbox('Code de zone', [''] + sorted(compatible), format_func=lambda x: x or 'Choisir une zone')
                    if st.button('Retenir le code', disabled=not alternative):
                        st.session_state['terra_zone'] = alternative
                        st.rerun()
            if not compatible:
                st.warning('Aucune zone restante : retire un critère pour revoir ton hypothèse.')
            if st.session_state.get('terra_zone'):
                st.success('Zone retenue : ' + st.session_state['terra_zone'])
            st.caption('Contours simplifiés uniquement pour l’affichage ; sélection calculée sur les contours originaux.')
if not answered and st.session_state.get('terra_zone') in compatible:
    if st.button('Valider ma réponse', type='primary'):
        try:
            if collective:
                store.submit(shared['code'], dataset_id, token, record['id'], st.session_state['terra_zone'], by_id, compatible)
            else:
                submit_answer(game, record, st.session_state['terra_zone'], compatible)
            st.rerun()
        except PartyError as exc:
            st.error(str(exc))

if answered:
    answer = shared['own'] if collective else game['answers'][game['index']]
    props = zone_props[record['code_ensem']]
    st.header('Correction géographique')
    st.metric('Points de la manche', points(answer['correct']))
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
    if collective:
        st.info('Attends le lancement de la prochaine manche par l’enseignant, puis actualise la partie.')
    else:
        st.button('Manche suivante' if game['index']+1 < len(game['order']) else 'Voir les résultats', on_click=next_round, type='primary')
st.caption('Sources : DatARA / DREAL Auvergne-Rhône-Alpes · CORINE Land Cover 2018. ')
