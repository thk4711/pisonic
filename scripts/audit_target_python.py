"""Audit the actual cross-built Python inventory without importing ARM modules.

Run on the build host, with pip-audit installed, before publishing firmware:
    python scripts/audit_target_python.py BUILDROOT/output/target
No target binary is executed. Missing metadata/pins fail closed.
"""

import argparse
import importlib.metadata
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED = {
    "pillow": "13.0.0",
    "requests": "2.34.2",
    "urllib3": "2.8.0",
    "certifi": "2026.10.23",
    "idna": "3.20",
    "pydantic": "2.13.3",
    "numpy": "2.4.6",
    "pyyaml": "6.0.3",
}


def inventory(target: Path) -> dict[str, str]:
    site = target / "usr/lib/python3.14/site-packages"
    if not site.is_dir():
        raise ValueError("Target must contain Python 3.14 site-packages")
    packages = {}
    for distribution in importlib.metadata.distributions(path=[str(site)]):
        name = distribution.metadata.get("Name", "")
        version = distribution.metadata.get("Version", "")
        if (
            not isinstance(version, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", version)
        ):
            raise ValueError("Invalid target distribution metadata")
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in packages:
            raise ValueError(f"Duplicate target distribution: {key}")
        packages[key] = version
    for name, expected in REQUIRED.items():
        if packages.get(name) != expected:
            raise ValueError(f"Target requires {name}=={expected}; found {packages.get(name)}")
    return dict(sorted(packages.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument(
        "--output", type=Path, help="Also save the audited inventory for release review"
    )
    args = parser.parse_args()
    try:
        packages = inventory(args.target)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Target Python audit: {exc}\n")
    content = "".join(f"{name}=={version}\n" for name, version in packages.items())
    print(content, end="", flush=True)
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="pisonic-python-audit-") as directory:
        requirements = Path(directory) / "requirements.txt"
        requirements.write_text(content, encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--strict",
                "--disable-pip",
                "--no-deps",
                "-r",
                str(requirements),
            ],
            check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
