"""Interface collective, indépendante du mode solo."""
import os
import secrets
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
                if os.environ.get('TERRA_PUBLIC') == '1':
                    teacher_secret = os.environ.get('TERRA_TEACHER_SECRET', '')
                    supplied = st.text_input('Clé enseignant', type='password')
                    if not teacher_secret or not secrets.compare_digest(teacher_secret.encode(), supplied.encode()):
                        st.info('Clé enseignant nécessaire pour créer une partie.')
                        st.stop()
                demo = os.environ.get('TERRA_PUBLIC') != '1' and os.environ.get('TERRA_ALLOW_DEMO') == '1' and st.checkbox('Démonstration privée — droits des photos non confirmés')
                available = eligible_rounds(records, demo)
                if not available:
                    st.info('Aucune manche de diffusion autorisée.')
                    st.stop()
                n = st.selectbox('Nombre de manches', range(1,len(available)+1), index=len(available)-1)
                school = st.text_input('Établissement (facultatif)', max_chars=80)
                level = st.text_input('Niveau scolaire (facultatif)', max_chars=80)
                class_label = st.text_input('Classe (facultatif)', max_chars=80)
                st.caption('Utiliser uniquement des informations de classe, sans noms d’élèves.')
                if st.button('Créer la partie', type='primary'):
                    connect(*store.create(dataset, [r['id'] for r in available[:n]], {'school':school,'level':level,'class_label':class_label}))
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
    st.write(f'Code de participation : {code}')
    if p['metadata']:
        st.caption(' · '.join(p['metadata'].get(k,'') for k in ('school','level','class_label') if p['metadata'].get(k)))
    with st.expander('Clé de reprise (à garder privée)'):
        st.code(token)
    st.button('Quitter la session', on_click=leave)
    st.button('Actualiser la partie')
    phase = p['phase']
    st.caption('Enseignant' if p['actor'] is None else 'Équipe : '+p['actor'])
    if os.environ.get('TERRA_PUBLIC') == '1' and p['actor'] is None:
        st.caption('Hébergement gratuit : exportez les résultats à la fin de la partie. La base locale peut être effacée lors d’un redémarrage.')
    board = leaderboard(store, code, dataset, token)
    st.caption(f'Barème : {POINTS_PER_CORRECT} points par bonne réponse, 0 sinon. Aucun bonus de vitesse.')
    if board['revealed']:
        st.subheader('Classement final' if board['finished'] else 'Classement provisoire')
        for r in board['rows']:
            with st.container(border=True):
                st.write(f"#{r['rank']} — {r['name']}")
                st.caption(f"{r['correct']} bonne(s) réponse(s) · {r['points']} points")
        if board['finished']:
            champions = winners(board)
            st.success(('Équipe gagnante : ' if len(champions)==1 else 'Équipes gagnantes ex æquo : ') + ', '.join(champions))
            if p['actor'] is None:
                st.download_button('Exporter les résultats (CSV)', results_csv(board), file_name=f'terra_{code}_resultats.csv', mime='text/csv')
    if phase == 'lobby' or p['actor'] is None or phase == 'finished':
        st.write('Équipes inscrites :', len(p['teams']))
        for team in p['teams']:
            st.write(f"{team['name']} · {team['size']} élèves")
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
