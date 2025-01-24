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

# This demo intended to be run from within the scripts folder to avoid import issues
from common import (
    build_transfer_options,
    parse_target,
    requires_data_access_scope,
    str_ne,
)

logger = logging.getLogger(__name__)


def add_transfer_scopes(client: TransferClient, coll_id: str) -> TransferClient:
    """
    If (and only if) something is a non-HA GCSv5 mapped collection, special extra login scopes are required.
    https://globus-sdk-python.readthedocs.io/en/stable/services/transfer.html#globus_sdk.TransferClient.add_app_data_access_scope

    NOTE that transfer and timer clients have similar helper methods, but not the same name
    """
    # Don't run this method with a guest collection, because authorization will fail with "unknown scopes" error.
    #   Sorry. This feature was created for humans, and hence it looks weird when expressed as code.
    logger.info('Adding transfer scopes for mapped collection. You can avoid this double login by using guest collections instead')
    return client.add_app_data_access_scope(coll_id)


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

    This example is based on INCLUDING certain files (whitelist).
    See the timer demo for an example based on EXCLUDING (blacklist).
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
    transfer_options = build_transfer_options(s_coll, s_path, d_coll, d_path)
    transfer_options = add_demo_filters(transfer_options)
    resp = client.submit_transfer(transfer_options)

    task_id = resp.data['task_id']

    # For the demo script, we check result by long polling. But in the real world, no need!
    #   You'll get emailed a status report when the task is completed.
    polled_result = report_result(client, task_id)
    print(f"Transfer task '{task_id}' complete! Final task status is: ", polled_result)
