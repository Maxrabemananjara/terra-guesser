"""Vérification de l'application réelle avec Playwright et données synthétiques."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect
from tests.browser_fixture import create_fixture

class ResponsiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        fixture=Path(cls.tmp.name)/'fixture.zip'
        create_fixture(fixture)
        env={**os.environ,'TERRA_DATA_ZIP':str(fixture),'TERRA_PARTIES_DB':str(Path(cls.tmp.name)/'party.sqlite')}
        cls.server=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.headless=true','--server.port=8765'],env=env)
        cls.addClassCleanup(cls.server.terminate)
        for _ in range(60):
            try:
                with urlopen('http://localhost:8765/_stcore/health',timeout=1) as r:
                    if r.status==200: break
            except OSError: time.sleep(1)
        else: raise RuntimeError('Streamlit non disponible')

    def test_five_viewports(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for width in (360,390,768,1024,1920):
                with self.subTest(width=width):
                    page=browser.new_page(viewport={'width':width,'height':900},has_touch=width<=1024)
                    try:
                        page.goto('http://localhost:8765')
                        page.get_by_text('Individuel',exact=True).click(timeout=30000)
                        page.get_by_role('button',name='Commencer la partie').click(timeout=30000)
                        expect(page.get_by_role('heading',name='Observer le paysage')).to_be_visible(timeout=30000)
                        expect(page.locator('.st-key-terra_photo_grid img')).to_have_count(4,timeout=30000)
                        expect(page.locator('.st-key-terra_map iframe')).to_be_attached(timeout=30000)
                        photo=page.locator('.st-key-terra_photo_grid').bounding_box()
                        mapbox=page.locator('.st-key-terra_map').bounding_box()
                        self.assertEqual(mapbox['y']>photo['y']+20,width<=1024)
                        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width+1)
                        page.get_by_text('Filtres et calques d’observation',exact=True).click()
                        expect(page.get_by_text('filtre_00',exact=True).first).to_be_visible()
                        page.get_by_text('Sélection alternative par code de zone',exact=True).click()
                        page.get_by_role('textbox',name='Code de zone').fill('100')
                        page.get_by_role('textbox',name='Code de zone').press('Tab')
                        page.get_by_role('button',name='Retenir le code').click()
                        page.get_by_role('button',name='Valider ma réponse').click()
                        expect(page.get_by_role('heading',name='Correction géographique')).to_be_visible(timeout=30000)
                        expect(page.get_by_text('Bonne réponse !',exact=True)).to_be_visible()
                        self.assertEqual(page.locator('[data-testid="stException"]').count(),0)
                    finally:
                        Path('browser-artifacts').mkdir(exist_ok=True)
                        page.screenshot(path=f'browser-artifacts/{width}.png',full_page=True)
                        page.close()
            browser.close()
