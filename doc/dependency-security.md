# Appliance dependency security

PiSonic's application and host tests target **Python 3.14**, the interpreter
bundled in the pinned Buildroot image. Old interpreter compatibility is not a
release requirement. The separate ESP32 firmware uses its SDK-managed tools.

## Policy

- Use reviewed, tested versions and immutable sources with checked hashes.
- Audit direct **and transitive** dependencies for known vulnerabilities.
- Run CI on pushes, pull requests and weekly, since advisories change without
  source changes. Dependabot checks Python manifests and GitHub Actions weekly.
- Enable GitHub's automatic Dependabot security updates in repository settings.
- A clean audit means no known issue in the consulted database, not a guarantee
  of vulnerability-free software. Do not dismiss all alerts as unused code.
- Any exception requires a specific reachability assessment, a documented
  mitigation, owner and review date. The default gates contain no ignore list.

## Python sources and locks

`requirements.txt` selects application versions. `requirements-runtime.txt`
locks their complete PyPI dependency graph with hashes for Python 3.14.
`requirements-dev.in` selects only the host-compatible application packages plus
test/lint/audit tools; its hashed `requirements-dev.txt` is constrained by the
runtime lock. GPIO, ALSA and D-Bus are stubbed in host tests.

Regeneration and audit commands are in [development.md](development.md).
For a non-Buildroot install, use `pip install --require-hashes -r
requirements-runtime.txt` in a Python 3.14 virtualenv, plus the OS-provided
libraries documented in `requirements.txt`. Native ARMv7 packages may build
from source; wheel availability on a workstation is not target validation.

## Buildroot backports

The stock Buildroot checkout remains pinned and clean. The defconfig selects
`buildroot/external/board/radio/python-security.mk` via
`BR2_PACKAGE_OVERRIDE_FILE`, included **before** packages finalize their build
and download paths. Do not move version overrides into late `external.mk` or
use `OVERRIDE_SRCDIR`, which skips source hash checks and patches.

For idna, the license text changed, so its target/host hash-file list explicitly
uses the reviewed new archive/license hashes instead of also applying the
obsolete stock license checksum. Source hash checking remains mandatory.

The backports cover Pillow 13.0.0, Requests 2.34.2, urllib3 2.8.0,
certifi 2026.10.23, idna 3.20 and NumPy 2.4.6 (replacing yanked 2.4.0).
Versioned package directories under
`board/radio/patches/` provide verified archive/license hashes. Pillow includes
the upstream Buildroot cross-compilation patch from commit
`2b8e5fe2c7ace7b89d02d9d4203d716a1bf54ed8`; its AVIF option is corrected too.
Other Python packages remain defined by the pinned Buildroot recipes.

Use a **clean output rebuild** when first adopting these backports. An
incremental build can leave old metadata or packages behind; the target audit
rejects missing/stale required packages and duplicate distributions.

## Firmware security gate

Install `pip-audit==2.10.1` in a **Python 3.14** build-host virtualenv and set
`PYTHON_AUDIT_PYTHON` to that virtualenv's Python when running `buildroot/build.sh`.
This audit environment is not installed on the appliance. Network access to the
advisory service is required; failed/missing audit data blocks the gate.

On the build host, once Python 3.14 is installed:

```bash
python3.14 -m venv ~/pisonic-audit
~/pisonic-audit/bin/python -m pip install pip-audit==2.10.1
export PYTHON_AUDIT_PYTHON="$HOME/pisonic-audit/bin/python"
./buildroot/build.sh --clean
```

When using `scripts/build_image.py`, set INI key `python_audit_python` or pass
`--python-audit-python` to select that interpreter. In remote mode provide its
absolute path **on the remote build host**; the workstation environment is not
implicitly forwarded over SSH. Both local and remote `--fast` rebuilds repeat
the audit after their final compilation, before collecting firmware artifacts.

After compilation the build script calls:

```bash
python scripts/audit_target_python.py /absolute/buildroot/output/target \
  --output /absolute/buildroot/output/images/python-requirements.txt
```

It reads installed `.dist-info`/`.egg-info` metadata without executing ARM
binaries, checks the expected interpreter/package versions, then audits **every
discovered distribution**. The saved inventory is release-review evidence, not
a host dependency resolver or a firmware package installer.

Dependabot and this Python check do not cover the full image. Before publishing,
on the Linux build host also generate Buildroot's `show-info` inventory and run
`make pkg-stats`, then review the native library/kernel/toolchain/media-backend
CVE findings and the custom shairport-sync/go-librespot sources. These tools
require their own host prerequisites and vulnerability databases; they are not
equivalent to proof that every image component is secure.

## Application safeguards and validation

External logos/artwork only use PNG/JPEG decoders. Downloads are byte-bounded
while streaming; image dimensions are checked before pixel conversion and
decompression-bomb warnings/errors are rejected. These restrictions do not
replace Pillow security fixes: EXIF parsing and malformed supported formats can
still be vulnerable in older releases.

Before release:

1. Audit both Python locks and run lint, format, mypy and the complete host suite.
2. Build a fresh image; verify target inventory and native CVE review.
3. Inspect Pillow-related visual changes, not blindly rebaseline golden tests.
4. On the Pi test both display shapes, logos, Spotify/AirPlay/Bluetooth artwork,
   playback and the health-checked A/B trial/rollback process.
5. Publish new firmware. Merging dependency changes does not update installed
   devices or close alerts until GitHub rescans the default branch.