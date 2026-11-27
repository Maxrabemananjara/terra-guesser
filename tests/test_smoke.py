"""Contrôle du démarrage réel Streamlit, sans données privées."""
import unittest
from streamlit.testing.v1 import AppTest

class SmokeTests(unittest.TestCase):
    def test_app_starts(self):
        at = AppTest.from_file('app.py', default_timeout=30).run()
        self.assertEqual(len(at.exception), 0, str(at.exception))
