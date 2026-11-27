"""Contrôle du paquet V5 réellement ajouté au dépôt."""
import unittest
from pathlib import Path
from modules.bundled_data import load_bundled
from modules.interface_data import load_data,web_geometry,filter_zones
from modules.thematic_layers import load_catalog,load_layer,visible_zones,make_thematic_map
from modules.rounds import load_rounds,eligible_rounds

class PublicArchiveTests(unittest.TestCase):
    def test_release_archive(self):
        root=Path(__file__).resolve().parents[1]
        archive=load_bundled(root)
        self.assertIsNotNone(archive,'Le paquet V5 doit être présent')
        matrix,geo=load_data(root,archive)
        self.assertEqual(len(web_geometry(geo)['features']),115)
        catalog=load_catalog(root,archive,matrix)
        self.assertEqual(len(catalog),31)
        for code,entry in catalog.items():
            self.assertEqual(len(load_layer(root,archive,code,entry)['features']),entry['count'])
        records=eligible_rounds(load_rounds(root,archive,geo,matrix))
        self.assertEqual(len(records),2)
        self.assertTrue(all(len(r['photos'])==4 for r in records))

    def test_isolation_for_every_filter(self):
        root=Path(__file__).resolve().parents[1]
        matrix,geo=load_data(root,load_bundled(root))
        web=web_geometry(geo)
        for code in matrix.code_filtre.unique():
            with self.subTest(code=code):
                remaining,uncertain=filter_zones(matrix,[code])
                visible=visible_zones(web,remaining)
                self.assertEqual({f['properties']['code_ensem'] for f in visible['features']},remaining)
                self.assertTrue(uncertain <= remaining)
        codes=list(matrix.code_filtre.unique())
        remaining,_=filter_zones(matrix,codes)
        self.assertEqual({f['properties']['code_ensem'] for f in visible_zones(web,remaining)['features']},remaining)
        self.assertEqual(visible_zones(web,set())['features'],[])
        ids=[f['properties']['code_ensem'] for f in web['features'][:2]]
        self.assertEqual({f['properties']['code_ensem'] for f in visible_zones(web,set(),ids[0],ids[1])['features']},set(ids))
        m=make_thematic_map(web,{ids[0]},set(),None,[])
        layers=[child for child in m._children.values() if child.__class__.__name__=='GeoJson']
        self.assertEqual(len(layers),1)
        self.assertEqual([f['properties']['code_ensem'] for f in layers[0].data['features']],[ids[0]])
