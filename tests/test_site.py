"""Regression checks for the static site's navigation, assets, and legacy routes."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids = set()
        self.references = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag in ('a', 'link') and attrs.get('href'):
            self.references.append(attrs['href'])
        if tag in ('img', 'script') and attrs.get('src'):
            self.references.append(attrs['src'])


class StaticSiteTests(unittest.TestCase):
    def test_local_links_assets_and_fragments_exist(self):
        for path in ROOT.rglob('*.html'):
            doc = Document(path)
            for reference in doc.references:
                url = urlsplit(reference)
                if url.scheme or url.netloc:
                    continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                if target.is_dir():
                    target /= 'index.html'
                with self.subTest(page=str(path.relative_to(ROOT)), reference=reference):
                    self.assertTrue(target.is_file(), f'Missing file: {target}')
                    if url.fragment:
                        self.assertIn(url.fragment, Document(target).ids)

    def test_css_assets_exist(self):
        for path in ROOT.glob('*.css'):
            for reference in re.findall(r'url\([\'"]?([^\)\'"\s]+)', path.read_text()):
                url = urlsplit(reference)
                if not url.scheme and not url.netloc:
                    with self.subTest(css=path.name, reference=reference):
                        self.assertTrue((path.parent / unquote(url.path)).is_file())

    def test_photo_files_contain_webp_data(self):
        photos = list((ROOT / 'images').glob('*.webp'))
        self.assertGreaterEqual(len(photos), 5)
        for path in photos:
            with self.subTest(image=path.name):
                data = path.read_bytes()
                self.assertTrue(data.startswith(b'RIFF') and data[8:12] == b'WEBP')

    def test_pages_include_navigation_home_and_shared_behavior(self):
        for path in ROOT.glob('*.html'):
            text = path.read_text()
            with self.subTest(page=path.name):
                self.assertIn('id="site-navigation"', text)
                self.assertIn('href="./"', text)
                self.assertIn('src="site.js"', text)
                self.assertNotIn('onerror=', text)
                self.assertNotIn('https://www.norrengjoring.no/wp-content/', text)

    def test_all_old_page_routes_have_static_fallbacks(self):
        slugs = ['om-oss', 'kontakt', 'tjenester', 'daglig-renhold', 'hovedreingjoring',
                 'flyttevask', 'dodbo', 'puss-og-rens', 'byggrengjoring-2',
                 'skuring-og-boning-av-gulv', 'our-team-7-2']
        redirects = (ROOT / '.htaccess').read_text()
        for slug in slugs:
            with self.subTest(route=slug):
                self.assertTrue((ROOT / slug / 'index.html').is_file())
                self.assertIn(f'^{slug}/?$', redirects)

    def test_map_is_not_loaded_by_initial_html(self):
        text = (ROOT / 'kontakt.html').read_text()
        self.assertNotIn('<iframe', text)
        self.assertIn('data-map', text)


if __name__ == '__main__':
    unittest.main()
