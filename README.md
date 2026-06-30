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
