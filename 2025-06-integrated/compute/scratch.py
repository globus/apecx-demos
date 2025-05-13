"""
Tutorial endpoint uses older python

```
pyenv install 3.11.8
pyenv local 3.11.8

python3 -m venv .venv
source .venv/bin/activate
pip install globus_compute_sdk globus_sdk

# ...run this script

```
"""

from globus_compute_sdk import Client, Executor
from globus_sdk import UserApp
from globus_compute_sdk.serialize import ComputeSerializer, CombinedCode

app = UserApp(client_id="5f4fc571-4fa2-4d84-ab6e-567d5245af7a")
cc = Client(app=app)

def add_func(a, b):
    return a + b

def multiply_func(a, b):
    return a * b

def do_math(a, b):
    # a * (a+b)
    return multiply_func(a, add_func(a, b))



serializer = ComputeSerializer(strategy_code=CombinedCode())
with Executor(
        endpoint_id='4b116d3c-1703-4f8f-9f6f-39921e5864df',
        serializer=serializer,
) as gce:
    # ... then submit for execution, ...
    future = gce.submit(do_math, 5, 10)
    print(future.result())
