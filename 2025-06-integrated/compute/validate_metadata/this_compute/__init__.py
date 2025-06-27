"""
Validate that a globus-hosted file complies with JSON-formatted datacite schema

Doing this all in one function allows bypassing the 256k state size limit if the data were passed across multiple
    steps in flow state.

* Receive automation-friendly globus service account credentials via envvar (CLIENT_ID, CLIENT_SECRET)
* Use credentials to download a file via HTTPS from a collection known to allow HTTPS (subscribed, non-HA, guest)
* Validate JSON against the datacite schema and report errors back to the flow (list of 0 or more items)
"""
import logging
import os

from globus_sdk import GlobusAPIError
from this_compute.gcs_https import read_file_from_gcs, write_file_to_https
from this_compute.validators import validate_datacite_json

logger = logging.getLogger(__name__)



def validate_gcs_json_datacite(
    collection_id: str,
    metadata_path: str, *,
    # Kwargs for local testing, only
    client_id: str= None,
    client_secret: str= None,
):
    """
    DEPRECATED
    In an early version of this feature, compute permissions were read only, and this read metadata from a
        file that was part of the user's existing dataset. Validation of the file was performed separate from flow inputs.
    """
    try:
        CLIENT_ID = client_id or os.environ['GLOBUS_CLIENT_ID']
        CLIENT_SECRET = client_secret or os.environ['GLOBUS_CLIENT_SECRET']
    except KeyError:
        raise Exception("Globus Client ID and Client Secret must be set via worker environment variables")

    content = read_file_from_gcs(CLIENT_ID, CLIENT_SECRET, collection_id, metadata_path)

    res = validate_datacite_json(content)

    if len(res) > 0:
        logger.error('Invalid user input!')
        logger.error(res)
    return {
        "errors": res,
        # Put count in payload directly, as this is easier to reference with an expression in the flow logic
        "n_errors": len(res),
        "data": content
    }


def write_metadata_to_remote_file(
        *,
        collection_id: str,
        dataset_path: str,
        metadata_path: str,

        identifier: str,
        search_metadata: dict,

        # For debugging only
        client_id: str= None,
        client_secret: str= None
    ):
    """
    Note: due to quirks of Step Functions, all args are presented as required kwargs.
        (it's easier to use jsonpath syntax with kwargs)
    """
    # Make sure output is logged to stdout, so that compute will capture logs TODO: improve use of named loggers
    logging.basicConfig(level=logging.INFO)

    try:
        CLIENT_ID = client_id or os.environ['GLOBUS_CLIENT_ID']
        CLIENT_SECRET = client_secret or os.environ['GLOBUS_CLIENT_SECRET']
    except KeyError:
        raise Exception("Globus Client ID and Client Secret must be set via worker environment variables")

    # TODO: break "payload formatting" and "file writing" into separate functions, if the app grows
    #   For now we combine them in a single function because that has lower latency when used via flows APs
    combined_search_metadata = {
        "identifier": identifier,
        **search_metadata,  # We rely on the flow to define this datacite schema and ensure it contains only the expected params
        "globus": {
            "collection_id": collection_id,
            "path": dataset_path
        }
    }

    try:
        resp = write_file_to_https(
            client_id, client_secret,
            collection_id,
            metadata_path,
            json=combined_search_metadata
        )
    except GlobusAPIError as e:
        # Can include failure to login, or failures in auth stage (such as attempting HTTPS on a GCP collection)
        return {
            "status": "FAILURE",
            "error": e.code,
            "code": e.http_status,
        }
    # Return info required to consume the exact search payload (for index ingest) and check result
    # NOTE: File write may fail
    return {
        "status": "SUCCESS" if resp.ok else "FAILURE",
        "code": resp.status_code,
        "data": combined_search_metadata,
    }


# Alias makes it easier to use the generic "register GCE function(s)" helper scripts
main = write_metadata_to_remote_file
