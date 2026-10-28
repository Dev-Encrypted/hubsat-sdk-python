import json
import threading
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from hubsat_api import HubSatClient, HubSatApiError
from hubsat_api.operations import OPERATIONS

TOKEN = 'hub_' + 'a' * 48


class Handler(BaseHTTPRequestHandler):
    requests = []
    def log_message(self, *_args):
        pass

    def do_GET(self):
        self.requests.append((self.path, dict(self.headers)))
        if self.headers.get('If-None-Match'):
            self.send_response(304)
            self.send_header('ETag', '"etag-1"')
            self.end_headers()
        elif 'plans' in self.path:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'data': [{'id': 2}]}).encode())
        elif 'openapi' in self.path:
            self.send_response(302)
            self.send_header('Location', self.server.base_url + '/capture')
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.end_headers()
            self.wfile.write(b'%PDF')

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.requests.append((self.path, dict(self.headers), data))
        self.send_response(408)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'code': 'TIMEOUT', 'error': 'Timeout', 'requestId': 'request-1'}).encode())


class ClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.base_url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        Handler.requests = []
        self.client = HubSatClient(TOKEN, self.server.base_url + '/api/integracao')

    def test_catalogue_and_encoded_parameters(self):
        document = json.loads((Path(__file__).resolve().parents[1] / 'docs/openapi.json').read_text(encoding='utf-8'))
        expected = {(method.upper(), route) for route, item in document['paths'].items()
                    for method in ('get', 'post', 'put', 'patch', 'delete') if method in item}
        self.assertEqual({(op['method'], op['path']) for op in OPERATIONS.values()}, expected)
        response = self.client.listar_planos_guest_wifi(path={'routerId': 'router/id'}, query={'active': False})
        self.assertEqual(response['data'][0]['id'], 2)
        self.assertIn('router%2Fid/plans?active=false', Handler.requests[0][0])
        self.assertEqual(Handler.requests[0][1]['Authorization'], 'Bearer ' + TOKEN)
        self.assertEqual(Handler.requests[0][1]['User-Agent'], 'HubSatSDK-Python/1')

    def test_mutation_timeout_never_retries(self):
        with self.assertRaises(HubSatApiError) as result:
            self.client.criar_assinante_cadastro(body={'nome': 'João'}, idempotency_key='subscriber-001')
        self.assertEqual(result.exception.code, 'TIMEOUT')
        self.assertEqual(result.exception.request_id, 'request-1')
        self.assertEqual(len(Handler.requests), 1)
        self.assertEqual(Handler.requests[0][2], {'nome': 'João'})

    def test_redirect_refused_and_binary_download(self):
        public = next(name for name, op in OPERATIONS.items() if op['path'] == '/v1/openapi.json')
        with self.assertRaises(HubSatApiError) as result:
            self.client.call(public)
        self.assertEqual(result.exception.status, 302)
        self.assertFalse(any('/capture' in row[0] for row in Handler.requests))
        download = next(name for name, op in OPERATIONS.items() if op['path'] == '/v1/relatorios/exportacoes/{exportId}/download')
        self.assertEqual(self.client.call(download, path={'exportId': 'a' * 64}), b'%PDF')

    def test_invalid_targets(self):
        with self.assertRaises(ValueError):
            HubSatClient(TOKEN, 'http://example.com/api/integracao')
        with self.assertRaises(ValueError):
            self.client.listar_planos_guest_wifi(path={'routerId': '..'})
        with self.assertRaises(ValueError):
            self.client.call('__class__')
        self.assertNotIn(TOKEN, repr(self.client))

    def test_conditional_response_preserves_status_and_headers(self):
        result = self.client.call_with_response('listarPlanosGuestWifi', path={'routerId': 'r'}, if_none_match='"etag-1"')
        self.assertEqual(result.status, 304)
        self.assertEqual(result.headers.get('ETag'), '"etag-1"')
        self.assertIsNone(result.data)


if __name__ == '__main__':
    unittest.main()
