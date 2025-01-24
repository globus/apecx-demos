"""
Perform a transfer, leveraging the power of filters. This isn't a fully generic reusable script, but may be useful for example purposes.

This ensures that sensitive data never reaches the server. Mistakes happen, but Globus Transfer provides ways to
    safeguard against accidental data breaches, by establishing a whitelist of allowed file types.

Ths SDK is the recommended way to use filters.

See this article for one example of "the wrong files getting uploaded", with major potential consequences!
https://blog.pypi.org/posts/2024-07-08-incident-report-leaked-admin-personal-access-token/

This script is called via CLI
"""
import argparse
import logging
import time

from globus_sdk import (
    UserApp,

    TransferClient,
    TransferData,
)

logger = logging.getLogger(__name__)


def str_ne(value):
    """Validator rejects empty strings"""
    if not value:
        raise ValueError("Must not be an empty string")
    return value

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

def add_transfer_scopes(client: TransferClient, coll_id: str) -> TransferClient:
    """
    If (and only if) something is a non-HA GCSv5 mapped collection, special extra login scopes are required.
    https://globus-sdk-python.readthedocs.io/en/stable/services/transfer.html#globus_sdk.TransferClient.add_app_data_access_scope
    """
    # Don't run this method with a guest collection, because authorization will fail with "unknown scopes" error.
    #   Sorry. This feature was created for humans, and hence it looks weird when expressed as code.
    logger.info('Adding transfer scopes for mapped collection. You can avoid this double login by using guest collections instead')
    return client.add_app_data_access_scope(coll_id)

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

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'client_id',
        type=str_ne,
        help='The Globus oauth native/thick client ID to use for user credential requests'
    )
    parser.add_argument('source', help='Source UUID:path', type=parse_target)
    parser.add_argument('dest', help='Destination UUID:path', type=parse_target)
    parser.add_argument('-v', help='Verbose output', action='store_true')
    return parser.parse_args()


def create_client(client_id: str, s_coll: str, d_coll: str) -> TransferClient:
    app = UserApp(client_id=client_id)
    client = TransferClient(app=app)

    if requires_data_access_scope(client, s_coll):
        add_transfer_scopes(client, s_coll)

    if requires_data_access_scope(client, d_coll):
        add_transfer_scopes(client, d_coll)
    return client


def add_demo_filters(options: TransferData) -> TransferData:
    """
    Add some upload filters that are only relevant to this demo. Separated out for clarity.

    This example is based on INCLUDING selected files. See timer example in this repo for an EXCLUDE based rule.
    """
    # By default, sync copies everything. To copy only one file type,
    #   we need both specific include (*.cff) AND general exclude (everything else = *).

    # CAUTION: the exclude must explicitly specify type=None. If you exclude only type=file, you may see more stuff
    #   copied than you expect. Since the CLI only supports these filters on *files*, the SDK is the most reliable way
    #   to perform filter operations (you can mostly do it via the webapp, but it's not super intuitive)
    #   Ref: https://docs.globus.org/api/transfer/task_submit/#filter_rules
    options.add_filter_rule("*.cff", method="include", type='file')
    options.add_filter_rule("*", method="exclude", type=None)
    return options


def build_transfer_options(client: TransferClient, s_coll, s_path, d_coll, d_path, verbose=False) -> TransferData:
    """
    Build base options for the transfer, moving data from one source to one destination.
    """
    tdata = TransferData(
        client,
        s_coll,
        d_coll,
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

    if verbose:
        logger.debug("Your transfer options will be reported to the API as:")
        logger.debug(tdata)

    return tdata


def report_result(client: TransferClient, task_id, delay_sec=15, max_sec=3600) -> str:
    """Poll server every n seconds until transfer status resolves, up max interval.
        This is a very short demo, so we picked short times; in the real world, prefer much slower polling, or
         use something like a Globus flow that handles the details internally

    See status list: https://docs.globus.org/api/transfer/task/
    """
    elapsed = 0
    while True and elapsed < max_sec:
        resp = client.get_task(task_id)

        s = resp.data['status']
        if s == 'INACTIVE':
            # Usually user will get email about credential expiration, such as timers + HA
            raise Exception(f'Manual intervention required to resolve task {task_id}- see your email for details')
        elif s == 'ACTIVE':
            # Continue polling until resolved
            elapsed += delay_sec
            time.sleep(delay_sec)
        else:
            # Resolve to SUCCEEDED / FAILED
            return s

    # If we hit max time
    raise Exception("Task did not complete in any way after x time")


if __name__ == "__main__":
    args = parse_args()

    if args.v:
        # Verbose mode: make sure to output logs to console
        logging.basicConfig(level=logging.DEBUG)

    s_coll, s_path = args.source
    d_coll, d_path = args.dest

    client = create_client(args.client_id, s_coll, d_coll)

    # See: https://globus-sdk-python.readthedocs.io/en/stable/services/transfer.html#globus_sdk.TransferClient.submit_transfer
    transfer_options = build_transfer_options(client, s_coll, s_path, d_coll, d_path)
    transfer_options = add_demo_filters(transfer_options)
    resp = client.submit_transfer(transfer_options)

    task_id = resp.data['task_id']

    # For the demo script, we check result by long polling. But in the real world, no need!
    #   You'll get emailed a status report when the task is completed.
    polled_result = report_result(client, task_id)
    print(f"Transfer task '{task_id}' complete! Final task status is: ", polled_result)
