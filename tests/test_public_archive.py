"""Contrôle du paquet V5 réellement ajouté au dépôt."""
import unittest
from pathlib import Path
from modules.bundled_data import load_bundled
from modules.interface_data import load_data,web_geometry
from modules.thematic_layers import load_catalog,load_layer
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
