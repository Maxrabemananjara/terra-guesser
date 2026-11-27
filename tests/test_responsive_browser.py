"""Vérification de l'application réelle avec Playwright et données synthétiques."""
import os
import re
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
                        page.get_by_role('checkbox',name='filtre_00',exact=True).check()
                        expect(page.locator('.st-key-terra_metrics').get_by_text('58',exact=True)).to_be_visible(timeout=30000)
                        expect(page.locator('.st-key-terra_metrics').get_by_text('57',exact=True)).to_be_visible(timeout=30000)
                        page.get_by_text('Filtres et calques d’observation',exact=True).click()
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

    def test_collective_browser(self):
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            contexts=[browser.new_context(viewport={'width':390 if i else 1280,'height':900}) for i in range(3)]
            teacher,one,two=[c.new_page() for c in contexts]
            try:
                teacher.goto('http://localhost:8765')
                teacher.get_by_text('Collectif',exact=True).click(timeout=30000)
                teacher.get_by_role('button',name='Créer la partie').click(timeout=30000)
                code_text=teacher.get_by_text(re.compile(r'Code de participation : [A-Z2-9]{6}'))
                expect(code_text).to_be_visible(timeout=30000)
                code=re.search(r'[A-Z2-9]{6}$',code_text.inner_text().strip()).group()
                for page,name in ((one,'Alpha'),(two,'Beta')):
                    page.goto('http://localhost:8765')
                    page.get_by_text('Collectif',exact=True).click(timeout=30000)
                    page.get_by_text('Rejoindre une partie (équipe)',exact=True).click(timeout=30000)
                    page.get_by_role('textbox',name='Code de participation').fill(code)
                    page.get_by_role('textbox',name='Nom de l’équipe (sans nom d’élève)').fill(name)
                    page.get_by_role('textbox',name='Nom de l’équipe (sans nom d’élève)').press('Tab')
                    page.get_by_role('button',name='Rejoindre',exact=True).click()
                    expect(page.get_by_text('En attente du lancement par l’enseignant. Actualise la partie.')).to_be_visible(timeout=30000)
                teacher.get_by_role('button',name='Actualiser la partie').click()
                teacher.get_by_role('button',name='Lancer la partie').click(timeout=30000)
                for page,guess in ((one,'100'),(two,'101')):
                    page.get_by_role('button',name='Actualiser la partie').click()
                    expect(page.get_by_role('heading',name='Observer le paysage')).to_be_visible(timeout=30000)
                    page.get_by_text('Sélection alternative par code de zone',exact=True).click()
                    page.get_by_role('textbox',name='Code de zone').fill(guess)
                    page.get_by_role('textbox',name='Code de zone').press('Tab')
                    page.get_by_role('button',name='Retenir le code').click()
                    page.get_by_role('button',name='Valider ma réponse').click()
                    expect(page.get_by_text('Réponse enregistrée. En attente de la correction collective.')).to_be_visible(timeout=30000)
                    expect(page.get_by_role('heading',name='Correction géographique')).to_have_count(0)
                teacher.get_by_role('button',name='Actualiser la partie').click()
                teacher.get_by_role('button',name='Révéler la correction').click(timeout=30000)
                for page,correct in ((one,True),(two,False)):
                    page.get_by_role('button',name='Actualiser la partie').click()
                    expect(page.get_by_role('heading',name='Correction géographique')).to_be_visible(timeout=30000)
                    expect(page.get_by_text('Bonne réponse !' if correct else 'Ce n’est pas le bon ensemble paysager.',exact=True)).to_be_visible()
                teacher.get_by_role('button',name='Manche suivante / terminer').click(timeout=30000)
                expect(teacher.get_by_text('Équipe gagnante : Alpha',exact=True)).to_be_visible(timeout=30000)
                for page in (one,two):
                    page.get_by_role('button',name='Actualiser la partie').click()
                    expect(page.get_by_text('Équipe gagnante : Alpha',exact=True)).to_be_visible(timeout=30000)
            finally:
                Path('browser-artifacts').mkdir(exist_ok=True)
                for name,page in zip(('teacher','team1','team2'),(teacher,one,two)):
                    page.screenshot(path=f'browser-artifacts/{name}.png',full_page=True)
                for context in contexts: context.close()
                browser.close()
