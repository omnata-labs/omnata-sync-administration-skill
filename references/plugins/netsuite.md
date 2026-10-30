# NetSuite

| | |
|---|---|
| Plugin FQN | `OMNATA__NETSUITE` |
| Page | `netsuite.md` |

Look up directions, outbound strategies and stream strategies from the installed apps first ("Plugin capabilities come from the installed apps" in `configure-syncs.md`). Point the user to the plugin's `DOCS_URL` for explanations and setup.

## Inbound

**Sync parameters** (`SYNC_PARAMETERS`): None, pass `OBJECT_CONSTRUCT()`.

**Streams**: discovered from the SuiteAnalytics Connect tables, named by table name, such as `transaction` and `customer`. Some tables have no source-defined primary key and need `STREAM_PRIMARY_KEYS`.

## Notes

- The NetSuite JDBC driver must be installed, with network access on TCP port 1708. See the docs.
- The first stream listing can take several minutes on large accounts.
- NetSuite limits concurrent connections per account. Keep the `max_concurrent_streams` tuning parameter well below that limit.
- Tables for multi-select relationships, named with a map_ prefix, are not selected automatically. Add them to `STREAM_NAMES` yourself.
