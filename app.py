from pathlib import Path
import streamlit as st
from streamlit_folium import st_folium
from modules.interface_data import load_data, filter_zones, web_geometry, zones_at_point, make_map

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
    return matrix, geo, web_geometry(geo)

archive = None
if not (ROOT / 'data/processed/matrice_filtres_application.csv').exists() or not (ROOT / 'data/geographic/ensembles_paysagers.geojson.gz').exists():
    upload = st.file_uploader('Importer le paquet de données Terra Guesser V2', type=['zip'])
    if upload is None:
        st.info('Le dépôt ne contient pas encore les données. Importe le ZIP V2 pour ouvrir la carte réelle.')
        st.stop()
    archive = upload.getvalue()
try:
    matrix, geo, web_geo = cached_data(archive)
except Exception as exc:
    st.error(f'Impossible de lire les données : {exc}')
    st.stop()

catalog = matrix[['code_filtre','theme_canva','categorie_canva','filtre_canva','couleur_hex']].drop_duplicates()
with st.sidebar:
    st.header('Filtres de déduction')
    st.caption('Les critères sélectionnés se cumulent (ET).')
    if st.button('Réinitialiser les filtres', use_container_width=True):
        for code in catalog.code_filtre:
            st.session_state['filter_' + code] = False
        st.session_state.pop('terra_zone', None)
    chosen = []
    for theme, rows in catalog.groupby('theme_canva', sort=True):
        with st.expander(theme, expanded=True):
            for category, items in rows.groupby('categorie_canva', sort=True):
                st.markdown('**' + category + '**')
                for row in items.itertuples():
                    if st.checkbox(row.filtre_canva, key='filter_' + row.code_filtre):
                        chosen.append(row.code_filtre)

compatible, uncertain = filter_zones(matrix, chosen)
a,b,c = st.columns(3)
a.metric('Zones compatibles', len(compatible))
b.metric('Zones éliminées', 115-len(compatible))
c.metric('Compatibilité incertaine', len(uncertain))
left, right = st.columns([1,2])
with left:
    st.subheader('Observer le paysage')
    st.info('Les quatre photographies de la manche seront intégrées à l’étape de la banque photographique.')
    for row in range(2):
        for i,col in enumerate(st.columns(2)):
            with col:
                st.container(border=True).caption(f'Photo {row*2+i+1} — à intégrer')
    st.subheader('Indices sélectionnés')
    for item in catalog[catalog.code_filtre.isin(chosen)].itertuples():
        st.markdown(f'<span style="color:{item.couleur_hex}">●</span> {item.filtre_canva}', unsafe_allow_html=True)
    if not chosen:
        st.caption('Aucun filtre actif.')
with right:
    st.subheader('Explorer la carte')
    st.caption('Vert : compatible · Jaune : incertitude · Gris : éliminé · Bleu foncé : sélection')
    if st.session_state.get('terra_zone') not in compatible:
        st.session_state.pop('terra_zone', None)
    m = make_map(web_geo, compatible, uncertain, st.session_state.get('terra_zone'))
    result = st_folium(m, key='terra_map', height=560, use_container_width=True, returned_objects=['last_clicked'])
    click = result.get('last_clicked')
    if click:
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
st.caption('Sources : DatARA / DREAL Auvergne-Rhône-Alpes · CORINE Land Cover 2018. Les manches et le classement ne sont pas encore activés.')
