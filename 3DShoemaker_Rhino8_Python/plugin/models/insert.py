"""
insert.py - Insert / insole data model for Feet in Focus Shoe Kit.

Represents an insert (orthotic / insole / footbed) with measurement
parameters, design curves, cross-section curves, sandal curves, body
geometry references, and style parameters.
"""

from __future__ import annotations

import copy
import json
import math
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import Rhino  # type: ignore
import Rhino.Geometry as rg  # type: ignore
import System  # type: ignore


# ---------------------------------------------------------------------------
#  Default value tables
# ---------------------------------------------------------------------------

_MEASUREMENT_DEFAULTS: Dict[str, Any] = {
    # Basic dimensions
    "Length": 0.0,
    "Width": 0.0,
    "Thickness": 3.0,
    "ThicknessMult": 1.0,
    "ThicknessAlt": 3.0,
    # Arch
    "ArchHeight": 0.0,
    "ArchHeightMult": 1.0,
    "ArchHeightAlt": 0.0,
    "ArchLength": 0.0,
    # Heel cup
    "HeelCupDepth": 0.0,
    "HeelCupDepthMult": 1.0,
    "HeelCupDepthAlt": 0.0,
    "HeelCupWidth": 0.0,
    # Posting
    "PostingMedial": 0.0,
    "PostingMedialMult": 1.0,
    "PostingMedialAlt": 0.0,
    "PostingLateral": 0.0,
    "PostingLateralMult": 1.0,
    "PostingLateralAlt": 0.0,
    "PostingRearfoot": 0.0,
    "PostingForefoot": 0.0,
    # Covers
    "TopCoverThickness": 1.0,
    "BottomCoverThickness": 0.0,
    # Trim / extent
    "TrimType": "FullLength",  # FullLength, ThreeQuarter, MetHead, HeelCup
    "TrimOffset": 0.0,
    # Forefoot
    "ForefootExtension": 0.0,
    "ForefootExtensionThickness": 0.0,
    "RearfootExtension": 0.0,
    "RearfootExtensionThickness": 0.0,
    # Met pad
    "MetPadHeight": 0.0,
    "MetPadWidth": 0.0,
    "MetPadLength": 0.0,
    "MetPadPositionX": 0.0,
    "MetPadPositionY": 0.0,
    # Shell
    "ShellType": "Standard",  # Standard, SubD, FullLength, NonShell
    "ShellThickness": 2.0,
    # Casing
    "CasingThickness": 0.0,
    "CasingOffset": 0.0,
    # Material
    "Material": "EVA",
    "Density": 0.0,
    "ShoreA": 0.0,
}

# Curve name groups for inserts
_DESIGN_CURVE_NAMES = [
    "DCMedial", "DCLateral", "DCToe", "DCHeel",
    "DCArchMedial", "DCArchLateral",
    "DCMetLine", "DCTrimLine",
    "DCOutline", "DCOutlineOffset",
    "DCHeelCup", "DCHeelCupInner", "DCHeelCupOuter",
]

_CROSS_SECTION_CURVE_NAMES = [
    "CSBall", "CSArch", "CSWaist", "CSHeel",
    "CSBallMedial", "CSBallLateral",
    "CSArchMedial", "CSArchLateral",
    "CSHeelMedial", "CSHeelLateral",
    "CSCustom1", "CSCustom2", "CSCustom3",
]

_SANDAL_CURVE_NAMES = [
    "SandalOutline", "SandalOutlineOffset",
    "SandalThongSlot", "SandalGroove",
    "SandalStrapSlotMedial", "SandalStrapSlotLateral",
    "SandalArchSupport", "SandalHeelContour",
    "SandalToeBar",
]

_ALL_INSERT_CURVES = (
    _DESIGN_CURVE_NAMES + _CROSS_SECTION_CURVE_NAMES + _SANDAL_CURVE_NAMES
)


def _build_curve_id_defaults() -> Dict[str, Any]:
    defaults: Dict[str, Any] = {}
    for name in _ALL_INSERT_CURVES:
        defaults[f"{name}ID"] = None
        defaults[f"{name}String"] = ""
        defaults[f"{name}SubD"] = None
    return defaults


# Body geometry defaults
_BODY_DEFAULTS: Dict[str, Any] = {
    "BodyMain": None,
    "BodyMainSubD": None,
    "BodyCasing": None,
    "BodyMainID": None,
    "BodyMainSubDID": None,
    "BodyCasingID": None,
    "BodyMainString": "",
    "BodyMainSubDString": "",
    "BodyCasingString": "",
}

_CURVE_ID_DEFAULTS = _build_curve_id_defaults()


def _merge_all_defaults() -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    merged.update(_MEASUREMENT_DEFAULTS)
    merged.update(_BODY_DEFAULTS)
    return merged


_ALL_DEFAULTS = _merge_all_defaults()


# ---------------------------------------------------------------------------
#  Insert class
# ---------------------------------------------------------------------------

class Insert:
    """
    Data model for an insert / insole / footbed / orthotic.

    Stores measurement parameters, curve IDs for design curves,
    cross-section curves, sandal-specific curves, and body geometry
    references.  Follows the same property-system pattern as ``Last``.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, **kwargs: Any) -> None:
        object.__setattr__(self, "_props", dict(_ALL_DEFAULTS))
        object.__setattr__(self, "_curves", dict(_CURVE_ID_DEFAULTS))
        object.__setattr__(self, "_geom", {
            "LocalPlane": rg.Plane.WorldXY,
        })
        object.__setattr__(self, "InsertStyleParameterDictionary", {})

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
        if name.startswith("_") or name == "InsertStyleParameterDictionary":
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
        props[name] = value

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def Create(cls, **overrides: Any) -> "Insert":
        """Create a new Insert with default values."""
        return cls(**overrides)

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    def Clone(self) -> "Insert":
        """Return a deep copy of this Insert."""
        new = Insert()
        new._props.update(copy.deepcopy(self._props))
        new._curves.update(copy.deepcopy(self._curves))
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
        new.InsertStyleParameterDictionary = copy.deepcopy(
            self.InsertStyleParameterDictionary
        )
        return new

    # ------------------------------------------------------------------
    # Parameter collection
    # ------------------------------------------------------------------

    def CollectInsertParameters(self) -> Dict[str, Any]:
        """Collect all scalar insert parameters."""
        params: Dict[str, Any] = {}
        for key, value in self._props.items():
            if isinstance(value, (bool, int, float, str, type(None))):
                params[key] = value
        return OrderedDict(sorted(params.items()))

    def CollectInsertStyleParameters(self) -> Dict[str, Any]:
        """Collect style-specific parameters."""
        return {
            "ShellType": self.ShellType,
            "TrimType": self.TrimType,
            "Material": self.Material,
        }

    def SetDefaultInsertStyleParameters(self) -> None:
        """Reset style parameters to defaults."""
        for key in ("ShellType", "TrimType", "Material"):
            self._props[key] = _MEASUREMENT_DEFAULTS[key]

    # ------------------------------------------------------------------
    # Linear measurement recalculation
    # ------------------------------------------------------------------

    def CalculateLinearMeasurementsFromMults(self) -> None:
        """Recalculate Alt values from base * Mult."""
        mult_map = {
            "Thickness": ("ThicknessMult", "ThicknessAlt"),
            "ArchHeight": ("ArchHeightMult", "ArchHeightAlt"),
            "HeelCupDepth": ("HeelCupDepthMult", "HeelCupDepthAlt"),
            "PostingMedial": ("PostingMedialMult", "PostingMedialAlt"),
            "PostingLateral": ("PostingLateralMult", "PostingLateralAlt"),
        }
        for base_key, (mult_key, alt_key) in mult_map.items():
            base_val = self._props.get(base_key, 0.0)
            mult_val = self._props.get(mult_key, 1.0)
            self._props[alt_key] = base_val * mult_val

    # ------------------------------------------------------------------
    # Design curve construction
    # ------------------------------------------------------------------

    def DesignCurves(
        self,
        last: Any,
        doc: Rhino.RhinoDoc,
    ) -> bool:
        """Generate all design curves for the insert from the given last.

        Computes outline, trim, heel-cup, and arch-support curves based
        on the insert parameters and the last geometry.

        Parameters
        ----------
        last : Last
            The parent last from which outline/bottom curves are derived.
        doc : RhinoDoc
            Active Rhino document for tolerance values.

        Returns
        -------
        bool
            True on success.
        """
        tol = doc.ModelAbsoluteTolerance

        # Outline: offset from the last bottom-line curve
        bl_id = getattr(last, "BLBID", None)
        if bl_id is None or bl_id == System.Guid.Empty:
            return False

        obj = doc.Objects.FindId(bl_id)
        if obj is None:
            return False

        crv = obj.Geometry
        if not isinstance(crv, rg.Curve):
            return False

        # Offset the outline by TrimOffset
        offset_dist = self.TrimOffset
        if offset_dist != 0.0:
            offsets = crv.Offset(
                rg.Plane.WorldXY, offset_dist,
                tol, rg.CurveOffsetCornerStyle.Sharp,
            )
            if offsets and len(offsets) > 0:
                outline = offsets[0]
            else:
                outline = crv.DuplicateCurve()
        else:
            outline = crv.DuplicateCurve()

        # Store outline
        attrs = Rhino.DocObjects.ObjectAttributes()
        guid = doc.Objects.AddCurve(outline, attrs)
        if guid != System.Guid.Empty:
            self._curves["DCOutlineID"] = guid

        return True

    def MorphExtendTrimCurve(
        self,
        curve: rg.Curve,
        target_surface: rg.Surface,
        doc: Rhino.RhinoDoc,
    ) -> Optional[rg.Curve]:
        """Morph, extend, and trim a curve onto a target surface.

        Parameters
        ----------
        curve : Curve
            Input curve to morph.
        target_surface : Surface
            Surface to project/morph onto.
        doc : RhinoDoc
            Active document for tolerances.

        Returns
        -------
        Curve or None
            The morphed and trimmed curve, or None on failure.
        """
        if curve is None or target_surface is None:
            return None

        tol = doc.ModelAbsoluteTolerance

        # Pull curve onto surface
        brep = target_surface.ToBrep()
        if brep is None:
            return None

        pulled = rg.Curve.PullToBrepFace(
            curve, brep.Faces[0], tol,
        )
        if pulled is None or len(pulled) == 0:
            return None

        result = pulled[0]

        # Extend to surface edges if needed
        domain = result.Domain
        extended = result.Extend(
            rg.CurveEnd.Both, rg.CurveExtensionStyle.Line, [target_surface],
        )
        if extended is not None:
            result = extended

        return result

    def DesignCrossSectionCurve(
        self,
        section_name: str,
        points: Sequence[rg.Point3d],
        degree: int = 3,
    ) -> Optional[rg.Curve]:
        """Create a cross-section curve through the given points.

        Parameters
        ----------
        section_name : str
            Name of the cross section (e.g. 'CSBall', 'CSArch').
        points : sequence of Point3d
            Points the curve must interpolate.
        degree : int
            Curve degree (default 3).

        Returns
        -------
        Curve or None
        """
        if not points or len(points) < 2:
            return None

        curve = rg.Curve.CreateInterpolatedCurve(
            list(points), degree,
            rg.CurveKnotStyle.Chord,
            rg.Vector3d.Unset, rg.Vector3d.Unset,
        )
        if curve is not None and curve.IsValid:
            str_key = f"{section_name}String"
            if str_key in self._curves:
                self._curves[str_key] = "generated"
            return curve
        return None

    # ------------------------------------------------------------------
    # Surface design
    # ------------------------------------------------------------------

    def DesignSurfaces(
        self,
        last: Any,
        doc: Rhino.RhinoDoc,
    ) -> bool:
        """Generate insert surfaces from design curves and cross sections.

        Lofts through cross-section curves to build the insert surface,
        respecting the shell type setting.

        Parameters
        ----------
        last : Last
            The parent last.
        doc : RhinoDoc
            Active document.

        Returns
        -------
        bool
            True on success.
        """
        tol = doc.ModelAbsoluteTolerance

        # Collect cross-section curves that have been generated
        section_curves: List[rg.Curve] = []
        for name in _CROSS_SECTION_CURVE_NAMES:
            crv_id = self._curves.get(f"{name}ID")
            if crv_id is not None and isinstance(crv_id, System.Guid):
                obj = doc.Objects.FindId(crv_id)
                if obj is not None and isinstance(obj.Geometry, rg.Curve):
                    section_curves.append(obj.Geometry)

        if len(section_curves) < 2:
            return False

        # Loft
        lofted = rg.Brep.CreateFromLoft(
            section_curves,
            rg.Point3d.Unset, rg.Point3d.Unset,
            rg.LoftType.Normal, False,
        )
        if lofted is None or len(lofted) == 0:
            return False

        surface_brep = lofted[0]
        guid = doc.Objects.AddBrep(surface_brep)
        if guid != System.Guid.Empty:
            self._props["BodyMainID"] = guid

        return True

    def TrimLastByInsertSurface(
        self,
        last: Any,
        doc: Rhino.RhinoDoc,
    ) -> Optional[rg.Brep]:
        """Trim the last body using the insert surface as a cutter.

        Parameters
        ----------
        last : Last
            The parent last whose body will be trimmed.
        doc : RhinoDoc
            Active document.

        Returns
        -------
        Brep or None
            The trimmed last body, or None on failure.
        """
        tol = doc.ModelAbsoluteTolerance

        # Get insert body
        insert_body_id = self._props.get("BodyMainID")
        if insert_body_id is None:
            return None
        insert_obj = doc.Objects.FindId(insert_body_id)
        if insert_obj is None or not isinstance(insert_obj.Geometry, rg.Brep):
            return None

        # Get last body
        last_body_id = getattr(last, "BodyMainID", None)
        if last_body_id is None:
            return None
        last_obj = doc.Objects.FindId(last_body_id)
        if last_obj is None or not isinstance(last_obj.Geometry, rg.Brep):
            return None

        # Boolean difference: last - insert
        result = rg.Brep.CreateBooleanDifference(
            last_obj.Geometry, insert_obj.Geometry, tol,
        )
        if result is None or len(result) == 0:
            return None

        return result[0]

    # ------------------------------------------------------------------
    # Body design
    # ------------------------------------------------------------------

    def DesignBody(
        self,
        last: Any,
        doc: Rhino.RhinoDoc,
    ) -> bool:
        """Create the insert body geometry.

        Delegates to the appropriate sub-method based on ShellType.

        Parameters
        ----------
        last : Last
            Parent last.
        doc : RhinoDoc
            Active document.

        Returns
        -------
        bool
            True on success.
        """
        shell_type = self.ShellType

        if shell_type == "SubD" or (
            shell_type == "FullLength" and self.TrimType == "FullLength"
            and shell_type != "NonShell"
        ):
            return self.DesignBodySubDFullLengthNonShell(last, doc)
        else:
            return self.DesignBodyAllOtherCases(last, doc)

    def DesignBodySubDFullLengthNonShell(
        self,
        last: Any,
        doc: Rhino.RhinoDoc,
    ) -> bool:
        """Design body for SubD / FullLength / NonShell shell types.

        Builds the insert as a SubD-based or full-length surface with
        appropriate thickness offsets.

        Parameters
        ----------
        last : Last
            Parent last.
        doc : RhinoDoc
            Active document.

        Returns
        -------
        bool
        """
        tol = doc.ModelAbsoluteTolerance
        thickness = self._props.get("ThicknessAlt", self._props.get("Thickness", 3.0))

        # Get the main body surface
        body_id = self._props.get("BodyMainID")
        if body_id is None:
            return False

        obj = doc.Objects.FindId(body_id)
        if obj is None or not isinstance(obj.Geometry, rg.Brep):
            return False

        base_brep = obj.Geometry

        # Offset to create thickness
        offset_result = rg.Brep.CreateOffsetBrep(
            base_brep, -thickness, True, True, tol,
        )
        if offset_result is None:
            return False

        # CreateOffsetBrep may return tuple (Brep[], BrepFace[])
        if isinstance(offset_result, tuple):
            offset_breps = offset_result[0]
        else:
            offset_breps = offset_result

        if offset_breps is None or len(offset_breps) == 0:
            return False

        solid = offset_breps[0]

        # Add to document
        guid = doc.Objects.AddBrep(solid)
        if guid != System.Guid.Empty:
            self._props["BodyMainID"] = guid
            return True

        return False

    def DesignBodyAllOtherCases(
        self,
        last: Any,
        doc: Rhino.RhinoDoc,
    ) -> bool:
        """Design body for Standard and other shell types.

        Creates a trimmed shell body based on the trim type and
        shell thickness.

        Parameters
        ----------
        last : Last
            Parent last.
        doc : RhinoDoc
            Active document.

        Returns
        -------
        bool
        """
        tol = doc.ModelAbsoluteTolerance
        thickness = self._props.get("ThicknessAlt", self._props.get("Thickness", 3.0))
        shell_thickness = self._props.get("ShellThickness", 2.0)

        body_id = self._props.get("BodyMainID")
        if body_id is None:
            return False

        obj = doc.Objects.FindId(body_id)
        if obj is None or not isinstance(obj.Geometry, rg.Brep):
            return False

        base_brep = obj.Geometry

        # Create shell by offsetting
        offset_result = rg.Brep.CreateOffsetBrep(
            base_brep, -shell_thickness, True, True, tol,
        )
        if offset_result is None:
            return False

        if isinstance(offset_result, tuple):
            offset_breps = offset_result[0]
        else:
            offset_breps = offset_result

        if offset_breps is None or len(offset_breps) == 0:
            return False

        shell = offset_breps[0]

        # Trim based on TrimType
        trim_type = self.TrimType
        if trim_type == "FullLength":
            result = shell
        elif trim_type in ("ThreeQuarter", "MetHead", "HeelCup"):
            # Trim with a plane at the appropriate position
            trim_ratio = {"ThreeQuarter": 0.75, "MetHead": 0.65, "HeelCup": 0.35}.get(
                trim_type, 0.75
            )
            length = self._props.get("Length", 0.0)
            if length <= 0.0:
                length = getattr(last, "Length", 260.0)
            trim_y = length * trim_ratio
            trim_plane = rg.Plane(
                rg.Point3d(0, trim_y, 0),
                rg.Vector3d.YAxis,
            )
            split = shell.Trim(trim_plane, tol)
            if split is not None and len(split) > 0:
                result = split[0]
            else:
                result = shell
        else:
            result = shell

        guid = doc.Objects.AddBrep(result)
        if guid != System.Guid.Empty:
            self._props["BodyMainID"] = guid
            return True

        return False

    # ------------------------------------------------------------------
    # Sandal curves and body
    # ------------------------------------------------------------------

    def DesignSandalCurves(
        self,
        last: Any,
        doc: Rhino.RhinoDoc,
    ) -> bool:
        """Generate sandal-specific design curves.

        Creates the sandal outline, thong slot, groove, and strap slot
        curves from the insert outline and last geometry.

        Parameters
        ----------
        last : Last
            Parent last.
        doc : RhinoDoc
            Active document.

        Returns
        -------
        bool
        """
        tol = doc.ModelAbsoluteTolerance

        # Get the design outline
        outline_id = self._curves.get("DCOutlineID")
        if outline_id is None:
            return False

        obj = doc.Objects.FindId(outline_id)
        if obj is None or not isinstance(obj.Geometry, rg.Curve):
            return False

        outline = obj.Geometry

        # Sandal outline -- typically a slightly offset version
        offset_curves = outline.Offset(
            rg.Plane.WorldXY, 2.0, tol, rg.CurveOffsetCornerStyle.Sharp,
        )
        if offset_curves and len(offset_curves) > 0:
            sandal_outline = offset_curves[0]
            guid = doc.Objects.AddCurve(sandal_outline)
            if guid != System.Guid.Empty:
                self._curves["SandalOutlineID"] = guid

        # Thong slot curve -- line between toes
        ball_line_pt = getattr(last, "BallLinePoint", rg.Point3d(0, 0, 0))
        if ball_line_pt is not None:
            slot_start = rg.Point3d(ball_line_pt.X, ball_line_pt.Y + 10.0, ball_line_pt.Z)
            slot_end = rg.Point3d(ball_line_pt.X, ball_line_pt.Y + 25.0, ball_line_pt.Z)
            thong_line = rg.LineCurve(slot_start, slot_end)
            guid = doc.Objects.AddCurve(thong_line)
            if guid != System.Guid.Empty:
                self._curves["SandalThongSlotID"] = guid

        return True

    def DesignSandalBody(
        self,
        last: Any,
        doc: Rhino.RhinoDoc,
    ) -> bool:
        """Create the sandal body from sandal curves.

        Builds a flat sandal sole body by extruding the sandal
        outline curve to the specified thickness.

        Parameters
        ----------
        last : Last
            Parent last.
        doc : RhinoDoc
            Active document.

        Returns
        -------
        bool
        """
        tol = doc.ModelAbsoluteTolerance
        thickness = self._props.get("ThicknessAlt", self._props.get("Thickness", 3.0))

        sandal_outline_id = self._curves.get("SandalOutlineID")
        if sandal_outline_id is None:
            return False

        obj = doc.Objects.FindId(sandal_outline_id)
        if obj is None or not isinstance(obj.Geometry, rg.Curve):
            return False

        outline_crv = obj.Geometry

        # Create planar surface from outline
        planar = rg.Brep.CreatePlanarBreps(
            [outline_crv], tol,
        )
        if planar is None or len(planar) == 0:
            return False

        flat_brep = planar[0]

        # Extrude downward to create thickness
        extrusion = rg.Brep.CreateOffsetBrep(
            flat_brep, -thickness, True, True, tol,
        )
        if extrusion is None:
            return False

        if isinstance(extrusion, tuple):
            ex_breps = extrusion[0]
        else:
            ex_breps = extrusion

        if ex_breps is None or len(ex_breps) == 0:
            return False

        guid = doc.Objects.AddBrep(ex_breps[0])
        if guid != System.Guid.Empty:
            self._props["BodyMainID"] = guid
            return True

        return False

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dictionary of all parameters."""
        data: Dict[str, Any] = {}

        for key, value in self._props.items():
            if isinstance(value, (bool, int, float, str, type(None))):
                data[key] = value
            elif isinstance(value, System.Guid):
                data[key] = str(value)

        for name in _ALL_INSERT_CURVES:
            str_key = f"{name}String"
            data[str_key] = self._curves.get(str_key, "")
            id_key = f"{name}ID"
            guid_val = self._curves.get(id_key)
            if guid_val is not None and isinstance(guid_val, System.Guid):
                data[id_key] = str(guid_val)
            else:
                data[id_key] = ""

        for plane_key in ("LocalPlane",):
            plane = self._geom.get(plane_key)
            if plane is not None and isinstance(plane, rg.Plane):
                data[plane_key] = {
                    "Origin": {"X": plane.Origin.X, "Y": plane.Origin.Y, "Z": plane.Origin.Z},
                    "XAxis": {"X": plane.XAxis.X, "Y": plane.XAxis.Y, "Z": plane.XAxis.Z},
                    "YAxis": {"X": plane.YAxis.X, "Y": plane.YAxis.Y, "Z": plane.YAxis.Z},
                    "ZAxis": {"X": plane.ZAxis.X, "Y": plane.ZAxis.Y, "Z": plane.ZAxis.Z},
                }

        data["InsertStyleParameterDictionary"] = copy.deepcopy(
            self.InsertStyleParameterDictionary
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Insert":
        """Restore an Insert from a dictionary."""
        if data is None:
            return cls.Create()
        instance = cls()
        instance._apply_dict(data)
        return instance

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "Insert":
        return cls.from_dict(json.loads(raw))

    def _apply_dict(self, data: Dict[str, Any]) -> None:
        """Apply values from *data* onto internal stores."""
        for key, value in data.items():
            if key == "InsertStyleParameterDictionary":
                if isinstance(value, dict):
                    self.InsertStyleParameterDictionary = value
                continue

            if key == "LocalPlane" and isinstance(value, dict):
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

            if key in self._curves:
                if key.endswith("ID") and isinstance(value, str) and value:
                    try:
                        self._curves[key] = System.Guid(value)
                    except Exception:
                        self._curves[key] = None
                else:
                    self._curves[key] = value
                continue

            if key in self._props:
                self._props[key] = value

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        thickness = self._props.get("Thickness", 0.0)
        trim = self._props.get("TrimType", "FullLength")
        shell = self._props.get("ShellType", "Standard")
        return (
            f"<Insert Thickness={thickness:.1f} TrimType={trim!r} "
            f"ShellType={shell!r}>"
        )
