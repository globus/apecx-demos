"""
Use the environment defined by the container to submit a function to Globus Compute
    (based on string as dotted module path)

This helps discourage drift between function registration host and endpoint worker.
"""
import argparse
from importlib import import_module
import logging
import sys
import typing as t

from globus_sdk import (ClientApp, GlobusApp, UserApp)
from globus_compute_sdk import Client as ComputeClient


logger = logging.getLogger(__file__)


def parse_arguments():
    parser = argparse.ArgumentParser()

    # Authentication
    parser.add_argument('client_id', type=str, help='Globus Compute Client ID')
    parser.add_argument('--client_secret', type=str, help='If provided, uses a service account + client secret')
    parser.add_argument(
        'function_name',
        type=str,
        default='this_compute.main',
        help="Module path of the function to register (must be in PYTHONPATH)"
    )

    # Visibility options
    parser.add_argument(
        '--public',
        default=False,
        action='store_true',
        help="Is this function code available for all globus users?"
    )
    parser.add_argument('--group', type=str, help='A globus group uuid to share this function with')

    return parser.parse_args()


#####
# Helpers (from django import_string) allow loading the python function by name.
# This allows registering multiple functions from a single container
def _cached_import(module_path, class_name):
    # Check whether module is loaded and fully initialized.
    if not (
        (module := sys.modules.get(module_path))
        and (spec := getattr(module, "__spec__", None))
        and getattr(spec, "_initializing", False) is False
    ):
        module = import_module(module_path)
    return getattr(module, class_name)


def _import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    try:
        return _cached_import(module_path, class_name)
    except AttributeError as err:
        raise ImportError(
            'Module "%s" does not define a "%s" attribute/class'
            % (module_path, class_name)
        ) from err


def create_app(client_id, client_secret):
    """Register an authentication client. If secret is provided, this will use a service account (allowing automation)"""
    if client_secret:
        return ClientApp(client_id=client_id, client_secret=client_secret)
    return UserApp(client_id=client_id)


def gce_submit_function(app: GlobusApp, func: t.Callable, *, public: bool=False, group: str=None):
    """
    Submit a function to GCE (as a specific user) and return the function ID
    """
    client = ComputeClient(app=app)

    func_id = client.register_function(func, public=public, group=group)
    logger.info(f'Registered GCE function  "{func.__name__}" with ID "{func_id}"')
    return func_id


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    args = parse_arguments()

    func = _import_string(args.function_name)
    app = create_app(args.client_id, args.client_secret)
    func_id = gce_submit_function(app, func, public=args.public, group=args.group)

    logger.info(f'Function successfully registered with ID "{func_id}"')
