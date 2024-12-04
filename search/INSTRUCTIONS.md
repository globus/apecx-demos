# How to create a tutorial app

This document covers the full commands used to create this demo.

## Requirements
* This tutorial uses the [Globus command line (CLI)](https://docs.globus.org/cli/).
* Advanced file transfer features (like HTTPS over the web) may require access to a server with a Globus endpoint, and possibly a Globus subscription. If your university does not have something ready, basic file transfers can be done from your laptop via [Globus Connect Personal](https://www.globus.org/globus-connect-personal). 
* Some of the features in this demo are subject to [service limits](https://docs.globus.org/api/search/limits/). In particular, if you have already done other Globus search tutorials, there is a limit of three trial indices. (you may need to clean up any previous tutorial assets)

## 0. Create an auth Group to serve as owner
In a large complex project, it is often difficult to keep track of who has access to what resource. Globus provides a "groups" feature that can be used to centralize granting permissions in one place. Although you do not *need* to create a group, doing so will make it easier to manage your team as the project grows.

Before we begin work on the search index, we will create a new group for the project:

```bash
# Create a group and view all output
globus group create "$(whoami) admin group - Globus Search Lit Demo" --description "Owners of the Lit Demo search index"  --format json
 
# Dummy code- for this tutorial, manually replace with your group ID to assign the newly created group ID to a variable name for later use 
GG_ID="01234567-abcd-cdef-555e-abc1234567890"

# View details of this group, and make sure that all policies are set to your preferred defaults. You may also control this group from the web app UI: https://app.globus.org/groups
globus group show "${GG_ID}"
```

As we create resources later, we will use this group to define permissions on those resources.

> Advanced tip: every Globus CLI command allows specific fields to be [extracted for bash scripting purposes](https://docs.globus.org/cli/jmespath_queries/). This can 
> make it easier to save group ID as a variable for later!
> 
> `GG_ID=$(  globus group create "$(whoami) admin group - Globus Search Lit Demo" --description "Owners of the Lit Demo search index" --format unix --jq id  )`

## 1. Build the search index
Any given collection of documents is grouped together into a search index. If your institution is a subscriber, you are allowed to create many different indices with a lot of data in each. Note that you will need to contact Globus support if you plan to use the service heavily or long-term. (small trial datasets will be periodically deleted)

For index creation, we will demonstrate the use of the [Globus CLI](https://docs.globus.org/cli/), which provides many commands to interact with Globus Search. Globus Search is a fully managed service, which means that you can start using it immediately (even if other parts of your web data portal are still in progress).

```bash
globus search index create "$(whoami) - Globus Search Lit Demo"  "Scholarly literature and supporting files for search demo"
```

Make a note of the search index ID! If you lose it, you can check the output of `globus search index list` later. The commands below will assume you saved your value as a shell variable, so that you can more easily paste in following commands without retyping:
```bash
GSI_UUID="abcde123-1234-abcd-123a-1234567890abc"
```

As with the groups example above, most commands support a suffix like `--format unix --jq id`, which allows you to [extract specific response fields](https://docs.globus.org/cli/jmespath_queries/) (like task or index ID) from command output for scripting purposes.


(optional) Once the group is created, give your admin/project group [admin permission](https://docs.globus.org/api/search/reference/role_create/), so that multiple developers can edit the search index:
```bash
globus search index role create "${GSI_UUID}" admin "${GG_ID}"
```

NOTE: The above only governs ability to edit the index. What records can be viewed is controlled separately, via `visible_to` and `principal_set` entries specified when a record is [ingested](https://docs.globus.org/api/search/ingest/). See [role based filtering](https://docs.globus.org/api/search/guides/role_filtering/) for details. Globus Auth provides powerful granular control over all aspects of read _and_ write operations.


## 2. Get some citations
### Export from a citation manager
Globus search can index any kind of document ([up to ~10MB](https://docs.globus.org/api/search/limits/)), but it helps if your data is structured in a consistent way. To create this demo, I downloaded my personal citations from Google Scholar into [Zotero](https://www.zotero.org/) via a convenient [web browser extension](https://www.zotero.org/download/connectors), then exported the citations to RIS format. Almost any export format can be indexed, but RIS allowed me to export some file attachments for a more interesting demo. (the choice is an implementation detail)

### Transform data into the format expected by the server
The Globus Search API requires document information to be in a [specific format](https://docs.globus.org/api/search/reference/ingest/) for single or multiple data submissions. We provide example scripts showing how one file format might be converted into this format. Since our dataset is very small, we can combine all the items together and add them to the search index all at once. ("batch mode")

Like ElasticSearch, Globus Search uses [dynamic typings](https://docs.globus.org/api/search/mapped_data_types/): it assumes that all records will always have the same type of data in a given field. If you change the field type (like converting from a string to a date), you may experience errors that require rebuilding the entire collection from scratch. The sample scripts in this repository demonstrate how a text-based RIS file might be cleaned up to avoid common errors.

> Advanced tip:
> It's a good idea to keep a copy of your input data, in case you need to rebuild the index later!

## 3. Populate the search index
The CLI allows you to submit the JSON-formatted search data tpo be indexed. 

```bash
# Import documents into the index created previously. These can be new documents, OR updates to existing documents (subject IDs)
globus search ingest "${GSI_UUID}" "data/abought-citations-as-globus-gingest.json" --format json
```

A big collection can take some time to be processed, so you will receive a "Task" ID and can check it to see the result. If your data has errors, the task result will tell you what happened and how to fix it.

```bash
# Check on the search task (may finish quickly if dataset is small)
globus search task list "${GSI_UUID}"
globus search task show "$GS_TASKID" --format json
```

Once all records have been loaded successfully, the search API will list records in your collection! If you are updating existing records, the number of records should be the same as previously, but there will be new information in the index.

```bash
globus search index show "${GSI_UUID}" --format json --jq num_entries
```

If your updates do not show correctly, or you need to rebuild the index, use this command to wipe the entire index, then repopulate:
```bash
globus search delete-by-query "${GSI_UUID}" -q "*"
```

### Fixing a mistake
Globus Search uses [dynamic schemas](https://docs.globus.org/api/search/mapped_data_types/), inferred the first time it sees a new type of field in a document. If user data is messy, sometimes two fields with the same name will have a different data type, which can cause problems.

Changing the schema in Elasticsearch can be rather tricky, and _there is no substitute for cleaning up the data before it goes in_. There are times when it is helpful to re-index all documents to fix a problem; always keep a copy of the source data!

If you are updating an existing index, you might see ingest errors if the new documents use a different datatype in a field of the same name. If you see problems, you can either delete and recreate the index (if you are just starting out), or [contact Globus Support for help](https://docs.globus.org/api/search/mapped_data_types/#changing_the_type_of_indexed_data) (if this is an established search index). Don't delete an index that is part of an established website.

> Advanced tip: Some ElasticSearch users will index a hidden "dummy" document when the index is created. This ensures that the index will assume the correct datatypes for every field, even if there is bad data in one user-provided item. 

## 4. Run some example queries
We provide several example queries in this repository, based on the data format in the ingest records. Full documentation of query features is available if you would like to [build your own queries](https://docs.globus.org/api/search/reference/post_query/).

1. A query that discovers interesting facets (like "top keywords"), but does not search for any words. This is great for building a UI that suggests common categories for data exploration.
2. A query that imposes specific conditions, like "show me records that have supporting data attached"
3. A keyword search query that limits results to specific words from a particular date range

For today, we will run the example queries via the [Globus Command Line](https://docs.globus.org/cli/) (CLI). If you follow these instructions, your computer will have this handy tool installed and ready for all future projects. 

To run the example queries:
```bash
# First query discovers broad facets (like "top keywords"), but does not run a specific search. This is great for building a UI that suggests common categories for data exploration
globus search query "${GSI_UUID}" --query-document queries/query_facets.json --format json --jq "facet_results"

# Second query imposes conditions like "has sample data available"; filter conditions can be more abstract than just keywords! Note how the powerful JMESPath output filter syntax flattens a complex result into a more manageable list 
globus search query "${GSI_UUID}" --query-document queries/has_files.json --format json --jq "gmeta[].entries[]"

# Third query is generic key word search, much like you'd see in the web app search box. This search demonstrates an abbreviated output format
globus search query "${GSI_UUID}" -q "oocyte" --format text

# Fourth query demonstrates "advanced" search mode, where a single query string can search fields without creating an entire query document. This is useful for quick scripting experiments. Eg Filter by citation type and print just the number of results:
globus search query "${GSI_UUID}" -q 'citation.type_of_reference:JOUR' --advanced --format json --jq "total"

# Fifth query demonstrates combination of facets (tag counts) + filters (date range query) Note that results are paginated. To fetch beyond first page (offset parameter), you will need to use the SDK. The Globus CLI exposes many, but not all, of the available features.
globus search query "${GSI_UUID}" --limit 50 --query-document queries/date_range.json --format unix --jq "facet_results[].buckets[].[count, value]"
```

> NOTE: Future demos will emphasize the Globus SDK, which lets you control Globus features directly from other programming languages ([python](https://globus-sdk-python.readthedocs.io/en/stable/) or [JavaScript](https://globus.github.io/globus-sdk-javascript/)). Today's focus is on showing high level concepts, and we have used the CLI to make demos accessible to a broader audience. 

## 5. Upload supporting files
This step is not required to use Globus Search, but it is required to demonstrate the web application, which renders supporting files alongside user data.

### Find a Globus endpoint where you can store files
The same Globus Transfer service that moves data among researchers can optionally allow files to be downloaded from a webapp directly, with [granular access control](https://www.globus.org/platform/services/auth) provided by the Globus Platform.

We will be serving files directly from a file server [over HTTPS](https://docs.globus.org/globus-connect-server/v5/https-access-collections/), which requires a Globus endpoint. Many research groups already use Globus to transfer datasets, so you may already have an endpoint available... Contact your systems administrator to see if your local compute cluster will work for your needs.

### Use Globus Connect Personal to transfer your files directly to the server
* [Install Globus connect personal](https://docs.globus.org/globus-connect-personal/), which allows secure transfer between your computer and an endpoint
  * (optional) Configure the access rules to limit what data Globus can manage
* In the [Globus web app](https://app.globus.org/file-manager), set up a transfer between your local machine and the remote storage endpoint. Transfer your files to a subfolder on the server.


### Create a guest collection, exposing ONLY those files to the public
A "guest collection" allows sharing data with people who do not have account on your local system. You can share all or part of your data, and you can even set permissions to make the data public (viewable by anyone on the internet). Globus Search and Globus Auth can work together to control what data is shown.

Use the [Globus Web app](https://app.globus.org/collections) to [create a guest collection and manage permissions](https://docs.globus.org/guides/tutorials/manage-files/share-files/). For this demo, I made a guest collection in a subfolder of the Globus endpoint, and files in the guest collection are set to *public* visibility.

> NOTE: A Globus search index is not limited to just files, which means that there is no direct automatic link between the filesystem permissions (guest collection) and search `visible_to` access controls. Your application / data ingest pipeline is responsible for keeping permissions in sync.

## 6. Create a sample data portal
Follow the instructions in the Globus [template data portal](https://github.com/globus/template-data-portal) to clone your own project, and customize static.json with your search and file access preferences. This is a quick dataset browser with limited customization options, but it is useful for demonstrating what the Globus Platform can do.

> NOTE: This project is experimental. Features may be added/removed at any time, and there may be bugs.

## 7. View the demo webapp
An interactive webapp is available that uses the sample data prepared via the instructions in this document.
[View the demo](https://abought.github.io/apecx-demo-static-search-portal/search)

The webapp showcases how Globus features can integrate to create a rich interactive experience. It is based on the experimental [Globus template search portal](https://github.com/globus/template-search-portal?tab=readme-ov-file#staticjson), which provides a stock website for the most common basic search use cases.

Features of the portal include:

* Generate facets for data (like biological organisms), so that the UI doesn't have to be hardcoded. The website automatically updates available categories as new data arrives.
* Facet counts update as a search is performed, allowing users to drill down into the data one step at a time 
* Embeddable files (like pictures or interactive plots)
  * Search is not a dry technical subject. These discussions will allow us to start thinking about features that showcase your results for maximum impact 
* Show integration with other Globus Services, like transfer. In my case, I'll use a [Globus Connect Personal](https://www.globus.org/globus-connect-personal) endpoint to demonstrate transfer to my laptop (`~/Documents/globus-connect-personal/downloads`)


**This website is only a demo**- it's a quick hack based on a narrow special-purpose tool created for another project. We can, and will, create our own site with specialized features for APECx!
