"""Interface collective, indépendante du mode solo."""
import os
from pathlib import Path
import streamlit as st
from modules.parties import Store, PartyError
from modules.rounds import eligible_rounds
from modules.scoring import leaderboard, winners, results_csv, POINTS_PER_CORRECT


@st.cache_resource
def get_store():
    path = Path(os.environ.get('TERRA_PARTIES_DB', '.terra/parties.sqlite'))
    path.parent.mkdir(parents=True, exist_ok=True)
    return Store(path)


def party_screen(records, dataset, clear_round):
    store = get_store()
    def leave():
        st.session_state.pop('terra_party', None)
        st.session_state.pop('terra_party_round', None)
        clear_round()
    def connect(code, token):
        store.state(code, dataset, token)
        st.session_state['terra_party'] = (code, token)
        st.rerun()
    if 'terra_party' not in st.session_state:
        st.subheader('Partie collective')
        mode = st.radio('Accès', ['Créer une partie (enseignant)', 'Rejoindre une partie (équipe)', 'Reprendre une session'])
        try:
            if mode.startswith('Créer'):
                demo = os.environ.get('TERRA_ALLOW_DEMO') == '1' and st.checkbox('Démonstration privée — droits des photos non confirmés')
                available = eligible_rounds(records, demo)
                if not available:
                    st.info('Aucune manche de diffusion autorisée.')
                    st.stop()
                n = st.selectbox('Nombre de manches', range(1,len(available)+1), index=len(available)-1)
                if st.button('Créer la partie', type='primary'):
                    connect(*store.create(dataset, [r['id'] for r in available[:n]]))
            elif mode.startswith('Rejoindre'):
                code = st.text_input('Code de participation').strip().upper()
                name = st.text_input('Nom de l’équipe (sans nom d’élève)')
                size = st.radio('Nombre d’élèves', [4,5], horizontal=True)
                if st.button('Rejoindre', type='primary'):
                    connect(code, store.join(code,dataset,name,size))
            else:
                code = st.text_input('Code de participation').strip().upper()
                token = st.text_input('Clé personnelle de reprise', type='password')
                if st.button('Reprendre', type='primary'):
                    connect(code,token)
        except PartyError as exc:
            st.error(str(exc))
        st.stop()
    code, token = st.session_state['terra_party']
    try:
        p = store.state(code,dataset,token)
    except PartyError as exc:
        st.error(str(exc))
        st.button('Retour', on_click=leave)
        st.stop()
    st.write('Code de participation :', code)
    with st.expander('Clé de reprise (à garder privée)'):
        st.code(token)
    st.button('Quitter la session', on_click=leave)
    st.button('Actualiser la partie')
    phase = p['phase']
    st.caption('Enseignant' if p['actor'] is None else 'Équipe : '+p['actor'])
    board = leaderboard(store, code, dataset, token)
    st.caption(f'Barème : {POINTS_PER_CORRECT} points par bonne réponse, 0 sinon. Aucun bonus de vitesse.')
    if board['revealed']:
        st.subheader('Classement final' if board['finished'] else 'Classement provisoire')
        st.table([{'Rang': r['rank'], 'Équipe': r['name'], 'Bonnes réponses': r['correct'], 'Points': r['points']} for r in board['rows']])
        if board['finished']:
            champions = winners(board)
            st.success(('Équipe gagnante : ' if len(champions)==1 else 'Équipes gagnantes ex æquo : ') + ', '.join(champions))
            if p['actor'] is None:
                st.download_button('Exporter les résultats (CSV)', results_csv(board), file_name=f'terra_{code}_resultats.csv', mime='text/csv')
    if phase == 'lobby' or p['actor'] is None or phase == 'finished':
        st.write('Équipes inscrites :', len(p['teams']))
        st.table(p['teams'])
        if phase == 'finished':
            st.success('Partie terminée. Félicitations aux équipes !')
        elif p['actor'] is None:
            if phase != 'lobby':
                st.subheader(f"Manche {p['index']+1}/{len(p['order'])}")
                st.write(f"{p['submitted']} / {len(p['teams'])} équipes ont répondu")
            action, label, enabled = {
                'lobby': ('start','Lancer la partie',len(p['teams'])>=2),
                'playing': ('reveal','Révéler la correction',p['submitted']==len(p['teams'])),
                'revealed': ('next','Manche suivante / terminer',True)
            }[phase]
            if st.button(label, disabled=not enabled, type='primary'):
                try:
                    store.control(code,dataset,token,action,expected_index=p['index'])
                    st.rerun()
                except PartyError as exc:
                    st.error(str(exc))
        else:
            st.info('En attente du lancement par l’enseignant. Actualise la partie.')
        st.stop()
    key = (code,p['index'])
    if st.session_state.get('terra_party_round') != key:
        clear_round()
        st.session_state['terra_party_round'] = key
    if phase == 'playing' and p['own'] is not None:
        st.success('Réponse enregistrée. En attente de la correction collective.')
        st.stop()
    return store, p, token
