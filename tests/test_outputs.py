"""Tests for the npm workspace override resolver task."""
import json
import subprocess
from pathlib import Path

import pytest

ROOT_PKG = Path("/app/package.json")


@pytest.fixture(scope="module")
def package_json():
    assert ROOT_PKG.exists(), f"{ROOT_PKG} not found"
    return json.loads(ROOT_PKG.read_text())


@pytest.fixture(scope="module")
def overrides(package_json):
    assert "overrides" in package_json, (
        "No 'overrides' field found in /app/package.json. "
        "The agent must add an overrides block based on the RFC."
    )
    return package_json["overrides"]


# ── Correct final versions ────────────────────────────────────────────────────

def test_lodash_override(overrides):
    """lodash must be pinned to 4.17.21 (CVE-2021-23337 fix)."""
    assert overrides.get("lodash") == "4.17.21", (
        f"Expected lodash override '4.17.21', got '{overrides.get('lodash')}'"
    )


def test_semver_override(overrides):
    """semver must be pinned to 7.6.3 (Round 3 decision, not 7.5.4 or 7.6.0)."""
    assert overrides.get("semver") == "7.6.3", (
        f"Expected semver override '7.6.3', got '{overrides.get('semver')}'"
    )


def test_axios_override(overrides):
    """axios must be pinned to 1.6.8 (Round 3 decision, not the rejected 1.4.0 or Round 2's 1.6.0)."""
    assert overrides.get("axios") == "1.6.8", (
        f"Expected axios override '1.6.8', got '{overrides.get('axios')}'"
    )


def test_express_override(overrides):
    """express must be pinned to 4.19.2 (the rejected 4.18.3 must not be used)."""
    assert overrides.get("express") == "4.19.2", (
        f"Expected express override '4.19.2', got '{overrides.get('express')}'"
    )


def test_react_override(overrides):
    """react must be pinned to 18.3.1 (superseded 18.2.0 must not be used)."""
    assert overrides.get("react") == "18.3.1", (
        f"Expected react override '18.3.1', got '{overrides.get('react')}'"
    )


# ── Rejected / superseded versions must not appear ───────────────────────────

def test_axios_rejected_version_not_used(overrides):
    """axios 1.4.0 was explicitly rejected by the Security Guild — must not appear."""
    assert overrides.get("axios") != "1.4.0", (
        "axios override is '1.4.0', which was rejected in the RFC (does not fix CVE-2023-45857)"
    )


def test_express_rejected_version_not_used(overrides):
    """express 4.18.3 was explicitly rejected — must not appear."""
    assert overrides.get("express") != "4.18.3", (
        "express override is '4.18.3', which was rejected in the RFC (does not fix CVE-2024-29041)"
    )


def test_semver_superseded_version_not_used(overrides):
    """semver 7.5.4 and 7.6.0 were superseded by Round 3 — must not appear."""
    assert overrides.get("semver") not in ("7.5.4", "7.6.0"), (
        f"semver override '{overrides.get('semver')}' was superseded; final decision is 7.6.3"
    )


# ── No spurious overrides ─────────────────────────────────────────────────────

def test_no_extra_overrides(overrides):
    """Only the five approved packages should be in the overrides block."""
    approved = {"lodash", "semver", "axios", "express", "react"}
    extra = set(overrides.keys()) - approved
    assert not extra, (
        f"Unexpected overrides added: {extra}. "
        "Only lodash, semver, axios, express, and react are approved."
    )


def test_react_dom_not_overridden(overrides):
    """react-dom must NOT be in overrides — the RFC explicitly excluded it."""
    assert "react-dom" not in overrides, (
        "react-dom should not be overridden. The RFC deferred it to a direct dep update in @monostack/ui."
    )


# ── npm install ran successfully ──────────────────────────────────────────────

def test_npm_install_completed():
    """node_modules must exist, confirming npm install was run after overrides were applied."""
    assert Path("/app/node_modules").is_dir(), (
        "node_modules not found. The agent must run 'npm install' after updating package.json."
    )


def test_overrides_reflected_in_lockfile():
    """package-lock.json must reference the override versions, not the originals."""
    lock = Path("/app/package-lock.json")
    assert lock.exists(), "package-lock.json not found"
    data = json.loads(lock.read_text())
    packages = data.get("packages", {})
    # The lockfile should NOT contain the old vulnerable/outdated versions at the root
    old_versions = {
        "lodash": "4.17.20",
        "semver": "7.5.3",
        "axios": "1.3.4",
    }
    for pkg_name, old_ver in old_versions.items():
        entry = packages.get(f"node_modules/{pkg_name}", {})
        installed_ver = entry.get("version", "")
        assert installed_ver != old_ver, (
            f"{pkg_name} lockfile still shows old version '{old_ver}' — "
            f"override may not have been applied and npm install re-run"
        )


def test_package_lock_updated():
    """package-lock.json must exist and be updated (newer than package.json)."""
    lock = Path("/app/package-lock.json")
    assert lock.exists(), "package-lock.json not found — npm install may not have run"
    lock_data = json.loads(lock.read_text())
    assert lock_data.get("lockfileVersion", 0) >= 3, (
        "package-lock.json lockfileVersion should be 3 (npm 7+)"
    )
