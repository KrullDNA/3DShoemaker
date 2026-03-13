"""
3DShoemaker Rhino 8 Plugin - License activation / deactivation commands.

Commands:
    Activate3DShoemaker   - Prompt for a license key, validate via the
                            Cryptolens network API, and activate the plugin.
    Deactivate3DShoemaker - Deactivate the current license and free the
                            machine slot on the licensing server.
"""

from __future__ import annotations

import json
import os
import typing
import urllib.request
import urllib.error
import urllib.parse

import Rhino  # type: ignore
import Rhino.Commands  # type: ignore
import Rhino.Input  # type: ignore
import Rhino.Input.Custom  # type: ignore
import Rhino.RhinoApp  # type: ignore

import plugin  # top-level package – constants live here


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_machine_id() -> str:
    """Return a stable machine identifier for license binding."""
    import hashlib
    import platform

    raw = platform.node() + platform.machine() + (os.environ.get("USERNAME", "")
                                                    or os.environ.get("USER", ""))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _license_file_path() -> str:
    """Return the path to the local license cache file."""
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(appdata, "3DShoemaker")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "license.json")


def _save_license(data: dict) -> None:
    with open(_license_file_path(), "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)


def _load_license() -> dict | None:
    path = _license_file_path()
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def _delete_license() -> None:
    path = _license_file_path()
    if os.path.isfile(path):
        os.remove(path)


def _activate_license_network(license_key: str) -> tuple[bool, str, dict]:
    """Call the Cryptolens Activate endpoint.

    Returns (success, message, response_dict).
    """
    params = urllib.parse.urlencode({
        "token": plugin.CRYPTOLENS_AUTH_TOKEN,
        "ProductId": plugin.CRYPTOLENS_PRODUCT_ID,
        "Key": license_key,
        "MachineCode": _get_machine_id(),
        "Sign": True,
    }).encode("utf-8")

    url = plugin.LICENSE_VALIDATE_URL
    try:
        req = urllib.request.Request(url, data=params, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        return False, f"Network error: {exc}", {}

    if body.get("result") == 0:
        # Successful activation
        license_info = body.get("licenseKey", {})
        return True, "License activated successfully.", license_info
    else:
        msg = body.get("message", "Activation failed (unknown reason).")
        return False, msg, {}


def _deactivate_license_network(license_key: str) -> tuple[bool, str]:
    """Call the Cryptolens Deactivate endpoint to free the machine slot.

    Returns (success, message).
    """
    deactivate_url = "https://api.cryptolens.io/api/key/Deactivate"
    params = urllib.parse.urlencode({
        "token": plugin.CRYPTOLENS_AUTH_TOKEN,
        "ProductId": plugin.CRYPTOLENS_PRODUCT_ID,
        "Key": license_key,
        "MachineCode": _get_machine_id(),
    }).encode("utf-8")

    try:
        req = urllib.request.Request(deactivate_url, data=params, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        return False, f"Network error: {exc}"

    if body.get("result") == 0:
        return True, "License deactivated successfully."
    else:
        return False, body.get("message", "Deactivation failed.")


# ---------------------------------------------------------------------------
#  Activate3DShoemaker
# ---------------------------------------------------------------------------

class Activate3DShoemaker(Rhino.Commands.Command):
    """Prompt for a license key, validate via the network, and activate."""

    _instance: Activate3DShoemaker | None = None

    def __init__(self):
        super().__init__()
        Activate3DShoemaker._instance = self

    # -- Singleton -----------------------------------------------------------
    @classmethod
    @property
    def Instance(cls) -> Activate3DShoemaker | None:
        return cls._instance

    # -- Command metadata ----------------------------------------------------
    @property
    def EnglishName(self) -> str:
        return "Activate3DShoemaker"

    # -- Execution -----------------------------------------------------------
    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        # Check if already activated
        existing = _load_license()
        if existing and existing.get("activated"):
            Rhino.RhinoApp.WriteLine("3DShoemaker is already activated.")
            gs = Rhino.Input.Custom.GetString()
            gs.SetCommandPrompt("Enter 'Y' to re-activate with a new key, or press Enter to cancel")
            gs.AcceptNothing(True)
            gs.Get()
            if gs.CommandResult() != Rhino.Commands.Result.Success:
                return Rhino.Commands.Result.Cancel
            answer = gs.StringResult().strip().upper() if gs.StringResult() else ""
            if answer != "Y":
                return Rhino.Commands.Result.Cancel

        # Prompt for the license key
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Enter your 3DShoemaker license key")
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        license_key = gs.StringResult().strip()
        if not license_key:
            Rhino.RhinoApp.WriteLine("No license key entered. Activation cancelled.")
            return Rhino.Commands.Result.Cancel

        # Validate format (basic check: non-empty, alphanumeric with dashes)
        cleaned = license_key.replace("-", "")
        if not cleaned.isalnum():
            Rhino.RhinoApp.WriteLine("Invalid license key format.")
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("Contacting license server...")

        success, message, info = _activate_license_network(license_key)

        if success:
            # Determine edition from feature flags
            features = info.get("f1", 0)
            if features & 4:
                edition = plugin.EDITION_ENTERPRISE
            elif features & 2:
                edition = plugin.EDITION_BUSINESS
            elif features & 1:
                edition = plugin.EDITION_PERSONAL
            else:
                edition = plugin.EDITION_UNKNOWN

            _save_license({
                "activated": True,
                "key": license_key,
                "machine_id": _get_machine_id(),
                "edition": edition,
                "expires": info.get("expires", ""),
            })
            Rhino.RhinoApp.WriteLine(f"3DShoemaker activated ({edition} edition). {message}")
            return Rhino.Commands.Result.Success
        else:
            Rhino.RhinoApp.WriteLine(f"Activation failed: {message}")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  Deactivate3DShoemaker
# ---------------------------------------------------------------------------

class Deactivate3DShoemaker(Rhino.Commands.Command):
    """Deactivate the current license and free the machine slot."""

    _instance: Deactivate3DShoemaker | None = None

    def __init__(self):
        super().__init__()
        Deactivate3DShoemaker._instance = self

    # -- Singleton -----------------------------------------------------------
    @classmethod
    @property
    def Instance(cls) -> Deactivate3DShoemaker | None:
        return cls._instance

    # -- Command metadata ----------------------------------------------------
    @property
    def EnglishName(self) -> str:
        return "Deactivate3DShoemaker"

    # -- Execution -----------------------------------------------------------
    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        existing = _load_license()
        if not existing or not existing.get("activated"):
            Rhino.RhinoApp.WriteLine("3DShoemaker is not currently activated.")
            return Rhino.Commands.Result.Nothing

        # Confirm deactivation
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Type 'YES' to confirm deactivation")
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        confirmation = (gs.StringResult() or "").strip().upper()
        if confirmation != "YES":
            Rhino.RhinoApp.WriteLine("Deactivation cancelled.")
            return Rhino.Commands.Result.Cancel

        license_key = existing.get("key", "")
        Rhino.RhinoApp.WriteLine("Contacting license server...")

        success, message = _deactivate_license_network(license_key)

        if success:
            _delete_license()
            Rhino.RhinoApp.WriteLine(f"3DShoemaker deactivated. {message}")
            return Rhino.Commands.Result.Success
        else:
            # Even on server failure, allow local deactivation so the user
            # is not permanently locked.
            Rhino.RhinoApp.WriteLine(
                f"Server deactivation failed ({message}). Removing local license anyway."
            )
            _delete_license()
            return Rhino.Commands.Result.Success
