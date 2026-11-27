"""Tests d'intégrité et de rendu du paquet V3."""
import os
import unittest
from pathlib import Path
from shapely.geometry import shape
from modules.interface_data import load_data, web_geometry, filter_zones
from modules.thematic_layers import load_catalog, load_layer, make_thematic_map


class ThematicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        p = os.environ.get('TERRA_DATA_ZIP')
        cls.archive = Path(p).read_bytes() if p else None
        cls.matrix, cls.geo = load_data(cls.root, cls.archive)
        cls.catalog = load_catalog(cls.root, cls.archive, cls.matrix)

    def test_all_layers(self):
        counts = {'grand': 0, 'typo': 0, 'clc': 0}
        ids = {k: set() for k in counts}
        for code, entry in self.catalog.items():
            data = load_layer(self.root, self.archive, code, entry)
            kind = 'grand' if code.startswith('grand_') else 'typo' if code.startswith('typo_') else 'clc'
            for feature in data['features']:
                geom = shape(feature['geometry'])
                self.assertTrue(geom.is_valid and not geom.is_empty)
                identifier = feature['properties']['id_source']
                self.assertNotIn(identifier, ids[kind])
                ids[kind].add(identifier)
                counts[kind] += 1
        self.assertEqual(counts, {'grand': 115, 'typo': 301, 'clc': 39645})

    def test_render(self):
        code = 'viticulture'
        entry = self.catalog[code]
        compatible, uncertain = filter_zones(self.matrix, [])
        data = load_layer(self.root, self.archive, code, entry)
        m = make_thematic_map(web_geometry(self.geo), compatible, uncertain, None, [(code, entry, data)])
        html = m.get_root().render()
        self.assertIn(entry['color'], html)
        self.assertEqual(len(compatible), 115)
