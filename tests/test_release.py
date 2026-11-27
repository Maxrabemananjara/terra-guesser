import tempfile
import unittest
from pathlib import Path
from modules.parties import Store, PartyError
from modules.scoring import leaderboard

class ReleaseTests(unittest.TestCase):
    def test_stale_teacher_action(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d)/'test.sqlite')
            code, owner = store.create('test', ['r1','r2'])
            tokens = [store.join(code,'test', name,4) for name in ('A','B')]
            records = {'r1':{'code_ensem':'605'}, 'r2':{'code_ensem':'710'}}
            store.control(code,'test',owner,'start',expected_index=0)
            for t in tokens: store.submit(code,'test',t,'r1','605',records,{'605','710'})
            store.control(code,'test',owner,'reveal',expected_index=0)
            store.control(code,'test',owner,'next',expected_index=0)
            for t in tokens: store.submit(code,'test',t,'r2','710',records,{'605','710'})
            with self.assertRaises(PartyError): store.control(code,'test',owner,'reveal',expected_index=0)
            self.assertEqual(store.state(code,'test',owner)['phase'],'playing')
            self.assertEqual(leaderboard(store,code,'test',owner)['revealed'],1)
            store.control(code,'test',owner,'reveal',expected_index=1)
            with self.assertRaises(PartyError): store.control(code,'test',owner,'next',expected_index=0)
            store.control(code,'test',owner,'next',expected_index=1)
            self.assertTrue(leaderboard(store,code,'test',owner)['finished'])
