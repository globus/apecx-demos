"""
Lists the contents of whatever is in a remote directory
https://docs.globus.org/api/transfer/file_operations/#dir_listing_filtering

Results are filtered based on set criteria. This is useful if you have to work with a dataset that is already
  delivered, and want to guarantee operations are only performed on certain results. For example, a workflow
  may not want to add everything to the search index (think OS-default "junk files", or QC script debug logs)

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
    return parser.parse_args()


def create_client(client_id: str, s_coll: str) -> TransferClient:
    app = UserApp(client_id=client_id)
    client = TransferClient(app=app)
    # TODO: This is quite the footnote: https://globus-sdk-python.readthedocs.io/en/stable/services/transfer.html#globus_sdk.TransferClient.add_app_data_access_scope
    #   What do we do for HA / guest collections? (delve into the abyss)
    # For now will only accept a mapped collection- we can either check type in script or, better, implement access alternative here
    client.add_app_data_access_scope(s_coll)
    return client


if __name__ == "__main__":
    args = parse_args()
    s_coll, s_path = parse_target(args.source)

    client = create_client(args.client_id, s_coll)

    # Compare two ls queries of same directory to see effect of filters
    resp = client.operation_ls(s_coll, s_path, show_hidden=True)
    print(f"Unfiltered ls yields {resp.data['length']} results out of {resp.data['total']} eligible in directory")

    resp = client.operation_ls(
        s_coll,
        s_path,
        show_hidden=False,
        filter={
            # Search for files (not folders), excluding empty files or known junk
            "name": ["!~.*", "!Thumbs.db", "!desktop.ini", "!~*.pyc"],
            "type": "file",
            "size": "!0"
        }
    )
    # Same directory as above shows different count of total files in directory results. This is due to
    #   `show_hidden` flag being applied before we start filtering: fewer files are "eligible" to filter!
    print(f"Filtered ls yields {resp.data['length']} results out of {resp.data['total']} eligible in directory")
