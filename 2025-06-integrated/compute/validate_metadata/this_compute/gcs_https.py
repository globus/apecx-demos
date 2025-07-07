"""
Functions to read and write small files to an (eligible) GCS collection via HTTPS features
"""
import logging
import os
from urllib.parse import urljoin

from globus_sdk import (
    ClientApp,
    GlobusAppConfig,
    TransferClient, AuthAPIError,
)
from globus_sdk.tokenstorage import JSONTokenStorage
import requests


logger = logging.getLogger(__name__)


def _check_filename(filename: str):
    """Very crude validation/sanity checking for untrusted user inputs."""
    path_segs = os.path.split(filename)
    if '.' in path_segs or '..' in path_segs or '~' in path_segs:
        raise Exception(f'Only absolute paths are supported. Rejected filename: {filename}')


def _create_app(client_id, client_secret, collection_id):
    """
    Generate a client app that can log in using credentials from envvars.
        This client identity must have access to the specified collection.
    GCE currently doesn't provide a way to get user credentials, and we use a ClientApp to avoid human-in-the-loop
        authentication
    """
    # When we run a container under `--user $(id -u)`, it doesn't guarantee a home directory.
    #   Ensure cache is writable by using a tmp file, or else SDK calls will fail.
    storage = JSONTokenStorage("/tmp/gsdk_token_cache.json")
    config = GlobusAppConfig(token_storage=storage)
    return ClientApp(
        client_id=client_id,
        client_secret=client_secret,
        config = config,
        scope_requirements={
            'auth.globus.org': ['openid', 'profile', 'email'],
            collection_id: [f'https://auth.globus.org/scopes/{collection_id}/https']
        }
    )


def _requires_data_access_scope(client: TransferClient, coll_id: str) -> bool:
    """
    Standard error checking safeguard: ensures that the target collection is guest (not mapped) and
    """
    r = client.get_endpoint(coll_id)
    if not r.http_status == 200:
        logger.debug(f"Guest collection endpoint returned status {r.http_status} - {r.http_reason}")
        logger.debug(r)
        raise Exception(f"Error encountered while querying status for endpoint {coll_id}")
    return (r.data['high_assurance'] is False) and (r.data['entity_type'] == 'GCSv5_mapped_collection')


def _get_https_url(client: TransferClient, coll_id: str) -> str:
    # FIXME: Consider doing this outside the flow, such as via another action
    #    https://docs.globus.org/api/transfer/action-providers/collection-info/
    ep_info = client.get_endpoint(coll_id)
    if not ep_info.http_status == 200:
        raise Exception('Failed to query endpoint')

    if ep_info['high_assurance']:
        logger.warning(
            'High assurance collections may impose special authentication restrictions or timeouts. Consider using a different collection.')
    req_da_scope = (ep_info.data['high_assurance'] is False) and (
                ep_info.data['entity_type'] == 'GCSv5_mapped_collection')
    if req_da_scope or not ep_info['https_server'] or not ep_info['subscription_id']:
        raise NotImplementedError(
            "This collection does not meet requirements. It must be a guest collection, subscribed, with HTTPS access enabled.")

    return ep_info['https_server']


def _get_https_request_headers(app: ClientApp, collection_id: str) -> dict:
    t = app.token_storage.get_token_data(collection_id)
    return {'Authorization': f'Bearer {t.access_token}'}


def _read_file_from_https(collection_base_url: str, filename: str, auth_headers: dict) -> 'requests.Response':
    url = urljoin(collection_base_url, filename)

    logger.info(f'Requesting file at {url}')

    headers = {
        **auth_headers,
        # Ensure errors are represented as machine-readable JSON
        "X-Requested-With": "XMLHttpRequest",
    }
    res = requests.get(url, headers=headers)
    return res


def _write_file_to_https(collection_base_url: str, filename: str, auth_headers: dict,
                         data=None, json=None) -> 'requests.Response':
    url = urljoin(collection_base_url, filename)

    logger.info(f'Writing file to {url}')

    headers = {
        **auth_headers,
        # Ensure errors are represented as machine-readable JSON
        "X-Requested-With": "XMLHttpRequest",
    }
    res = requests.put(url, data=data, json=json, headers=headers)
    return res


def read_file_from_gcs(client_id: str, client_secret: str, collection_id: str, filename: str) -> 'requests.Response':
    app = _create_app(client_id, client_secret, collection_id)
    client = TransferClient(app=app)

    # This may raise a globus API error
    app.login()

    if _requires_data_access_scope(client, collection_id):
        raise NotImplementedError('Only non-HA guest collections are supported.')

    _check_filename(filename)

    collection_https_url = _get_https_url(client, collection_id)
    headers = _get_https_request_headers(app, collection_id)

    # Note: This returns the raw HTTPS response, so consumer must check status code
    return _read_file_from_https(collection_https_url, filename, headers)


def write_file_to_https(client_id: str, client_secret: str,
                        collection_id: str, filename: str,
                        data=None, json=None):
    """
    Write data to an HA GCS/HA https endpoint. The `data` and `json` args are mutually exclusive and follow the
        serialization rules of `requests.put`
    """
    app = _create_app(client_id, client_secret, collection_id)
    client = TransferClient(app=app)

    try:
        app.login()
    except AuthAPIError:
        raise Exception('User does not have the requested credentials on this collection')

    if _requires_data_access_scope(client, collection_id):
        raise NotImplementedError('Only non-HA guest collections are supported.')

    _check_filename(filename)

    collection_https_url = _get_https_url(client, collection_id)
    headers = _get_https_request_headers(app, collection_id)

    return _write_file_to_https(collection_https_url, filename, headers, data=data, json=json)
