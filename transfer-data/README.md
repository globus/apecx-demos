 # Introduction to Globus Data Services: Move, share, and automate
This presentation provides an overview of how Globus can help you move and share data. The Globus documentation can be quite extensive, so this supplemental document provides a quick reference to key information. Many tutorials exist, so we will not attempt to duplicate separate instructions here.

## Quick links


### References
* [Getting started](https://www.globus.org/get-started)
* [How to share data using Globus](https://docs.globus.org/guides/tutorials/manage-files/share-files/): Introduction to guest collections
* [Subscriptions](https://www.globus.org/why-subscribe) provide access to advanced features. [Search](https://app.globus.org/settings/subscriptions/search) to see if your institution (or a partner) already has a subscription!


### Tools
* [Globus web app](https://app.globus.org/file-manager): Go to app.globus.org to use the file manager and manage collections on any kind of storage system. Many researchers use this to manage their data, without having to learn SSH.
* [Globus Connect Personal](https://docs.globus.org/api/transfer/): Create your own endpoint on a laptop
* All Globus transfer features can be controlled via the [Transfer API](https://docs.globus.org/api/transfer/). Several tools exist to help control this functionality:
  * The Globus [command line](https://docs.globus.org/cli/) tool (CLI) lets you interact with Globus services. It does not support every possible API feature, but it is very useful for scripting common file operations. (including list, copy, or delete)
  * The [Python SDK](https://globus-sdk-python.readthedocs.io/en/stable/) provides control over the most advanced Globus transfer features, like filters. It can do (almost) anything that the API can do, which makes it very useful for building applications on top of Globus Transfer.
* The [globus-jupyter-notebooks](https://github.com/globus/globus-jupyter-notebooks) repository demonstrates how to control many advanced features via the Python SDK

## Create your own endpoint
### Globus Connect Personal (GCP)
This can be used to enable transfer for a single-user machine, such as a laptop or personal cloud workstation. Data can be exchanged with other Globus destinations, and (if your institution is a subscriber) even other personal endpoints. [Get started with Globus Connect Personal](https://docs.globus.org/api/transfer/)

_This is a good place for someone to get started with Globus_, because GCP will let you try many Globus features even if you don't have access to a big HPC computer system. Personal endpoints do not support more advanced features, such as serving files over HTTPS. You would not use them to build a web server for global usage!

### Globus Connect Server (GCS)
This is the flagship product of Globus: an agent that runs on a remote server and enables the full range of Globus Transfer features. It supports many storage types and authentication modes, for any number of users on the host system. There are tens of thousands of active endpoints at institutions all over the world, serving hundreds of thousands of users.

Because Globus enables peer-to-peer data transfer, you will need to run your own copy of GCS even if using a cloud based storage system (like S3). There are many options for controlling identity and access: running your own endpoint gives you full control. 

* [Search](https://app.globus.org/collections) to see if your systems already have an endpoint set up. Not every endpoint is publicly listed; when in doubt, ask your systems administrator.
* [Create an endpoint](https://docs.globus.org/globus-connect-server/v5.4/)
  * [Data access and sharing options](https://docs.globus.org/globus-connect-server/v5.4/data-access-guide/) allow you to set system policies that define what users can do
* Advanced deployment tips
  * Tips for [automating a deployment](https://docs.globus.org/globus-connect-server/v5.4/automated-deployment/)
  * Use [multiple data transfer nodes](https://docs.globus.org/globus-connect-server/v5/reference/node/) for robust service and low downtime
  * Administrators can [schedule pause rules](https://www.globus.org/blog/cancel-and-pauseresume-tasks-using-management-console) when they need to plan for downtime, and trust that transfers will complete when the system returns to service

## Permissions management
### Authentication
GCS Mapped Collections allow you to control how users log in. The default behavior of mapped collections is to match the username portion of their Globus linked identity (`<username>@domain.example`) to a matching username on the host system.

Your Globus Endpoint can configure this to work with on-campus login systems, add domain restrictions, and apply other policy controls.

* https://docs.globus.org/globus-connect-server/v5.4/identity-mapping-guide/
* https://docs.globus.org/globus-connect-server/v5.4/globus-oidc-guide/

Globus Guest Collections build on top of Mapped collections and can connect to many possible forms of identity provider. You can control who has access to the data via the web interface, across multiple institutions.

### Mapped collections
Mapped collections are the default way of accessing files. They best resemble the experience of logging into an HPC system: a user will see the same files as their existing account on the HPC system. Special [connectors](https://www.globus.org/connectors) are available that seamlessly enable access to many different kinds of storage through a single unified interface. Many [options](https://docs.globus.org/globus-connect-server/v5/reference/collection/create/) are available to give the systems administrator control of what users can see.

### Guest collections
Guest collections allow you to share part of your storage with users who do not have an account on your HPC cluster. Different users can be granted access to different sub-paths within the same guest collection. We provide a tutorial for [how to share data using Globus](https://docs.globus.org/guides/tutorials/manage-files/share-files/).

For large collaborations, this is often a far easier way to extend sharing than other methods (such as sponsored university affiliate accounts). If your subscription support High Assurance (HA) features, sharing grants can be also be [set to expire](https://docs.globus.org/faq/transfer-sharing/#can_i_set_permissions_on_guest_collections_to_automatically_expire_can_i_limit_how_long_everyone_can_share_data_from_my_collection) after a defined period of time.

In general, due to rules negotiated with universities in secure environments, Guest Collections require deliberate opt-in, and therefore are easier to use with most Globus features (such as automation and timers). Mapped collections will often encounter more permissions and access prompts.

> **Prescriptive guidance**: Use guest collections and Globus auth identities wherever possible.

#### Users and Groups
Guest collection access and/or administration privileges can be granted to all members of a group. This is useful for managing large distributed collaborations, because it lets you centralize privileges in one place.

* [How to manage Globus Groups](https://docs.globus.org/guides/tutorials/manage-identities/manage-groups/)


## Privacy and security
Globus features can be used even if your data is subject to restrictions. Certain subscriptions can take advantage of additional [high-assurance features](https://docs.globus.org/guides/overviews/high-assurance/). If your data is subject contains things like Personally Identifiable Information (PII), Controlled Unclassified Information (CUI), or Protected Health Information (PHI), reach out to learn more about our [High Assurance or HIPAA BAA subscription tier](https://www.globus.org/subscriptions) options.

## Automation capabilities
### Workflow automation with Globus Flows
Big data applications often act as more than a neutral archive of files. They typically need to _do_ something with the data.

For example, data portal submission usually involves running a QC script after upload, then adding the file to a search index. Ideally this would be a [two-stage transfer](https://docs.globus.org/api/flows/examples/), where a user only has access to the staging area, and yet data can make it into the final repository when it is ready for sharing. 

Globus provides an automation product called [flows](https://www.globus.org/automation) that can do these things and more. Flows has access to the full range of [operations](https://docs.globus.org/api/transfer/action-providers/) exposed by transfer for use in scripting.

### Scheduled tasks with Timers
Sometimes, it is useful to perform file operations on a schedule. The most obvious example would be nightly backups/sync, but [other examples](https://www.globus.org/instruments) include regularly distributing new files across nodes in a global data partnership. [Globus Timers](https://dl.acm.org/doi/10.1145/3569951.3597571) provides the ability to control file transfers on a schedule.


## Glossary
Globus provides a common interface to many kinds of storage systems. To achieve this customizability, there are several [layers of resource](https://docs.globus.org/guides/overviews/collections-and-endpoints/) that need to be created. 

* Endpoint: the host server (or cluster of servers). A single endpoint can govern access to multiple kinds of storage.
  * Storage Gateway (each endpoint can control access to multiple storage systems at once): defines how to access a particular storage type (S3, POSIX, etc). Even if you are using cloud storage, you must register your own endpoint and gateway.
    * Mapped collection (each gateway can have multiple views of storage): this is the storage type that most closely resembles accessing the host system. You will see paths and authentication rules similar to if your authenticated user had directly accessed the system. 
      * Guest collection (each mapped collection can expose multiple guest collections): The unit of storage most useful for sharing resources with external users. With guest collections, user authorization is handled by globus.org, rather than the rules on the host system. Guest collections can only be created by users with appropriate permissions on the parent mapped collection. They provide an easier way to control data sharing, and tend to be the best path for using most Globus automation features.

> **NOTE**: Old documentation (pre GCSv5) may refer to storage collections as "endpoints". If you see confusing outdated language, it may be using terminology that reflects an older system design. Let us know and we can update the documentation!