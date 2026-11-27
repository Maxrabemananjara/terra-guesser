import gzip,io,json,unittest,zipfile,os,copy
from pathlib import Path
import pandas as pd
from modules.rounds import load_rounds, eligible_rounds, new_game, submit_answer, advance, read_member, CATALOG

class RoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=Path(os.environ['TERRA_DATA_ZIP']).read_bytes()
        with zipfile.ZipFile(io.BytesIO(cls.archive)) as z:
            cls.geo=json.loads(gzip.decompress(z.read('data/geographic/ensembles_paysagers.geojson.gz')))
            cls.matrix=pd.read_csv(z.open('data/processed/matrice_filtres_application.csv'),dtype={'code_ensem':str,'present':str})
        cls.records=load_rounds('.',cls.archive,cls.geo,cls.matrix)
        cls.codes=set(cls.matrix.code_ensem)

    def test_catalogue(self):
        self.assertEqual(len(self.records),2)
        self.assertEqual(len(eligible_rounds(self.records, demo=True)),2)
        self.assertEqual(len(eligible_rounds(self.records)),0)
        self.assertEqual({r['code_ensem'] for r in self.records},{'605','710'})

    def test_all_answers(self):
        for record in self.records:
            for code in self.codes:
                g=new_game([record],1)
                submit_answer(g,record,code,self.codes)
                self.assertEqual(g['answers'][0]['correct'],code==record['code_ensem'])
                with self.assertRaises(ValueError): submit_answer(g,record,code,self.codes)
                advance(g)
                self.assertEqual(g['index'],1)

    def test_full_game(self):
        g=new_game(self.records,2)
        for r in self.records:
            with self.assertRaises(ValueError): advance(g)
            submit_answer(g,r,r['code_ensem'],self.codes)
            advance(g)
        self.assertEqual(len(g['answers']),2)
        self.assertTrue(all(a['correct'] for a in g['answers']))
        with self.assertRaises(ValueError): advance(g)

    def test_invalid_game(self):
        for n in (0,3,-1,1.5):
            with self.assertRaises(ValueError): new_game(self.records,n)
        g=new_game(self.records,2)
        with self.assertRaises(ValueError): submit_answer(g,self.records[1],'710',self.codes)
        with self.assertRaises(ValueError): submit_answer(g,self.records[0],'0',self.codes)

    def test_image_paths(self):
        with self.assertRaises(ValueError): read_member('.',self.archive,'../photo.jpg')

if __name__=='__main__': unittest.main()
