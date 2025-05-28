# Useful CLI examples

Many of the scripts in this repository are amed at demonstrating full SDK automation, but they are not the only way to use Globus.

This demonstrates some useful CLI examples for regular usage scenarios. It may be expanded over time.

## Transfer
A basic transfer can be initiated via the CLI.

```bash
GLOBUS_SOURCE_COLL="REPLACEME"
GLOBUS_SOURCE_PATH="REPLACEME"

GLOBUS_DEST_COLL="REPLACEME"
GLOBUS_DEST_PATH="REPLACEME"

globus transfer \
  --label "One time transfer via CLI" \
  --sync-level checksum \
  --preserve-timestamp \
  --encrypt-data \
  ${GLOBUS_SOURCE_COLL}:${GLOBUS_SOURCE_PATH} ${GLOBUS_DEST_COLL}:${GLOBUS_DEST_PATH}
```



## Timers
### Scheduling a transfer for later
Sometimes, a destination collection will be down for maintenance. It may be useful to schedule a transfer to *only*
begin after the maintenance window ends, and to only run once. This can be accomplished by creating a timer. 
([see docs](https://docs.globus.org/cli/reference/timer_create_transfer/))

```bash
# Start trying the transfer at 5PM UTC-4 time, on a specific day
GLOBUS_SOURCE_COLL="REPLACEME"
GLOBUS_SOURCE_PATH="REPLACEME"

GLOBUS_DEST_COLL="REPLACEME"
GLOBUS_DEST_PATH="REPLACEME"

globus timer create transfer \
  --name "Schedule a transfer for when maintenance window is complete" \
  --label "One time scheduled transfer" \
  --stop-after-runs 1 \
  --start "2025-05-29T17:00:00-04:00" \
  --sync-level checksum \
  --encrypt-data \
  --preserve-timestamp \
   ${GLOBUS_SOURCE_COLL}:${GLOBUS_SOURCE_PATH} ${GLOBUS_DEST_COLL}:${GLOBUS_DEST_PATH}
```
