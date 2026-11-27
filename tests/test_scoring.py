import itertools
import tempfile
import unittest
from pathlib import Path
from modules.parties import Store, PartyError
from modules.scoring import leaderboard, points, results_csv, winners


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'scores.sqlite')
        self.records = {'r1': {'code_ensem': '605'}, 'r2': {'code_ensem': '710'}}
        self.names = ['Alpha', 'Beta', 'Gamma']

    def party(self):
        code, owner = self.store.create('test', list(self.records))
        tokens = [self.store.join(code, 'test', n, 4) for n in self.names]
        return code, owner, tokens

    def test_all_64_outcomes(self):
        for outcome in itertools.product((0, 1), repeat=6):
            code, owner, tokens = self.party()
            board = lambda token=owner: leaderboard(self.store, code, 'test', token)
            ctl = lambda action: self.store.control(code, 'test', owner, action)
            self.assertTrue(all(r['rank'] is None for r in board()['rows']))
            ctl('start')
            totals = dict.fromkeys(self.names, 0)
            for idx, (rid, record) in enumerate(self.records.items()):
                for i, token in enumerate(tokens):
                    correct = outcome[idx*3+i]
                    selected = record['code_ensem'] if correct else ('710' if rid == 'r1' else '605')
                    self.store.submit(code, 'test', token, rid, selected, self.records, {'605','710'})
                    self.assertEqual({r['name']:r['points'] for r in board(token)['rows']}, totals)
                ctl('reveal')
                for i, name in enumerate(self.names):
                    totals[name] += 100*outcome[idx*3+i]
                rows = board()['rows']
                self.assertEqual({r['name']:r['points'] for r in rows}, totals)
                for r in rows:
                    self.assertEqual(r['rank'], 1+sum(v>r['points'] for v in totals.values()))
                self.assertEqual(winners(board()), [])
                for token in tokens:
                    self.assertEqual(board(token), board())
                ctl('next')
            final = board()
            self.assertTrue(final['finished'])
            self.assertEqual(set(winners(final)), {n for n,v in totals.items() if v==max(totals.values())})
            self.assertEqual(final['revealed'], 2)
            self.assertEqual(len(results_csv(final).decode('utf-8-sig').splitlines()), 4)

    def test_authentication(self):
        code, owner, tokens = self.party()
        with self.assertRaises(PartyError):
            leaderboard(self.store, code, 'test', 'invalid')
        with self.assertRaises(PartyError):
            leaderboard(self.store, code, 'different', owner)

    def test_points_and_csv(self):
        self.assertEqual(points(True), 100)
        self.assertEqual(points(False), 0)
        self.assertIn("'-1", results_csv({'rows':[{'rank':1,'name':'-1','played':1,'correct':1,'points':100}]}).decode('utf-8-sig'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
