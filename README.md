# nexus-tools-glyphhold

Nexus tool pack for connecting agents to Glyph Hold memory and secrets.

## Install

From a Nexus checkout or runtime environment:

```bash
pip install -e /path/to/nexus-tools-glyphhold
```

## Configure

Set the Glyph Hold connection values in the environment used by Nexus, or in Nexus' `.env` file:

```env
NEXUS_TOOL_PACKAGES=nexus_tools_glyphhold
GLYPHHOLD_URL=https://glyphhold.example.com
GLYPHHOLD_API_KEY=gh_live_xxxxxxxxxxxxxxxxx
```

If combining with other tool packs, append the package root:

```env
NEXUS_TOOL_PACKAGES=nexus_tools_sonarr,nexus_tools_radarr,nexus_tools_tautulli,nexus_tools_glyphhold
```

## Safety

Secret metadata tools do not return secret values. Secret reveal tools are intended only for explicit user requests to reveal or use secret values.

## Tools

This pack registers tools under the `glyphhold` namespace.

Memory tools:

- `glyphhold.health`
- `glyphhold.list_categories`
- `glyphhold.list_memories`
- `glyphhold.get_memory`
- `glyphhold.search_memories`
- `glyphhold.prefetch_memories`
- `glyphhold.find_similar_memories`
- `glyphhold.prepare_memory_write`
- `glyphhold.create_memory`
- `glyphhold.update_memory`
- `glyphhold.update_memory_confidence`
- `glyphhold.archive_memory`
- `glyphhold.supersede_memory`
- `glyphhold.list_memory_revisions`
- `glyphhold.restore_memory_revision`
- `glyphhold.delete_memory`

Secret tools:

- `glyphhold.search_secrets`
- `glyphhold.get_secret_metadata`
- `glyphhold.create_secret`
- `glyphhold.update_secret`
- `glyphhold.delete_secret`
- `glyphhold.reveal_secret`
- `glyphhold.reveal_secret_env`

## Development

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e /path/to/nexus/nexus -e '.[dev]'
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
```

When testing against a local Nexus checkout whose editable install does not expose the `nexus` package, run Nexus-backed tests with the checkout root on `PYTHONPATH`:

```bash
PYTHONPATH=/path/to/nexus .venv/bin/python -m pytest -q tests/test_api.py
```
