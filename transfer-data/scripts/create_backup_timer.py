"""
Create a timer that runs a transfer on a set schedule. This is a narrow example (not aimed at reuse).

For daily use, consider using the official Globus CLI instead!!
`globus timer create transfer [OPTIONS] SOURCE_ENDPOINT_ID[:SOURCE_PATH] DEST_ENDPOINT_ID[:DEST_PATH]`

Ref:
https://docs.globus.org/cli/reference/timer_create_transfer/

This script is mainly for educational purposes. But in general, the CLI doesn't expose all features (like filters).
    This script shows how you can go deeper and access hidden functionality with the full power of the python SDK.

This can be used to synchronize between machines/environments on a regular basis, or run backups. A single uniform API
    lets you write the same backup code even if you are transferring to multiple different kinds of storage.
https://www.globus.org/automation

This script is called via CLI.
"""
import argparse
import logging

from globus_sdk import (
    UserApp,
    RecurringTimerSchedule,
    TimersClient,
    TransferData,
    TransferTimer, TransferClient,
)

from common import (
    build_transfer_options,
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
    parser.add_argument('source', help='Source UUID:path', type=parse_target)
    parser.add_argument('dest', help='Source UUID:path', type=parse_target)
    parser.add_argument('-v', help='Verbose output', action='store_true')

    return parser.parse_args()


def add_transfer_scopes(client: TimersClient, coll_id: str) -> TimersClient:
    """
    If (and only if) something is a non-HA GCSv5 mapped collection, special extra login scopes are required.
    https://globus-sdk-python.readthedocs.io/en/stable/services/transfer.html#globus_sdk.TransferClient.add_app_data_access_scope

    NOTE that transfer and timer clients have similar helper methods, but not the same name
    """
    # Don't run this method with a guest collection, because authorization will fail with "unknown scopes" error.
    #   Sorry. This feature was created for humans, and hence it looks weird when expressed as code.
    logger.info('Adding transfer scopes for mapped collection. You can avoid this double login by using guest collections instead')
    return client.add_app_transfer_data_access_scope(coll_id)


def create_client(client_id: str, s_coll: str, d_coll: str) -> TimersClient:
    """Create the access client and set required user permissions"""
    app = UserApp(client_id=client_id)

    # This script needs two clients: one to see if this is a mapped collection, and another to handle transfer stuff
    transfer_client = TransferClient(app=app)
    timers_client = TimersClient(app=app)

    if requires_data_access_scope(transfer_client, s_coll):
        logger.warning(f'Collection {s_coll} is a mapped collection, and your consent may expire and cause timers to fail. We strongly recommend guest collections for timers.')
        add_transfer_scopes(timers_client, s_coll)

    if requires_data_access_scope(transfer_client, d_coll):
        logger.warning(
            f'Collection {d_coll} is a mapped collection, and your consent may expire and cause timers to fail. We strongly recommend guest collections for timers.')
        add_transfer_scopes(timers_client, d_coll)
    return timers_client


def add_demo_filters(options: TransferData) -> TransferData:
    """
    Add some upload filters that are only relevant to this demo. Separated out for clarity.

    This example is based on EXCLUDING certain files (blacklist).
    See the transfer demo for an example based on INCLUDING.
    """
    # The list of filters available to timers is limited to filename patterns. Unlike the `ls` collection feature,
    #   we don't have an option to do things like "exclude by file size" (or other common backup conventions).
    #   More features/filter options may be added if there is demand.
    options.add_filter_rule(type='file', method='exclude', name='*.git')
    return options


if __name__ == "__main__":
    args = parse_args()
    if args.v:
        # Verbose mode: make sure to output logs to console
        logging.basicConfig(level=logging.DEBUG)

    s_coll, s_path = args.source
    d_coll, d_path = args.dest

    client = create_client(args.client_id, s_coll, d_coll)

    transfer_options = build_transfer_options(s_coll, s_path, d_coll, d_path)
    transfer_options = add_demo_filters(transfer_options)

    daily_timer = TransferTimer(
        name="test_timer",
        schedule=RecurringTimerSchedule(24 * 60 * 60),
        body=transfer_options
    )
    resp = client.create_timer(daily_timer)



    if args.v:
        # The timers API is exposed via the CLI, but not publicly documented. This script uses the payload for our
        #   own automation, so it might break. Print the full response to aid in debugging.
        from pprint import pprint as pp
        pp(resp.data)

    # See active timers, and clean up dead ones from example scripts! https://app.globus.org/activity/timers
    timer_id = resp.data['timer']['job_id']
    print(f'Timer created. Visit https://app.globus.org/activity/timers/{timer_id}/overview to manage and see results.')
    print('Once the timer has succeeded (or failed), be sure to delete it! Due to the time-delayed nature of things, this script does not clean up for you.')
