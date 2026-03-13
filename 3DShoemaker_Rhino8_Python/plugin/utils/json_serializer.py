"""
json_serializer.py - JSON serialization utilities for Feet in Focus Shoe Kit.

Handles serialization and deserialization of domain objects (Last, Insert,
Bottom, Foot) as well as Rhino geometry types (Point3d, Plane, Guid,
Curves, Breps) that need to be persisted inside .3dm document user text
or exported to external JSON files.

Key concepts:

* ``WriteSimplePropertiesSorted`` -- deterministic JSON output with
  alphabetically sorted keys.
* ``ReadJsonApproach`` -- parse JSON produced by the current format.
* ``SimpleTypesOnlyContractResolver`` -- filter that only serializes
  primitive / simple-typed properties for compact storage.
* ``StoreGeometriesAsJsonStrings`` / ``GetGeometryFromStoredString`` --
  round-trip Rhino geometry through Base-64-encoded 3dm byte arrays
  wrapped in JSON strings.
"""

from __future__ import annotations

import base64
import json
import math
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set, Tuple, Type

import Rhino
import Rhino.FileIO
import Rhino.Geometry as rg
import System


# ---------------------------------------------------------------------------
# Simple-type filtering (equivalent to SimpleTypesOnlyContractResolver)
# ---------------------------------------------------------------------------

# Types that are considered "simple" and safe to round-trip in JSON
# without risk of circular references or unbounded expansion.
_SIMPLE_TYPES: Set[Type] = {
    bool, int, float, str, type(None),
}


def _is_simple_value(value: Any) -> bool:
    """Return True if *value* is a simple JSON-safe scalar."""
    return type(value) in _SIMPLE_TYPES


def _filter_simple(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *data* containing only simple-typed values.

    Lists of simple values are also retained.  Nested dicts are
    recursively filtered.
    """
    result: Dict[str, Any] = {}
    for key, value in data.items():
        if _is_simple_value(value):
            result[key] = value
        elif isinstance(value, (list, tuple)):
            if all(_is_simple_value(v) for v in value):
                result[key] = list(value)
        elif isinstance(value, dict):
            filtered = _filter_simple(value)
            if filtered:
                result[key] = filtered
    return result


class SimpleTypesOnlyContractResolver:
    """Callable filter that mirrors the .NET SimpleTypesOnlyContractResolver.

    Usage::

        resolver = SimpleTypesOnlyContractResolver()
        clean = resolver(some_dict)
    """

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return _filter_simple(data)


# ---------------------------------------------------------------------------
# Rhino geometry <-> JSON helpers
# ---------------------------------------------------------------------------

def _point3d_to_dict(pt: rg.Point3d) -> Dict[str, float]:
    return {"X": pt.X, "Y": pt.Y, "Z": pt.Z}


def _dict_to_point3d(d: Dict[str, Any]) -> rg.Point3d:
    return rg.Point3d(
        float(d.get("X", 0.0)),
        float(d.get("Y", 0.0)),
        float(d.get("Z", 0.0)),
    )


def _plane_to_dict(plane: rg.Plane) -> Dict[str, Any]:
    return {
        "Origin": _point3d_to_dict(plane.Origin),
        "XAxis": {
            "X": plane.XAxis.X, "Y": plane.XAxis.Y, "Z": plane.XAxis.Z,
        },
        "YAxis": {
            "X": plane.YAxis.X, "Y": plane.YAxis.Y, "Z": plane.YAxis.Z,
        },
        "ZAxis": {
            "X": plane.ZAxis.X, "Y": plane.ZAxis.Y, "Z": plane.ZAxis.Z,
        },
    }


def _dict_to_plane(d: Dict[str, Any]) -> rg.Plane:
    origin = _dict_to_point3d(d.get("Origin", {}))
    x_axis = rg.Vector3d(
        d.get("XAxis", {}).get("X", 1.0),
        d.get("XAxis", {}).get("Y", 0.0),
        d.get("XAxis", {}).get("Z", 0.0),
    )
    y_axis = rg.Vector3d(
        d.get("YAxis", {}).get("X", 0.0),
        d.get("YAxis", {}).get("Y", 1.0),
        d.get("YAxis", {}).get("Z", 0.0),
    )
    return rg.Plane(origin, x_axis, y_axis)


def _guid_to_str(guid: System.Guid) -> str:
    return str(guid)


def _str_to_guid(s: str) -> System.Guid:
    return System.Guid(s)


def _geometry_to_base64(geom: rg.GeometryBase) -> Optional[str]:
    """Serialize a Rhino GeometryBase to a Base-64 string.

    Uses Rhino's native 3dm byte-array serialization for full fidelity.
    """
    if geom is None:
        return None
    try:
        opts = Rhino.FileIO.SerializationOptions()
        byte_array = Rhino.Runtime.CommonObject.ToByteArray(geom, opts)
        return System.Convert.ToBase64String(byte_array)
    except Exception:
        return None


def _base64_to_geometry(b64: str) -> Optional[rg.GeometryBase]:
    """Deserialize a Base-64 string back into a Rhino GeometryBase."""
    if not b64:
        return None
    try:
        byte_array = System.Convert.FromBase64String(b64)
        obj = Rhino.Runtime.CommonObject.FromByteArray(byte_array)
        if isinstance(obj, rg.GeometryBase):
            return obj
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# JsonSerializer
# ---------------------------------------------------------------------------

class JsonSerializer:
    """JSON serialization utilities for Feet in Focus Shoe Kit domain objects.

    All methods are static -- no instance state is required.
    """

    # ======================================================================
    # Sorted-key output (WriteSimplePropertiesSorted equivalent)
    # ======================================================================

    @staticmethod
    def WriteSimplePropertiesSorted(data: Dict[str, Any]) -> str:
        """Serialize *data* to a JSON string with alphabetically sorted keys.

        Only simple-typed values (bool, int, float, str, None) and lists
        of simple values are included.  Complex nested objects are
        recursively filtered so the output is always flat and deterministic.

        Parameters
        ----------
        data : dict
            Arbitrary dictionary to serialize.

        Returns
        -------
        str
            JSON string with sorted keys.
        """
        resolver = SimpleTypesOnlyContractResolver()
        filtered = resolver(data)
        ordered = OrderedDict(sorted(filtered.items()))
        return json.dumps(ordered, indent=2)

    # ======================================================================
    # JSON reading (ReadJsonApproach equivalent)
    # ======================================================================

    @staticmethod
    def ReadJsonApproach(raw: str) -> Optional[Dict[str, Any]]:
        """Parse a JSON string into a dictionary.

        Returns None when *raw* is not valid JSON.

        Parameters
        ----------
        raw : str
            JSON text.

        Returns
        -------
        dict or None
        """
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return None

    # ======================================================================
    # Geometry ↔ JSON-string storage
    # ======================================================================

    @staticmethod
    def StoreGeometriesAsJsonStrings(
        geometries: Dict[str, rg.GeometryBase],
    ) -> Dict[str, str]:
        """Serialize a dictionary of named geometries to JSON-safe strings.

        Each geometry is converted to a Base-64-encoded 3dm byte array.

        Parameters
        ----------
        geometries : dict[str, GeometryBase]
            Mapping of name -> geometry.

        Returns
        -------
        dict[str, str]
            Mapping of name -> Base-64 string.  Entries where serialization
            failed are silently omitted.
        """
        result: Dict[str, str] = {}
        for name, geom in geometries.items():
            b64 = _geometry_to_base64(geom)
            if b64 is not None:
                result[name] = b64
        return result

    @staticmethod
    def GetGeometryFromStoredString(
        stored: str,
    ) -> Optional[rg.GeometryBase]:
        """Deserialize a single geometry from a Base-64 string.

        Parameters
        ----------
        stored : str
            Base-64-encoded 3dm byte array.

        Returns
        -------
        GeometryBase or None
        """
        return _base64_to_geometry(stored)

    @staticmethod
    def RestoreGeometriesFromJsonStrings(
        data: Dict[str, str],
    ) -> Dict[str, rg.GeometryBase]:
        """Restore a dictionary of named geometries from stored strings.

        Parameters
        ----------
        data : dict[str, str]
            Mapping of name -> Base-64 string.

        Returns
        -------
        dict[str, GeometryBase]
            Only successfully deserialized entries are included.
        """
        result: Dict[str, rg.GeometryBase] = {}
        for name, b64 in data.items():
            geom = _base64_to_geometry(b64)
            if geom is not None:
                result[name] = geom
        return result

    # ======================================================================
    # Domain object serialization
    # ======================================================================

    @staticmethod
    def serialize_last(last_obj: Any) -> Dict[str, Any]:
        """Serialize a Last domain object to a JSON-compatible dict.

        Handles Point3d, Plane, Guid, and curve properties.
        Curve geometry is stored as Base-64 strings.
        """
        return JsonSerializer._serialize_domain_object(last_obj, "Last")

    @staticmethod
    def deserialize_last(data: Dict[str, Any], cls: type) -> Any:
        """Deserialize a Last domain object from a dict."""
        return JsonSerializer._deserialize_domain_object(data, cls)

    @staticmethod
    def serialize_insert(insert_obj: Any) -> Dict[str, Any]:
        """Serialize an Insert domain object."""
        return JsonSerializer._serialize_domain_object(insert_obj, "Insert")

    @staticmethod
    def deserialize_insert(data: Dict[str, Any], cls: type) -> Any:
        """Deserialize an Insert domain object from a dict."""
        return JsonSerializer._deserialize_domain_object(data, cls)

    @staticmethod
    def serialize_bottom(bottom_obj: Any) -> Dict[str, Any]:
        """Serialize a Bottom domain object."""
        return JsonSerializer._serialize_domain_object(bottom_obj, "Bottom")

    @staticmethod
    def deserialize_bottom(data: Dict[str, Any], cls: type) -> Any:
        """Deserialize a Bottom domain object from a dict."""
        return JsonSerializer._deserialize_domain_object(data, cls)

    @staticmethod
    def serialize_foot(foot_obj: Any) -> Dict[str, Any]:
        """Serialize a Foot domain object."""
        return JsonSerializer._serialize_domain_object(foot_obj, "Foot")

    @staticmethod
    def deserialize_foot(data: Dict[str, Any], cls: type) -> Any:
        """Deserialize a Foot domain object from a dict."""
        return JsonSerializer._deserialize_domain_object(data, cls)

    # ======================================================================
    # Point3d / Plane / Guid convenience
    # ======================================================================

    @staticmethod
    def serialize_point3d(pt: rg.Point3d) -> Dict[str, float]:
        """Convert a Point3d to a JSON-safe dict."""
        return _point3d_to_dict(pt)

    @staticmethod
    def deserialize_point3d(d: Dict[str, Any]) -> rg.Point3d:
        """Restore a Point3d from a dict."""
        return _dict_to_point3d(d)

    @staticmethod
    def serialize_plane(plane: rg.Plane) -> Dict[str, Any]:
        """Convert a Plane to a JSON-safe dict."""
        return _plane_to_dict(plane)

    @staticmethod
    def deserialize_plane(d: Dict[str, Any]) -> rg.Plane:
        """Restore a Plane from a dict."""
        return _dict_to_plane(d)

    @staticmethod
    def serialize_guid(guid: System.Guid) -> str:
        """Convert a Guid to a string."""
        return _guid_to_str(guid)

    @staticmethod
    def deserialize_guid(s: str) -> System.Guid:
        """Restore a Guid from a string."""
        return _str_to_guid(s)

    @staticmethod
    def serialize_curve(curve: rg.Curve) -> Optional[str]:
        """Serialize a Curve to a Base-64 string."""
        return _geometry_to_base64(curve)

    @staticmethod
    def deserialize_curve(b64: str) -> Optional[rg.Curve]:
        """Deserialize a Curve from a Base-64 string."""
        geom = _base64_to_geometry(b64)
        if isinstance(geom, rg.Curve):
            return geom
        return None

    # ======================================================================
    # Internal generic domain-object serializer
    # ======================================================================

    @staticmethod
    def _serialize_domain_object(
        obj: Any, type_tag: str,
    ) -> Dict[str, Any]:
        """Generic serializer for domain objects with mixed property types.

        Introspects the object's ``__dict__`` and serializes each
        attribute according to its runtime type.
        """
        data: Dict[str, Any] = {"_type": type_tag}

        if obj is None:
            return data

        # If the object provides its own to_dict, prefer that
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            base = obj.to_dict()
            base["_type"] = type_tag
            # Post-process geometry values
            for key, val in list(base.items()):
                base[key] = JsonSerializer._serialize_value(val)
            return base

        # Fall back to __dict__ introspection
        for key, val in sorted(vars(obj).items()):
            if key.startswith("_"):
                continue
            data[key] = JsonSerializer._serialize_value(val)

        return data

    @staticmethod
    def _serialize_value(val: Any) -> Any:
        """Convert a single value to a JSON-safe representation."""
        if val is None or isinstance(val, (bool, int, float, str)):
            return val

        # Rhino Point3d
        if isinstance(val, rg.Point3d):
            return _point3d_to_dict(val)

        # Rhino Plane
        if isinstance(val, rg.Plane):
            return _plane_to_dict(val)

        # System.Guid
        if isinstance(val, System.Guid):
            return _guid_to_str(val)

        # Rhino geometry (Curve, Brep, Mesh, etc.)
        if isinstance(val, rg.GeometryBase):
            b64 = _geometry_to_base64(val)
            return {"_geom_b64": b64} if b64 else None

        # Lists
        if isinstance(val, (list, tuple)):
            return [JsonSerializer._serialize_value(v) for v in val]

        # Dicts
        if isinstance(val, dict):
            return {
                k: JsonSerializer._serialize_value(v)
                for k, v in val.items()
            }

        # Fallback -- try str()
        try:
            return str(val)
        except Exception:
            return None

    @staticmethod
    def _deserialize_domain_object(
        data: Dict[str, Any], cls: type,
    ) -> Any:
        """Generic deserializer that creates an instance of *cls* and
        populates its attributes from *data*.

        *cls* should accept keyword arguments or be populated via
        ``setattr`` after a no-argument construction.
        """
        if data is None:
            return None

        # Attempt keyword construction first
        try:
            filtered = {
                k: v for k, v in data.items() if not k.startswith("_")
            }
            # Restore special types
            for key, val in list(filtered.items()):
                filtered[key] = JsonSerializer._deserialize_value(val)
            return cls(**filtered)
        except TypeError:
            pass

        # Fall back to no-arg construction + setattr
        try:
            obj = cls()
            for key, val in data.items():
                if key.startswith("_"):
                    continue
                setattr(obj, key, JsonSerializer._deserialize_value(val))
            return obj
        except Exception:
            return None

    @staticmethod
    def _deserialize_value(val: Any) -> Any:
        """Restore a value from its JSON representation."""
        if val is None or isinstance(val, (bool, int, float, str)):
            return val

        if isinstance(val, dict):
            # Check for geometry blob
            if "_geom_b64" in val:
                return _base64_to_geometry(val["_geom_b64"])

            # Check for Point3d-like dict
            if set(val.keys()) == {"X", "Y", "Z"}:
                try:
                    return _dict_to_point3d(val)
                except Exception:
                    pass

            # Check for Plane-like dict
            if "Origin" in val and "XAxis" in val:
                try:
                    return _dict_to_plane(val)
                except Exception:
                    pass

            # Generic nested dict
            return {
                k: JsonSerializer._deserialize_value(v)
                for k, v in val.items()
            }

        if isinstance(val, list):
            return [JsonSerializer._deserialize_value(v) for v in val]

        return val
