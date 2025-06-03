# Compute functions supporting demos
## Purpose

This module represents compute functions used by this demo. It allows defining each GCE function inside a container, which can be used to submit the function (locally) and then  

## Motivation
Globus Compute is very sensitive to differences between where the function is defined (submit to the central service) and where it is used (the execution environment). It can also be tricky to define a complex program for this reason: symbols must be defined inside a nested package, which greatly limits the ability to call complex models or programs.

The solution is to bundle the entire [execution environment](https://globus-compute.readthedocs.io/en/stable/endpoints/endpoints.html#ensuring-execution-environment) in one container.

## Design goals
* Enable local development in a way that ensures matching of local and remote environments
* Provide helpers for registering GCE functions, while minimizing the "management" code present in the container

## General structure
This is currently rough and relies on convention rather than configuration. One or more GCE functions can be packaged into a given worker image. Each such worker is bundled inside one subfolder of `compute/`, and contains:

* `requirements/worker.txt`
* `Dockerfile`
* A folder named `this_compute`: the python code associated with this worker (by default, the "register function with GCE" script will look for one function in this module, named `main`). 
* Unit tests (optional); will be auto-discovered by pytest


## Useful commands
Each subdirectory represents one containerized environment (which can include more than one function)

The following containers rely on building the image first:

```bash
cd validate_metadata

docker build . -t gce_workers/validate_metadata:latest

# ALTERNATE: ultra pedantic mode
docker build --no-cache . -t gce_workers/validate_metadata:latest
```


* Running tests:
  `docker run -it gce_workers/validate_metadata:latest bash -c "pip install -r requirements/tests.txt && pytest ."` 
* Submitting a function: (eventually we can push the image, or else it's enough to run the same image in both local and remote configurations)
  * ```bash
    GLOBUS_CLIENT_ID="REPLACEME"
    
    # Replace with absolute path to ../common
    docker run -it -v `realpath ../common/commands`:/app/commands gce_workers/validate_metadata:latest python3 /app/commands/register_function.py ${GLOBUS_CLIENT_ID} this_compute.main
    ```
    * ` (optional args: `--public` and `--group UUID`)
      * Binds commands in as a volume, so that they don't need to be installed in the container up front. This reduces the amount of "extra management" code present in the worker in production.
  * Build a worker (remote host)
    * `docker build . -t gce_workers/validate_metadata:latest`
  * Note: eventually we'll push the built image to a repository for use in workers. In first proof of concept test, we'll build locally, then build same Dockerfile on test host.
  * Run a function on a remote endpoint after it was submitted to GCE:
  ```bash
  
  GLOBUS_CLIENT_ID="REPLACEME"
  GLOBUS_ENDPOINT_ID="REPLACEME"
  GLOBUS_FUNCTION_ID="REPLACEME"  # output from above register_function.py script
  
  # Function args for file validation function example
  TEST_COLLECTION_ID="dba0d7c0-1f63-44d1-bcd0-76865d3d44a0"
  TEST_FILENAME="/subfolder/example_metadata_bad.json"
  
  # NOTE: Replace with actual path to ../common
  docker run -it \
  -v $(realpath ../common/commands):/app/commands \
  -v $(realpath ~/.globus/):/~./globus \
   gce_workers/validate_metadata:latest python3 /app/commands/run_function.py ${GLOBUS_CLIENT_ID} ${GLOBUS_ENDPOINT_ID} ${GLOBUS_FUNCTION_ID}  ${TEST_COLLECTION_ID} ${TEST_FILENAME} 
  ```


## Deployment notes
Using containers is more complicated than functions, because they require more manual intervention to re-deploy a function.

1. The worker must be configured to use containers
2. The container must be built on the host where the endpoint lives (or placed in a repository the endpoint host can pull from)
3. The endpoint/worker must be configured to use the container, and probably restarted to ensure that the new definition is used. This may entail editing config.yml 