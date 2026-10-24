"""Keep production-domain signals, the sitemap, and page metadata consistent."""
from html.parser import HTMLParser
import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.norrengjoring.no/'


class SEOPage(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.metas = {}
        self.canonicals = []
        self.titles = []
        self.h1s = []
        self.images = []
        self.json_blocks = []
        self.current = None
        self.buffer = []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            key = attrs.get('name') or attrs.get('property')
            self.metas.setdefault(key, []).append(attrs.get('content', ''))
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs['href'])
        if tag == 'img':
            self.images.append(attrs)
        if tag in ('title', 'h1') or tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.current = tag
            self.buffer = []

    def handle_data(self, data):
        if self.current:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == self.current:
            text = ''.join(self.buffer).strip()
            if tag == 'title':
                self.titles.append(text)
            elif tag == 'h1':
                self.h1s.append(text)
            else:
                self.json_blocks.append(json.loads(text))
            self.current = None


class SEOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = {p.name: SEOPage(p) for p in ROOT.glob('*.html') if p.name != '404.html'}

    def test_every_content_page_has_unique_metadata_and_one_h1(self):
        titles, descriptions = [], []
        for name, page in self.pages.items():
            with self.subTest(page=name):
                self.assertEqual(len(page.titles), 1)
                self.assertEqual(len(page.h1s), 1)
                self.assertEqual(len(page.metas['description']), 1)
                self.assertTrue(page.metas['description'][0].strip())
                self.assertNotIn('noindex', page.metas['robots'][0])
                titles += page.titles
                descriptions += page.metas['description']
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(len(descriptions), len(set(descriptions)))

    def test_canonical_and_social_urls_use_final_domain(self):
        for name, page in self.pages.items():
            expected = BASE + ('' if name == 'index.html' else name)
            with self.subTest(page=name):
                self.assertEqual(page.canonicals, [expected])
                self.assertEqual(page.metas['og:url'], [expected])
                self.assertEqual(page.metas['og:locale'], ['nb_NO'])
                for key in ['og:image', 'twitter:image']:
                    url = page.metas[key][0]
                    self.assertTrue(url.startswith(BASE))
                    self.assertTrue((ROOT / urlsplit(url).path.lstrip('/')).is_file())

    def test_sitemap_matches_all_canonical_content_pages(self):
        root = ET.parse(ROOT / 'sitemap.xml').getroot()
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [node.text for node in root.findall('s:url/s:loc', ns)]
        expected = {p.canonicals[0] for p in self.pages.values()}
        self.assertEqual(set(urls), expected)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertNotIn(BASE + '404.html', urls)
        self.assertIn('Sitemap: ' + BASE + 'sitemap.xml', (ROOT / 'robots.txt').read_text())

    def test_structured_data_graph_matches_visible_business_and_service_pages(self):
        for name, page in self.pages.items():
            with self.subTest(page=name):
                self.assertEqual(len(page.json_blocks), 1)
                graph = page.json_blocks[0]['@graph']
                ids = [node['@id'] for node in graph]
                self.assertEqual(len(ids), len(set(ids)))
                business = next(node for node in graph if node['@type'] == 'LocalBusiness')
                self.assertEqual(business['telephone'], '+4790012461')
                self.assertEqual(business['address']['addressLocality'], 'Drammen')
                self.assertEqual(business['url'], BASE)
                self.assertNotIn('aggregateRating', business)
                if name != 'index.html':
                    crumbs = next(node for node in graph if node['@type'] == 'BreadcrumbList')
                    self.assertEqual(crumbs['itemListElement'][-1]['item'], page.canonicals[0])
                for node in graph:
                    if node['@type'] == 'Service':
                        self.assertEqual(node['url'], page.canonicals[0])
                        self.assertEqual(node['provider']['@id'], BASE + '#business')

    def test_images_have_dimensions_and_explicit_alt_attributes(self):
        for name, page in self.pages.items():
            for image in page.images:
                with self.subTest(page=name, image=image.get('src')):
                    self.assertGreater(int(image['width']), 0)
                    self.assertGreater(int(image['height']), 0)
                    self.assertIn('alt', image)

    def test_error_page_is_not_indexable(self):
        error = SEOPage(ROOT / '404.html')
        self.assertIn('noindex', error.metas['robots'][0])
        self.assertFalse(error.canonicals)


if __name__ == '__main__':
    unittest.main()
