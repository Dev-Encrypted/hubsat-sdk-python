"""Explicit test-account write. Store HUBSAT_IDEMPOTENCY_KEY before running."""
import argparse
import os
from hubsat_api import HubSatClient

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create one synthetic subscriber in an authorized test account.')
    parser.add_argument('--confirm-test-account', action='store_true', required=True)
    parser.parse_args()
    client = HubSatClient(os.environ['HUBSAT_TOKEN'])
    result = client.criar_assinante_cadastro(
        body={'nome': 'Cliente de teste SDK', 'tipo': 'PF'},
        idempotency_key=os.environ['HUBSAT_IDEMPOTENCY_KEY'],
    )
    print({'id': result['data']['id']})
