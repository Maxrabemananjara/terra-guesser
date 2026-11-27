from pathlib import Path
import hashlib
import os
from html import escape
from modules.party_ui import party_screen
from modules.bundled_data import load_bundled
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
st.markdown('<style>' + (ROOT / 'assets/mobile.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)
in_game = 'terra_game' in st.session_state or 'terra_party' in st.session_state
st.markdown('<div class="terra-brand"><b>🌍 Terra Guesser</b><span>DATABLE · MEE</span></div>' if in_game else '<div class="terra-banner"><div class="terra-kicker">DÉFIS DATABLE · ÉQUIPE MEE</div><h1>🌍 Terra Guesser</h1><p>À toi de découvrir le paysage mystère !</p><div class="terra-steps"><span>① Observer</span><span>② Récolter</span><span>③ Superposer</span><span>④ Interpréter</span><span>⑤ Restituer</span></div></div>', unsafe_allow_html=True)

@st.cache_data(show_spinner='Chargement des données vérifiées…')
def cached_data(archive):
    matrix, geo = load_data(ROOT, archive)
    return matrix, geo, web_geometry(geo), load_catalog(ROOT, archive, matrix), load_rounds(ROOT, archive, geo, matrix)

@st.cache_data(show_spinner=False, max_entries=8)
def cached_layer(archive, code, entry):
    return load_layer(ROOT, archive, code, entry)

@st.cache_data(show_spinner=False)
def bundled_archive():
    return load_bundled(ROOT)

server_archive = os.environ.get('TERRA_DATA_ZIP')
try:
    archive = None if server_archive else bundled_archive()
except (OSError, ValueError) as exc:
    st.error(f'Données serveur : {exc}')
    st.stop()
if archive is not None:
    os.environ['TERRA_PUBLIC'] = '1'
    os.environ['TERRA_ALLOW_DEMO'] = '0'
if archive is None and server_archive:
    try:
        archive = Path(server_archive).read_bytes()
    except OSError as exc:
        st.error(f'Paquet serveur inaccessible : {exc}')
        st.stop()
elif archive is None and not all((ROOT / p).exists() for p in ('data/processed/matrice_filtres_application.csv', 'data/geographic/ensembles_paysagers.geojson.gz', CATALOG, PHOTO_CATALOG)):
    if os.environ.get('TERRA_PUBLIC') == '1':
        st.error('Données serveur indisponibles. Contactez l’administrateur.')
        st.stop()
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
    st.session_state.pop('terra_alternative_code', None)
    st.session_state.pop('terra_show_chosen', None)

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
    with st.container(key='terra_home'):
        st.markdown('<div class="terra-intro"><b>Ta mission, si tu l’acceptes…</b><p>Quatre photos, des indices et une carte. Réduis les possibilités et retrouve le territoire mystère.</p></div>', unsafe_allow_html=True)
        st.markdown('<div class="terra-section-title">Choisis ton mode de jeu</div>', unsafe_allow_html=True)
        collective = st.radio('Mode de jeu', ['Individuel', 'Collectif'], horizontal=True,
                              captions=['Explore à ton rythme.', 'Défie les autres explorateurs.'],
                              label_visibility='collapsed') == 'Collectif'
        with st.expander('Comment jouer ?'):
            st.markdown('1. **Observer** les quatre photos.\n2. **Récolter** les indices.\n3. **Superposer** les calques.\n4. **Interpréter** et sélectionner un territoire.\n5. **Restituer** en validant ta réponse.')
            st.caption('100 points par bonne réponse. Pas de bonus de vitesse.')
if collective:
    store, shared, token = party_screen(records, dataset_id, clear_round)
    record = by_id[shared['order'][shared['index']]]
    answered = shared['phase'] == 'revealed'
    game = shared
    if answered and shared['own']:
        st.session_state['terra_zone'] = shared['own']['selected']
elif 'terra_game' not in st.session_state:
    with st.container(key='terra_start', border=True):
        st.subheader('Nouvelle partie')
        demo = os.environ.get('TERRA_PUBLIC') != '1' and os.environ.get('TERRA_ALLOW_DEMO') == '1' and st.checkbox('Mode démonstration privée : images fournies, droits et identité originale non confirmés')
        available = eligible_rounds(records, demo)
        if not available:
            st.info('Aucune manche de diffusion validée : quatre images distinctes, identité et droits vérifiés sont requis.')
            st.stop()
        n = st.selectbox('Nombre de manches', list(range(1, len(available) + 1)), index=len(available)-1)
        if st.button('Commencer la partie', type='primary', use_container_width=True):
            st.session_state['terra_game'] = new_game(available, n)
            st.rerun()
    st.stop()

if not collective:
    game = st.session_state['terra_game']
if not collective and game['index'] >= len(game['order']):
    with st.container(key='terra_finish', border=True):
        st.markdown('<div class="terra-step">🏆 BILAN DE TON EXPÉDITION</div>', unsafe_allow_html=True)
        st.header('Partie terminée')
        c1, c2 = st.columns(2)
        c1.metric('Bonnes réponses', f"{sum(a['correct'] for a in game['answers'])} / {len(game['order'])}")
        c2.metric('Score total', f"{sum(points(a['correct']) for a in game['answers'])} / {len(game['order'])*POINTS_PER_CORRECT} points")
        for answer in game['answers']:
            st.write(('✓ ' if answer['correct'] else '✗ ') + by_id[answer['id']]['place'])
        st.button('Nouvelle partie', on_click=restart, type='primary', use_container_width=True)
    st.stop()
if not collective:
    record = by_id[game['order'][game['index']]]
    answered = len(game['answers']) > game['index']
current_score = sum(points(x['correct']) for x in game['answers']) if not collective else None
score_html = f'<div class="terra-score">★ {current_score} pts</div>' if current_score is not None else ''
st.markdown(f'<div class="terra-round"><div>MISSION {game["index"] + 1} / {len(game["order"])} <span>Retrouve le paysage mystère</span></div>{score_html}</div>', unsafe_allow_html=True)
st.progress((game['index'] + int(answered))/len(game['order']), text='Progression des missions')
if not collective:
    st.button('Quitter la partie', on_click=restart)
if len(record['photos']) < 4:
    st.caption(f"Démonstration privée : {len(record['photos'])}/4 photos disponibles pour ce lieu.")

with st.container(key='terra_workspace'):
    left, right = st.columns([1,1.5], gap='medium')
    with left:
        st.markdown('<div class="terra-step">01 · OBSERVER</div>', unsafe_allow_html=True)
        st.subheader('Observer le paysage')
        st.caption('Repère le relief, la végétation, l’eau et les traces d’activités humaines.')
        with st.container(key='terra_photo_grid'):
            for row in range(2):
                for i,col in enumerate(st.columns(2)):
                    with col:
                        j = row * 2 + i
                        if j < len(record['photos']):
                            photo = record['photos'][j]
                            credit = f" — {photo['author']} ({photo['license']})" if photo.get('author') else ''
                            st.image(read_member(ROOT, archive, photo['path']), caption=f'Photo {j+1}'+credit, use_container_width=True)
                        else:
                            st.container(border=True).caption(f'Photo {j+1} — non disponible')
        st.markdown('<div class="terra-step">02 · RÉCOLTER LES INDICES</div>', unsafe_allow_html=True)
        with st.expander('Filtres et calques d’observation', expanded=False):
            st.markdown('**🧩 Quels éléments reconnais-tu ?**')
            st.caption('Chaque indice sélectionné élimine les territoires incompatibles. Les indices se cumulent.')
            if st.button('Réinitialiser les filtres', use_container_width=True, disabled=answered):
                for code in catalog.code_filtre:
                    st.session_state['filter_' + code] = False
                for theme in catalog.theme_canva.unique():
                    st.session_state.pop('observe_' + theme, None)
                st.session_state.pop('terra_zone', None)
            chosen = []
            for theme, rows in catalog.groupby('theme_canva', sort=True):
                st.subheader(theme)
                for category, items in rows.groupby('categorie_canva', sort=True):
                    st.markdown('**' + category + '**')
                    for row in items.itertuples():
                        if st.checkbox(row.filtre_canva, key='filter_' + row.code_filtre, disabled=answered):
                            chosen.append(row.code_filtre)
            st.divider()
            st.markdown('**🗺️ Superposer les calques**')
            st.caption('Les calques montrent les données géographiques à l’intérieur des territoires restants. Leur affichage seul ne change pas ton hypothèse.')
            observed = []
            for theme, rows in catalog.groupby('theme_canva', sort=True):
                codes = rows.code_filtre.tolist()
                observed.extend(st.multiselect(theme, codes, format_func=lambda c: layers_catalog[c]['label'], key='observe_' + theme, disabled=answered))
            if chosen and not answered and st.toggle('Afficher aussi les calques des indices sélectionnés', value=False, key='terra_show_chosen'):
                observed = list(dict.fromkeys(chosen + observed))

        st.markdown('**Carnet d’indices**')
        if chosen:
            chips = ''.join(f'<span><i style="background:{escape(str(item.couleur_hex), quote=True)}"></i>{escape(str(item.filtre_canva))}</span>' for item in catalog[catalog.code_filtre.isin(chosen)].itertuples())
            st.markdown('<div class="terra-chips">'+chips+'</div>', unsafe_allow_html=True)
        else:
            st.caption('Aucun indice sélectionné. Commence ton enquête !')
    compatible, uncertain = filter_zones(matrix, chosen)
    with right:
        with st.container(key='terra_map'):
            st.markdown('<div class="terra-step">03 · SUPERPOSER &nbsp; 04 · INTERPRÉTER</div>', unsafe_allow_html=True)
            st.subheader('Explorer la carte')
            with st.container(key='terra_metrics'):
                c1,c2,c3 = st.columns(3)
                c1.metric('Possibles', len(compatible))
                c2.metric('Éliminés', 115-len(compatible))
                c3.metric('Incertains', len(uncertain))
            st.markdown('<div class="terra-legend"><span><i style="background:#684192"></i>Possible</span><span><i style="background:#FCA845"></i>Incertain</span><span><i style="background:#D47EB3;border:2px solid #684192"></i>Ta réponse</span><span><i style="background:#C3CE6C;border:2px solid #477522"></i>Bonne réponse</span></div>', unsafe_allow_html=True)
            st.caption('Les zones éliminées disparaissent. Touche une zone restante pour la retenir.')
            if chosen and not answered:
                st.progress((115-len(compatible))/115, text=f"Enquête : {115-len(compatible)} territoires éliminés sur 115")
            if len(compatible) == 1 and not answered:
                st.success('Un seul territoire reste possible ! Examine-le avant de répondre.')
            if observed and not answered:
                layer_chips = ''.join(f'<span><i style="background:{escape(str(layers_catalog[c]["color"]), quote=True)}"></i>{escape(str(layers_catalog[c]["label"]))}</span>' for c in observed)
                st.markdown('<div class="terra-chips">'+layer_chips+'</div>', unsafe_allow_html=True)
            if not answered and st.session_state.get('terra_zone') not in compatible:
                st.session_state.pop('terra_zone', None)
            try:
                active_layers = [(code, layers_catalog[code], cached_layer(archive, code, layers_catalog[code])) for code in observed]
                m = make_thematic_map(web_geo, compatible, uncertain, st.session_state.get('terra_zone'), active_layers, answer=record['code_ensem'] if answered else None)
            except Exception as exc:
                st.error(f'Impossible de charger un calque : {exc}')
                st.stop()
            if answered:
                for i, photo in enumerate(record['photos'], 1):
                    folium.Marker([photo.get('latitude',record['latitude']), photo.get('longitude',record['longitude'])], tooltip=f'Point de vue {i}', icon=folium.Icon(color='red')).add_to(m)
            map_height = 650 if st.toggle('Agrandir la carte', value=False, key='terra_large_map') else 480
            view_id = hashlib.sha256(repr((sorted(chosen), sorted(observed), st.session_state.get('terra_zone'), answered)).encode()).hexdigest()[:12]
            result = st_folium(m, key='terra_map_' + record['id'] + '_' + view_id, height=map_height, use_container_width=True, returned_objects=['last_clicked'])
            click = result.get('last_clicked')
            if click and not answered:
                matches = zones_at_point(geo, click['lat'], click['lng'], compatible)
                if len(matches) == 1:
                    if st.session_state.get('terra_zone') != matches[0]:
                        st.session_state['terra_zone'] = matches[0]
                        st.rerun()
                elif matches:
                    picked = st.selectbox('Zone au point sélectionné', matches, format_func=lambda x: 'Zone '+x)
                    if st.button('Retenir cette zone'):
                        st.session_state['terra_zone'] = picked
                        st.rerun()
                else:
                    st.caption('Ce point ne correspond à aucune zone encore compatible.')
            if not answered and compatible:
                with st.expander('Sélection alternative par code de zone'):
                    alternative = st.text_input('Code de zone', max_chars=12, key='terra_alternative_code').strip()
                    if st.button('Retenir le code', disabled=not alternative):
                        if alternative not in compatible:
                            st.error('Ce code ne correspond pas à une zone compatible.')
                        else:
                            st.session_state['terra_zone'] = alternative
                            st.rerun()
            if not compatible:
                st.warning('Aucune zone restante : retire un critère pour revoir ton hypothèse.')
            if st.session_state.get('terra_zone'):
                st.success('Zone retenue : ' + st.session_state['terra_zone'])
            with st.expander('À propos de la carte'):
                st.caption('Contours simplifiés uniquement pour l’affichage ; sélection calculée sur les contours originaux. Données DatARA et CORINE Land Cover.')
if not answered:
    st.markdown('<div class="terra-step">05 · RESTITUER</div>', unsafe_allow_html=True)
    if not st.session_state.get('terra_zone') in compatible:
        st.caption('Sélectionne un territoire sur la carte pour valider ta réponse.')
    if st.button('Valider ma réponse', type='primary', use_container_width=True, disabled=st.session_state.get('terra_zone') not in compatible):
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
    st.markdown('<div class="terra-step">🏆 MISSION TERMINÉE</div>', unsafe_allow_html=True)
    st.header('Correction géographique')
    with st.container(key='terra_reveal', border=True):
        st.markdown(f'<div class="terra-reveal-title">{escape(str(record["place"]))}</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        c1.metric('Points de la manche', points(answer['correct']))
        c2.markdown('**Ensemble paysager**')
        c2.write(props['nom_ensemb'])
    if answer['correct']:
        st.success('Bonne réponse !')
    else:
        st.error('Ce n’est pas le bon ensemble paysager.')
    st.write('**Grand paysage :**', props['nom_grandp'])
    st.markdown('**Ce que les photos nous apprennent**')
    st.write(record['observation'])
    labels = catalog.set_index('code_filtre').filtre_canva.to_dict()
    st.write('Indices observables et compatibles :', ', '.join(labels[c] for c in record['indices']))
    with st.expander('Informations géographiques et sources'):
        st.write('Coordonnées du premier point de vue :', record['latitude'], record['longitude'])
        st.markdown('[Fiche de l’ensemble paysager](' + props['url_fiche'] + ')')
        st.markdown('[Source du point photographique](' + record['source'] + ')')
    with st.expander('Crédits photographiques et licences'):
        for i, photo in enumerate(record['photos'], 1):
            if photo.get('source'):
                st.write(f"Photo {i} : {photo['author']} — {photo['license']}")
                st.markdown('[Fiche originale](' + photo['source'] + ')')
                st.markdown('[Licence](' + photo['license_url'] + ')')
                st.caption(photo['modifications'])
    if collective:
        st.info('Attends le lancement de la prochaine manche par l’enseignant, puis actualise la partie.')
    else:
        st.button('Manche suivante' if game['index']+1 < len(game['order']) else 'Voir les résultats', on_click=next_round, type='primary')
if not answered and any(p.get('source') for p in record['photos']):
    with st.expander('Crédits photographiques (les liens peuvent révéler le lieu)'):
        for photo in record['photos']:
            if photo.get('source'):
                st.write(photo['author'], '—', photo['license'], '—', photo['modifications'])
                st.markdown('[Fiche originale](' + photo['source'] + ')')
                st.markdown('[Licence](' + photo['license_url'] + ')')
st.caption('Sources : DatARA / DREAL Auvergne-Rhône-Alpes · CORINE Land Cover 2018. ')
