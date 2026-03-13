#!/usr/bin/env python3
"""
build_rhi.py - Build a .rhi installer package for the Feet in Focus Shoe Kit Rhino 8 plugin.

A .rhi file is a ZIP archive that Rhino's package manager can install by
double-clicking.  This script packages all required plugin files into the
correct directory structure so that Rhino 8 installs them into the
PythonPlugIns directory automatically.

Usage:
    python build_rhi.py                  Build the .rhi file
    python build_rhi.py --output NAME    Specify output filename
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLUGIN_NAME = "FIFShoeKit"
PLUGIN_VERSION = "1.0"

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEV_INIT = _SCRIPT_DIR / "dev" / PLUGIN_NAME / "__init__.py"
_PLUGIN_PY = _SCRIPT_DIR / "__plugin__.py"
_PLUGIN_DIR = _SCRIPT_DIR / "plugin"
_MANIFEST = _SCRIPT_DIR / "manifest.yml"
_TERMS_PRIMARY = _SCRIPT_DIR.parent / "8.4.0.8" / "Terms.txt"
_TERMS_FALLBACK = _SCRIPT_DIR / "Terms.txt"
_README_INSTALL = _SCRIPT_DIR / "README_INSTALL.txt"
_QUICK_REFERENCE = _SCRIPT_DIR / "QUICK_REFERENCE.txt"
_RUI_FILE = _SCRIPT_DIR / "FIFShoeKit.rui"

# Files/dirs to exclude from the package
_SKIP_DIRS = {"__pycache__", ".git", ".vscode", ".idea"}
_SKIP_EXTENSIONS = {".pyc", ".pyo"}


def _find_terms() -> Path | None:
    """Locate Terms.txt."""
    for p in (_TERMS_PRIMARY, _TERMS_FALLBACK):
        if p.is_file():
            return p
    return None


def _should_skip(path: Path) -> bool:
    """Return True if the file should be excluded from the package."""
    parts = path.parts
    for skip in _SKIP_DIRS:
        if skip in parts:
            return True
    if path.suffix in _SKIP_EXTENSIONS:
        return True
    return False


def build_rhi(output_path: Path) -> None:
    """Build the .rhi package.

    Structure inside the ZIP (flat -- matching Orthotic Toolkit format
    so that Rhino's installer engine recognises it as a Python plugin)::

        __plugin__.py        (plugin metadata: id, version, title)
        __init__.py          (plugin entry point)
        manifest.yml
        Terms.txt
        README_INSTALL.txt
        QUICK_REFERENCE.txt
        FIFShoeKit.rui
        plugin/
            __init__.py
            plugin_main.py
            commands/
                ...
            forms/
                ...
            models/
                ...
            utils/
                ...
    """
    print(f"Building {output_path.name} ...")
    print(f"  Plugin: {PLUGIN_NAME} v{PLUGIN_VERSION}")
    print()

    file_count = 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. __plugin__.py -- required for Rhino to detect Python plugin
        if not _PLUGIN_PY.is_file():
            print(f"  ERROR: __plugin__.py not found: {_PLUGIN_PY}")
            sys.exit(1)
        zf.write(_PLUGIN_PY, "__plugin__.py")
        file_count += 1
        print("  + __plugin__.py")

        # 2. Plugin entry point
        if not _DEV_INIT.is_file():
            print(f"  ERROR: Entry point not found: {_DEV_INIT}")
            sys.exit(1)
        zf.write(_DEV_INIT, "__init__.py")
        file_count += 1
        print("  + __init__.py")

        # 3. Manifest
        if not _MANIFEST.is_file():
            print(f"  ERROR: manifest.yml not found: {_MANIFEST}")
            sys.exit(1)
        zf.write(_MANIFEST, "manifest.yml")
        file_count += 1
        print("  + manifest.yml")

        # 4. Terms.txt
        terms = _find_terms()
        if terms:
            zf.write(terms, "Terms.txt")
            file_count += 1
            print("  + Terms.txt")
        else:
            print("  Warning: Terms.txt not found, skipping.")

        # 5. README_INSTALL.txt
        if _README_INSTALL.is_file():
            zf.write(_README_INSTALL, "README_INSTALL.txt")
            file_count += 1
            print("  + README_INSTALL.txt")
        else:
            print("  Warning: README_INSTALL.txt not found, skipping.")

        # 6. QUICK_REFERENCE.txt
        if _QUICK_REFERENCE.is_file():
            zf.write(_QUICK_REFERENCE, "QUICK_REFERENCE.txt")
            file_count += 1
            print("  + QUICK_REFERENCE.txt")
        else:
            print("  Warning: QUICK_REFERENCE.txt not found, skipping.")

        # 7. FIFShoeKit.rui toolbar
        if _RUI_FILE.is_file():
            zf.write(_RUI_FILE, "FIFShoeKit.rui")
            file_count += 1
            print("  + FIFShoeKit.rui")
        else:
            print("  Warning: FIFShoeKit.rui not found, skipping.")

        # 8. Entire plugin/ package
        if not _PLUGIN_DIR.is_dir():
            print(f"  ERROR: plugin/ directory not found: {_PLUGIN_DIR}")
            sys.exit(1)

        for filepath in sorted(_PLUGIN_DIR.rglob("*")):
            if not filepath.is_file():
                continue
            if _should_skip(filepath):
                continue

            rel = filepath.relative_to(_PLUGIN_DIR)
            arc_name = f"plugin/{rel}"
            zf.write(filepath, arc_name)
            file_count += 1
            print(f"  + {arc_name}")

    size_kb = output_path.stat().st_size / 1024
    print()
    print("=" * 55)
    print(f"  Created: {output_path}")
    print(f"  Files:   {file_count}")
    print(f"  Size:    {size_kb:.1f} KB")
    print("=" * 55)
    print()
    print("To install: double-click the .rhi file with Rhino 8")
    print("installed, or drag it onto the Rhino window.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a .rhi installer for Feet in Focus Shoe Kit Rhino 8 plugin",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output filename (default: Feet in Focus Shoe Kit_<version>.rhi)",
    )
    args = parser.parse_args()

    if args.output:
        out = Path(args.output).resolve()
    else:
        out = _SCRIPT_DIR / f"{PLUGIN_NAME}_{PLUGIN_VERSION}.rhi"

    build_rhi(out)


if __name__ == "__main__":
    main()
