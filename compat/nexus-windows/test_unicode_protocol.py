"""Verify Nexus subprocess Unicode transport using legacy Windows encodings."""

import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(os.environ["NEXUS_SOURCE_DIR"]).resolve()
sys.path.insert(0, str(ROOT))
VALUE = "\u2192 \U0001f511 \u4f60\u597d fianc\u00e9e"


@pytest.mark.parametrize(
    "module,function",
    [
        ("nexus.execution_worker", "_send_message"),
        ("nexus.tool_execution_worker", "_write_response"),
    ],
)
def test_worker_unicode_survives_windows_legacy_encoding(module, function):
    code = f"from {module} import {function}; {function}({{'value': {ascii(VALUE)}}})"
    env = os.environ.copy()
    env.update(PYTHONIOENCODING="cp1252", PYTHONUTF8="0", PYTHONPATH=str(ROOT))
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode("ascii", errors="replace")[:500]
    assert json.loads(result.stdout.decode("ascii")) == {"value": VALUE}


def test_host_unicode_requests_survive_windows_legacy_encoding():
    from nexus.runner import _send_worker_message

    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="cp1252")
    _send_worker_message(SimpleNamespace(stdin=stream), {"value": VALUE})
    assert json.loads(buffer.getvalue().decode("ascii")) == {"value": VALUE}
