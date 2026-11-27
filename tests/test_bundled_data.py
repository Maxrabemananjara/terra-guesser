import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from modules.bundled_data import load_bundled

class BundledDataTests(unittest.TestCase):
    def test_all_modes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertIsNone(load_bundled(root))
            (root/'terra_v5.part1').write_bytes(b'abc')
            with self.assertRaises(ValueError): load_bundled(root)
            (root/'terra_v5.part2').write_bytes(b'def')
            with self.assertRaises(ValueError): load_bundled(root)
            with patch('modules.bundled_data.V5_SHA256',hashlib.sha256(b'abcdef').hexdigest()):
                self.assertEqual(load_bundled(root),b'abcdef')
                (root/'terra_guesser_public_v5.zip').write_bytes(b'abcdef')
                self.assertEqual(load_bundled(root),b'abcdef')
                (root/'terra_guesser_public_v5.zip').write_bytes(b'bad')
                with self.assertRaises(ValueError): load_bundled(root)
