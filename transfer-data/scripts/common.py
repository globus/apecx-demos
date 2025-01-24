"""
Common functions used by multiple demos
"""
import logging
import typing as ty

from globus_sdk import TransferData, TransferClient

logger = logging.getLogger(__name__)


def str_ne(value):
    """Validator rejects empty strings"""
    if not value:
        raise ValueError("Must not be an empty string")
    return value


def parse_target(location: str) -> (str, str):
    """
    Allow CLI-friendly `source:path` syntax for copies. Path is required.
    """
    loc = location.split(':')
    if len(loc) != 2:
        # Mapped collections present the path on the filesystem, rather than just the directories a user can see
        # So
        # We want to be careful to avoid requesting a transfer of "way too much" by accident, so user must always specify path
        raise ValueError("Must specify `source:path`")

    coll, path = loc
    return coll, path


def requires_data_access_scope(client: TransferClient, coll_id: str) -> bool:
    """
    Determine if this collection requires special extra auth permissions before
        we can use this script to create a transfer. Non-HA GCSv5 mapped collections require extra data access scopes.

    This is an extremely pedantic thing, which mostly comes up if you're writing a script that does things on behalf
        of other users a lot. This script is demonstrating deep quirky stuff.

    tl;dr, mapped collections are odd because most Guest Collections have opted into the full range of globus features.
    Some institutions prefer that mapped collections ("behave like the host system") should get affirmative consent
    from the user before a script can do anything on the user's behalf. To make things even trickier, once a user
    has authorized a specific client + collection once, Globus auth will remember this (under "manage my consents")
    and not require the "data access scope" grant again

    See:
        https://globus-sdk-python.readthedocs.io/en/stable/services/timer.html#globus_sdk.TimersClient.add_app_transfer_data_access_scope
        https://docs.globus.org/api/transfer/endpoints_and_collections/#entity_types

    If you want to script timers and transfers, it is easier to authenticate using guest collections, not mapped.
        Our guidance: Design your project accordingly!
    """
    r = client.get_endpoint(coll_id)
    if not r.http_status == 200:
        logger.debug(f"Guest collection endpoint returned status {r.http_status} - {r.http_reason}")
        logger.debug(r)
        raise Exception(f"Error encountered while querying status for endpoint {coll_id}")
    return (r.data['high_assurance'] is False) and (r.data['entity_type'] == 'GCSv5_mapped_collection')


def build_transfer_options(s_coll, s_path, d_coll, d_path) -> TransferData:
    """
    Build base options for the transfer, moving data from one source to one destination.
    """
    tdata = TransferData(
        source_endpoint=s_coll,
        destination_endpoint=d_coll,
        label="SDK example",

        # Values useful to this situation
        encrypt_data=True,  # if your endpoint doesn't support encryption, talk to your sysadmin
        preserve_timestamp=True,  # Where possible. In s3, globus follows rec practice and saves this as a custom tag.
        verify_checksum=True,  # May be slower, but more robust

        # Always on by default, but these are useful to know about
        sync_level="checksum",
        notify_on_failed=True,
        notify_on_inactive=True,
        notify_on_succeeded=True,  # For an immediate one-time transfer, notifications are helpful
    )

    tdata.add_item(s_path, d_path, recursive=True)

    return tdata
