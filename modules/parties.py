"""Parties collectives sur une instance Streamlit, stockage SQLite transactionnel."""
import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager


class PartyError(ValueError):
    pass


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.tx() as db:
            db.execute('CREATE TABLE IF NOT EXISTS parties (code TEXT PRIMARY KEY, owner TEXT NOT NULL, dataset TEXT NOT NULL, rounds TEXT NOT NULL, idx INTEGER NOT NULL DEFAULT 0, phase TEXT NOT NULL DEFAULT "lobby")')
            db.execute('CREATE TABLE IF NOT EXISTS teams (code TEXT NOT NULL REFERENCES parties(code), name TEXT NOT NULL, token TEXT NOT NULL, size INTEGER NOT NULL, PRIMARY KEY(code, name), UNIQUE(code, token))')
            db.execute('CREATE TABLE IF NOT EXISTS answers (code TEXT NOT NULL, name TEXT NOT NULL, idx INTEGER NOT NULL, selected TEXT NOT NULL, correct INTEGER NOT NULL, PRIMARY KEY(code,name,idx), FOREIGN KEY(code,name) REFERENCES teams(code,name))')

    @contextmanager
    def tx(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, dataset, rounds):
        if not rounds or len(set(rounds)) != len(rounds):
            raise PartyError('Liste de manches invalide.')
        token = secrets.token_urlsafe(24)
        with self.tx() as db:
            while True:
                code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))
                if not db.execute('SELECT 1 FROM parties WHERE code=?',(code,)).fetchone():
                    break
            db.execute('INSERT INTO parties(code,owner,dataset,rounds) VALUES(?,?,?,?)',(code,digest(token),dataset,json.dumps(rounds)))
        return code, token

    def _party(self, db, code, dataset):
        p = db.execute('SELECT * FROM parties WHERE code=?',(code,)).fetchone()
        if p is None or p['dataset'] != dataset:
            raise PartyError('Partie inconnue ou paquet de données différent.')
        return p

    def _actor(self, db, p, token):
        h = digest(token)
        if secrets.compare_digest(p['owner'],h):
            return None
        team = db.execute('SELECT name FROM teams WHERE code=? AND token=?',(p['code'],h)).fetchone()
        if team is None:
            raise PartyError('Accès non autorisé.')
        return team['name']

    def join(self, code, dataset, name, size):
        name = name.strip()
        if not re.fullmatch(r'[\w .-]{1,40}',name) or size not in (4,5):
            raise PartyError('Nom d’équipe valide et 4 ou 5 élèves requis.')
        token = secrets.token_urlsafe(24)
        with self.tx() as db:
            p = self._party(db,code,dataset)
            if p['phase'] != 'lobby':
                raise PartyError('Les inscriptions sont closes.')
            if db.execute('SELECT 1 FROM teams WHERE code=? AND lower(name)=lower(?)',(code,name)).fetchone():
                raise PartyError('Ce nom est déjà pris.')
            db.execute('INSERT INTO teams VALUES(?,?,?,?)',(code,name,digest(token),size))
        return token

    def state(self, code, dataset, token):
        with self.tx() as db:
            p = self._party(db,code,dataset)
            actor = self._actor(db,p,token)
            teams = [dict(r) for r in db.execute('SELECT name,size FROM teams WHERE code=? ORDER BY name',(code,))]
            rows = [dict(r) for r in db.execute('SELECT name,idx,selected,correct FROM answers WHERE code=? ORDER BY idx,name',(code,))]
            idx, phase = p['idx'],p['phase']
            own = next((a for a in rows if a['name']==actor and a['idx']==idx),None)
            if own is not None and phase == 'playing':
                own = {'selected':own['selected']}
            return {'code':code,'actor':actor,'order':json.loads(p['rounds']),'index':idx,'phase':phase,'teams':teams,'submitted':sum(a['idx']==idx for a in rows),'own':own}

    def control(self, code, dataset, token, action):
        with self.tx() as db:
            p = self._party(db,code,dataset)
            if self._actor(db,p,token) is not None:
                raise PartyError('Action réservée à l’enseignant.')
            phase, idx = p['phase'], p['idx']
            total = db.execute('SELECT count(*) FROM teams WHERE code=?',(code,)).fetchone()[0]
            answered = db.execute('SELECT count(*) FROM answers WHERE code=? AND idx=?',(code,idx)).fetchone()[0]
            if action == 'start' and phase == 'lobby' and total >= 2:
                phase = 'playing'
            elif action == 'reveal' and phase == 'playing' and total == answered:
                phase = 'revealed'
            elif action == 'next' and phase == 'revealed':
                idx += 1
                phase = 'finished' if idx == len(json.loads(p['rounds'])) else 'playing'
            else:
                raise PartyError('Action impossible dans cet état.')
            db.execute('UPDATE parties SET phase=?,idx=? WHERE code=?',(phase,idx,code))

    def submit(self, code, dataset, token, round_id, selected, records, valid_codes):
        with self.tx() as db:
            p = self._party(db,code,dataset)
            actor = self._actor(db,p,token)
            if actor is None or p['phase'] != 'playing' or json.loads(p['rounds'])[p['idx']] != round_id or selected not in valid_codes:
                raise PartyError('Réponse non autorisée ou manche expirée.')
            if db.execute('SELECT 1 FROM answers WHERE code=? AND name=? AND idx=?',(code,actor,p['idx'])).fetchone():
                raise PartyError('Réponse déjà enregistrée.')
            correct = int(selected == records[round_id]['code_ensem'])
            db.execute('INSERT INTO answers VALUES(?,?,?,?,?)',(code,actor,p['idx'],selected,correct))
