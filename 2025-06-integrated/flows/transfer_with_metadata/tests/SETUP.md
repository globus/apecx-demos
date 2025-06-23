# Testing this flow
Globus flows does not have a native means of testing a flow.

## Running tests

```bash
# Fill in config information needed to create the flow. Some permissions need adding in advance, so provide hard-coded IDs
cp .env-sample .env

# Log in to Globus when prompted. There are no mocks for flows/APs, so this uses real live infra. TODO Add notes on how to run in sandbox environment, which requires an extra SDK envvar.
cd 2025-06-integrated/flows/transfer_with_metadata/
pytest . -s
```


## Requirements
* Any globus transfer (GCSv5) collection (**source**)- I recommend Globus Connect Personal, as it has the least features. In general, this flow adopts a rule that "data can come from any globus source, and stuff will work".
  * This repository provides a set of _files that must be present in the source collection_, such as "good metadata", "no metadata", etc.
* A GCSv5 guest collection, part of a subscription, with HTTPS enabled (**destination**). This flow assumes that data is being transferred to a data repository under our control.
  * Eventually the guest collection will have additional requirements, such as `--flow-transfer-destination` to ensure that it only accepts data submitted via a flow.

* A globus compute endpoint (GCE) specifically enabled to run the compute function / worker defined in this repository.

* A globus flow that was defined to hard-code the compute function ID (from above)


### Setting things up
The flow relies on constrained permissions between pieces, as follows:
* The GCP collection (source) must be readable by the person running the flow 
* The GCSv5 collection (dest) must be readable _and writable_ by the person running the flow. It's (probably) ok if the collection is locked down to only work via a flow. (TODO test this)
* The GCE MEP endpoint must allow running jobs as the flow identity
* The GCE function must allow access to a group that contains the flow identity
* The Globus search collection must allow the flow identity to create or update records (___ permission)



## NOTES
### Scenarios to test 
* Collection issues
  * src is not a folder
  * dest path already exists
  * source or dest is unreachable
  * dest does not support HTTPS
* metadata not found
* metadata failed to transfer to dest
* Compute validator fails because...
  * Endpoint permissions
  * Uncaught exception (like "metadata is not valid json")
* Metadata is...
  * Valid
  * Invalid
* Data copied to dest...
  * Fails
* Search index...
  * accepts metadata
  * Rejects metadata due to error (like field types changing)
