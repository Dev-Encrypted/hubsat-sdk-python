"""Read a single antenna page; requires HUBSAT_TOKEN with read:antenas."""
import os
from hubsat_api import HubSatClient

if __name__ == '__main__':
    client = HubSatClient(os.environ['HUBSAT_TOKEN'])
    page = client.get_antenas(query={'limit': 10})
    print({'ids': [row['id'] for row in page['data']], 'next_cursor': page['meta']['next_cursor']})
