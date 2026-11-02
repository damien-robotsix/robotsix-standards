#!/usr/bin/env python3
"""Dockerfile pin-shape gate: every image pin is one Dependabot can read.

docs/docker-standard.md (Build) and docs/security-posture.md (gate 3) require
every external image reference to be written literally on a ``FROM`` line as
``<image>:<tag>@sha256:<digest>``, with the python base as the first ``FROM``
and later python stages reusing it via ``FROM base``. The uv binary comes in
through a digest-pinned named stage, and ``COPY --from`` may only name a stage.

Dependabot's ``docker`` ecosystem reads only that shape. A digest held in an
``ARG`` (``FROM python:3.14-slim@${BASE_DIGEST}``) or an image pulled inline
(``COPY --from=ghcr.io/astral-sh/uv:0.11.26``) is never bumped and never
flagged, so the base image silently stops receiving OS security patches.

**Failure mode prevented:** a base-image or uv pin that Dependabot cannot see
is never bumped, while gate 3 still appears satisfied.

Fail-closed: any violation exits 1. The script checks the Dockerfiles named on
the command line (pre-commit passes the staged ones when this runs as the
remote ``check-dockerfile-pins`` hook published in ``.pre-commit-hooks.yaml``);
with no arguments it scans every ``Dockerfile`` (or ``*.Dockerfile`` /
``Dockerfile.*``) under the current directory and exits 0 when there is none.

Exits 0 when every Dockerfile uses the Dependabot-readable shape, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from pathlib import Path

# Directories never scanned (vendored or generated trees, VCS metadata).
EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "site", "_build"}

# A literal, tagged, digest-pinned external image reference.
PINNED_IMAGE_RE = re.compile(r"[^\s@$]+:[^\s@$]+@sha256:[0-9a-f]{64}")


def is_dockerfile(path: Path) -> bool:
    """Return True for ``Dockerfile``, ``Dockerfile.*`` and ``*.Dockerfile``."""
    name = path.name
    return (
        name == "Dockerfile"
        or name.startswith("Dockerfile.")
        or name.endswith(".Dockerfile")
    )


def find_dockerfiles(root: Path) -> list[Path]:
    """Return every Dockerfile under ``root``, skipping excluded directories."""
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and is_dockerfile(path)
        and not EXCLUDED_DIRS.intersection(path.relative_to(root).parts)
    )


def logical_instructions(text: str) -> list[tuple[int, str]]:
    """Join backslash continuations; return ``(first_line_number, instruction)``.

    Comment and blank lines are dropped, including inside a continuation, as
    Docker itself does.
    """
    instructions: list[tuple[int, str]] = []
    pending = ""
    start = 0
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not pending:
            start = lineno
        if stripped.endswith("\\"):
            pending += stripped[:-1] + " "
            continue
        instructions.append((start, pending + stripped))
        pending = ""
    if pending.strip():
        instructions.append((start, pending.strip()))
    return instructions


def check_dockerfile(text: str) -> list[tuple[int, str]]:
    """Return ``(line_number, problem)`` pairs for one Dockerfile's text."""
    problems: list[tuple[int, str]] = []
    stages: set[str] = set()
    seen_from = False

    for lineno, instruction in logical_instructions(text):
        keyword, _, rest = instruction.partition(" ")
        keyword = keyword.upper()

        if keyword == "FROM":
            tokens = [tok for tok in rest.split() if not tok.startswith("--")]
            if not tokens:
                problems.append((lineno, "FROM without an image reference"))
                continue
            image = tokens[0]
            alias = (
                tokens[2].lower()
                if len(tokens) >= 3 and tokens[1].upper() == "AS"
                else None
            )
            first = not seen_from
            seen_from = True

            if image.lower() in stages:
                # Reuse of an earlier named stage (`FROM base`): the digest is
                # written once, on the stage that declared it.
                pass
            elif image == "scratch":
                pass
            elif "$" in image:
                problems.append(
                    (
                        lineno,
                        f"FROM {image}: image held in an ARG (Dependabot cannot bump it)",
                    )
                )
            elif not PINNED_IMAGE_RE.fullmatch(image):
                problems.append(
                    (
                        lineno,
                        f"FROM {image}: external image must be <image>:<tag>@sha256:<digest>",
                    )
                )
            elif first and not image.startswith("python:"):
                problems.append(
                    (lineno, f"FROM {image}: the first FROM must be the python base")
                )

            if alias:
                stages.add(alias)

        elif keyword == "COPY":
            for tok in rest.split():
                if not tok.startswith("--from="):
                    continue
                value = tok[len("--from=") :]
                if value.isdigit() or value.lower() in stages:
                    continue
                problems.append(
                    (
                        lineno,
                        (
                            f"COPY {tok}: --from must name a prior stage "
                            "(an inline registry image is invisible to Dependabot)"
                        ),
                    )
                )

    if not seen_from:
        problems.append((1, "no FROM instruction found"))
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Check Dockerfiles for the Dependabot-readable pin shape.

    Checks the paths given in ``argv`` (as pre-commit passes them) or, with no
    paths, every Dockerfile under the current directory — never this script's
    own checkout, which is a pre-commit cache when run as a remote hook.

    Exit codes:
      0 — no Dockerfile, or every Dockerfile uses the readable pin shape
      1 — one or more pins are not written where Dependabot reads them
    """
    args = list(argv) if argv is not None else sys.argv[1:]
    root = Path.cwd()
    if args:
        dockerfiles = [Path(arg) for arg in args]
    else:
        dockerfiles = [path.relative_to(root) for path in find_dockerfiles(root)]
    print(f"Checked {len(dockerfiles)} Dockerfile(s) for Dependabot-readable pins ...")

    failing: list[str] = []
    for path in dockerfiles:
        rel = path.as_posix()
        for lineno, problem in check_dockerfile(path.read_text(encoding="utf-8")):
            failing.append(f"  {rel}:{lineno}: {problem}")

    if failing:
        print("\n".join(failing))
        print(
            f"\n{len(failing)} pin(s) not in the Dependabot-readable shape. Write each "
            "external image literally on a FROM line as <image>:<tag>@sha256:<digest>, "
            "with the python base first (docs/docker-standard.md#build-the-dockerfile)."
        )
        return 1

    print("All Dockerfile pins are Dependabot-readable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
