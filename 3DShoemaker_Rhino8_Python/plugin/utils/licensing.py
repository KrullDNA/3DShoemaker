"""
licensing.py - License management for Feet in Focus Shoe Kit.

Provides the ``LicenseManager`` class that handles license key validation,
machine-based activation/deactivation, and edition detection.  Designed to
be Cryptolens-compatible using the REST API over HTTPS.

Supports three edition tiers (Personal, Business, Enterprise) and stores
license state in a local JSON cache so the plugin can operate during
temporary network outages.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

import urllib.error
import urllib.parse
import urllib.request


# ---------------------------------------------------------------------------
# Edition enum
# ---------------------------------------------------------------------------

class Edition(Enum):
    """License edition tiers."""
    Personal = "Personal"
    Business = "Business"
    Enterprise = "Enterprise"
    Unknown = "Unknown"


# ---------------------------------------------------------------------------
# Cryptolens-compatible model classes
# ---------------------------------------------------------------------------

class KeyLockModel:
    """Represents a locked machine entry for a license key.

    Mirrors the Cryptolens ``ActivatedMachines`` object.
    """

    def __init__(
        self,
        mid: str = "",
        friendly_name: str = "",
        ip: str = "",
        time: str = "",
    ) -> None:
        self.mid = mid
        self.friendly_name = friendly_name
        self.ip = ip
        self.time = time

    def to_dict(self) -> Dict[str, str]:
        return {
            "Mid": self.mid,
            "FriendlyName": self.friendly_name,
            "IP": self.ip,
            "Time": self.time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyLockModel":
        return cls(
            mid=data.get("Mid", ""),
            friendly_name=data.get("FriendlyName", ""),
            ip=data.get("IP", ""),
            time=data.get("Time", ""),
        )


class ListDataObjectsToKeyModel:
    """Represents a data object attached to a license key.

    Used for feature flags, metadata, and per-key configuration stored
    on the Cryptolens server.
    """

    def __init__(
        self,
        id: int = 0,
        name: str = "",
        string_value: str = "",
        int_value: int = 0,
    ) -> None:
        self.id = id
        self.name = name
        self.string_value = string_value
        self.int_value = int_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Id": self.id,
            "Name": self.name,
            "StringValue": self.string_value,
            "IntValue": self.int_value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListDataObjectsToKeyModel":
        return cls(
            id=data.get("Id", 0),
            name=data.get("Name", ""),
            string_value=data.get("StringValue", ""),
            int_value=data.get("IntValue", 0),
        )


# ---------------------------------------------------------------------------
# LicenseManager
# ---------------------------------------------------------------------------

class LicenseManager:
    """Manages license validation, activation, and machine binding.

    Typical usage::

        mgr = LicenseManager(
            auth_token="WyI...",
            product_id=12345,
            rsa_pub_key="<RSA>...</RSA>",
        )
        ok, msg = mgr.activate_license("XXXXX-XXXXX-XXXXX-XXXXX",
                                        mgr.get_machine_code())
        if ok:
            print(f"Edition: {mgr.edition.value}")

    Parameters
    ----------
    auth_token : str
        Cryptolens access token with Activate / Deactivate permission.
    product_id : int
        Cryptolens Product ID.
    rsa_pub_key : str
        RSA public key for signature verification (optional in Python
        builds -- signature check is performed server-side).
    activate_url : str
        Base URL for the Activate endpoint.
    deactivate_url : str
        Base URL for the Deactivate endpoint.
    """

    # Default Cryptolens API endpoints
    DEFAULT_ACTIVATE_URL = "https://api.cryptolens.io/api/key/Activate"
    DEFAULT_DEACTIVATE_URL = "https://api.cryptolens.io/api/key/Deactivate"
    DEFAULT_DATA_OBJECTS_URL = (
        "https://api.cryptolens.io/api/data/ListDataObjectsToKey"
    )

    def __init__(
        self,
        auth_token: str = "",
        product_id: int = 0,
        rsa_pub_key: str = "",
        activate_url: str = "",
        deactivate_url: str = "",
    ) -> None:
        self.auth_token = auth_token
        self.product_id = product_id
        self.rsa_pub_key = rsa_pub_key
        self.activate_url = activate_url or self.DEFAULT_ACTIVATE_URL
        self.deactivate_url = deactivate_url or self.DEFAULT_DEACTIVATE_URL

        # State
        self._activated: bool = False
        self._license_key: str = ""
        self._edition: Edition = Edition.Unknown
        self._expires: Optional[str] = None
        self._customer: str = ""
        self._machine_code: str = ""
        self._activated_machines: List[KeyLockModel] = []
        self._data_objects: List[ListDataObjectsToKeyModel] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def edition(self) -> Edition:
        """Currently detected edition."""
        return self._edition

    @property
    def license_key(self) -> str:
        return self._license_key

    @property
    def expires(self) -> Optional[str]:
        return self._expires

    @property
    def customer(self) -> str:
        return self._customer

    @property
    def activated_machines(self) -> List[KeyLockModel]:
        return list(self._activated_machines)

    @property
    def data_objects(self) -> List[ListDataObjectsToKeyModel]:
        return list(self._data_objects)

    # ------------------------------------------------------------------
    # Machine identification
    # ------------------------------------------------------------------

    @staticmethod
    def get_machine_code() -> str:
        """Return a unique, stable machine identifier.

        Combines the hostname, MAC address, platform, and user name into
        a SHA-256 hash that is reproducible across reboots.
        """
        try:
            mac = uuid.getnode()
            raw = (
                f"{platform.node()}|"
                f"{mac:012x}|"
                f"{platform.machine()}|"
                f"{os.environ.get('USERNAME', os.environ.get('USER', ''))}"
            )
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
        except Exception:
            # Absolute fallback -- still deterministic per-session
            return hashlib.sha256(
                platform.node().encode("utf-8")
            ).hexdigest()[:32]

    # ------------------------------------------------------------------
    # Activation state
    # ------------------------------------------------------------------

    def is_activated(self) -> bool:
        """Return True if a valid license is currently activated."""
        return self._activated

    # ------------------------------------------------------------------
    # Online validation
    # ------------------------------------------------------------------

    def validate_license_key(self, key: str) -> tuple[bool, str]:
        """Validate a license key against the Cryptolens API.

        This does *not* bind the key to a machine -- use
        ``activate_license`` for that.

        Parameters
        ----------
        key : str
            The license key string (e.g. ``XXXXX-XXXXX-XXXXX-XXXXX``).

        Returns
        -------
        (bool, str)
            ``(True, message)`` on success, ``(False, error_message)`` on
            failure.
        """
        if not key:
            return False, "Empty license key."

        if not self.auth_token:
            # Dev / offline mode -- try cached license
            cached = self._load_cache()
            if cached and cached.get("key") == key:
                self._apply_from_cache(cached)
                return True, "License accepted (offline/dev mode)."
            return False, "Auth token not configured and no cached license."

        params = urllib.parse.urlencode({
            "token": self.auth_token,
            "ProductId": self.product_id,
            "Key": key,
            "Sign": True,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                self.activate_url, data=params, method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body: Dict[str, Any] = json.loads(
                    resp.read().decode("utf-8")
                )
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
            return False, f"Network error: {exc}"

        if body.get("result") == 0:
            lk = body.get("licenseKey", {})
            self._parse_license_key(key, lk)
            return True, "License key is valid."
        else:
            return False, body.get("message", "Validation failed.")

    # ------------------------------------------------------------------
    # Activation / deactivation
    # ------------------------------------------------------------------

    def activate_license(
        self, key: str, machine_code: str,
    ) -> tuple[bool, str]:
        """Activate a license key on the specified machine.

        Parameters
        ----------
        key : str
            License key string.
        machine_code : str
            Machine identifier (from ``get_machine_code()``).

        Returns
        -------
        (bool, str)
        """
        if not key:
            return False, "Empty license key."

        if not self.auth_token:
            cached = self._load_cache()
            if cached and cached.get("key") == key:
                self._apply_from_cache(cached)
                return True, "Activated (offline/dev mode)."
            return False, "Auth token not configured."

        params = urllib.parse.urlencode({
            "token": self.auth_token,
            "ProductId": self.product_id,
            "Key": key,
            "MachineCode": machine_code,
            "Sign": True,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                self.activate_url, data=params, method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body: Dict[str, Any] = json.loads(
                    resp.read().decode("utf-8")
                )
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
            return False, f"Network error: {exc}"

        if body.get("result") == 0:
            lk = body.get("licenseKey", {})
            self._parse_license_key(key, lk)
            self._machine_code = machine_code
            self._activated = True
            self._save_cache(key, machine_code)
            return True, f"Activated ({self._edition.value} edition)."
        else:
            return False, body.get("message", "Activation failed.")

    def deactivate_license(
        self, key: str, machine_code: str,
    ) -> tuple[bool, str]:
        """Deactivate a license key and free the machine slot.

        Parameters
        ----------
        key : str
            License key string.
        machine_code : str
            Machine identifier.

        Returns
        -------
        (bool, str)
        """
        if not key:
            return False, "Empty license key."

        if not self.auth_token:
            self._clear_state()
            self._delete_cache()
            return True, "Deactivated (offline/dev mode)."

        params = urllib.parse.urlencode({
            "token": self.auth_token,
            "ProductId": self.product_id,
            "Key": key,
            "MachineCode": machine_code,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                self.deactivate_url, data=params, method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body: Dict[str, Any] = json.loads(
                    resp.read().decode("utf-8")
                )
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
            # Allow local deactivation even on network failure
            self._clear_state()
            self._delete_cache()
            return True, f"Local deactivation done. Server error: {exc}"

        if body.get("result") == 0:
            self._clear_state()
            self._delete_cache()
            return True, "License deactivated successfully."
        else:
            msg = body.get("message", "Deactivation failed.")
            # Still deactivate locally so the user is not stuck
            self._clear_state()
            self._delete_cache()
            return True, f"Local deactivation done. Server: {msg}"

    # ------------------------------------------------------------------
    # Data objects
    # ------------------------------------------------------------------

    def list_data_objects(
        self, key: str,
    ) -> tuple[bool, List[ListDataObjectsToKeyModel]]:
        """Fetch data objects attached to a license key.

        Returns
        -------
        (bool, list[ListDataObjectsToKeyModel])
        """
        if not self.auth_token or not key:
            return False, []

        params = urllib.parse.urlencode({
            "token": self.auth_token,
            "ProductId": self.product_id,
            "Key": key,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                self.DEFAULT_DATA_OBJECTS_URL, data=params, method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body: Dict[str, Any] = json.loads(
                    resp.read().decode("utf-8")
                )
        except (urllib.error.URLError, json.JSONDecodeError, OSError):
            return False, []

        if body.get("result") == 0:
            objects_raw = body.get("dataObjects", [])
            objects = [
                ListDataObjectsToKeyModel.from_dict(o) for o in objects_raw
            ]
            self._data_objects = objects
            return True, objects
        return False, []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_license_key(
        self, key: str, lk: Dict[str, Any],
    ) -> None:
        """Extract edition, expiry, customer, and machines from the
        Cryptolens ``licenseKey`` response object."""
        self._license_key = key

        # Edition detection from feature flags
        if lk.get("f3", False):
            self._edition = Edition.Enterprise
        elif lk.get("f2", False):
            self._edition = Edition.Business
        elif lk.get("f1", False):
            self._edition = Edition.Personal
        else:
            self._edition = Edition.Unknown

        self._expires = lk.get("expires")
        customer_obj = lk.get("customer")
        if isinstance(customer_obj, dict):
            self._customer = customer_obj.get("name", "")
        elif isinstance(customer_obj, str):
            self._customer = customer_obj
        else:
            self._customer = ""

        # Parse activated machines
        self._activated_machines = []
        for m in lk.get("activatedMachines", []):
            self._activated_machines.append(KeyLockModel.from_dict(m))

        # Parse data objects if included
        self._data_objects = []
        for do in lk.get("dataObjects", []):
            self._data_objects.append(
                ListDataObjectsToKeyModel.from_dict(do)
            )

    def _clear_state(self) -> None:
        """Reset all license state to defaults."""
        self._activated = False
        self._license_key = ""
        self._edition = Edition.Unknown
        self._expires = None
        self._customer = ""
        self._machine_code = ""
        self._activated_machines = []
        self._data_objects = []

    # ------------------------------------------------------------------
    # Cache persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_path() -> str:
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(appdata, "Feet in Focus Shoe Kit")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "license.json")

    def _save_cache(self, key: str, machine_code: str) -> None:
        """Persist license info to a local JSON file."""
        data = {
            "activated": True,
            "key": key,
            "machine_code": machine_code,
            "edition": self._edition.value,
            "expires": self._expires,
            "customer": self._customer,
        }
        try:
            with open(self._cache_path(), "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except OSError:
            pass

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """Read cached license data from disk."""
        path = self._cache_path()
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None

    def _delete_cache(self) -> None:
        """Remove the local license cache file."""
        path = self._cache_path()
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def _apply_from_cache(self, data: Dict[str, Any]) -> None:
        """Restore license state from cached data."""
        self._license_key = data.get("key", "")
        self._machine_code = data.get("machine_code", "")
        edition_str = data.get("edition", "Unknown")
        try:
            self._edition = Edition(edition_str)
        except ValueError:
            self._edition = Edition.Unknown
        self._expires = data.get("expires")
        self._customer = data.get("customer", "")
        self._activated = data.get("activated", False)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "activated" if self._activated else "not activated"
        return (
            f"<LicenseManager {status}, "
            f"edition={self._edition.value}, "
            f"key={'***' if self._license_key else '(none)'}>"
        )
