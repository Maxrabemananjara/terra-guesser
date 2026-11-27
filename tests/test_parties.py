import json, tempfile, unittest, zipfile, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from modules.parties import Store, PartyError

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'test.sqlite'; self.s=Store(self.path)
        with zipfile.ZipFile(os.environ['TERRA_DATA_ZIP']) as z:
            self.records={r['id']:r for r in json.loads(z.read('data/photos/rounds.json'))['rounds']}
        self.order=list(self.records); self.code,self.owner=self.s.create('v4',self.order)
        self.tokens=[self.s.join(self.code,'v4',f'Equipe {i}',4+i%2) for i in range(5)]
    def ctl(self,a,token=None): self.s.control(self.code,'v4',token or self.owner,a)
    def submit(self,t,r,zone): self.s.submit(self.code,'v4',t,r,zone,self.records,{'605','710'})
    def state(self,t=None): return self.s.state(self.code,'v4',t or self.owner)
    def test_game(self):
        self.ctl('start')
        for i,r in enumerate(self.order):
            self.assertEqual(self.state()['index'],i)
            with self.assertRaises(PartyError): self.ctl('reveal')
            with ThreadPoolExecutor(max_workers=5) as pool: list(pool.map(lambda t:self.submit(t,r,self.records[r]['code_ensem']),self.tokens))
            self.assertEqual(self.state()['submitted'],5)
            for t in self.tokens:
                self.assertNotIn('correct',self.state(t)['own'])
                with self.assertRaises(PartyError): self.submit(t,r,'605')
            self.ctl('reveal')
            self.assertTrue(all(self.state(t)['own']['correct'] for t in self.tokens)); self.ctl('next')
        self.assertEqual(self.state()['phase'],'finished')
    def test_security(self):
        for token in (self.tokens[0],'fake'):
            with self.assertRaises(PartyError): self.ctl('start',token)
        with self.assertRaises(PartyError): self.s.state(self.code,'bad',self.owner)
        with self.assertRaises(PartyError): self.s.join(self.code,'v4','Equipe 0',4)
        with self.assertRaises(PartyError): self.s.join(self.code,'v4','Autre',3)
        self.ctl('start')
        with self.assertRaises(PartyError): self.s.join(self.code,'v4','Autre',4)
        with self.assertRaises(PartyError): self.submit(self.owner,self.order[0],'605')
        with self.assertRaises(PartyError): self.submit(self.tokens[0],self.order[1],'605')
        with self.assertRaises(PartyError): self.submit(self.tokens[0],self.order[0],'999')
    def test_persistence(self):
        self.ctl('start'); self.submit(self.tokens[0],self.order[0],'710')
        self.s=Store(self.path); self.assertEqual(self.state(self.tokens[0])['own'],{'selected':'710'})
    def test_concurrent_duplicate(self):
        self.ctl('start')
        def attempt(_):
            try: self.submit(self.tokens[0],self.order[0],'605'); return True
            except PartyError: return False
        with ThreadPoolExecutor(max_workers=10) as pool: results=list(pool.map(attempt,range(10)))
        self.assertEqual(sum(results),1)
    def test_two_teams_required(self):
        code,owner=self.s.create('v4',self.order)
        self.s.join(code,'v4','Solo',4)
        with self.assertRaises(PartyError): self.s.control(code,'v4',owner,'start')

if __name__=='__main__': unittest.main(verbosity=2)
