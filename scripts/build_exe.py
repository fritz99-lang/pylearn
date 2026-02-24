# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Build a standalone PyLearn .exe using PyInstaller.

Usage:
    python scripts/build_exe.py

Output:
    dist/PyLearn/PyLearn.exe
"""

import subprocess
import sys
from pathlib import Path


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

    print(f"Building PyLearn from {spec_file} ...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_file)],
        cwd=str(project_root),
    )

    if result.returncode != 0:
        print("BUILD FAILED")
        return result.returncode

    output_dir = project_root / "dist" / "PyLearn"
    exe_path = output_dir / "PyLearn.exe"

    print()
    print("BUILD SUCCEEDED")
    print(f"  Output directory: {output_dir}")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"  Executable: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"  (exe not found at {exe_path} — check dist/ for output)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
