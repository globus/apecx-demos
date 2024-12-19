 # Introduction to Globus Data Services: Move, share, and automate
This presentation provides an overview of how Globus can help you move and share data. The Globus documentation can be quite extensive, so this supplemental document provides a quick reference to key information. Many tutorials exist, so we will not attempt to duplicate separate instructions here.

## Quick links: Useful Tutorials
-


## Create your own endpoint
### Globus Connect Personal (GCP)
This can be used to enable transfer for a single-user machine, such as a laptop or personal cloud workstation. Data can be exchanged with other Globus destinations, and (if your institution is a subscriber) even other personal endpoints.

Personal endpoints do not support more advanced features, such as serving files over HTTPS: you would not use them to build a web server for global usage!

### Globus Connect Server (GCS)
This is the flagship product of Globus: an agent that runs on a remote server and enables the full range of Globus Transfer features. It supports many storage types and authentication modes, for any number of users on the host system. There are tens of thousands of active endpoints at institutions all over the world.

Because Globus enables peer-to-peer data transfer, you will need to run your own copy of GCS even if using a cloud based storage system (like S3).

## Permissions management
### Authentication

### Users and Groups

### Mapped collections

### Guest collections



## Automation capabilities
* Timers: 
* Flows: https://www.globus.org/automation



## Glossary
Globus provides a common interface to many kinds of storage systems. To achieve this customizability, there are several layers of resource that need to be created

* Endpoint: the host server (or cluster of servers). A single endpoint can govern access to multiple kinds of storage.
  * Storage Gateway (each endpoint can control access to multiple storage systems at once): defines how to access a particular storage type (S3, POSIX, etc). Even if you are using cloud storage, you must register your own endpoint and gateway.
    * Mapped collection (each gateway can have multiple views of storage): this is the storage type that most closely resembles accessing the host system. You will see paths and authentication rules similar to if your authenticated user had directly accessed the system. 
      * Guest collection (each mapped collection can expose multiple guest collections): The unit of storage most useful for sharing resources with external users. With guest collections, user authorization is handled by globus.org, rather than the rules on the host system. Guest collections can only be created by users with appropriate permissions on the parent mapped collection.


## Demo
### Setup required
- Create two Globus storage gateways, with doc links (source and dest)
- Set up GCP on local machine
- Create an ALCF globus guest collection, assigning permissions to a user group

### Things to demonstrate
- Globus app can be used to find a storage collection and view contents of a storage location: https://app.globus.org/file-manager
- Transfer files from POSIX to S3: just selected files, or an entire folder recursively
- Apply filters: `match files named *.cff` (see slack discussion, use a CLI example to demo filters. Need exclude AND include!)
- Control over other options (like encryption of transfer)
- Optional: get access to an ALCF guest collection and show how that can be used as a transfer destination too (highlight that system is locked down to owners, but with a guest collection, we gain flexibility. Maybe show auth rules assigned to a group.)

### Multiple interfaces to the same operation!
(note: certain operations, like filters, are best done via the SDK; the expecyted behavior is a bit complex and hard to present concisely. The CLI can only filter filenames, and )
- Copy file via the web app
- Copy same file via the CLI:
```bash
GCS_SOURCE_UUID="REPLACE-SOURCE"
GCS_SOURCE_PATH="/"

# Written as example of copying from POSIX to s3, where bucket name must be part of the path
GCS_DEST_UUID="20eb90f3-e3f9-4c7a-823f-bcc6fedf1f29"
GCS_DEST_PATH="/some-aws-bucket-name/target-dest-folder"

# Note that we specify both include and exclude. 
#   A file that does not match either option is included by default, and earlier options have priority. Filters are powerful, but not always intuitive! 
globus transfer \
    "${GCS_SOURCE_UUID}:${GCS_SOURCE_PATH}" \
    "${GCS_DEST_UUID}:${GCS_DEST_PATH}" \
    --label "abought APECx demo" \
    --recursive \
    --include "*.cff" --exclude "*" \
    --preserve-timestamp \
    --encrypt-data \
    --notify on
    
# Monitor task status using CLI. You will receive an email message when transfer succeeds/fails.
globus task show ${GCS_TRANSFER_TASK_ID}
    
```


UI lets me exclude files, folders, or both

CLI above produces for the exclude rule:
```
    {
      "DATA_TYPE": "filter_rule",
      "method": "exclude",
      "name": "*",
      "type": "file"
    }
```

Can CLI let me exclude all? Web site usage per slack produces an API request as below. Note no "type:file" on the exclude. (if we specify type:file for exclude, we copy everything!!)
`{"DATA_TYPE":"transfer","DATA":[{"DATA_TYPE":"transfer_item","source_path":"/home/andrew.boughton/","destination_path":"/abought-globus-development-globus-storage/andrew.boughton/","recursive":true}],"submission_id":"8ee26f89-be2d-11ef-967f-61ba15b0390d","source_endpoint":"bfe8ac24-4e2e-4380-840b-d7da53a58532","destination_endpoint":"20eb90f3-e3f9-4c7a-823f-bcc6fedf1f29","deadline":null,"delete_destination_extra":false,"encrypt_data":true,"fail_on_quota_errors":false,"filter_rules":[{"DATA_TYPE":"filter_rule","method":"include","name":"*.cff","type":"file"},{"DATA_TYPE":"filter_rule","method":"exclude","name":"*"}],"label":null,"preserve_timestamp":true,"skip_source_errors":false,"sync_level":null,"verify_checksum":true,"notify_on_succeeded":true,"notify_on_failed":true,"notify_on_inactive":true,"store_base_path_info":true}`