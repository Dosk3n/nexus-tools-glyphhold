# Nexus tools for Glyph Hold

Version 2.1.1 targets Glyph Hold 2.x's `/api/v2` contract. Install the tool pack into your
Nexus environment and enable `nexus_tools_glyphhold.api` using the existing Nexus
pack-loading mechanism. Configure `GLYPHHOLD_URL`, `GLYPHHOLD_API_KEY`, optional
`GLYPHHOLD_TIMEOUT_SECONDS`, `GLYPHHOLD_VERIFY_SSL` and `GLYPHHOLD_CA_BUNDLE`.

Create a connection in Glyph Hold with explicit space grants and a default space. Use
separate keys for work/home connections as appropriate. General access requires
an explicit grant. Capabilities report the permitted destinations and effective
default. API-level admin scope never implicitly grants every space.

The `glyphhold` tool namespace exposes:

- capabilities, health, list_categories;
- prefetch_memories, search_memories, list_memories, get_memory;
- create_memory, update_memory, archive_memory, move_memory;
- list_memory_revisions, restore_memory_revision;
- get_context, set_context, placement_guidance;
- search_secrets, get_secret_metadata, create_secret, reveal_secret.

Recall uses the active space plus permitted General. Search broadens only when
requested. Returned records retain ID, version, space, provenance and freshness.
Use a unique conversation `session_id` consistently with context/recall/write
operations. Context is isolated by authenticated key and session. Finding a
record in another space never changes the normal write destination.

Search before creating. Create requires a caller-generated stable idempotency
key: reuse it for retries, and use a new key for a distinct operation. Updates,
archive, move and restore require the last-read `expected_version`. On conflict,
reread and reconcile. A move needs write access in both spaces. Owner-confirmed
placement guidance is available to writing agents; text hints never grant access.

Secret metadata excludes values; reveal is a separate operation used only for
an explicit user request or an authorised task requiring the value. The tools
are the same for built-in and Bitwarden/Vaultwarden providers. Bulk environment
reveals and destructive delete tools are deliberately not exposed.

This upgrade removes the v1 category permission model and unversioned maintenance
calls. Upgrade the service and pack together; GH2 disables legacy data routes by
default. Tool availability does not guarantee automatic recall: hosts must call
prefetch or use a native lifecycle integration such as the Hermes provider.

Run `python -m pytest tests`. Local tests cover transport, API request contracts,
path escaping, idempotency/version arguments and provider-neutral secret paths.
The test registry is isolated when Nexus is unavailable; validate tool registration
against your installed Nexus version before deployment.

Version 0.1.x targets Glyph Hold 1; upgrade the service and tool pack together.
HTTP redirects are rejected so credentials are never forwarded to another host.
Errors exclude response bodies, and responses are limited to 8 MiB; reduce the
requested record count if that budget is exceeded. Secret reveal supports legacy
`requesting_agent` and `tool` labels when an installation retains those constraints.

## Live secret providers (2.1)

With Vaultwarden enabled, search and metadata read all accessible vault entries
directly, including pre-existing items. Built-in secrets remain accessible.
Secret `space_id` is accepted for compatibility but no longer scopes access;
API keys still require secret permissions. Memory spaces are unchanged.

`create_secret` uses the active provider and rejects duplicate names. Optional
`folder_id` chooses a vault folder; omission uses the configured default and an
empty string means unfiled. `list_secret_folders` and `create_secret_folder`
manage optional folders. No memory-to-folder mapping or item linking is needed.

`reveal_secret(field=...)` selects a field from metadata (password, username,
SSH keys, notes, card/identity or custom fields). `update_secret` requires the
current metadata version and preserves other fields. External changes cannot
be made atomically against concurrent edits in other Bitwarden clients.

`migrate_secret` transfers a built-in secret without exposing its value to the
agent. Search first: provide an existing `target_id` and field to verify equal
values, or omit target ID to create only when the name is unused. Conflicts
retain both values for user review; never blindly overwrite or export plaintext.
Provider outages fail explicitly rather than look like an empty vault. Upgrade
the server and adapters together to use these operations.

### 2.1.1 search and migration recovery

`search_secrets(query=...)` also matches saved website addresses and hostnames,
including IP addresses. Metadata adds `websites` (normalised origins only) and
`hostnames`; URL usernames/passwords, paths, query tokens and fragments are
excluded. Multiple accounts stay separate; never select one by hostname alone.
Use `provider_name=builtin` for the remaining migration checklist.

`migrate_secret(dry_run=true)` checks an existing field or previews creation
without changing either provider. Known provider failure codes produce safe,
actionable tool errors; arbitrary error bodies are not echoed. An uncertain
write requires destination inspection before retrying.
