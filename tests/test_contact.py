"""Exercise the PHP API locally without sending any email."""
import http.cookiejar
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('php'), 'PHP is required for contact API tests')
class ContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.servers = []
        cls.urls = []
        for test_mode in ('1', '0'):
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env = {**os.environ, 'NOR_CONTACT_TEST_MODE': test_mode}
            server = subprocess.Popen(
                ['php', '-d', f'session.save_path={cls.temp.name}', '-d', 'sendmail_path=/usr/bin/false',
                 '-S', f'127.0.0.1:{port}', '-t', str(ROOT)],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cls.servers.append(server)
            url = f'http://127.0.0.1:{port}/contact.php'
            cls.urls.append(url)
            for _ in range(100):
                try:
                    build_opener().open(url, timeout=1).close()
                    break
                except OSError:
                    time.sleep(.03)
            else:
                cls.tearDownClass()
                raise RuntimeError('PHP test server failed to start')

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:
            server.terminate()
            server.wait(timeout=5)
        cls.temp.cleanup()

    def setUp(self):
        self.client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, fields=None, production=False):
        url = self.urls[int(production)]
        request = Request(url, data=urlencode(fields).encode() if fields is not None else None)
        try:
            response = self.client.open(request)
        except HTTPError as error:
            response = error
        try:
            return response.status, json.loads(response.read())
        finally:
            response.close()

    def valid(self, production=False):
        _, result = self.request(production=production)
        return dict(token=result['token'], navn='Local test', epost='test@example.invalid',
                    emne='Local verification', melding='Test message, never delivered.', tlf='', website='')

    def test_missing_csrf_token_rejected(self):
        self.assertEqual(self.request({'navn': 'test'})[0], 403)

    def test_invalid_email_rejected(self):
        data = self.valid()
        data['epost'] = 'not-an-email'
        self.assertEqual(self.request(data)[0], 422)

    def test_header_injection_rejected(self):
        data = self.valid()
        data['emne'] = 'Subject\r\nBcc: other@example.invalid'
        self.assertEqual(self.request(data)[0], 422)

    def test_honeypot_rejected(self):
        data = self.valid()
        data['website'] = 'spam'
        self.assertEqual(self.request(data)[0], 422)

    def test_oversized_body_rejected(self):
        data = self.valid()
        data['melding'] = 'x' * 25000
        self.assertEqual(self.request(data)[0], 413)

    def test_non_scalar_field_rejected(self):
        data = self.valid()
        del data['epost']
        data['epost[]'] = 'test@example.invalid'
        self.assertEqual(self.request(data)[0], 422)

    def test_success_is_explicit_test_mode_and_rate_limited(self):
        code, response = self.request(self.valid())
        self.assertEqual(code, 200)
        self.assertTrue(response['ok'])
        self.assertTrue(response['test_mode'])
        self.assertEqual(self.request(self.valid())[0], 429)

    def test_transport_failure_never_claims_success(self):
        code, response = self.request(self.valid(production=True), production=True)
        self.assertEqual(code, 503)
        self.assertNotIn('ok', response)


if __name__ == '__main__':
    unittest.main()
