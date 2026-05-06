"""One-shot release build.

Usage:
    python build_release.py

What it does:
  1. Verifies PyInstaller is importable.
  2. Cleans any previous `build/` and `dist/`.
  3. Runs `pyinstaller CalendarTaskAI.spec --clean`.
  4. Sanity-checks that `dist/CalendarTaskAI/CalendarTaskAI.exe` exists.
  5. Packages the bundle as `dist/CalendarTaskAI-v<VER>.zip` for upload.
  6. Prints a summary including the zip path and uncompressed size.

The same script runs locally and inside GitHub Actions (`release.yml`).
The CI workflow uploads the produced zip as a release artifact.

Exit codes:
  0  success
  1  PyInstaller not installed
  2  pyinstaller subprocess failed
  3  expected exe missing after build
  4  pytest failed; build aborted
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SPEC = PROJECT_ROOT / "CalendarTaskAI.spec"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
BUNDLE = DIST_DIR / "CalendarTaskAI"


def _read_version() -> str:
    """Read APP_VERSION from constants.py without importing the module
    (importing would pull in heavy deps like google-genai which we may
    not have at build time on a clean CI runner).
    """
    text = (PROJECT_ROOT / "constants.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("APP_VERSION"):
            # APP_VERSION = "1.0.0"
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Could not find APP_VERSION in constants.py")


def _step(msg: str) -> None:
    print(f"\n>>> {msg}", flush=True)


def main() -> int:
    version = _read_version()
    _step(f"Building CalendarTaskAI v{version}")

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller is not installed.", file=sys.stderr)
        print("Install with: pip install -r requirements-dev.txt", file=sys.stderr)
        return 1

    # Test gate: never package a release if the test suite is red. This
    # also makes the README's "build runs pytest first" claim true and
    # mirrors the CI behavior so local builds and tag-triggered CI builds
    # both fail in the same way.
    _step("Running tests")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        print(f"ERROR: tests failed (exit {result.returncode}); aborting build",
              file=sys.stderr)
        return 4

    _step("Cleaning previous build/ and dist/")
    for path in (BUILD_DIR, DIST_DIR):
        if path.exists():
            shutil.rmtree(path)

    _step("Running PyInstaller")
    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC), "--clean", "--noconfirm"]
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"ERROR: pyinstaller exited {result.returncode}", file=sys.stderr)
        return 2

    expected_exe = BUNDLE / "CalendarTaskAI.exe"
    if not expected_exe.is_file():
        print(f"ERROR: expected exe not found at {expected_exe}", file=sys.stderr)
        return 3

    _step("Packaging zip")
    archive_base = DIST_DIR / f"CalendarTaskAI-v{version}"
    # `make_archive` returns the path it actually wrote (with .zip suffix).
    archive_path = Path(shutil.make_archive(
        base_name=str(archive_base),
        format="zip",
        root_dir=str(DIST_DIR),
        base_dir="CalendarTaskAI",
    ))

    _step("Build complete")
    print(f"  exe   : {expected_exe}")
    print(f"  zip   : {archive_path}")
    print(f"  size  : {_human_size(archive_path.stat().st_size)} (zip)")
    print(f"  bundle: {_human_size(_dir_size(BUNDLE))} (uncompressed)")
    print()
    print("Next steps:")
    print(f"  - Test:    {expected_exe}")
    print(f"  - Tag:     git tag v{version} && git push --tags")
    print(f"  - Release: gh release create v{version} {archive_path}")

    return 0


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


if __name__ == "__main__":
    sys.exit(main())
