# Globus Flows and Compute
_Smart automation around data submission_

## Introduction
### Globus Flows
Globus Flows are a tool for automating processes and tasks, especially around the management of research data. They can leverage the full set of features in the Globus Platform.

Flows are not intended to manage complex computational pipelines, and they do not replace analysis pipeline tools like Snakemake and Nextflow. Instead, flows leverage the power of the Globus platform for _data movement_ and _data management_. They can be used for things like secure data upload, backups, search indexing, generating DOIs, and anything where sensitive data must be handled in a reliable and reproducible way. They are run in a distributed and scalable way, making them resilient to temporary downtime in a single system component.

References:
* [Getting started with Globus Flows](https://docs.globus.org/api/flows/getting-started/)
* Use core Globus features in a flow via [Action Providers](https://docs.globus.org/api/flows/hosted-action-providers/)
* Interesting features
  * [Performing actions as different users](https://docs.globus.org/api/flows/authoring-flows/roles/): Each step can be run by a different user. This means that a flow can be used to "hide" a resource so that it is only invoked in a specific and highly controlled way.
  * [Protecting secrets](https://docs.globus.org/api/flows/authoring-flows/secrets/): normally, a flow will show detailed logs to the user who started the run. Private parameters and run state can be used to hard-code secret information in the flow definition, without exposing it via logs.
* [States language](https://states-language.net/spec.html) specification: Globus Flows exposes some (though not all) Amazon States Language features, and this is a useful guide for syntax where other documentation is ambiguous.

### Globus Compute
Globus Compute provides federated function as a service: the ability to run python functions inside secure compute environments.

There are many potential applications, such as allowing exploratory notebooks to access a larger pool of compute resources and retrieve results. This can be used for exploratory scenarios such as machine learning and data science. 

This tutorial focuses on one narrow application: running compute functions inside a workflow. In this context, they can be used to add a small bit of custom intelligence into automation, beyond the simple variable manipulations that are possible via the flow definition language.

See:

* [Federated Function as a Service](https://globus-compute.readthedocs.io/en/stable/quickstart.html)
* [Globus compute tutorial](https://globus-compute.readthedocs.io/en/stable/tutorial.html)
* Introduction to [endpoints](https://globus-compute.readthedocs.io/en/stable/endpoints/endpoints.html)


## Demo
This repository provides several examples in the `flows/` folder. Run them via the script `flows/make_flow.py`. This script isn't generic, and contains several IDs used in my own testing. You will need to substitute your own GCS/GCE IDs to make them work for you.

### Setup requirements
Globus Compute is a much newer product than our other offerings, and as such, it is not fully integrated with Globus storage. To add "smart file operations" into workflows, this repository provides some exploration of potential workarounds.

In essence: Globus Compute will be accessing files directly via the file system. As a result, if you want to perform compute on files, you will need to ensure that your compute endpoint is installed on a host that also has access to the filesystem being used by Globus Connect Server.

In brief, you will do the following:
* Set up GCE (one endpoint) (must be on a computer that has access to the same filesystem as gcs)
* Set up GCS (two guest collections, but they can share different parts of the same mapped collection, see storage setup notes below)
* Ensure there is a folder on the GCE host accessible to both the user who will be running the flow (Globus user mapped to local system for GCS + flows), but also accessible to the user who is running the compute endpoint (GCE). Since GCE does not talk to Globus storage directly, this requires some basic POSIX trickery.

> *Note*: We recommend always using guest collections for all automation and scripting related tasks. Mapped collections require extra permissions and more frequent re-authorization. These examples deliberately do not demonstrate the advanced case of mapped collections.

#### Create a folder that GCS and GCE can both access
```bash
# Permissions logic: ensure that files will be accessible to both GCS (file transfer) and GCE (compute)
sudo addgroup apecx-flows-example-group
sudo adduser compute-user apecx-flows-example-group
sudo adduser yourusername apecx-flows-example-group
```

```bash
# Create a shared storage location and ensure it will be accessible. This isn't Globus configuration; we're using old-school POSIX commands to fill in the missing connection between GCS and GCE
# NOTE! This means that the compute server could have access to more files than the globus user. Use this very carefully, and only for GCE functions initiated in a highly controlled way (such as via a workflow that regulates the input arguments passed to compute).   
sudo mkdir -p /share/gcs-demo  # Make sure that your GCS path-restrictions file allows sharing of `/share`
# First item (set default rule) for new items, second for existing. Remember to log out and back in for new groups to take effect.
sudo setfacl -Rdm g:apecx-flows-example-group:rwx /share/gcs-demo
sudo setfacl -Rm g:apecx-flows-example-group:rwx /share/gcs-demo
```

#### Tell Globus Compute how to access storage files
The `validate_in_place` example workflow runs a function that reads an uploaded file. To do this, the workflow receives an argument `compute.gcs_root`, which is used by the compute function to turn a globus path into a POSIX path. (there's no magic here; just a precise knowledge of the underlying computer technology).

Below is a conceptual example of the technique we are using here. 

```python
def read_globus_file(collection_uuid, gcs_file_path):
    import os
    # Globus guest collections can present any folder to look like the root of that collection- eg `/share/globus-data` may present to the outside world as the root path `/` of `my-shared-guest-collection`. Globus transfer hides the details of the underlying filesystem... but globus compute needs to undo that illusion manually.
    COLLECTION_TO_FILESYSTEM = {
        'some-uuid': '/share/gcs-demo',
        'another-uuid': '/share/second-folder',
    }
    folder = COLLECTION_TO_FILESYSTEM.get(collection_uuid)
    if folder is None or not os.path.exists(folder):
        raise Exception('The specified GCS collection is not configured to work with this compute function/endpoint')
    
    # Note: see security warning below about sensitive data handling
    return os.path.join(COLLECTION_TO_FILESYSTEM[collection_uuid], gcs_file_path) 
```

> *WARNING*: The above is a highly simplified example. Emerging compute features such as [multi-user/ templatable](https://globus-compute.readthedocs.io/en/stable/endpoints/endpoints.html#templating-endpoint-configuration) endpoints will provide greater control over who has access to the files, by controlling who runs the compute function. Be very careful to ensure that the compute user does not have different permissions than the person running the flow. Otherwise, you risk exposing sensitive or protected data. 

## Other Examples
* Globus-provided [runnable example flows](https://app.globus.org/flows/library?filter_subscription=4fa609fc-14f6-4c62-acfd-680873d3b6fe)
* Jupyter Notebook: [Flows + Compute + Search](https://github.com/globus/globus-jupyter-notebooks/blob/master/Flow_with_Compute.ipynb)
* Jupyter Notebook: [Introduction to Compute](https://github.com/globus/globus-jupyter-notebooks/blob/master/Compute_Introduction.ipynb)

## Tools
* Globus [Flows IDE](https://globus.github.io/flows-ide): A graphical tool for visualizing workflow definitions, and provides feedback for schema validation.
  * This is a beta tool, and does not provide UI to generate all parts of a Globus Flow from scratch; you will still need to know the basic JSON syntax. However, it is _highly_ useful for visualizing existing workflows as an aid to debugging!
* [Gladier](https://github.com/globus-gladier/gladier) is a tool for authoring flows. It especially provides helpers for working with compute functions, and makes it easier to update the flow definition when a compute function definition / ID is changed.
  * It works best for flow definitions with linear logic.  Although the underlying Globus flows language (JSON-based) is capable of supporting branching logic, these are not as easy to represent in the abstract syntax used by Gladier.
