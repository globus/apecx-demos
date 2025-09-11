"""
This is mainly used for testing that a function is runnable. (relates to how GCE sometimes exhibits serialization differences across python versions)

It's not used for any production or key deployment steps.
 """
import argparse
import logging
import time

from globus_compute_sdk import Client as ComputeClient
from globus_compute_sdk.errors import TaskPending
from globus_sdk import UserApp


logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('client_id', type=str)
    parser.add_argument('endpoint_id', type=str)
    parser.add_argument('function_id', type=str, help="Run a function UUID previously registered with GCE")

    # TODO Basic version. In future allow non-str args, and kwargs
    parser.add_argument('func_args', nargs="*")
    return parser.parse_args()


def check_result(client: ComputeClient, task_id):
    while True:
        try:
            return client.get_result(task_id)
        except TaskPending:
            logger.debug('Task pending, will recheck in 10 seconds')
            time.sleep(10)
        except Exception as e:
            logger.exception('Task {} failed: {}'.format(task_id, e))
            raise e



if __name__ == '__main__':
    args = parse_args()
    logging.basicConfig(level=logging.INFO)

    app = UserApp(client_id=args.client_id)

    client = ComputeClient(app=app)

    task_id = client.run(
        *args.func_args,
        endpoint_id=args.endpoint_id,
        function_id=args.function_id
    )

    logger.debug("Function submitted with task ID: {}".format(task_id))
    res = check_result(client, task_id)

    logger.info(f'Task ID {task_id} completed.')
    logger.info(res)
