# Nexus on native Windows

Some Nexus runtimes serialize subprocess JSON with non-ASCII characters while
Windows pipes use a legacy encoding. A valid memory containing an arrow, emoji
or non-Latin text can then fail with a `charmap` encoding error.

`unicode-protocol.patch` changes only internal JSON messages to ASCII escaping.
JSON decoding restores the original Unicode text, including emoji. It does not
change memories, HTTP responses, secret handling or Glyph Hold's server image.
The patch covers host requests, persistent execution workers and tool workers.

This is a compatibility patch for Nexus core, not a change to the Glyph Hold
pack. Check the installed Nexus source first: versions already using ASCII-safe
JSON transport or explicit UTF-8 pipes may not need it. From a Nexus checkout:

```bash
git apply --check --ignore-space-change --ignore-whitespace /absolute/path/to/unicode-protocol.patch
git apply --ignore-space-change --ignore-whitespace /absolute/path/to/unicode-protocol.patch
```

Back up the three affected source files before applying to an installed bundle.
If the check fails, review the Nexus version instead of forcing the patch.
Restart the process hosting Nexus after changing its runtime files.

To run the actual legacy-encoding regression checks with Nexus's Python:

```powershell
$env:NEXUS_SOURCE_DIR = "C:\path\to\nexus"
python -m pytest C:\path\to\nexus-tools-glyphhold\compat\nexus-windows\test_unicode_protocol.py -q
```

These checks verify lossless arrow, emoji, Chinese and accented text through
CP1252 subprocess pipes. No user data or credentials are required.
