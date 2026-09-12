"""Unit tests for the workflow security gate (scripts/check-workflow-security.py).

Covers the two rules it enforces from docs/security-posture.md:
  - 4a — every `uses:` is pinned to a full commit SHA with a `#` version
    comment (local `./` refs and `docker://@sha256:` refs exempt / pinned).
  - 4c — every workflow declares a top-level `permissions:` block and no
    `permissions: write-all` appears at workflow or job level.
Plus the main() happy path and failure edges.
"""

from __future__ import annotations

from pathlib import Path

SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"

# A fully-compliant workflow: top-level permissions, SHA-pinned step uses.
GOOD = f"""\
name: Test

on: push

permissions: {{}}

jobs:
  build:
    permissions:
      contents: read
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@{SHA} # v7.0.1
"""

# A compliant reusable-workflow caller job (job-level `uses:`), SHA-pinned
# first-party ref with a `# main` comment.
GOOD_CALLER = f"""\
name: Test

on: push

permissions: {{}}

jobs:
  caller:
    uses: damien-robotsix/robotsix-github-workflows/.github/workflows/ci.yml@{SHA} # main
"""

# 4c: no top-level permissions block at all.
NO_TOP_PERMISSIONS = f"""\
name: Test

on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA} # v7.0.1
"""

# 4c: write-all at the workflow level.
WORKFLOW_WRITE_ALL = f"""\
name: Test

on: push

permissions: write-all

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA} # v7.0.1
"""

# 4c: write-all at the job level.
JOB_WRITE_ALL = f"""\
name: Test

on: push

permissions: {{}}

jobs:
  build:
    permissions: write-all
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA} # v7.0.1
"""

# 4a: a mutable tag ref instead of a full SHA.
MUTABLE_REF = """\
name: Test

on: push

permissions: {}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4 # v4
"""

# 4a: a full SHA but no trailing `#` version comment.
SHA_NO_COMMENT = f"""\
name: Test

on: push

permissions: {{}}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA}
"""

# 4a: docker:// ref pinned to a digest (compliant).
DOCKER_PINNED = """\
name: Test

on: push

permissions: {}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: docker://ghcr.io/foo/bar@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
"""

# 4a: docker:// ref with a mutable tag (fails).
DOCKER_MUTABLE = """\
name: Test

on: push

permissions: {}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: docker://ghcr.io/foo/bar:latest
"""

# 4a: local ref is exempt.
LOCAL_REF = f"""\
name: Test

on: push

permissions: {{}}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: ./local-action@{SHA}
"""


def _write_workflow(tmp_path: Path, text: str, name: str = "test.yml") -> Path:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    wf = wf_dir / name
    wf.write_text(text)
    return wf


# ---------------------------------------------------------------------------
# check_workflow: the 4a/4c rules
# ---------------------------------------------------------------------------


def test_good_workflow_ok(check_workflow_security):
    assert check_workflow_security.check_workflow(GOOD) == []


def test_good_caller_ok(check_workflow_security):
    assert check_workflow_security.check_workflow(GOOD_CALLER) == []


def test_missing_top_permissions_fails(check_workflow_security):
    problems = check_workflow_security.check_workflow(NO_TOP_PERMISSIONS)
    assert any("top-level permissions" in p for p in problems)


def test_workflow_write_all_fails(check_workflow_security):
    problems = check_workflow_security.check_workflow(WORKFLOW_WRITE_ALL)
    assert any("write-all" in p for p in problems)


def test_job_write_all_fails(check_workflow_security):
    problems = check_workflow_security.check_workflow(JOB_WRITE_ALL)
    assert any("write-all" in p for p in problems)


def test_mutable_ref_fails(check_workflow_security):
    problems = check_workflow_security.check_workflow(MUTABLE_REF)
    assert any("not a full 40-char commit SHA" in p for p in problems)


def test_sha_without_comment_fails(check_workflow_security):
    problems = check_workflow_security.check_workflow(SHA_NO_COMMENT)
    assert any("trailing" in p and "#" in p for p in problems)


def test_docker_pinned_ok(check_workflow_security):
    assert check_workflow_security.check_workflow(DOCKER_PINNED) == []


def test_docker_mutable_fails(check_workflow_security):
    problems = check_workflow_security.check_workflow(DOCKER_MUTABLE)
    assert any("docker://" in p and "@sha256:" in p for p in problems)


def test_local_ref_exempt(check_workflow_security):
    assert check_workflow_security.check_workflow(LOCAL_REF) == []


# ---------------------------------------------------------------------------
# main(): end-to-end gate
# ---------------------------------------------------------------------------


def test_main_happy_path(tmp_path, check_workflow_security, monkeypatch):
    _write_workflow(tmp_path, GOOD)
    monkeypatch.setattr(
        check_workflow_security,
        "WORKFLOWS_DIR",
        tmp_path / ".github" / "workflows",
    )
    assert check_workflow_security.main() == 0


def test_main_violation_fails(
    tmp_path, check_workflow_security, monkeypatch, capsys
):
    _write_workflow(tmp_path, MUTABLE_REF)
    monkeypatch.setattr(
        check_workflow_security,
        "WORKFLOWS_DIR",
        tmp_path / ".github" / "workflows",
    )
    assert check_workflow_security.main() == 1
    assert "4a" in capsys.readouterr().out


def test_main_multiple_files(
    tmp_path, check_workflow_security, monkeypatch, capsys
):
    _write_workflow(tmp_path, GOOD, "good.yml")
    _write_workflow(tmp_path, JOB_WRITE_ALL, "bad.yml")
    monkeypatch.setattr(
        check_workflow_security,
        "WORKFLOWS_DIR",
        tmp_path / ".github" / "workflows",
    )
    assert check_workflow_security.main() == 1
    assert "bad.yml" in capsys.readouterr().out
