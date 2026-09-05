"""node_server dotenv persistence (atomic key updates).

The control service generates and persists a credential encryption key / internal
token once, so they survive restarts. These tests exercise the persistence path
against a temp .env — they never touch the real repo .env.

Imports go through the ``node_server`` package namespace: the module under test
(``bootstrap_ini``) resolves ``dotenv_loader`` as ``node_server.dotenv_loader``,
so importing it the same way here guarantees monkeypatching ``ENV_FILE`` patches
the same module object the code under test reads.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def temp_env(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nNODE_CONTROL_TOKEN=\nNODE_CREDENTIAL_ENCRYPTION_KEY=\n", encoding="utf-8")
    return env


def test_update_replaces_existing_key(temp_env):
    from node_server import dotenv_loader

    dotenv_loader.update_env_vars(
        {"NODE_CREDENTIAL_ENCRYPTION_KEY": "abc"},
        path=temp_env,
    )
    text = temp_env.read_text(encoding="utf-8")
    assert "NODE_CREDENTIAL_ENCRYPTION_KEY=abc" in text
    assert "# comment" in text
    assert "NODE_CONTROL_TOKEN=" in text


def test_update_appends_missing_key(temp_env):
    from node_server import dotenv_loader

    dotenv_loader.update_env_vars({"NEW_KEY": "value"}, path=temp_env)
    assert "NEW_KEY=value" in temp_env.read_text(encoding="utf-8")


def test_update_creates_file_when_missing(tmp_path):
    env = tmp_path / ".env"
    from node_server import dotenv_loader

    dotenv_loader.update_env_vars({"NODE_CONTROL_TOKEN": "generated"}, path=env)
    assert env.exists()
    assert "NODE_CONTROL_TOKEN=generated" in env.read_text(encoding="utf-8")


def test_bootstrap_ini_persists_via_loader(temp_env, monkeypatch):
    """``bootstrap_ini.update_ini_section`` delegates to the dotenv loader."""
    from node_server import bootstrap_ini, dotenv_loader

    monkeypatch.setattr(dotenv_loader, "ENV_FILE", temp_env)
    bootstrap_ini.update_ini_section("ai_lubricant", {"NODE_CONTROL_TOKEN": "tok"})
    assert "NODE_CONTROL_TOKEN=tok" in temp_env.read_text(encoding="utf-8")
