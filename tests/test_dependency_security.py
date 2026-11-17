"""Appliance version/pin policy and actual-target inventory regression checks."""

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from scripts import audit_target_python as audit

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "buildroot/external/board/radio"


def test_application_and_ci_use_appliance_python():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["project"]["requires-python"] == ">=3.14"
    assert project["tool"]["ruff"]["target-version"] == "py314"
    assert project["tool"]["mypy"]["python_version"] == "3.14"
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    assert "strategy" not in workflow["jobs"]["checks"]
    steps = workflow["jobs"]["checks"]["steps"]
    assert any(step.get("with", {}).get("python-version") == "3.14" for step in steps)
    assert any("pip_audit" in step.get("run", "") for step in steps)


def test_runtime_pins_match_target_security_policy():
    pins = dict(
        line.lower().split("==")
        for line in (ROOT / "requirements.txt").read_text().splitlines()
        if "==" in line and not line.startswith("#")
    )
    for name, version in audit.REQUIRED.items():
        assert pins[name] == version


def test_buildroot_security_overrides_are_loaded_before_package_finalization(tmp_path):
    config = (ROOT / "buildroot/external/configs/radio_rpi3_defconfig").read_text()
    assert (
        'BR2_PACKAGE_OVERRIDE_FILE="$(BR2_EXTERNAL_RADIO_PATH)/board/radio/python-security.mk"'
        in config
    )
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        f"include {BOARD}/python-security.mk\n"
        "PYTHON_PILLOW_VERSION = 12.0.0\n"
        "PYTHON_PILLOW_DIR := build/python-pillow-$(PYTHON_PILLOW_VERSION)\n"
        "PYTHON_PILLOW_BUILD_OPTS = -Clibavif=disable\n"
        "BR2_PACKAGE_FREETYPE = y\nBR2_PACKAGE_JPEG = y\n"
        "all:\n\t@echo $(PYTHON_PILLOW_DIR) $(PYTHON_PILLOW_BUILD_OPTS)\n"
    )
    result = subprocess.run(
        ["make", "-f", str(makefile)], check=True, capture_output=True, text=True
    )
    assert "python-pillow-13.0.0" in result.stdout
    assert "-Cfreetype=enable" in result.stdout
    assert "-Cjpeg=enable" in result.stdout
    assert "-Cavif=disable" in result.stdout
    assert "-Clibavif" not in result.stdout
    overrides = (BOARD / "python-security.mk").read_text()
    assert "override PYTHON_IDNA_HASH_FILES =" in overrides
    assert "override HOST_PYTHON_IDNA_HASH_FILES =" in overrides
    for name in ("pillow", "requests", "urllib3", "certifi", "idna", "numpy"):
        version = audit.REQUIRED[name]
        hashes = BOARD / f"patches/python-{name}/{version}/python-{name}.hash"
        assert f"{name}-{version}.tar.gz" in hashes.read_text()
    patch = (
        BOARD
        / "patches/python-pillow/13.0.0/0001-Skip-Python-installation-paths-for-build-tree-Python.patch"
    )
    assert "+        if not sysconfig.is_python_build():" in patch.read_text()


def _target(tmp_path, packages=None):
    site = tmp_path / "usr/lib/python3.14/site-packages"
    site.mkdir(parents=True)
    for name, version in (audit.REQUIRED if packages is None else packages).items():
        directory = site / f"{name}-{version}.dist-info"
        directory.mkdir()
        (directory / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
        )
    return tmp_path


def test_target_inventory_includes_transitive_dependencies(tmp_path):
    target = _target(tmp_path, {**audit.REQUIRED, "typing_extensions": "4.15.0"})
    assert audit.inventory(target)["typing-extensions"] == "4.15.0"


def test_target_inventory_rejects_wrong_interpreter(tmp_path):
    with pytest.raises(ValueError, match="Python 3.14"):
        audit.inventory(tmp_path)


def test_target_inventory_rejects_duplicate_distribution(tmp_path):
    target = _target(tmp_path)
    site = target / "usr/lib/python3.14/site-packages"
    duplicate = site / "pillow-12.0.0.dist-info"
    duplicate.mkdir()
    (duplicate / "METADATA").write_text("Name: Pillow\nVersion: 12.0.0\n")
    with pytest.raises(ValueError, match="Duplicate target distribution"):
        audit.inventory(target)


@pytest.mark.parametrize(
    "metadata",
    ["Name: invalid/name\nVersion: 1.0\n", "Name: extra\n", "Name: extra\nVersion: 1.0 --option\n"],
)
def test_target_inventory_rejects_invalid_metadata(tmp_path, metadata):
    target = _target(tmp_path)
    directory = target / "usr/lib/python3.14/site-packages/extra-1.0.dist-info"
    directory.mkdir()
    (directory / "METADATA").write_text(metadata)
    with pytest.raises(ValueError, match="Invalid target distribution metadata"):
        audit.inventory(target)


def test_target_audit_missing_inventory_exits_with_diagnostic(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["audit_target_python.py", str(tmp_path)])
    with pytest.raises(SystemExit) as raised:
        audit.main()
    assert raised.value.code == 1
    assert "Target Python audit:" in capsys.readouterr().err


@pytest.mark.parametrize("version", [None, "12.0.0"])
def test_target_inventory_rejects_missing_or_stale_pillow(tmp_path, version):
    packages = dict(audit.REQUIRED)
    if version is None:
        packages.pop("pillow")
    else:
        packages["pillow"] = version
    with pytest.raises(ValueError, match="pillow==13.0.0"):
        audit.inventory(_target(tmp_path, packages))


def test_target_audit_propagates_security_failure_and_saves_inventory(tmp_path, monkeypatch):
    target = _target(tmp_path / "target")
    output = tmp_path / "inventory.txt"
    monkeypatch.setattr(
        sys, "argv", ["audit_target_python.py", str(target), "--output", str(output)]
    )

    def run(command, **kwargs):
        assert "--strict" in command
        assert "--no-deps" in command
        assert "pillow==13.0.0" in Path(command[-1]).read_text()
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(audit.subprocess, "run", run)
    assert audit.main() == 1
    assert "pillow==13.0.0" in output.read_text()


@pytest.mark.parametrize("make_status,audit_status", [(1, 0), (0, 1), (0, 0)])
def test_firmware_build_failure_cannot_audit_stale_target(tmp_path, make_status, audit_status):
    text = (ROOT / "buildroot/build.sh").read_text()
    function = text[text.index("build_image() {") : text.index("\n# --- 6. Report")]
    buildroot = tmp_path / "buildroot"
    (buildroot / "output/images").mkdir(parents=True)
    calls = tmp_path / "calls"
    calls.write_text("")
    script = tmp_path / "gate.sh"
    script.write_text(
        "#!/bin/sh\nset -eu\n"
        'die() { echo "$*" >&2; exit 1; }\n'
        "repository_commit() { echo test-source; }\n"
        'make() { case "$1" in -j*) return "$MAKE_STATUS";; *) return 0;; esac; }\n'
        'audit() { echo called >> "$CALLS"; return "$AUDIT_STATUS"; }\n'
        + function
        + "\nbuild_image\n"
    )
    env = {
        **os.environ,
        "BUILDROOT_DIR": str(buildroot),
        "EXTERNAL_DIR": str(ROOT / "buildroot/external"),
        "BUILD_MARKER": str(buildroot / "output/build.started"),
        "REPO_DIR": str(ROOT),
        "DEFCONFIG_NAME": "radio_rpi3_defconfig",
        "BR2_DL_DIR": str(tmp_path / "downloads"),
        "do_dirclean": "0",
        "do_clean": "0",
        "jobs": "1",
        "BUILDROOT_ACTUAL_COMMIT": "test-buildroot",
        "SHAIRPORT_SYNC_SRCDIR": str(tmp_path / "shairport"),
        "PYTHON_AUDIT_PYTHON": "audit",
        "CALLS": str(calls),
        "MAKE_STATUS": str(make_status),
        "AUDIT_STATUS": str(audit_status),
    }
    result = subprocess.run(["sh", str(script)], env=env, capture_output=True, text=True)
    assert result.returncode == (1 if make_status or audit_status else 0)
    assert len(calls.read_text().splitlines()) == (0 if make_status else 1)
