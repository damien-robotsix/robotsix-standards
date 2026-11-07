"""Unit tests for the Dockerfile pin-shape gate (scripts/check-dockerfile-pins.py).

These tests exercise the parsing and violation logic directly: file matching
(is_dockerfile / find_dockerfiles), continuation joining
(logical_instructions), the pin-shape rules (check_dockerfile) and the
main() exit codes.

docs/docker-standard.md (Build) requires every external image to be written
literally on a ``FROM`` line as ``<image>:<tag>@sha256:<digest>`` so
Dependabot can bump it. The gate is published as the remote
``check-dockerfile-pins`` pre-commit hook, so these tests also cover the
hook's calling convention: pre-commit passes the matched file paths, and the
script runs from the consumer repo's root, not from its own checkout.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

DIGEST = "sha256:" + "a" * 64
UV_DIGEST = "sha256:" + "b" * 64

VALID = f"""\
# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.11.26@{UV_DIGEST} AS uv

FROM python:3.14-slim@{DIGEST} AS base
RUN useradd app

FROM base AS builder
COPY --from=uv /uv /usr/local/bin/uv
RUN uv sync

FROM base
COPY --from=builder /app /app
"""

GOOD = f"""\
FROM python:3.14-slim@{DIGEST} AS base
FROM ghcr.io/astral-sh/uv:0.11.26@{DIGEST} AS uv
FROM base AS builder
COPY --from=uv /uv /uvx /bin/
FROM base
COPY --from=builder /app /app
"""


def _problems(module: ModuleType, text: str) -> list[str]:
    return [problem for _, problem in module.check_dockerfile(text)]


# --- is_dockerfile -----------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["Dockerfile", "Dockerfile.dev", "Dockerfile.prod", "worker.Dockerfile"],
)
def test_is_dockerfile_matches(check_dockerfile_pins: ModuleType, name: str) -> None:
    assert check_dockerfile_pins.is_dockerfile(Path("some/dir") / name)


@pytest.mark.parametrize(
    "name",
    ["dockerfile", "Dockerfile-dev", "MyDockerfile", "docker-compose.yml", "README.md"],
)
def test_is_dockerfile_rejects(check_dockerfile_pins: ModuleType, name: str) -> None:
    assert not check_dockerfile_pins.is_dockerfile(Path(name))


# --- find_dockerfiles --------------------------------------------------------


def test_find_dockerfiles_skips_excluded_dirs(
    check_dockerfile_pins: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "services" / "api").mkdir(parents=True)
    (tmp_path / "services" / "api" / "api.Dockerfile").write_text("FROM scratch\n")
    for excluded in (".git", ".venv", "node_modules", "site", "_build", "venv"):
        (tmp_path / excluded / "nested").mkdir(parents=True)
        (tmp_path / excluded / "nested" / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "README.md").write_text("not a dockerfile\n")
    (tmp_path / "Dockerfile.d").mkdir()  # a directory, not a file

    found = check_dockerfile_pins.find_dockerfiles(tmp_path)

    assert [p.relative_to(tmp_path).as_posix() for p in found] == [
        "Dockerfile",
        "services/api/api.Dockerfile",
    ]


def test_find_dockerfiles_empty(check_dockerfile_pins: ModuleType, tmp_path: Path) -> None:
    assert check_dockerfile_pins.find_dockerfiles(tmp_path) == []


# --- logical_instructions ----------------------------------------------------


def test_logical_instructions_joins_continuations(
    check_dockerfile_pins: ModuleType,
) -> None:
    text = (
        "# comment\n"
        "FROM python:3.14-slim AS base\n"
        "\n"
        "RUN apt-get update \\\n"
        "    # comment inside a continuation\n"
        "    && apt-get install -y curl \\\n"
        "    && rm -rf /var/lib/apt/lists/*\n"
        "COPY . /app\n"
    )

    assert check_dockerfile_pins.logical_instructions(text) == [
        (2, "FROM python:3.14-slim AS base"),
        (
            4,
            (
                "RUN apt-get update  && apt-get install -y curl  "
                "&& rm -rf /var/lib/apt/lists/*"
            ),
        ),
        (8, "COPY . /app"),
    ]


def test_logical_instructions_trailing_continuation(
    check_dockerfile_pins: ModuleType,
) -> None:
    assert check_dockerfile_pins.logical_instructions("FROM a \\\n") == [(1, "FROM a")]


# --- check_dockerfile: accepted shapes ---------------------------------------


def test_check_accepts_valid_dockerfile(check_dockerfile_pins: ModuleType) -> None:
    # Python base first, a digest-pinned uv stage, later stages via FROM base.
    text = f"""\
FROM python:3.14-slim@{DIGEST} AS base
FROM ghcr.io/astral-sh/uv:0.11.26@{UV_DIGEST} AS uv
FROM base AS builder
COPY --from=uv /uv /usr/local/bin/uv
FROM base
COPY --from=builder /app /app
COPY --from=0 /etc/passwd /etc/passwd
"""
    assert check_dockerfile_pins.check_dockerfile(text) == []


def test_check_accepts_later_from_base_case_insensitive(
    check_dockerfile_pins: ModuleType,
) -> None:
    text = f"FROM python:3.14-slim@{DIGEST} AS Base\nFROM base\nFROM BASE AS final\n"
    assert check_dockerfile_pins.check_dockerfile(text) == []


def test_check_accepts_from_with_platform_flag(
    check_dockerfile_pins: ModuleType,
) -> None:
    text = f"FROM --platform=linux/amd64 python:3.14-slim@{DIGEST} AS base\n"
    assert check_dockerfile_pins.check_dockerfile(text) == []


def test_check_accepts_multiline_from(check_dockerfile_pins: ModuleType) -> None:
    text = f"FROM \\\n    python:3.14-slim@{DIGEST} \\\n    AS base\n"
    assert check_dockerfile_pins.check_dockerfile(text) == []


# --- check_dockerfile: rejected shapes ---------------------------------------


def test_check_rejects_digest_in_arg(check_dockerfile_pins: ModuleType) -> None:
    text = "ARG BASE_DIGEST\nFROM python:3.14-slim@${BASE_DIGEST} AS base\n"
    result = check_dockerfile_pins.check_dockerfile(text)
    assert len(result) == 1
    lineno, problem = result[0]
    assert lineno == 2
    assert "held in an ARG" in problem


def test_check_rejects_image_in_arg(check_dockerfile_pins: ModuleType) -> None:
    text = "ARG BASE_IMAGE\nFROM $BASE_IMAGE\n"
    assert any("held in an ARG" in p for p in _problems(check_dockerfile_pins, text))


@pytest.mark.parametrize(
    "image",
    [
        f"python@{DIGEST}",  # missing tag
        "python:3.14-slim",  # missing digest
        "python",  # neither
        "python:3.14-slim@sha256:abc",  # truncated digest
        "python:3.14-slim@sha256:" + "A" * 64,  # uppercase hex
    ],
)
def test_check_rejects_unpinned_image(
    check_dockerfile_pins: ModuleType, image: str
) -> None:
    result = check_dockerfile_pins.check_dockerfile(f"FROM {image} AS base\n")
    assert len(result) == 1
    lineno, problem = result[0]
    assert lineno == 1
    assert "must be <image>:<tag>@sha256:<digest>" in problem


def test_check_rejects_non_python_first_from(
    check_dockerfile_pins: ModuleType,
) -> None:
    text = (
        f"FROM ghcr.io/astral-sh/uv:0.11.26@{UV_DIGEST} AS uv\n"
        f"FROM python:3.14-slim@{DIGEST} AS base\n"
    )
    result = check_dockerfile_pins.check_dockerfile(text)
    assert len(result) == 1
    lineno, problem = result[0]
    assert lineno == 1
    assert "first FROM must be the python base" in problem


def test_check_valid_fixture_with_uv_first_flags_only_order(
    check_dockerfile_pins: ModuleType,
) -> None:
    problems = _problems(check_dockerfile_pins, VALID)
    assert len(problems) == 1
    assert "first FROM must be the python base" in problems[0]


def test_check_rejects_inline_registry_image_in_copy_from(
    check_dockerfile_pins: ModuleType,
) -> None:
    text = (
        f"FROM python:3.14-slim@{DIGEST} AS base\n"
        "COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv\n"
    )
    result = check_dockerfile_pins.check_dockerfile(text)
    assert len(result) == 1
    lineno, problem = result[0]
    assert lineno == 2
    assert "--from must name a prior stage" in problem


def test_check_rejects_copy_from_undefined_stage(
    check_dockerfile_pins: ModuleType,
) -> None:
    text = (
        f"FROM python:3.14-slim@{DIGEST} AS base\n"
        "COPY --from=builder /app /app\n"
        "FROM base AS builder\n"
    )
    result = check_dockerfile_pins.check_dockerfile(text)
    assert len(result) == 1
    lineno, problem = result[0]
    assert lineno == 2
    assert "COPY --from=builder" in problem


def test_check_rejects_missing_from(check_dockerfile_pins: ModuleType) -> None:
    assert check_dockerfile_pins.check_dockerfile("RUN echo hi\n") == [
        (1, "no FROM instruction found")
    ]


def test_check_rejects_empty_from(check_dockerfile_pins: ModuleType) -> None:
    assert _problems(check_dockerfile_pins, "FROM --platform=linux/amd64\n") == [
        "FROM without an image reference",
        "no FROM instruction found",
    ]


# --- main --------------------------------------------------------------------


def test_main_no_dockerfiles(
    check_dockerfile_pins: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    assert check_dockerfile_pins.main([]) == 0
    assert "Checked 0 Dockerfile(s)" in capsys.readouterr().out


def test_main_valid_dockerfile(
    check_dockerfile_pins: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "Dockerfile").write_text(
        f"FROM python:3.14-slim@{DIGEST} AS base\nFROM base\n"
    )
    monkeypatch.chdir(tmp_path)
    assert check_dockerfile_pins.main([]) == 0


def test_main_violation(
    check_dockerfile_pins: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "docker").mkdir()
    (tmp_path / "docker" / "Dockerfile").write_text(
        "FROM python:3.14-slim@${BASE_DIGEST}\n"
    )
    monkeypatch.chdir(tmp_path)
    assert check_dockerfile_pins.main([]) == 1
    out = capsys.readouterr().out
    assert "docker/Dockerfile:1:" in out
    assert "held in an ARG" in out


def test_readable_shape_passes(check_dockerfile_pins: ModuleType) -> None:
    assert _problems(check_dockerfile_pins, GOOD) == []


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("ARG D\nFROM python:3.14-slim@${D}\n", "ARG"),
        ("FROM python:3.14-slim\n", "<image>:<tag>@sha256:<digest>"),
        (
            (
                f"FROM python:3.14-slim@{DIGEST} AS base\n"
                "FROM ghcr.io/astral-sh/uv:0.11.26 AS uv\n"
            ),
            "<image>:<tag>@sha256:<digest>",
        ),
        (
            (
                f"FROM python:3.14-slim@{DIGEST}\n"
                "COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /bin/\n"
            ),
            "--from must name a prior stage",
        ),
        (
            f"FROM ghcr.io/astral-sh/uv:0.11.26@{DIGEST} AS uv\n",
            "first FROM must be the python base",
        ),
    ],
)
def test_unreadable_pins_fail(
    check_dockerfile_pins: ModuleType, text: str, fragment: str
) -> None:
    problems = _problems(check_dockerfile_pins, text)
    assert any(fragment in problem for problem in problems), problems


def test_main_checks_paths_passed_by_pre_commit(
    check_dockerfile_pins: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Dockerfile").write_text(GOOD, encoding="utf-8")
    (tmp_path / "bad.Dockerfile").write_text("FROM python:3.14-slim\n", encoding="utf-8")
    assert check_dockerfile_pins.main(["Dockerfile"]) == 0
    assert check_dockerfile_pins.main(["Dockerfile", "bad.Dockerfile"]) == 1


def test_main_without_args_scans_cwd(
    check_dockerfile_pins: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert check_dockerfile_pins.main([]) == 0
    sub = tmp_path / "svc"
    sub.mkdir()
    (sub / "Dockerfile").write_text("FROM python:3.14-slim\n", encoding="utf-8")
    assert check_dockerfile_pins.main([]) == 1
