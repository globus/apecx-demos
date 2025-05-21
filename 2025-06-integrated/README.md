# Integrated data ingestion demo: June 2025

Goals:
* Data submission path (target user: YOC of MU):
  * Custom guest collection with mandatory flow-to-submit
  * Metadata schema that anyone can "fill in the blanks"
  * Deposit to a well defined path in ALCF guest collection
  * Send data to a globus search collection
* Data viewing
  * Create an SSP that shows records only to members of a specific globus group
  * Deploy the SSP somewhere visible
  * Explore custom rendering of results if time permits
* Bonus items:
  * Extend the datacite schema using specific entities, like "virus name" or "organism name"




Questions left open
* How can we archive submitted search index metadata longterm?
  * Currently this requires a compute function on a bespoke endpoint. In theory, the endpoint could fetch the file via HTTPS, rather than gluing filesystems to one endpoint. (cleanup and error handling would be very important for the endpoint!!)

## Schema notes
The schema format is based on Datacite 4.6 ([spec](https://datacite-metadata-schema.readthedocs.io/_/downloads/en/4.6/pdf/), [JSON mappings](https://support.datacite.org/docs/datacite-xml-to-json-mapping)). Some fields have been removed from the first draft to avoid being overwhelming to users. As we develop a set of known biological entities / data ontology, we can add certain category tag fields back to the search schema. Globus has an [integration](https://docs.globus.org/api/flows/hosted-action-providers/ap-datacite-mint/) to mint DOIs for datasets that comply with the DataCite standard, and the spec attempts to [accommodate](https://datacite.org/blog/bioschemas_2024/) schemas of biological interest.


## Notes during development
Submitting a datacite schema via the web UI (flows library) does not work well. The web UI doesn't support array or array-of-objects parameters well, and the submit button never quite enabled (for unclear reasons). 

Fortunately, we don't really want metadata submitted via the flow at all, because we need to keep a copy to regenerate index / change permissions later. We'll test this out, then switch to compute + read-file-via-HTTPS incrementally.


## Required assets
* Storage
  * A source collection (test with GCP: we do not know what capabilities a user will have on their endpoint, and GCP is a minimum baseline)
    * An example dataset in source collection, requiring a file named metadata.json in the root
  * A destination collection (eventually will require flow for submission)
    * Dest collection must enable HTTPS features, since that is how we will read metadata in the compute function
    * Specifically use a guest collection to facilitate automation
* Search
  * One search index that expects records in the DataCite metadata schema format
    * `globus search index create "apecx-dev - Data Repository" "Dev/testing version of the APECx data repository"`
      * `GSI_UUID="8cd76948-c803-483b-88aa-cdd2f6a4cbe6"`

* Compute
  * One compute endpoint that accepts flow identity to run functions
  * One function that can retrieve a file via HTTPS using the Globus SDK
  * A packaged compute worker (container) that contains Globus SDK and any other required environment details (jsonschema validation etc)
* Auth
  * A way to authorize the flow to run compute functions (evaluate options; flow specific identity for compute provider? Multi-user or login as that person for endpoint?)
  * A way to authorize the flow for access to the storage collection, via HTTPS grant
* Permissions
  * Submitting user must be authorized at source and dest collection
  * Flow must be authorized to read the dest (https grant)
  * Flow must be authorized to run functions on the compute endpoint

* Webapp
  * A static search portal fork oriented around the Datacite schema
  * An example file for the MU VIOLIN scraping dataset
    * `globus search ingest "${GSI_UUID}" "compute/data/gsearch-example_metadata_violin-mu.json"`

  