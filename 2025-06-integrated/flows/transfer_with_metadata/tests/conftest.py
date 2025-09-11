import json
import os
import logging

from dotenv import dotenv_values
from globus_sdk import (
    FlowsClient,
    SpecificFlowClient,
    UserApp, FlowsAPIError
)
from globus_sdk.scopes import FlowsScopes, SpecificFlowScopeBuilder
import pytest

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@pytest.fixture(scope='session')
def config() -> dict:
    fn = os.path.join(
        os.path.dirname(__file__),
        '.env'
    )
    if not os.path.isfile(fn):
        raise Exception('Must provide .env file in tests folder with required config')
    return dotenv_values(fn)


@pytest.fixture(scope='session')
def user_app(config) -> UserApp:
    # Setup
    fid = config['GLOBUS_FLOW_DEBUG_ID']
    fscope = SpecificFlowScopeBuilder(fid)

    app = UserApp(
        client_id=config['GLOBUS_CLIENT_ID'],
        # Encode scopes up front so we only have to log in once
        scope_requirements={
            'auth.globus.org': ['openid', 'profile', 'email'],
            'flows.globus.org': [FlowsScopes.all],
            fid: [fscope.user]
        }
    )
    app.login()
    return app


@pytest.fixture(scope='session')
def flows_client(user_app) -> FlowsClient:
    # Ensures that the workflow definition in Globus is current and correct
    fc = FlowsClient(app=user_app)
    return fc


@pytest.fixture(scope='session')
def flow_id(config, flows_client) -> str:
    """
    Ensure that the remote (server) flow ID is in sync with local definitions, then return flow ID

    This is a fixture with permanent side effects!
    """
    fid = config['GLOBUS_FLOW_DEBUG_ID']

    loc = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..'
        ),
    )

    print('looking for defs in', loc)
    with open(os.path.join(loc, 'flow_definition.json'), 'r') as f:
        flow_def = json.load(f)

    with open(os.path.join(loc, 'input_schema.json'), 'r') as f:
        schema_def = json.load(f)

    try:
        resp = flows_client.update_flow(
            fid,
            definition=flow_def,
            input_schema=schema_def
        )
    except FlowsAPIError as e:
        logger.error(e.errors)
        raise e

    if resp.http_status != 200:
        raise Exception(f"Could not update existing flow {flow_id}: {resp.http_status} (code {resp.http_reason})")

    return fid


@pytest.fixture(scope='session')
def specific_flow_client(user_app, flow_id: str) -> SpecificFlowClient:
    return SpecificFlowClient(flow_id=flow_id, app=user_app)
