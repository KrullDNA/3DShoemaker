"""
last.py - Last data model for 3DShoemaker.

Represents a shoe last with all measurement parameters, curve IDs,
cross-section data, body geometry, and style parameters.  Uses a
dict-based property system to keep the large number of attributes
manageable while remaining fully serialisable via JSON.
"""

from __future__ import annotations

import copy
import json
import math
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import Rhino  # type: ignore
import Rhino.Geometry as rg  # type: ignore
import System  # type: ignore


# ---------------------------------------------------------------------------
#  Property section definitions
# ---------------------------------------------------------------------------

def _guid_empty() -> System.Guid:
    """Return System.Guid.Empty."""
    return System.Guid.Empty


def _point3d_origin() -> rg.Point3d:
    return rg.Point3d(0.0, 0.0, 0.0)


def _plane_world_xy() -> rg.Plane:
    return rg.Plane.WorldXY


# ---- Default value tables, grouped by section ----------------------------

_LENGTH_DEFAULTS: Dict[str, Any] = {
    "Length": 0.0,
    "BallLineLength": 0.0,
    "BallLineRatio": 0.69,
    "BallLineAngle": 0.0,
    "ArchLength": 0.0,
    "ArchLengthMult": 1.0,
}

_WIDTH_DEFAULTS: Dict[str, Any] = {
    "BallWidth": 0.0,
    "BallWidthPerp": 0.0,
    "BallWidthMult": 1.0,
    "BallWidthAuto": True,
    "HeelWidth": 0.0,
}

_GIRTH_BALL_DEFAULTS: Dict[str, Any] = {
    "BallGirth": 0.0,
    "BallGirthMult": 1.0,
    "BallGirthAngle": 0.0,
    "BallGirthAdapt": 0.0,
    "BallGirthAlt": 0.0,
}

_GIRTH_UPPER_DEFAULTS: Dict[str, Any] = {
    "InstepGirth": 0.0,
    "InstepGirthMult": 1.0,
    "InstepGirthAlt": 0.0,
    "WaistGirth": 0.0,
    "WaistGirthMult": 1.0,
    "WaistGirthAlt": 0.0,
    "Waist2Girth": 0.0,
    "Waist2GirthMult": 1.0,
    "Waist2GirthAlt": 0.0,
    "ArchGirth": 0.0,
    "ArchGirthMult": 1.0,
    "ArchGirthAlt": 0.0,
    "HeelGirth": 0.0,
    "HeelGirthMult": 1.0,
    "HeelGirthAlt": 0.0,
    "AnkleGirth": 0.0,
    "AnkleGirthMult": 1.0,
    "AnkleGirthAlt": 0.0,
}

_HEIGHT_ANGLE_DEFAULTS: Dict[str, Any] = {
    "HeelHeight": 0.0,
    "ToeSpring": 0.0,
    "BallBreakPointAngle": 0.0,
    "BallRollBulge": 0.0,
    "BallRollBulgeLat": 0.0,
}

_ALLOWANCE_DEFAULTS: Dict[str, Any] = {
    # Primary allowances
    "AllowanceLength": 0.0,
    "AllowanceBallGirth": 0.0,
    "AllowanceBallWidth": 0.0,
    "AllowanceHeelWidth": 0.0,
    "AllowanceHeelHeight": 0.0,
    "AllowanceToeSpring": 0.0,
    "AllowanceInstepGirth": 0.0,
    "AllowanceWaistGirth": 0.0,
    "AllowanceWaist2Girth": 0.0,
    # Sock allowances
    "AllowanceSockLength": 0.0,
    "AllowanceSockBallGirth": 0.0,
    "AllowanceSockBallWidth": 0.0,
    "AllowanceSockHeelWidth": 0.0,
    "AllowanceSockHeelHeight": 0.0,
    "AllowanceSockToeSpring": 0.0,
    "AllowanceSockInstepGirth": 0.0,
    "AllowanceSockWaistGirth": 0.0,
    "AllowanceSockWaist2Girth": 0.0,
    # Space allowances
    "AllowanceSpaceLength": 0.0,
    "AllowanceSpaceBallGirth": 0.0,
    "AllowanceSpaceBallWidth": 0.0,
    "AllowanceSpaceHeelWidth": 0.0,
    "AllowanceSpaceHeelHeight": 0.0,
    "AllowanceSpaceToeSpring": 0.0,
    "AllowanceSpaceInstepGirth": 0.0,
    "AllowanceSpaceWaistGirth": 0.0,
    "AllowanceSpaceWaist2Girth": 0.0,
    # Feather edge allowances
    "AllowanceFeatherEdgeLength": 0.0,
    "AllowanceFeatherEdgeBallGirth": 0.0,
    "AllowanceFeatherEdgeBallWidth": 0.0,
    "AllowanceFeatherEdgeHeelWidth": 0.0,
    "AllowanceFeatherEdgeHeelHeight": 0.0,
    "AllowanceFeatherEdgeToeSpring": 0.0,
    "AllowanceFeatherEdgeInstepGirth": 0.0,
    "AllowanceFeatherEdgeWaistGirth": 0.0,
    "AllowanceFeatherEdgeWaist2Girth": 0.0,
    # Fill-up allowances
    "AllowanceFillupLength": 0.0,
    "AllowanceFillupBallGirth": 0.0,
    "AllowanceFillupBallWidth": 0.0,
    "AllowanceFillupHeelWidth": 0.0,
    "AllowanceFillupHeelHeight": 0.0,
    "AllowanceFillupToeSpring": 0.0,
    "AllowanceFillupInstepGirth": 0.0,
    "AllowanceFillupWaistGirth": 0.0,
    "AllowanceFillupWaist2Girth": 0.0,
}

# Curve IDs -- Guid / String / SubD triples for each bottom-line curve
_BL_CURVE_NAMES = [
    "BLMesh", "BLB", "BLH", "BLI", "BLS", "BLT", "BLV", "BLIA", "BLTC", "BLTW", "BLCW",
]

# Centre-line curves
_CL_CURVE_NAMES = ["CLb", "CLt", "CLBW", "CLTW", "CLHG", "CSHG"]

# Cross-section curves (C1C..C5C with lateral/medial variants)
_CROSS_SECTION_CURVE_NAMES = []
for _prefix in ("C1C", "C2C", "C3C", "C4C", "C5C"):
    _CROSS_SECTION_CURVE_NAMES.append(_prefix)
    _CROSS_SECTION_CURVE_NAMES.append(f"{_prefix}l")
    _CROSS_SECTION_CURVE_NAMES.append(f"{_prefix}m")

# Alpha joint curves: CA / CH with lateral/medial sides and sub-variants
_ALPHA_CURVE_NAMES = []
for _base in ("CA", "CH"):
    for _side in ("l", "m"):
        _ALPHA_CURVE_NAMES.append(f"{_base}{_side}")
        _ALPHA_CURVE_NAMES.append(f"{_base}{_side}A")
        _ALPHA_CURVE_NAMES.append(f"{_base}{_side}extension")
        _ALPHA_CURVE_NAMES.append(f"{_base}{_side}Cap")
        _ALPHA_CURVE_NAMES.append(f"{_base}{_side}joined")

# Girth curves: CBG, CIG, CWG, CW2G with lateral/medial/p/di/dsi/dss variants
_GIRTH_CURVE_NAMES = []
for _base in ("CBG", "CIG", "CWG", "CW2G"):
    _GIRTH_CURVE_NAMES.append(_base)
    for _suffix in ("l", "m", "p", "di", "dsi", "dss"):
        _GIRTH_CURVE_NAMES.append(f"{_base}{_suffix}")

# Shank board curves: CSB with named sub-variants
_SHANK_BOARD_CURVE_NAMES = []
for _suffix in (
    "", "Arch", "Ball", "Heel", "HeelBack", "Instep", "Toe", "ToeFront", "Waist",
):
    _SHANK_BOARD_CURVE_NAMES.append(f"CSB{_suffix}")

# All curve names combined
_ALL_CURVE_NAMES = (
    _BL_CURVE_NAMES
    + _CL_CURVE_NAMES
    + _CROSS_SECTION_CURVE_NAMES
    + _ALPHA_CURVE_NAMES
    + _GIRTH_CURVE_NAMES
    + _SHANK_BOARD_CURVE_NAMES
)


def _build_curve_id_defaults() -> Dict[str, Any]:
    """Build default entries for all curve ID / String / SubD triples."""
    defaults: Dict[str, Any] = {}
    for name in _ALL_CURVE_NAMES:
        defaults[f"{name}ID"] = None       # System.Guid or None
        defaults[f"{name}String"] = ""     # serialised string form
        defaults[f"{name}SubD"] = None     # SubD geometry or None
    return defaults


# Cross-section parameters: A1, A2, A3 each with several sub-parameters
_CROSS_SECTION_PARAM_DEFAULTS: Dict[str, Any] = {}
for _a in ("A1", "A2", "A3"):
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}CS"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}Depth"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}Offset"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}CSlAngle"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}CSlHeight"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}CSmAngle"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}CSmHeight"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}GConcaveOffsetLateral"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}GConcaveOffsetLateralMult"] = 1.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}GConcaveOffsetMedial"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}GConcaveOffsetMedialMult"] = 1.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}GConcaveOffsetVertical"] = 0.0
    _CROSS_SECTION_PARAM_DEFAULTS[f"{_a}GConcaveOffsetVerticalMult"] = 1.0

# Body geometry defaults
_BODY_DEFAULTS: Dict[str, Any] = {
    "BodyMain": None,
    "BodyMainSubD": None,
    "BodyScrapCutter": None,
    "BodySoleCutter": None,
    "BodyMainID": None,
    "BodyMainSubDID": None,
    "BodyScrapCutterID": None,
    "BodySoleCutterID": None,
    "BodyMainString": "",
    "BodyMainSubDString": "",
    "BodyScrapCutterString": "",
    "BodySoleCutterString": "",
}

# Style parameters
_STYLE_DEFAULTS: Dict[str, Any] = {
    "ToeStyle": "Round",
    "ToeStylePointed": 0.0,
    "ToeStyleRound": 1.0,
    "ToeStyleSquare": 0.0,
    "BackEdgeShape": "Standard",
    "BottomType": "Flat",
    "ArchType": "Standard",
}

# Miscellaneous top-level parameters
_MISC_DEFAULTS: Dict[str, Any] = {
    "AlphaCutTiltFromMainPlane": 0.0,
    "AnkleJointxz": 0.0,
    "BallLinePointX": 0.0,
    "BallLinePointY": 0.0,
    "BallLinePointZ": 0.0,
}


def _merge_all_defaults() -> Dict[str, Any]:
    """Merge every section into a single ordered default dictionary."""
    merged: Dict[str, Any] = {}
    for section in (
        _LENGTH_DEFAULTS,
        _WIDTH_DEFAULTS,
        _GIRTH_BALL_DEFAULTS,
        _GIRTH_UPPER_DEFAULTS,
        _HEIGHT_ANGLE_DEFAULTS,
        _ALLOWANCE_DEFAULTS,
        _CROSS_SECTION_PARAM_DEFAULTS,
        _BODY_DEFAULTS,
        _STYLE_DEFAULTS,
        _MISC_DEFAULTS,
    ):
        merged.update(section)
    return merged


# Pre-compute once at import time
_ALL_DEFAULTS = _merge_all_defaults()
_CURVE_ID_DEFAULTS = _build_curve_id_defaults()


# ---------------------------------------------------------------------------
#  Last class
# ---------------------------------------------------------------------------

class Last:
    """
    Data model for a shoe last.

    Holds all measurement parameters (lengths, widths, girths, heights,
    allowances), curve IDs for construction geometry, cross-section
    parameters, body geometry references, and style settings.

    The property-based system stores values in ``self._props`` (simple
    scalar/string/bool parameters) and ``self._curves`` (Guid/String/SubD
    triples for each named curve).  Geometry objects (bodies, planes,
    points) that cannot be JSON-serialised as plain values are stored
    separately in ``self._geom``.

    Attributes are accessible as regular Python properties via
    ``__getattr__`` / ``__setattr__`` overrides.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, **kwargs: Any) -> None:
        # Scalar / serialisable properties
        object.__setattr__(self, "_props", dict(_ALL_DEFAULTS))
        # Curve ID / String / SubD triples
        object.__setattr__(self, "_curves", dict(_CURVE_ID_DEFAULTS))
        # Non-serialisable geometry (Plane, Point3d, Brep, SubD, etc.)
        object.__setattr__(self, "_geom", {
            "LocalPlane": _plane_world_xy(),
            "ViewingPlane": _plane_world_xy(),
            "BallLine": _point3d_origin(),
            "BallLinePoint": _point3d_origin(),
        })
        # Style parameter dictionary (user-extensible)
        object.__setattr__(self, "LastStyleParameterDictionary", {})

        # Apply any keyword overrides
        for key, value in kwargs.items():
            setattr(self, key, value)

    # ------------------------------------------------------------------
    # Attribute access
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        props = object.__getattribute__(self, "_props")
        if name in props:
            return props[name]
        curves = object.__getattribute__(self, "_curves")
        if name in curves:
            return curves[name]
        geom = object.__getattribute__(self, "_geom")
        if name in geom:
            return geom[name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "LastStyleParameterDictionary":
            object.__setattr__(self, name, value)
            return
        props = object.__getattribute__(self, "_props")
        if name in props:
            props[name] = value
            return
        curves = object.__getattribute__(self, "_curves")
        if name in curves:
            curves[name] = value
            return
        geom = object.__getattribute__(self, "_geom")
        if name in geom:
            geom[name] = value
            return
        # New attribute -- store in props by default
        props[name] = value

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def Create(cls, **overrides: Any) -> "Last":
        """Create a new Last with default values, optionally overridden."""
        return cls(**overrides)

    @classmethod
    def CreateViaJSon(cls, json_str: str) -> "Last":
        """Create a Last instance from a JSON string.

        Parameters
        ----------
        json_str : str
            JSON representation previously produced by ``to_json()``.

        Returns
        -------
        Last
        """
        data = json.loads(json_str)
        instance = cls()
        instance._apply_dict(data)
        return instance

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    def Clone(self) -> "Last":
        """Return a deep copy of this Last."""
        new = Last()
        new._props.update(copy.deepcopy(self._props))
        new._curves.update(copy.deepcopy(self._curves))
        # Geometry objects -- use Rhino Duplicate where possible
        for key, val in self._geom.items():
            if val is None:
                new._geom[key] = None
            elif isinstance(val, rg.Plane):
                new._geom[key] = rg.Plane(val)
            elif isinstance(val, rg.Point3d):
                new._geom[key] = rg.Point3d(val)
            elif hasattr(val, "Duplicate"):
                new._geom[key] = val.Duplicate()
            else:
                new._geom[key] = copy.deepcopy(val)
        new.LastStyleParameterDictionary = copy.deepcopy(
            self.LastStyleParameterDictionary
        )
        return new

    # ------------------------------------------------------------------
    # Parameter collection
    # ------------------------------------------------------------------

    def CollectLastParameters(self) -> Dict[str, Any]:
        """Collect all simple (JSON-serialisable) last parameters.

        Returns
        -------
        dict
            Flat dictionary of all scalar parameters suitable for JSON
            storage or UI display.
        """
        params: Dict[str, Any] = {}
        for key, value in self._props.items():
            if isinstance(value, (bool, int, float, str, type(None))):
                params[key] = value
        return OrderedDict(sorted(params.items()))

    def CollectLastGeneralStyleParameters(self) -> Dict[str, Any]:
        """Collect general style parameters (BottomType, ArchType, BackEdge)."""
        return {
            "BottomType": self.BottomType,
            "ArchType": self.ArchType,
            "BackEdgeShape": self.BackEdgeShape,
        }

    def CollectLastToeStyleParameters(self) -> Dict[str, Any]:
        """Collect toe-shape style parameters."""
        return {
            "ToeStyle": self.ToeStyle,
            "ToeStylePointed": self.ToeStylePointed,
            "ToeStyleRound": self.ToeStyleRound,
            "ToeStyleSquare": self.ToeStyleSquare,
        }

    # ------------------------------------------------------------------
    # Default setters
    # ------------------------------------------------------------------

    def SetDefaultLastToeStyleParameters(self) -> None:
        """Reset toe-style parameters to defaults."""
        for key in ("ToeStyle", "ToeStylePointed", "ToeStyleRound", "ToeStyleSquare"):
            self._props[key] = _STYLE_DEFAULTS[key]

    def SetDefaultLastGeneralStyleParameters(self) -> None:
        """Reset general style parameters to defaults."""
        for key in ("BackEdgeShape", "BottomType", "ArchType"):
            self._props[key] = _STYLE_DEFAULTS[key]

    # ------------------------------------------------------------------
    # Tertiary parameter calculations
    # ------------------------------------------------------------------

    def CalculateTertiaryParameters(self) -> None:
        """Derive dependent (tertiary) parameters from primary inputs.

        Computes arch length, ball-line length, perpendicular ball
        width, and girth 'Alt' values from their base + multiplier
        counterparts.
        """
        length = self.Length
        if length <= 0.0:
            return

        # Ball line length from ratio
        if self.BallLineLength <= 0.0 and self.BallLineRatio > 0.0:
            self._props["BallLineLength"] = length * self.BallLineRatio

        # Arch length from multiplier
        if self.ArchLengthMult != 1.0:
            base_arch = length * 0.5
            self._props["ArchLength"] = base_arch * self.ArchLengthMult

        # Perpendicular ball width
        if self.BallWidth > 0.0 and self.BallLineAngle != 0.0:
            angle_rad = math.radians(self.BallLineAngle)
            self._props["BallWidthPerp"] = self.BallWidth * math.cos(angle_rad)

        # Apply multiplier-based adjustments for widths
        if self.BallWidthMult != 1.0 and self.BallWidth > 0.0:
            self._props["BallWidth"] = self.BallWidth * self.BallWidthMult

        # Girth Alt values (effective = base * mult)
        girth_pairs = [
            ("BallGirth", "BallGirthMult", "BallGirthAlt"),
            ("InstepGirth", "InstepGirthMult", "InstepGirthAlt"),
            ("WaistGirth", "WaistGirthMult", "WaistGirthAlt"),
            ("Waist2Girth", "Waist2GirthMult", "Waist2GirthAlt"),
            ("ArchGirth", "ArchGirthMult", "ArchGirthAlt"),
            ("HeelGirth", "HeelGirthMult", "HeelGirthAlt"),
            ("AnkleGirth", "AnkleGirthMult", "AnkleGirthAlt"),
        ]
        for base_key, mult_key, alt_key in girth_pairs:
            base_val = self._props.get(base_key, 0.0)
            mult_val = self._props.get(mult_key, 1.0)
            if base_val > 0.0:
                self._props[alt_key] = base_val * mult_val

        # Cross-section concave offset multiplier application
        for a in ("A1", "A2", "A3"):
            for direction in ("Lateral", "Medial", "Vertical"):
                base_key = f"{a}GConcaveOffset{direction}"
                mult_key = f"{a}GConcaveOffset{direction}Mult"
                base_val = self._props.get(base_key, 0.0)
                mult_val = self._props.get(mult_key, 1.0)
                if mult_val != 1.0 and base_val != 0.0:
                    self._props[base_key] = base_val * mult_val

        # BallLine Point3d from stored scalar components
        self._geom["BallLinePoint"] = rg.Point3d(
            self._props.get("BallLinePointX", 0.0),
            self._props.get("BallLinePointY", 0.0),
            self._props.get("BallLinePointZ", 0.0),
        )

    def CalculateLinearMeasurementsFromMults(self) -> None:
        """Recalculate linear measurements from their multiplier values.

        For each girth/length that has a ``*Mult`` companion, the base
        value is multiplied by the Mult to produce the effective value
        stored in the corresponding ``*Alt`` key.
        """
        mult_map = {
            "BallGirth": "BallGirthMult",
            "InstepGirth": "InstepGirthMult",
            "WaistGirth": "WaistGirthMult",
            "Waist2Girth": "Waist2GirthMult",
            "ArchGirth": "ArchGirthMult",
            "HeelGirth": "HeelGirthMult",
            "AnkleGirth": "AnkleGirthMult",
            "BallWidth": "BallWidthMult",
            "ArchLength": "ArchLengthMult",
        }
        for base_key, mult_key in mult_map.items():
            base_val = self._props.get(base_key, 0.0)
            mult_val = self._props.get(mult_key, 1.0)
            alt_key = f"{base_key}Alt"
            if alt_key in self._props:
                self._props[alt_key] = base_val * mult_val

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dictionary of all parameters.

        Geometry objects are serialised as nested dicts (Point3d -> X/Y/Z,
        Plane -> Origin/XAxis/YAxis/ZAxis, Guid -> string).
        """
        data: Dict[str, Any] = {}

        # Scalar properties
        for key, value in self._props.items():
            if isinstance(value, (bool, int, float, str, type(None))):
                data[key] = value

        # Curve IDs -- only store the String variants
        for name in _ALL_CURVE_NAMES:
            str_key = f"{name}String"
            data[str_key] = self._curves.get(str_key, "")
            id_key = f"{name}ID"
            guid_val = self._curves.get(id_key)
            if guid_val is not None and isinstance(guid_val, System.Guid):
                data[id_key] = str(guid_val)
            else:
                data[id_key] = ""

        # Geometry
        bl = self._geom.get("BallLine")
        if bl is not None and isinstance(bl, rg.Point3d):
            data["BallLine"] = {"X": bl.X, "Y": bl.Y, "Z": bl.Z}
        blp = self._geom.get("BallLinePoint")
        if blp is not None and isinstance(blp, rg.Point3d):
            data["BallLinePoint"] = {"X": blp.X, "Y": blp.Y, "Z": blp.Z}
        for plane_key in ("LocalPlane", "ViewingPlane"):
            plane = self._geom.get(plane_key)
            if plane is not None and isinstance(plane, rg.Plane):
                data[plane_key] = {
                    "Origin": {"X": plane.Origin.X, "Y": plane.Origin.Y, "Z": plane.Origin.Z},
                    "XAxis": {"X": plane.XAxis.X, "Y": plane.XAxis.Y, "Z": plane.XAxis.Z},
                    "YAxis": {"X": plane.YAxis.X, "Y": plane.YAxis.Y, "Z": plane.YAxis.Z},
                    "ZAxis": {"X": plane.ZAxis.X, "Y": plane.ZAxis.Y, "Z": plane.ZAxis.Z},
                }

        # Style dictionary
        data["LastStyleParameterDictionary"] = copy.deepcopy(
            self.LastStyleParameterDictionary
        )

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Last":
        """Restore a Last from a dictionary (e.g. loaded from JSON)."""
        if data is None:
            return cls.Create()
        instance = cls()
        instance._apply_dict(data)
        return instance

    def to_json(self, indent: int = 2) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "Last":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(raw))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_dict(self, data: Dict[str, Any]) -> None:
        """Apply values from *data* onto internal stores."""
        for key, value in data.items():
            if key == "LastStyleParameterDictionary":
                if isinstance(value, dict):
                    self.LastStyleParameterDictionary = value
                continue

            # Reconstruct Point3d
            if key in ("BallLine", "BallLinePoint") and isinstance(value, dict):
                self._geom[key] = rg.Point3d(
                    float(value.get("X", 0.0)),
                    float(value.get("Y", 0.0)),
                    float(value.get("Z", 0.0)),
                )
                continue

            # Reconstruct Plane
            if key in ("LocalPlane", "ViewingPlane") and isinstance(value, dict):
                origin_d = value.get("Origin", {})
                x_d = value.get("XAxis", {})
                y_d = value.get("YAxis", {})
                origin = rg.Point3d(
                    float(origin_d.get("X", 0.0)),
                    float(origin_d.get("Y", 0.0)),
                    float(origin_d.get("Z", 0.0)),
                )
                x_axis = rg.Vector3d(
                    float(x_d.get("X", 1.0)),
                    float(x_d.get("Y", 0.0)),
                    float(x_d.get("Z", 0.0)),
                )
                y_axis = rg.Vector3d(
                    float(y_d.get("X", 0.0)),
                    float(y_d.get("Y", 1.0)),
                    float(y_d.get("Z", 0.0)),
                )
                self._geom[key] = rg.Plane(origin, x_axis, y_axis)
                continue

            # Curve ID entry (Guid stored as string)
            if key in self._curves:
                if key.endswith("ID") and isinstance(value, str) and value:
                    try:
                        self._curves[key] = System.Guid(value)
                    except Exception:
                        self._curves[key] = None
                else:
                    self._curves[key] = value
                continue

            # Scalar property
            if key in self._props:
                self._props[key] = value

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        length = self._props.get("Length", 0.0)
        bw = self._props.get("BallWidth", 0.0)
        hh = self._props.get("HeelHeight", 0.0)
        ts = self._props.get("ToeStyle", "Round")
        return (
            f"<Last Length={length:.1f} BallWidth={bw:.1f} "
            f"HeelHeight={hh:.1f} ToeStyle={ts!r}>"
        )
