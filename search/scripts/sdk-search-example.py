#!/usr/bin/env python3
"""
A simple example that uses the Globus Python SDK to perform a search.

 The SDK exposes the full power of Globus Search, and is a good choice for building webapps, or any scripts
    that want to process the output. We will use it to demonstrate advanced control of what results are shown,
    like only showing a specific subset for an admin or curator page.

Call via CLI
"""
import argparse
import json
import os.path

from globus_sdk import (
    SearchClient, UserApp
)

def str_ne(value):
    """Validator rejects empty strings"""
    if not value:
        raise ValueError("Must not be an empty string")
    return value

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('search_index', help='UUID of the search index to use')
    parser.add_argument(
        'client_id',
        type=str_ne,
        help='The Globus oauth native/thick client ID to use for user credential requests'
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    search_index = args.search_index

    # Compares the results of a search index query using an authenticated vs unauthenticated query
    unauthenticated = SearchClient()

    your_account = UserApp("authenticated", client_id=args.client_id)
    authenticated = SearchClient(app=your_account)

    # If you follow the tutorial, extra results will be added that are private to authenticated users,
    # Demonstrate that the same query can yield different results for a search term with a hidden record
    unauth_query = unauthenticated.search(search_index, "darpa")  # expect 1 result for unauthenticated
    auth_query = authenticated.search(search_index, "darpa")  # expect 2 results: some entries are only visible when logged in

    print('Number of results (unauthenticated): {}'.format(unauth_query.data['total']))
    print('Number of results (authenticated): {}'.format(auth_query.data['total']))

    # Now filter by principal sets and show how authenticated query results change!
    q_fn = os.path.abspath(os.path.join(os.path.dirname(__file__), '../queries/filter_principal_sets.json'))
    with open(q_fn, 'r') as f:
        role_query_doc = json.load(f)

    role_query = authenticated.post_search(search_index, role_query_doc)


    print('Number of results (authenticated, curators principal set only): {}'.format(role_query.data['total']))
    first_result = role_query.data['gmeta'][0]['entries'][0]
    print('Query matched principal sets for: ', first_result['matched_principal_sets'])
