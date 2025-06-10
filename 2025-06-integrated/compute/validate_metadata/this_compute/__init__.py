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

from this_compute.retrieval import get_file_from_gcs
from this_compute.validators import validate_datacite_json

logger = logging.getLogger(__name__)



def validate_gcs_json_datacite(
    collection_id: str,
    metadata_fn: str, *,
    # Kwargs for local testing, only
    client_id: str= None,
    client_secret: str= None,
):
    try:
        CLIENT_ID = client_id or os.environ['GLOBUS_CLIENT_ID']
        CLIENT_SECRET = client_secret or os.environ['GLOBUS_CLIENT_SECRET']
    except KeyError:
        raise Exception("Globus Client ID and Client Secret must be set via worker environment variables")

    content = get_file_from_gcs(CLIENT_ID, CLIENT_SECRET, collection_id, metadata_fn)

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

# Alias makes it easier to use the generic "register GCE function(s)" helper scripts
main = validate_gcs_json_datacite


if __name__ == '__main__':
    # Just for local testing purposes. Demonstrates how it would be called in GCS.
    COLLECTION_ID = "REPLACEME"  # GUEST-ified personal collection
    # res = main(COLLECTION_ID, '/subfolder/metadata.json') # A good file in my specific collection

    res = main(COLLECTION_ID, '/subfolder/example_metadata_bad.json')

    print('Script has completed. Result: {}'.format(res))
