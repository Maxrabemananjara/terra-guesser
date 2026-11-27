"""Classement des seules manches dont la correction a été révélée."""
import csv
import io

POINTS_PER_CORRECT = 100


def points(correct):
    return POINTS_PER_CORRECT * int(bool(correct))


def leaderboard(store, code, dataset, token):
    with store.tx() as db:
        p = store._party(db, code, dataset)
        store._actor(db, p, token)
        phase = p['phase']
        revealed = p['idx'] + int(phase == 'revealed')
        rows = db.execute('''SELECT t.name, COUNT(a.idx) AS played,
            COALESCE(SUM(a.correct),0) AS correct
            FROM teams t LEFT JOIN answers a
              ON a.code=t.code AND a.name=t.name AND a.idx < ?
            WHERE t.code=? GROUP BY t.name''', (revealed, code)).fetchall()
    result = [dict(r) for r in rows]
    result.sort(key=lambda r: (-r['correct'], r['name'].casefold(), r['name']))
    previous = None
    rank = 0
    for i, r in enumerate(result, 1):
        r['points'] = POINTS_PER_CORRECT * r['correct']
        if r['points'] != previous:
            rank = i
            previous = r['points']
        r['rank'] = rank if revealed else None
    return {'revealed': revealed, 'finished': phase == 'finished', 'rows': result}


def winners(board):
    if not board['finished']:
        return []
    return [r['name'] for r in board['rows'] if r['rank'] == 1]


def results_csv(board):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, delimiter=';')
    writer.writerow(['Rang', 'Équipe', 'Manches corrigées', 'Bonnes réponses', 'Points'])
    for r in board['rows']:
        name = r['name']
        if name.lstrip().startswith(('=', '+', '-', '@')):
            name = "'" + name
        writer.writerow([r['rank'], name, r['played'], r['correct'], r['points']])
    return stream.getvalue().encode('utf-8-sig')
