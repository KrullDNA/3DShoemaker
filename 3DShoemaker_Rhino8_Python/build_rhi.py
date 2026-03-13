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

    Structure inside the ZIP (flat, matching Orthotic Toolkit format)::

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

    Rhino extracts these into a folder named after the plugin
    (PythonPlugIns/FIFShoeKit/) automatically during installation.
    """
    print(f"Building {output_path.name} ...")
    print(f"  Plugin: {PLUGIN_NAME} v{PLUGIN_VERSION}")
    print()

    file_count = 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Plugin entry point (flat, at root of ZIP)
        if not _DEV_INIT.is_file():
            print(f"  ERROR: Entry point not found: {_DEV_INIT}")
            sys.exit(1)
        arc_name = "__init__.py"
        zf.write(_DEV_INIT, arc_name)
        file_count += 1
        print(f"  + {arc_name}")

        # 2. Manifest
        if not _MANIFEST.is_file():
            print(f"  ERROR: manifest.yml not found: {_MANIFEST}")
            sys.exit(1)
        arc_name = "manifest.yml"
        zf.write(_MANIFEST, arc_name)
        file_count += 1
        print(f"  + {arc_name}")

        # 3. Terms.txt
        terms = _find_terms()
        if terms:
            arc_name = "Terms.txt"
            zf.write(terms, arc_name)
            file_count += 1
            print(f"  + {arc_name}")
        else:
            print("  Warning: Terms.txt not found, skipping.")

        # 4. README_INSTALL.txt
        if _README_INSTALL.is_file():
            arc_name = "README_INSTALL.txt"
            zf.write(_README_INSTALL, arc_name)
            file_count += 1
            print(f"  + {arc_name}")
        else:
            print("  Warning: README_INSTALL.txt not found, skipping.")

        # 5. QUICK_REFERENCE.txt
        if _QUICK_REFERENCE.is_file():
            arc_name = "QUICK_REFERENCE.txt"
            zf.write(_QUICK_REFERENCE, arc_name)
            file_count += 1
            print(f"  + {arc_name}")
        else:
            print("  Warning: QUICK_REFERENCE.txt not found, skipping.")

        # 6. FIFShoeKit.rui toolbar
        if _RUI_FILE.is_file():
            arc_name = "FIFShoeKit.rui"
            zf.write(_RUI_FILE, arc_name)
            file_count += 1
            print(f"  + {arc_name}")
        else:
            print("  Warning: FIFShoeKit.rui not found, skipping.")

        # 7. Entire plugin/ package
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
