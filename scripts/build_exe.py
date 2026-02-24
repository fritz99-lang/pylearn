# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Build a standalone PyLearn executable using PyInstaller.

Usage:
    python scripts/build_exe.py

Output (per platform):
    Windows: dist/PyLearn/PyLearn.exe
    macOS:   dist/PyLearn.app
    Linux:   dist/PyLearn/PyLearn
"""

import subprocess
import sys
from pathlib import Path

PLATFORM = sys.platform


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    spec_file = project_root / "pylearn.spec"

    if not spec_file.exists():
        print(f"ERROR: spec file not found: {spec_file}")
        return 1

    # Check PyInstaller is installed
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller is not installed.")
        print("  Install it with: pip install pyinstaller")
        return 1

    # On macOS, auto-generate .icns if missing
    if PLATFORM == "darwin":
        icns_path = project_root / "assets" / "pylearn.icns"
        if not icns_path.exists():
            print("macOS detected — generating .icns icon ...")
            gen_script = project_root / "scripts" / "generate_icns.py"
            rc = subprocess.run(
                [sys.executable, str(gen_script)],
                cwd=str(project_root),
            ).returncode
            if rc != 0:
                print("WARNING: .icns generation failed; building without icon")

    print(f"Building PyLearn from {spec_file} ...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_file)],
        cwd=str(project_root),
    )

    if result.returncode != 0:
        print("BUILD FAILED")
        return result.returncode

    # Platform-specific output summary
    print()
    print("BUILD SUCCEEDED")

    if PLATFORM == "win32":
        output_path = project_root / "dist" / "PyLearn" / "PyLearn.exe"
        output_dir = project_root / "dist" / "PyLearn"
    elif PLATFORM == "darwin":
        output_path = project_root / "dist" / "PyLearn.app"
        output_dir = project_root / "dist"
    else:
        output_path = project_root / "dist" / "PyLearn" / "PyLearn"
        output_dir = project_root / "dist" / "PyLearn"

    print(f"  Output directory: {output_dir}")
    if output_path.exists():
        if output_path.is_file():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  Executable: {output_path} ({size_mb:.1f} MB)")
        else:
            # macOS .app is a directory
            print(f"  Application bundle: {output_path}")
    else:
        print(f"  (output not found at {output_path} — check dist/ for output)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
