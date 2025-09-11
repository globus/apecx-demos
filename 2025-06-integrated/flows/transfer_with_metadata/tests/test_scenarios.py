import json
import os
from pprint import pprint as pp
import time

from globus_sdk import (FlowsClient, FlowsAPIError, SpecificFlowClient, GlobusHTTPResponse)
import pytest

############################
# Helpers for use by tests

def _load_scenario(name: str) -> dict:
    # TODO: A lot of info is hardcoded into json files for initial prototyping; make this generic in future once we have a basic system working
    fn = os.path.join(os.path.dirname(__file__), 'scenarios', f'input_{name}.json')
    with open(fn, 'r') as f:
        return json.load(f)


def _run_flow(client: SpecificFlowClient, body: dict, label: str=None, tags: list[str]=None) -> GlobusHTTPResponse:
    try:
        resp = client.run_flow(body, label=label, tags=tags)
    except FlowsAPIError as e:
        # Provide additional info for debugging
        pp(e.errors, sort_dicts=False, indent=2)
        raise e

    if resp.http_status != 201:
        raise Exception(f"Could not run flow: {resp.http_status} (code {resp.http_reason})")

    print(f'Initiated flow "{resp.data["run_id"]}"')
    # Status is useful if the API rejects flow submission ("failed before it started")
    return resp


def _get_last_state(resp_data: dict) -> GlobusHTTPResponse:
    status = resp_data['status']
    if status == 'SUCCEEDED':
        return resp_data['details']['output']['state_name']
    elif status == 'FAILED':
        return resp_data['details']['details']['exception']
    else:
        raise Exception(f"Unhandled last state: {status}")


def _check_flow_status(client: FlowsClient, run_id: str) -> GlobusHTTPResponse:
    status = 'ACTIVE'
    resp = None
    while status == 'ACTIVE':
        time.sleep(10)
        resp = client.get_run(run_id)
        status = resp.data['status']

    print(f'Run id {run_id} had final resolved status "{status}"')
    return resp


def _run_until_complete(
        flows_client: FlowsClient,
        specific_flow_client: SpecificFlowClient,
        body: dict,
        label: str=None,
        tags: list[str]=None
) -> GlobusHTTPResponse:
    resp = _run_flow(specific_flow_client, body, label=label, tags=tags)
    run_id = resp.data['run_id']
    start_status = resp.data['status']

    if start_status != 'ACTIVE':
        status = start_status
    else:
        resp = _check_flow_status(flows_client, run_id)
        status = resp.data['status']

    print(f'Run id {run_id} had final resolved status "{status}"')
    return resp


##################
# Test some scenarios
def test_works_with_valid_metadata(flows_client, specific_flow_client):
    """Should run entire flow start to finish and return success, with a specific step marked as the last item"""
    name = 'good_metadata'
    payload = _load_scenario('good_metadata')

    res = _run_until_complete(flows_client, specific_flow_client, payload, f'unittests - {name}')
    status = res.data['status']
    assert status == 'SUCCEEDED'
    assert _get_last_state(res.data) == 'SearchIngest'



def test_fails_with_bad_metadata(flows_client, specific_flow_client):
    """Should fail instantly on submission due to invalid input schema"""
    name = 'bad_metadata'
    payload = _load_scenario(name)

    with pytest.raises(FlowsAPIError, match='disallowed_extra_field'):
        _run_until_complete(flows_client, specific_flow_client, payload, f'unittests - {name}')


def test_fails_source_folder_validation(flows_client, specific_flow_client):
    name = 'source_path_not_a_folder'
    payload = _load_scenario(name)

    res = _run_until_complete(flows_client, specific_flow_client, payload, f'unittests - {name}')

    status = res.data['status']
    assert status == 'FAILED'

    assert _get_last_state(res.data) == 'ErrorInvalidSourceDest'


def test_fails_source_unreachable(flows_client, specific_flow_client):
    name = 'invalid_source_id'
    payload = _load_scenario(name)

    res = _run_until_complete(flows_client, specific_flow_client, payload, f'unittests - {name}')

    status = res.data['status']
    assert status == 'FAILED'

    assert _get_last_state(res.data) == 'FailSetupGeneric'

