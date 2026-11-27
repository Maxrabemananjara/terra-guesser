"""Contrôles réels; fournir TERRA_DATA_ZIP ou décompresser les données V2 à la racine."""
import itertools
import os
import unittest
from pathlib import Path

from modules.interface_data import load_data, filter_zones, web_geometry, zones_at_point
from shapely.geometry import shape
from pyproj import Transformer


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        path = os.environ.get('TERRA_DATA_ZIP')
        cls.matrix, cls.geo = load_data(root, Path(path).read_bytes() if path else None)

    def test_matrix(self):
        self.assertEqual(len(self.matrix), 3565)
        self.assertEqual(len(filter_zones(self.matrix, [])[0]), 115)

    def test_filter_combinations(self):
        m = self.matrix
        ids = set(m.code_ensem)
        codes = sorted(m.code_filtre.unique())
        false = {c: set(m.loc[(m.code_filtre == c) & (m.present == 'False'), 'code_ensem']) for c in codes}
        unknown = {c: set(m.loc[(m.code_filtre == c) & m.present.isna(), 'code_ensem']) for c in codes}
        for k in (1, 2, 3):
            for group in itertools.combinations(codes, k):
                got, uncertain = filter_zones(m, group)
                expected = ids - set.union(*(false[c] for c in group))
                self.assertEqual(got, expected)
                self.assertEqual(uncertain, set.union(*(unknown[c] for c in group)) & expected)

    def test_geometries(self):
        web = web_geometry(self.geo)
        self.assertEqual(len(web['features']), 115)
        self.assertTrue(all(shape(f['geometry']).is_valid for f in web['features']))

    def test_clicks(self):
        ids = set(self.matrix.code_ensem)
        project = Transformer.from_crs(2154, 4326, always_xy=True).transform
        for f in self.geo['features']:
            pt = shape(f['geometry']).representative_point()
            lon, lat = project(pt.x, pt.y)
            self.assertIn(str(f['properties']['code_ensem']), zones_at_point(self.geo, lat, lon, ids))
