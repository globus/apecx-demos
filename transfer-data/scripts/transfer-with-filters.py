"""
Perform a transfer, leveraging the power of filters. This isn't a fully generic reusable script, but may be useful for example purposes.

Call via CLI
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

def parse_target(location: str):
    """Allow CLI-friendly `source[:path]` syntax for copies, where path is optional"""
    loc = location.split(':')
    coll = loc[0]
    path = loc[1] if len(loc) > 1 else '/'
    return coll, path

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'client_id',
        type=str_ne,
        help='The Globus oauth native/thick client ID to use for user credential requests'
    )
    parser.add_argument('source', help='Source UUID[:path]')
    parser.add_argument('dest', help='Destination UUID[:path]')
    parser.add_argument('-v', help='Verbose output', action='store_true')
    return parser.parse_args()


def create_client(client_id: str, s_coll: str, d_coll: str) -> TransferClient:
    app = UserApp(client_id=client_id)
    client = TransferClient(app=app)
    # TODO: This is quite the footnote: https://globus-sdk-python.readthedocs.io/en/stable/services/transfer.html#globus_sdk.TransferClient.add_app_data_access_scope
    #   What do we do for HA / guest collections? (delve into the abyss)
    # For now will only accept a mapped collection- we can either check type in script or, better, implement access alternative here
    client.add_app_data_access_scope(s_coll)
    client.add_app_data_access_scope(d_coll)
    return client


def build_transfer_options(client: TransferClient, s_coll, s_path, d_coll, d_path, verbose=False) -> TransferData:
    """
    Build options for a specific type of transfer: one source/dest item pair, recursive,
    with filters unique to this dataset
    """
    tdata = TransferData(
        client,
        s_coll,
        d_coll,
        label="SDK example",

        # These aren't the system default values, but I prefer them to always be true
        encrypt_data=True,  # if your endpoint doesn't support encryption, talk to your sysadmin
        preserve_timestamp=True,  # Where possible. In s3, globus follows rec practice and saves this as a custom tag.
        # Always on by default, but these are useful to know about
        sync_level="checksum",
        notify_on_failed=True,
        notify_on_inactive=True,
        notify_on_succeeded=True,  # you may not want notifications for nightly timed backups!
    )

    tdata.add_item(s_path, d_path, recursive=True)
    # By default, sync copies everything, and the first rule specified takes precedence. To copy only one file type,
    #   we need both specific include AND general exclude
    # CAUTION: the exclude must explicitly specify type=None. If you exclude only type=file, you may see more stuff
    #   copied than you expect. Since the CLI *only* supports these filters on files, the SDK is the most reliable way
    #   to perform filter operations (you can do it via the webapp, but it's not super intuitive)
    tdata.add_filter_rule("*.cff", method="include", type='file')
    tdata.add_filter_rule("*", method="exclude", type=None)

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
        logging.basicConfig(level=logging.DEBUG)

    s_coll, s_path = parse_target(args.source)
    d_coll, d_path = parse_target(args.dest)

    client = create_client(args.client_id, s_coll, d_coll)

    # See: https://globus-sdk-python.readthedocs.io/en/stable/services/transfer.html#globus_sdk.TransferClient.submit_transfer
    transfer_options = build_transfer_options(client, s_coll, s_path, d_coll, d_path)
    resp = client.submit_transfer(transfer_options)

    print('Transfer complete! Final task status is: ', report_result(client, resp.data['task_id']))
