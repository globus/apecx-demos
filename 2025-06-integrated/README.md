# Integrated data ingestion demo: July 2025

Goals:
* Submit data with mandatory metadata
  * UI showing a helpful metadata schema where anyone can "fill in the blanks"
  * Deposit to a system-controlled path in ALCF guest collection
  * Minimize user write/delete permissions, except during critical submission phase
  * Ingest the metadata to a globus search index 
  * Store a copy of the metadata for later, such as in a custom filename in the dataset directory (`_globus_search_metadata.json`)
* Data viewing
  * Create an SSP that shows example search records
  * Deploy the SSP somewhere visible
  * Explore custom rendering of results if time permits
* Bonus items:
  * Extend the datacite schema using specific entities, like "virus name" or "organism name"


## Schema notes
The schema format is based on Datacite 4.6 ([spec](https://datacite-metadata-schema.readthedocs.io/_/downloads/en/4.6/pdf/), [JSON mappings](https://support.datacite.org/docs/datacite-xml-to-json-mapping)). Some fields have been removed from the first draft to avoid being overwhelming to users. As we develop a set of known biological entities / data ontology, we can add certain category tag fields back to the search schema. Globus has an [integration](https://docs.globus.org/api/flows/hosted-action-providers/ap-datacite-mint/) to mint DOIs for datasets that comply with the DataCite standard, and the spec attempts to [accommodate](https://datacite.org/blog/bioschemas_2024/) schemas of biological interest.


## Notes during development
Submitting a datacite schema via the web UI (flows library) does not work well. The web UI doesn't support array or array-of-objects parameters well, which is particularly noticeable for fields such as `authors` or `tags`. A bespoke UI may be helpful going forward. 

Versioning does not exist yet. This is only for dataset creation.

It does not yet provide UI around managing access permissions during dataset submission- this is still manual. We'll want our own backend for that.

## Required assets
Running this demonstration requires setting up a few resources. Just, you know. A few.

### A Globus subscription
  * [Globus ARPA-H APECx](https://app.globus.org/groups/ed27319a-13eb-11f0-8c33-0affcb8df433/about) UUID: `4b8bbd04-30ee-4d29-858d-3d94454584d3`

### Storage
* A **source collection** (test with GCP: we do not know what capabilities a user will have on their endpoint, and GCP is a minimum baseline)
  * An example dataset in source collection (folder containing 1+ files)
* A **destination collection** (eventually will require flow for submission)
  * Dest collection must enable HTTPS features, since that is how we will write metadata in the compute function
  * Specifically use a guest collection to facilitate automation


### Groups
Several globus groups are used to gate permissions around parts of this feature. The general idea is that the user should have minimum possible access to resources in this system.

* Parent group: [automation](https://app.globus.org/groups/0d2b4afe-3fff-11f0-b03a-0affcae2cfad/about) (parent group): UUID 0d2b4afe-3fff-11f0-b03a-0affcae2cfad
  * General parent, no function except organizing
* Subgroup [apecx-dev-automation-submission](https://app.globus.org/groups/bc8f2f41-5b5c-11f0-9736-0e5f35b86a33/subgroups) UUID bc8f2f41-5b5c-11f0-9736-0e5f35b86a33
  * Who is allowed to RUN the data submission flow
* Subgroup [apecx-dev-automation-internals-compute](https://app.globus.org/groups/3dbaa856-3fff-11f0-b819-0e5f35b86a33/about) UUID 3dbaa856-3fff-11f0-b819-0e5f35b86a33
  * This is used by globus compute functions, to determine which identities are allowed to run the function. Specifically, the flow user must be added to this group.
* Subgroup `automation-admins`
  * TODO: People who should be allowed to administer the search index, and own other project resources. Figure out how this fits into the broader apecx hierarchy.

### Auth Service accounts
One CLI service account is required:
* `apecx-dev-compute-abought-js2` (UUID  `e7d021af-9782-4bf6-96c2-8785ed2a1e14`, client secret created via console and not tracked here)
  * This is used by the GCE endpoint to provide credentials for writing a file to the storage collection. This is required because the GCE endpoint has no inherent idea of context or instance metadata: it just gates whether you can run a function. It does not know who is running the flow and cannot provide credentials/tokens for that user.

### Flow
* A globus flow must be created before certain other assets, because key processes will be run under the flow identity 
  * Use the `transfer_with_metadata` flow in this repository:

```bash
cd flows/transfer_with_metadata

globus flows validate "flow_definition.json" --input-schema "input_schema.json"

globus flows create \
    "APECx Data Ingest Flow (dev)" \
    --subtitle "Transfer a dataset and store a copy of user metadata" \
    --description "A demonstration of globus platform capabilities for the ARPA-H APECx project." \
    --administrator  0d2b4afe-3fff-11f0-b03a-0affcae2cfad \
    --starter bc8f2f41-5b5c-11f0-9736-0e5f35b86a33 __ \
    --keyword apecx --keyword apecx-demo --keyword apecx-dev \
    --subscription-id 4b8bbd04-30ee-4d29-858d-3d94454584d3
```
* The resulting flow is: UUID `199bf87a-03b3-44da-ac7c-a9f6c34ee149` / username `199bf87a-03b3-44da-ac7c-a9f6c34ee149@clients.auth.globus.org`

### Search
One search index that expects records in the DataCite metadata schema format
```bash
globus search index create "apecx-dev - Data Repository" "Dev/testing version of the APECx data repository"
```
* `GSI_UUID="a803fd20-7c86-476f-8d0a-bd92bd5ff7fa"`
* Per docs, contact support to request this index be added to the subscription and marked non-trial
  


### Compute
* One MEP compute endpoint that accepts flow identity to run functions. See MEP setup instructions (notebook) and the config files provided in this repo (`compute/configs/validate_metadata/mep/`).
  * One function that can write a file via HTTPS using the Globus SDK
  * A packaged compute worker (container) that contains Globus SDK and any other required environment details (jsonschema validation etc)

To deploy the compute functions, follow the instructions in `compute/README.md`. Remember to:
* Build the function container locally, and ensure all tests pass.
* Run the provided script to register the function, and capture the UUID for future reference (the introspection tools for after-the-fact are rather bad)

Example local commands:
```bash
GLOBUS_CLIENT_ID="REPLACEME"  # a client app suitable for running commands like "register function" as a specific user. Will prompt for login when scripts are run.
GLOBUS_GROUP_ID_FUNCTION="3dbaa856-3fff-11f0-b819-0e5f35b86a33"

docker build --no-cache . -t gce_workers/validate_metadata:latest

docker run -it gce_workers/validate_metadata:latest bash -c "pip install -r requirements/tests.txt && pytest ."

docker run -it \
    -v `realpath ../common/commands`:/app/commands \
    gce_workers/validate_metadata:latest \
    python3 /app/commands/register_function.py ${GLOBUS_CLIENT_ID} this_compute.main --group ${GLOBUS_GROUP_ID_FUNCTION}
```

The remote environment (MEP) config should reference a matching container built somewhere, eg a repository that we can pull the correct tag from. If not set up as a systemd service yet, be sure to start the demo via:

```bash
# Note: on many systems, it's easier to install GCE manually in a venv with permissions accessible to both the root and UEP mapped identity unix accounts. (the package may depend on a very outdated python version, causing the MEP to give exchange errors due to python 3.9, even if the worker, host machine, and function are all on python 3.12)
source /opt/gce/bin/activate

globus-compute-endpoint start apecx-dev-compute-only-mep --log-to-console
```


### Webapp
  * A static search portal fork oriented around the Datacite schema
  * Some example metadata for the MU VIOLIN scraping dataset
    * `globus search ingest "${GSI_UUID}" "compute/data/gsearch-example_metadata_violin-mu.json"`

## Wiring together authorization
The above components need additional work to connect them. Ideally, as much of the system as possible should be private internal state. Users should not have default write access to the repository or its contents, but only to outside wrappers (like the flow) that mediate what they can do at each step. 

* The FLOW USER must be a member of the `-internals-compute` group
  * The webapp will only send an invite, which is silly for an identity with no email. Click through the `>` icon in list view and click "add member" to force immediate invite. IIRC the underlying CLI/APIs support direct addition.
* The FLOW USER must be allowed to create new entries in the search index 
* The `-admins` group should be granted access to the search index, and flow monitor/runner permissions
* The SERVICE ACCOUNT credentials must be made available to the endpoint MEP
* The SERVICE ACCOUNT must be granted read/write access on the root of the dest guest collection


## Running tests
See compute function notes for example of how to run tests for the GCE features.

To test flows in an automated fashion, the flows directory contains a series of scenarios that will be run automatically and report their results. In the future we will have a separate test environment for this.

Tests may be run via pytest. Parallel options may be considered in future, as long as tests are truly independent. This will still be much slower than a live service!

```bash
cd flows/transfer_with_metadata
# This pulls user credentials from a .env file in that directory, so follow instructions to populate
pytest . -s
```

Scenarios: (test as both an admin AND a vanilla user)
* Source collection ID cannot be reached
* Dest collection cannot be reached
* Success: Source path exists, and user input metadata is valid
* Error branch: Source path does not exist
* Error branch: Source path a file, not a folder
* Error branch: on flow submission, user submits invalid metadata and the flow insta-fails (not everyone goes through the UI, so test this!)
* Error branch: User already has an access grant at this destination which causes grantaccess to fail
* Error branch: File write is rejected (can we find a way to force this? A lot of control is removed from the user by the flow, so they can't write to a bad path, or write invalid metadata past validation etc)
