import tempfile,unittest
from pathlib import Path
from modules.parties import Store, PartyError

class ClassMetadataTests(unittest.TestCase):
    def test_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.sqlite'
            s=Store(p)
            code,owner=s.create('data',['r1'],{'school':'Collège test','level':'6e','class_label':'A'})
            team=s.join(code,'data','Équipe test',4)
            for token in (owner,team):
                self.assertEqual(Store(p).state(code,'data',token)['metadata'],{'school':'Collège test','level':'6e','class_label':'A'})
            with self.assertRaises(PartyError):
                s.create('data',['r1'],{'unexpected':'x'})
            with self.assertRaises(PartyError):
                s.create('data',['r1'],{'school':'a'*81})
