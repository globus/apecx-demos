# Demo
### Setup required
- Create two Globus storage gateways, with doc links (source and dest)
- Set up GCP on local machine
- Create an ALCF globus guest collection, assigning permissions to a user group

### Things to demonstrate
- Globus app can be used to find a storage collection and view contents of a storage location: https://app.globus.org/file-manager
- Transfer files from POSIX to S3: just selected files, or an entire folder recursively
  - Emphasize this is one interface to two different kinds of storage. User doesn't need to re-learn how to run `ls` in multiple environments; we handle the details
  - Apply filters: `match files named *.cff, exclude any type matching * otherwise`
    - Comment on how filters allow us to safeguard against uploading sensitive or temp files in a big data release; reference to the python 2024 credential leak and remind audience this can happen to anyone. Show how Globus automation helps us to make safeguards part of our everyday workflow. 
  - Control over other options (like encryption of transfer)
- Show a guest collection for access to just part of a filesystem: list my mapped collection and guest side-by-side. Same storage, different views.
- Optional: get access to an ALCF guest collection and show how that can be used as a transfer destination too (highlight that system is locked down to owners, but with a guest collection, we gain flexibility. Maybe show auth rules assigned to a group.)
- 

### Multiple interfaces to the same operation!
Show a CLI operation like list, and run it with list filters. Compare to SDK script.


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


## TODO
Show how the API enables other types of options. Eg
* transfer filters (we have a script)
Different ways of changing what a user sees in app:
  * Directory listing filters (useful for sending to search index) https://docs.globus.org/api/transfer/file_operations/
  * Guest collection permissions controls