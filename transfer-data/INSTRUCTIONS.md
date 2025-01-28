# Demo notes

## Getting started
Globus Transfer is widely used and documented, and where possible, we will refer you to existing tutorials. The instructions below are focused on specific features that we think would be of interest to the APECx audience.

See:
* [Tutorial: How To Log In and Transfer Files with Globus](https://docs.globus.org/guides/tutorials/manage-files/transfer-files/)
  * The instructions include links to two "example" collections. You will be able to explore Globus features without installing any software or using your own data. 
* [How to install and use Globus Connect Personal](https://docs.globus.org/globus-connect-personal/)
  * This is useful for a single user on a laptop or a VM. You can create your own Globus Endpoint and Collection for real-world interaction with data stored on a remote HPC cluster.
  * Allows you to go more "hands on" by using your own files with Globus.

> **NOTE**: Globus is designed around granular "least permissions" privileges. (eg read-only vs write) The first time you use any feature on a given collection, you may be prompted to log in and authorize access for that additional feature. It will seem a bit surprising to see so many authorization screens, but the system is behaving normally.
>
> As you follow tutorials or videos, you will notice that the host does not see as many login prompts as you. Globus will remember your  consent, and future usages will not prompt you again.


### Things to demonstrate
- Open the Globus webapp file manager: https://app.globus.org/file-manager
  - Show that this is a web-based view to find a storage collection and view contents
  - Demonstrate that it can be used to upload a single file from local computer
  - Demonstrate transfer files from POSIX to S3: just selected files, or an entire folder recursively. Mention here that in practice, most transfers are peer to peer, and user does not have to go through their local laptop. (This is important for web based portals uploading really big datasets. Users can initiate a transfer without having to download to a computer with a web browser first) 
    - Emphasize this is one interface to two different kinds of storage. User doesn't need to re-learn how to run `ls` in multiple environments; we handle the details
    - For the transfer demo: do an advanced transfer with custom filters: `{include} {files} named {*.cff}` ; `{exclude} {any type} matching {*}` 
      - Comment on how filters allow us to safeguard against uploading sensitive or temp files in a big data release; reference to the python 2024 credential leak and remind audience this can happen to anyone. Show how Globus automation helps us to make safeguards part of our everyday workflow. 
      - Control over other options (like encryption of transfer)
      - Mention parallels to how other familiar tools, like the S3 CLI, handle include/exclude rules. Filter syntax is powerful, but a bit fussy
      - To help people use them, the demo repo contains several scripts that showcase best practices
- Show a guest collection for access to just part of a filesystem: list my mapped collection and guest side-by-side. Same storage, different views.
  -For this demo: show access to an ALCF guest collection and show how that can be used as a transfer destination (highlight that system is locked down to owners, but with a guest collection, we gain flexibility. Show auth rules can be defined with different levels of access, and this is much easier to reason about than, eg, students running `chmod -R 777`)
- Mention bonus scripts in this repo
  - Create a timed backup on a schedule (restrict by max file size and exclude certain filetypes)
  - Control which files are transferred (upload)
  - Customize views of a folder
  - Automatically set permissions 
