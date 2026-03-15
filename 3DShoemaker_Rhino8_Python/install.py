#!/usr/bin/env python3
"""
install.py - Feet in Focus Shoe Kit Plugin Installer for Rhino 8.

Detects the Rhino 8 installation on Windows or macOS, copies plugin files
to the correct PythonPlugIns directory, creates the plugin manifest, and
registers the plugin so it is loaded automatically when Rhino starts.

Usage:
    python install.py             Install the plugin
    python install.py --uninstall Remove the plugin
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLUGIN_NAME = "FIFShoeKit"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Feet in Focus Shoe Kit utility plug-in for Rhino 3D"
PLUGIN_URL = "https://ShoeLastMaker.com"

# Directories inside this repository that contain plugin source
_SCRIPT_DIR = Path(__file__).resolve().parent
_PLUGIN_SRC = _SCRIPT_DIR / "plugin"
_DEV_SRC = _SCRIPT_DIR / "dev" / PLUGIN_NAME
_MANIFEST_SRC = _SCRIPT_DIR / "manifest.yml"
_TERMS_SRC = _SCRIPT_DIR.parent / "8.4.0.8" / "Terms.txt"
_TERMS_FALLBACK = _SCRIPT_DIR / "Terms.txt"


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def _is_windows() -> bool:
    return platform.system() == "Windows"


def _is_mac() -> bool:
    return platform.system() == "Darwin"


def _get_rhino8_plugin_dir() -> Path | None:
    """Return the PythonPlugIns directory for Rhino 8.

    Windows: %APPDATA%\\McNeel\\Rhinoceros\\8.0\\Plug-ins\\PythonPlugIns\\
    macOS:   ~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/PythonPlugIns/
    """
    if _is_windows():
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        return (
            Path(appdata)
            / "McNeel" / "Rhinoceros" / "8.0"
            / "Plug-ins" / "PythonPlugIns"
        )
    elif _is_mac():
        home = Path.home()
        return (
            home
            / "Library" / "Application Support"
            / "McNeel" / "Rhinoceros" / "8.0"
            / "Plug-ins" / "PythonPlugIns"
        )
    else:
        # Linux or unsupported
        print(
            f"Warning: Unsupported platform '{platform.system()}'. "
            "Attempting Linux-compatible path."
        )
        home = Path.home()
        return (
            home / ".rhinoceros" / "8.0"
            / "Plug-ins" / "PythonPlugIns"
        )


def _get_plugin_dest() -> Path | None:
    """Return the destination directory for the Feet in Focus Shoe Kit plugin."""
    base = _get_rhino8_plugin_dir()
    if base is None:
        return None
    return base / PLUGIN_NAME


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

_MANIFEST_CONTENT = f"""\
---
name: {PLUGIN_NAME}
version: {PLUGIN_VERSION}
authors:
- 'Feet in Focus'
description: {PLUGIN_DESCRIPTION}
url: {PLUGIN_URL}
keywords: []
"""


def _write_manifest(dest_dir: Path) -> None:
    """Write the plugin manifest.yml into the destination directory."""
    manifest_path = dest_dir / "manifest.yml"
    manifest_path.write_text(_MANIFEST_CONTENT, encoding="utf-8")
    print(f"  Created {manifest_path}")


# ---------------------------------------------------------------------------
# Copy helpers
# ---------------------------------------------------------------------------

def _copy_tree(src: Path, dst: Path) -> int:
    """Recursively copy a directory tree.  Returns file count."""
    count = 0
    for item in src.rglob("*"):
        if item.is_file():
            # Skip __pycache__ and .pyc
            if "__pycache__" in item.parts:
                continue
            if item.suffix == ".pyc":
                continue

            rel = item.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            count += 1
    return count


def _copy_terms(dest_dir: Path) -> None:
    """Copy Terms.txt into the destination directory."""
    terms_src = _TERMS_SRC if _TERMS_SRC.is_file() else _TERMS_FALLBACK
    if terms_src.is_file():
        shutil.copy2(terms_src, dest_dir / "Terms.txt")
        print(f"  Copied Terms.txt")
    else:
        print("  Warning: Terms.txt not found; skipping.")


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def install() -> bool:
    """Install the Feet in Focus Shoe Kit plugin for Rhino 8.

    Returns True on success.
    """
    print(f"Feet in Focus Shoe Kit Plugin Installer v{PLUGIN_VERSION}")
    print("=" * 50)

    dest = _get_plugin_dest()
    if dest is None:
        print("Error: Could not determine Rhino 8 plugin directory.")
        return False

    rhino_plugins_dir = dest.parent
    print(f"Rhino 8 PythonPlugIns directory: {rhino_plugins_dir}")

    # Create the target directory
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Plugin directory: {dest}")

    # 1. Copy the dev entry point (__init__.py, __plugin__.py, *_cmd.py)
    if _DEV_SRC.is_dir():
        init_file = _DEV_SRC / "__init__.py"
        if init_file.is_file():
            shutil.copy2(init_file, dest / "__init__.py")
            print(f"  Copied plugin entry point (__init__.py)")
        else:
            print("  Warning: dev/FIFShoeKit/__init__.py not found.")

        plugin_file = _DEV_SRC / "__plugin__.py"
        if plugin_file.is_file():
            shutil.copy2(plugin_file, dest / "__plugin__.py")
            print(f"  Copied plugin identifier (__plugin__.py)")
        else:
            print("  Warning: dev/FIFShoeKit/__plugin__.py not found.")

        cmd_files = sorted(_DEV_SRC.glob("*_cmd.py"))
        for cmd_file in cmd_files:
            shutil.copy2(cmd_file, dest / cmd_file.name)
        print(f"  Copied {len(cmd_files)} command files (*_cmd.py)")
    else:
        print("  Warning: dev/FIFShoeKit/ directory not found.")

    # 2. Copy the plugin package
    if _PLUGIN_SRC.is_dir():
        plugin_dest = dest / "plugin"
        plugin_dest.mkdir(parents=True, exist_ok=True)
        count = _copy_tree(_PLUGIN_SRC, plugin_dest)
        print(f"  Copied {count} plugin source files to {plugin_dest}")
    else:
        print("  Error: plugin/ source directory not found.")
        return False

    # 3. Create manifest
    _write_manifest(dest)

    # 4. Copy Terms.txt
    _copy_terms(dest)

    # 5. Verify the installation
    expected_files = [
        dest / "__init__.py",
        dest / "__plugin__.py",
        dest / "manifest.yml",
        dest / "plugin" / "__init__.py",
    ]
    all_ok = True
    for ef in expected_files:
        if not ef.is_file():
            print(f"  Warning: Expected file missing: {ef}")
            all_ok = False

    if all_ok:
        print()
        print("=" * 50)
        print("Installation successful!")
        print()
        print("Please restart Rhino 8 to load the Feet in Focus Shoe Kit plugin.")
        print(
            "The plugin will appear in the Rhino command line as "
            "'Feet in Focus Shoe Kit' commands."
        )
        return True
    else:
        print()
        print("Installation completed with warnings. Check messages above.")
        return True


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

def uninstall() -> bool:
    """Remove the Feet in Focus Shoe Kit plugin from Rhino 8.

    Returns True on success.
    """
    print(f"Feet in Focus Shoe Kit Plugin Uninstaller v{PLUGIN_VERSION}")
    print("=" * 50)

    dest = _get_plugin_dest()
    if dest is None:
        print("Error: Could not determine Rhino 8 plugin directory.")
        return False

    if not dest.exists():
        print(f"Plugin directory not found: {dest}")
        print("Nothing to uninstall.")
        return True

    print(f"Removing: {dest}")

    try:
        shutil.rmtree(dest)
        print("Plugin files removed successfully.")
    except OSError as exc:
        print(f"Error removing plugin files: {exc}")
        print(
            "Please close Rhino and try again, or manually delete:\n"
            f"  {dest}"
        )
        return False

    print()
    print("=" * 50)
    print("Uninstallation complete.")
    print("Please restart Rhino 8 to complete the removal.")
    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Feet in Focus Shoe Kit Plugin Installer for Rhino 8",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the Feet in Focus Shoe Kit plugin instead of installing it.",
    )
    parser.add_argument(
        "--dest",
        type=str,
        default=None,
        help=(
            "Override the destination directory "
            "(default: auto-detect Rhino 8 PythonPlugIns path)."
        ),
    )
    args = parser.parse_args()

    # Allow overriding the destination for CI / testing
    if args.dest:
        global _get_plugin_dest

        custom_dest = Path(args.dest).resolve()

        def _get_plugin_dest() -> Path:  # type: ignore[misc]
            return custom_dest

    if args.uninstall:
        success = uninstall()
    else:
        success = install()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
