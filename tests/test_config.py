"""Tests for the robotsix-config reference implementation.

Cover the load precedence, secret masking, the 0600 secret-file writer, and the
deploy-template emitter — the four properties the config standard promises.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from robotsix_config import (
    CONFIG_FILE_ENV,
    RobotsixConfig,
    emit_deploy_template,
    resolve_config_path,
    write_config_file,
)


class _Imap(RobotsixConfig):
    model_config = SettingsConfigDict(
        env_prefix="ROBOTSIX_MAIL_",
        env_nested_delimiter="__",
        extra="ignore",
    )
    host: str = "localhost"
    port: int = 993


class _Mail(RobotsixConfig):
    model_config = SettingsConfigDict(
        env_prefix="ROBOTSIX_MAIL_",
        env_nested_delimiter="__",
        extra="ignore",
    )
    log_level: str = "info"
    password: SecretStr = SecretStr("")
    imap: _Imap = _Imap()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    for key in list(os.environ):
        if key.startswith("ROBOTSIX_"):
            monkeypatch.delenv(key, raising=False)


def _point_at(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setenv(CONFIG_FILE_ENV, str(path))


# -- config-path resolution -------------------------------------------------


def test_resolve_config_path_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(CONFIG_FILE_ENV, raising=False)
    assert resolve_config_path() == Path("config/config.yaml")


def test_resolve_config_path_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    p = tmp_path / "custom.yaml"
    _point_at(monkeypatch, p)
    assert resolve_config_path() == p


# -- precedence -------------------------------------------------------------


def test_defaults_when_no_file_or_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _point_at(monkeypatch, tmp_path / "missing.yaml")  # file absent → {}
    cfg = _Mail()
    assert cfg.log_level == "info"
    assert cfg.imap.host == "localhost"
    assert cfg.imap.port == 993


def test_yaml_overrides_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text("log_level: debug\nimap:\n  host: mail.example.com\n")
    _point_at(monkeypatch, p)
    cfg = _Mail()
    assert cfg.log_level == "debug"
    assert cfg.imap.host == "mail.example.com"
    assert cfg.imap.port == 993  # untouched default


def test_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text("log_level: debug\nimap:\n  host: mail.example.com\n")
    _point_at(monkeypatch, p)
    monkeypatch.setenv("ROBOTSIX_MAIL_LOG_LEVEL", "warning")
    monkeypatch.setenv("ROBOTSIX_MAIL_IMAP__HOST", "env.example.com")
    cfg = _Mail()
    assert cfg.log_level == "warning"  # env beats file
    assert cfg.imap.host == "env.example.com"  # nested env beats file


def test_kwargs_override_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text("log_level: debug\n")
    _point_at(monkeypatch, p)
    monkeypatch.setenv("ROBOTSIX_MAIL_LOG_LEVEL", "warning")
    cfg = _Mail(log_level="error")  # explicit kwarg = the CLI layer
    assert cfg.log_level == "error"


# -- secrets ----------------------------------------------------------------


def test_secret_is_masked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    p = tmp_path / "config.yaml"
    p.write_text('password: "hunter2"\n')
    _point_at(monkeypatch, p)
    cfg = _Mail()
    assert cfg.password.get_secret_value() == "hunter2"
    assert "hunter2" not in repr(cfg)  # masked in repr
    assert "hunter2" not in str(cfg.password)


def test_top_level_non_mapping_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    p = tmp_path / "config.yaml"
    p.write_text("- just\n- a\n- list\n")
    _point_at(monkeypatch, p)
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        _Mail()


# -- 0600 writer ------------------------------------------------------------


def test_write_config_file_is_0600(tmp_path: Path):
    target = tmp_path / "nested" / "config.yaml"
    write_config_file(target, {"a": 1, "secret": ""})
    assert target.is_file()
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700


def test_write_config_file_tightens_preexisting_lax_file(tmp_path: Path):
    target = tmp_path / "config.yaml"
    target.write_text("old: 1\n")
    target.chmod(0o644)  # simulate a pre-existing world-readable file
    write_config_file(target, {"new": 2})
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_write_config_file_round_trips(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    target = tmp_path / "config.yaml"
    payload = {"log_level": "info", "imap": {"host": "h", "port": 993}}
    write_config_file(target, payload)
    _point_at(monkeypatch, target)
    cfg = _Mail()
    assert cfg.imap.host == "h"


# -- deploy template --------------------------------------------------------


def test_emit_deploy_template():
    import yaml

    text = emit_deploy_template(_Mail)
    data = yaml.safe_load(text)
    assert data["log_level"] == "info"  # default preserved
    assert data["password"] == ""  # secret slot is empty
    assert data["imap"] == {"host": "localhost", "port": 993}  # nested model expanded


def test_emit_template_required_secret_slot():
    class _Svc(RobotsixConfig):
        name: str  # required, no default
        token: SecretStr  # required secret

    import yaml

    data = yaml.safe_load(emit_deploy_template(_Svc))
    assert data["token"] == ""  # secret slot
    assert data["name"] == ""  # required str → empty placeholder
