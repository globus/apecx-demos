"""
Globus Connect Server Files can be downloaded via HTTPS, which is nice for building web portals. See:
https://docs.globus.org/globus-connect-server/v5/https-access-collections/#overview

This script demonstrates how to find the URL for a file and download a single item via HTTPS download.
    For small files like data tables or pictures, the file can then be embedded directly in the page
    (like via HTML `img` tag) without the need to download.
"""
import argparse
import logging
import os.path

import requests

from globus_sdk import TransferClient, UserApp

from common import (
    parse_target,
    requires_data_access_scope,
    str_ne,
)


logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'client_id',
        type=str_ne,
        help='The Globus oauth native/thick client ID to use for user credential requests'
    )
    parser.add_argument('source', help='Guest Collection UUID:path', type=parse_target)
    parser.add_argument('-v', help='Verbose output', action='store_true')
    return parser.parse_args()


def create_client(client_id, coll_id: str):
    app = UserApp(client_id=client_id)
    client = TransferClient(app=app)

    if requires_data_access_scope(client, coll_id):
        # Engage "zero subtlety" mode. Public data sharing portals shouldn't use highly access-restricted mapped collections.
        #    I mean, yes, the features exist if you're building tools for just your own lab, but we won't even pretend
        #    to demonstrate that with this script.
        raise NotImplementedError('Although mapped collections can use this feature, we strongly encourage use of guest collections for data portal use cases')
    return client


def download_file(base_url: str, remote_path: str, local_filename: str):
    """
    Download a file locally. The actual API has nuances aimed at web browsers (like content-disposition headers);
        we don't cover those in this simple demo. Consult the docs to see the full range of useful options available.
    """
    # This may fail if there is no such file!
    if not remote_path.startswith('/'):
        remote_path = '/' + remote_path

    url = base_url + remote_path

    try:
        # Globus works with big data! Use streaming downloads instead of fitting it all into memory
        resp = requests.get(url, stream=True)
    except Exception as e:
        logger.exception(f'Unknown download failure at URL {url}')
        return False

    if resp.status_code != requests.codes.ok:
        # File not found will yield 404.
        # Connection refused errors are possible if server firewall rules are not configured
        logger.error(f'Download of {url} failed with status code {resp.status_code}')
        return False

    with open(local_filename, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=16 * 1024):
            f.write(chunk)
    return True


if __name__ == '__main__':
    args = parse_args()

    if args.v:
        logging.basicConfig(level=logging.INFO)

    s_coll, s_path = args.source

    client = create_client(args.client_id, s_coll)

    collection_details = client.get_endpoint(s_coll)

    if collection_details['high_assurance']:
        # Warn the user to check for edge cases: is this endpoint a good choice for a web portal?
        print('Review the documentation closely; high assurance collections may impose special authentication restrictions or timeouts')

    if not collection_details['subscription_id']:
        print('HTTPS sharing may require your endpoint to be part of a Globus subscription')

    base_url = collection_details['https_server']

    if not base_url:
        print('This endpoint does not support HTTPS sharing. Consult the documentation for details.')
        print('https://docs.globus.org/globus-connect-server/v5/https-access-collections/')

    fn = os.path.basename(s_path)
    if '.' not in fn:
        # In practice, users are usually querying something like a globus search index, where the curator has carefully listed only things valid to download.
        # This demo is trusting CLI user input with knowledge of the file system, so let's be Extra Paranoid
        raise NotImplementedError('This script can only download files, not folders')

    if download_file(base_url, s_path, fn):
        print(f'Successfully downloaded remote file locally to: {fn}')
    else:
        print('Failed to download file. See verbose output for details.')

