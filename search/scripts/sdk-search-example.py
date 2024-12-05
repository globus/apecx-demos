"""
A simple example that uses the Globus Python SDK to perform a search.

 The SDK exposes the full power of Globus Search, and is a good choice for building webapps, or any scripts
    that want to process the output. We will use it to demonstrate advanced control of what results are shown,
    like only showing a specific subset for an admin or curator page.
"""
import json
import os.path

from globus_sdk import (
    SearchClient, UserApp
)


if __name__ == '__main__':
    GSI_UUID = '531c5ef8-02ff-4b0c-9652-8a033350ba53'
    G_CLIENT_ID = '5f4fc571-4fa2-4d84-ab6e-567d5245af7a'

    # Compares the results of a search index query using an authenticated vs unauthenticated query
    unauthenticated = SearchClient()

    your_account = UserApp("authenticated", client_id=G_CLIENT_ID)  #abought native client ID
    authenticated = SearchClient(app=your_account)

    # If you follow the tutorial, extra results will be added that are private to authenticated users,
    # Demonstrate that the same query can yield different results for a search term with a hidden record
    unauth_query = unauthenticated.search(GSI_UUID, "darpa")  # expect 1 result
    auth_query = authenticated.search(GSI_UUID, "darpa")  # expect 2 results: some entries are only visible when logged in

    print('Number of results (unauthenticated): {}'.format(unauth_query.data['total']))
    print('Number of results (authenticated): {}'.format(auth_query.data['total']))

    # Now filter by principal sets and show how authenticated query results change!
    q_fn = os.path.abspath(os.path.join(os.path.dirname(__file__), '../queries/filter_principal_sets.json'))
    with open(q_fn, 'r') as f:
        role_query_doc = json.load(f)

    role_query = authenticated.post_search(GSI_UUID, role_query_doc)


    print('Number of results (authenticated, curators principal set only): {}'.format(role_query.data['total']))
    first_result = role_query.data['gmeta'][0]['entries'][0]
    print(first_result)
    print('Query matched principal sets for: ', first_result['matched_principal_sets'])
