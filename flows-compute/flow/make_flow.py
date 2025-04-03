"""
Generate and run an example workflow with the following steps:


1. Copy a file to a specified location
2. Run a validation function
3. Place data in a specified location (eg globus search index)
"""


import json
import logging
from pprint import pp
import time
import typing as t

from globus_sdk import FlowsClient, UserApp, GlobusHTTPResponse, FlowsAPIError, SpecificFlowClient
from globus_compute_sdk import Client as ComputeClient


logger = logging.getLogger(__name__)

#######################
# Compute functions used to add custom logic into a single step of the workflow
######################
def _file_validation_func(gcs_root=None, path: str=None):
    """
    Read an input file at an agreed-upon location accessible to this function

    If we want to make this workflow generic, expect that every file validation function will return {status, message, data}.
        Normal file validation errors will fail via `message`, though workflows can also choose to define exception handlers.
    """
    import json
    import os

    if not gcs_root or not path:
        raise Exception("No input folder specified")

    manifest_fn = os.path.join(gcs_root, path, "manifest.json")
    if not os.path.exists(manifest_fn):
        return {
        'status': 'failure',
        'message': f'Manifest file could not be located at {manifest_fn}',
    }

    # The first stab at validation will be: "if a manifest.json file exists, then this can be imported to search"
    with open(manifest_fn, 'r') as f:
        manifest = json.load(f)
    return {
        'status': 'success',
        'message': 'File validated successfully',
        'data': {
            'size': len(manifest),
            'manifest': manifest
        }
    }


def _to_search_entry():
    """A compute function that combines dataset + metadata info"""


#######
# Workflow
def get_example_flow(src_fn, schema_fn, func_id):
    """Load a specific example workflow definition, and fill in the placeholders for assets created by this script"""
    with open(src_fn, 'r') as f:
        flow = json.load(f)

    with open(schema_fn, 'r') as f:
        schema = json.load(f)

    # TODO: In future, set appropriate func ID keys on compute step to hardcode into the flow
    #   For now, we can get away as is by making things variables to flow input (which leaks some info to user)
    return flow, schema


def register_function(client: ComputeClient, func: t.Callable) -> str:
    """
    Register a function and return the uuid

    TODO: Add permissions controls (like groups)
    """
    func_id = client.register_function(func, public=False)
    logger.info(f'Registered function  "{func.__name__}" {func_id}')
    return func_id


def register_flow(client: FlowsClient, flow_def: dict, schema_def: dict) -> str:
    try:
        resp = client.create_flow("Example flow", flow_def, schema_def, keywords=['apecx', 'apecx-demo'])
    except FlowsAPIError as e:
        # Provide additional info for debugging
        pp(e.errors, sort_dicts=False, indent=2)
        raise e

    if resp.http_status != 200:
        raise Exception(f"Could not create flow: {resp.http_status} (code {resp.http_reason})")

    return resp.data['id']


def update_flow(client: FlowsClient, flow_id, flow_def: dict, schema_def: dict) -> str:
    try:
        resp = client.update_flow(flow_id, definition=flow_def, input_schema=schema_def)
    except FlowsAPIError as e:
        # Provide additional info for debugging
        pp(e.errors, sort_dicts=False, indent=2)
        raise e

    if resp.http_status != 200:
        raise Exception(f"Could not update existing flow {flow_id}: {resp.http_status} (code {resp.http_reason})")

    return resp.data['id']

def run_flow(client: SpecificFlowClient, body: dict, label: str=None, tags: list[str]=None) -> (str, str):
    try:
        resp = client.run_flow(body, label=label, tags=tags)
    except FlowsAPIError as e:
        # Provide additional info for debugging
        pp(e.errors, sort_dicts=False, indent=2)
        raise e

    if resp.http_status != 201:
        raise Exception(f"Could not run flow: {resp.http_status} (code {resp.http_reason})")

    logger.info(f'Initiated flow "{resp.data["run_id"]}"')
    return resp.data['run_id'], resp.data['status']


def check_flow_status(client: FlowsClient, run_id: str) -> str:
    status = 'ACTIVE'
    while status == 'ACTIVE':
        time.sleep(15)
        run = client.get_run(run_id)
        status = run.data['status']

    logger.info(f'Run id {run_id} had final resolved status "{status}"')
    return status


def cleanup(cc: ComputeClient, fc: FlowsClient, func_ids: list[str], flow_id: str):
    """Clean up resources created for this demo, to leave a clean slate at end of script"""
    cc.delete_function(func_id)
    fc.delete_flow(flow_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    EXISTING_FLOW_ID = '8f62db7d-ac7f-4bba-9292-2fa3a26fb5ee' # None
    app = UserApp(client_id="5f4fc571-4fa2-4d84-ab6e-567d5245af7a")
    cc = ComputeClient(app=app)
    fc = FlowsClient(app=app)

    func_id = register_function(cc, _file_validation_func)
    flow_def, schema_def = get_example_flow(
        'data/validate_in_place/flow.json',
        'data/validate_in_place/input_schema.json',
        func_id
    )
    if EXISTING_FLOW_ID is None:
        # For exploratory purposes only: easier to re-define one flow in place while debugging
        flow_id = register_flow(fc, flow_def, schema_def)
    else:
        flow_id = update_flow(fc, EXISTING_FLOW_ID, flow_def, schema_def)

    # If creating a new flow, this might trigger re-auth
    sfc = SpecificFlowClient(flow_id, app=app)

    run_id, start_status = run_flow(
        sfc,
        {
            "source": {
                "id": "dba0d7c0-1f63-44d1-bcd0-76865d3d44a0",  # GUEST collection
                "path": "/2025-04-flows-demo/source"  # A folder
            },
            "intermediate": {
                # Guest collection on a server where GCS + GCE are both installed
                # GCE and GCS don't know about each other, so there's some blind faith involved; both options have to
                #   be under control of the workflow definition, not the end user.
                # Remember that GCE and GCS both need POSIX permissions on the target folder;
                #   this doesn't go through globus auth. Compute functions with file operations are thus coupled to a
                #   specific (set of) specially configured endpoints.
                "id": 'e0bf746e-d4db-48ff-b1d4-4c113956148c',
            },
            "compute": {
                "endpoint_id": "ab18eb68-2fb7-411a-9b72-5468bb6ced78",
                "gcs_root": '/share/gcs-demo',
            },
            "validation_function_uuid": func_id,
        },
        label="Test run",
        tags=['apecx', 'apecx-demo'],
    )

    if start_status != 'ACTIVE':
        final_status = start_status
        print(f'Run {run_id} failed with status {final_status}')
    else:
        final_status = check_flow_status(fc, run_id)

    print('See web logs: ', f'https://app.globus.org/runs/{run_id}/logs')


    # # This script is purely for demo purposes, so we can do something unusual: delete the resources when a flow runs successfully once
    # # But if the script failed, we keep the resources because we assume we're debugging in a REPL and will manually run again
    # if final_status == 'SUCCEEDED':
    #     cleanup(cc, fc, [func_id], flow_id)
    # else:
    #     print("The run failed. Keeping the following resources:")
    #     print('* func ID:', func_id)
    #     print('* flow ID:', flow_id)
