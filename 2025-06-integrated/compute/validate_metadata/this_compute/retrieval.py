import logging
from urllib.parse import urljoin

from globus_sdk import ClientApp, TransferClient
import requests

logger = logging.getLogger(__name__)


def _create_app(client_id, client_secret, collection_id):
    """
    Generate a client app that can log in using credentials from envvars.
        This client must have identity access to the specified collection.
    GCE currently doesn't provide a way to get user credentials, and we use a ClientApp to avoid human-in-the-loop
        authentication
    """
    return ClientApp(
        client_id=client_id,
        client_secret=client_secret,
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
            "This collection does not meet requirements. It must be a guest collections, subscribed, with HTTPS access enabled.")

    return ep_info['https_server']


def _get_https_request_headers(app: ClientApp, collection_id: str) -> dict:
    t = app.token_storage.get_token_data(collection_id)
    return {'Authorization': f'Bearer {t.access_token}'}


def _get_file_from_https(collection_base_url: str, filename: str, auth_headers: dict) -> dict:
    url = urljoin(collection_base_url, filename)

    logger.info(f'Requesting file at {url}')

    headers = {
        **auth_headers,
        # Ensure errors are represented as machine-readable JSON
        "X-Requested-With": "XMLHttpRequest",
    }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(f"Failed to retrieve file with code {res.status_code}")

    try:
        return res.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f'Request for URL {url} failed with code {res.status_code}')
        logger.warning(res.text)
        raise Exception('Unreadable json response from {}'.format(url))


def get_file_from_gcs(client_id: str, client_secret: str, collection_id: str, filename: str) -> dict:
    app = _create_app(client_id, client_secret, collection_id)
    client = TransferClient(app=app)

    app.login()

    if _requires_data_access_scope(client, collection_id):
        raise NotImplementedError('Only non-HA guest collections are supported.')

    collection_https_url = _get_https_url(client, collection_id)
    headers = _get_https_request_headers(app, collection_id)

    return _get_file_from_https(collection_https_url, filename, headers)

