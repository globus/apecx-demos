## Rendering example files
This demonstration relies on a search index with several example files. The initial demo uses a public GCS collection
    with a specific set of named files:

https://app.globus.org/file-manager?origin_id=a09b6cd8-9c06-4265-a2c9-7334949a5026&origin_path=%2F&two_pane=false

The guest collection provides public read permissions and is backed by an HTTPS server base URL of: 
https://g-b89568.554f69.8540.data.globus.org/

A sample search index was created manually to reference those files and provide test cases:

```bash
globus search index create "profserv - File Render Demo" "A list of various file types to render for testing purposes in a DGPF app"
```

```bash
GSI_UUID="ae4b521e-77b0-4047-997b-d45ca14194f1"
```
```bash
globus search ingest "${GSI_UUID}" "data/example_files.json"
```
