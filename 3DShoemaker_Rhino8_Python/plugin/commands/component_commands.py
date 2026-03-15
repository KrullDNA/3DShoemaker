"""
Feet in Focus Shoe Kit Rhino 8 Plugin - Footwear component creation commands.

Commands:
    CreateInsole        - Create insole geometry from last.
    CreateSole          - Create sole geometry.
    CreateHeel          - Create heel geometry.
    CreateHeelParts     - Create heel sub-components.
    CreateTopPiece      - Create top piece.
    CreateShankBoard    - Create shank board.
    CreateMetPad        - Create metatarsal pad.
    CreateToeCrest      - Create toe crest.
    CreateToeRidge      - Create toe ridge.
    CreateThongHole     - Create thong hole for sandals.
    CreatePinHole       - Create pin hole.
    CreateShoeTree      - Create shoe tree.
    CreateUpperBodies   - Create upper body components.
    MakeComponent       - Generic component creation command.
    CreateAlphaJoint    - Create alpha joint assembly.
    CreateRailGuideJoint - Create rail guide joint assembly.
    CreateMockup        - Create 3D mockup.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import Rhino  # type: ignore
import Rhino.Commands  # type: ignore
import Rhino.Display  # type: ignore
import Rhino.DocObjects  # type: ignore
import Rhino.Geometry  # type: ignore
import Rhino.Input  # type: ignore
import Rhino.Input.Custom  # type: ignore
import Rhino.RhinoApp  # type: ignore
import Rhino.RhinoDoc  # type: ignore
import rhinoscriptsyntax as rs  # type: ignore
import scriptcontext as sc  # type: ignore
import System  # type: ignore

import plugin as plugin_constants
from plugin.plugin_main import PodoCADPlugIn
from plugin.document_settings import DocumentSettings


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_plugin() -> PodoCADPlugIn:
    return PodoCADPlugIn.instance()


def _require_license() -> bool:
    plug = _get_plugin()
    return True


def _get_layer_index(doc: Rhino.RhinoDoc, layer_suffix: str) -> int:
    """Return the index of a SLM::<suffix> layer, creating it if needed."""
    full_path = f"{plugin_constants.SLM_LAYER_PREFIX}::{layer_suffix}"
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx < 0:
        _get_plugin().SetupLayers(doc)
        idx = doc.Layers.FindByFullPath(full_path, -1)
    return idx


def _get_last_brep(doc: Rhino.RhinoDoc) -> Optional[Rhino.Geometry.Brep]:
    """Retrieve the last brep from the document (stored geometry or layer objects)."""
    plug = _get_plugin()
    stored = plug.GetGeometryFromStoredString(doc, "LastBrep")
    if isinstance(stored, Rhino.Geometry.Brep):
        return stored

    # Fallback: find a brep on the Last layer
    last_path = f"{plugin_constants.SLM_LAYER_PREFIX}::{plugin_constants.CLASS_LAST}"
    layer_idx = doc.Layers.FindByFullPath(last_path, -1)
    if layer_idx < 0:
        return None
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        for obj in objs:
            if isinstance(obj.Geometry, Rhino.Geometry.Brep):
                return obj.Geometry
    return None


def _get_last_bbox(doc: Rhino.RhinoDoc) -> Optional[Rhino.Geometry.BoundingBox]:
    """Get the bounding box of the last geometry."""
    brep = _get_last_brep(doc)
    if brep is not None:
        return brep.GetBoundingBox(True)
    return None


def _add_component(
    doc: Rhino.RhinoDoc,
    geometry: Rhino.Geometry.GeometryBase,
    layer_suffix: str,
    name: str,
) -> System.Guid:
    """Add a component geometry to the document on the appropriate layer."""
    layer_idx = _get_layer_index(doc, layer_suffix)
    attrs = Rhino.DocObjects.ObjectAttributes()
    if layer_idx >= 0:
        attrs.LayerIndex = layer_idx
    attrs.Name = name

    if isinstance(geometry, Rhino.Geometry.Brep):
        guid = doc.Objects.AddBrep(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Mesh):
        guid = doc.Objects.AddMesh(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Curve):
        guid = doc.Objects.AddCurve(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Surface):
        guid = doc.Objects.AddSurface(geometry, attrs)
    else:
        guid = doc.Objects.Add(geometry, attrs)

    doc.Views.Redraw()
    return guid


def _prompt_float(prompt: str, default: float) -> Optional[float]:
    """Prompt the user for a floating point number."""
    gn = Rhino.Input.Custom.GetNumber()
    gn.SetCommandPrompt(prompt)
    gn.SetDefaultNumber(default)
    gn.AcceptNothing(True)
    if gn.Get() == Rhino.Input.GetResult.Number:
        return gn.Number()
    if gn.CommandResult() == Rhino.Commands.Result.Success:
        return default
    return None


def _prompt_string(prompt: str, default: str = "") -> Optional[str]:
    """Prompt the user for a string."""
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt(prompt)
    if default:
        gs.SetDefaultString(default)
    gs.AcceptNothing(True)
    result = gs.Get()
    if result == Rhino.Input.GetResult.String:
        return gs.StringResult().strip()
    if gs.CommandResult() == Rhino.Commands.Result.Success:
        return default
    return None


def _create_offset_surface(
    brep: Rhino.Geometry.Brep,
    offset_distance: float,
    tolerance: float,
) -> Optional[Rhino.Geometry.Brep]:
    """Create an offset surface from a brep at the given distance."""
    offsets = Rhino.Geometry.Brep.CreateOffsetBrep(
        brep, offset_distance, True, True, tolerance
    )
    if offsets and len(offsets) > 0:
        return offsets[0]
    return None


def _create_bottom_outline(
    brep: Rhino.Geometry.Brep,
    z_offset: float,
    tolerance: float,
) -> List[Rhino.Geometry.Curve]:
    """Extract the bottom outline of a brep at the given Z level.

    Uses a single cross-section plane at the specified Z offset above the
    bounding-box minimum.  When multiple contour curves are returned, only
    the largest (by area) is kept so the insole matches the outer sole
    outline rather than any interior features.
    """
    bbox = brep.GetBoundingBox(True)
    z_level = bbox.Min.Z + z_offset

    # Use a cutting plane instead of contour intervals to get exactly one slice
    cut_plane = Rhino.Geometry.Plane(
        Rhino.Geometry.Point3d(0, 0, z_level),
        Rhino.Geometry.Vector3d.ZAxis,
    )
    curves = Rhino.Geometry.Brep.CreateContourCurves(
        brep, cut_plane
    )

    if not curves or len(curves) == 0:
        return []

    # Keep only the largest closed curve (the outer sole outline)
    closed = [c for c in curves if c.IsClosed]
    if closed:
        largest = max(closed, key=lambda c: abs(Rhino.Geometry.AreaMassProperties.Compute(c).Area))
        return [largest]

    return [curves[0]]


def _extrude_curves_to_brep(
    curves: List[Rhino.Geometry.Curve],
    direction: Rhino.Geometry.Vector3d,
    cap: bool = True,
) -> Optional[Rhino.Geometry.Brep]:
    """Extrude curves along a direction to form a brep."""
    breps: List[Rhino.Geometry.Brep] = []
    for curve in curves:
        surface = Rhino.Geometry.Surface.CreateExtrusion(curve, direction)
        if surface is not None:
            brep = surface.ToBrep()
            if brep is not None:
                if cap:
                    capped = brep.CapPlanarHoles(0.01)
                    breps.append(capped if capped else brep)
                else:
                    breps.append(brep)
    if breps:
        joined = Rhino.Geometry.Brep.JoinBreps(breps, 0.01)
        if joined and len(joined) > 0:
            return joined[0]
        return breps[0]
    return None


# ---------------------------------------------------------------------------
#  CreateInsole
# ---------------------------------------------------------------------------

class CreateInsole(Rhino.Commands.Command):
    """Create insole geometry from last."""

    _instance: CreateInsole | None = None

    def __init__(self):
        super().__init__()
        CreateInsole._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateInsole | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateInsole"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)
        tol = doc.ModelAbsoluteTolerance

        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found. Build a last first.")
            return Rhino.Commands.Result.Failure

        thickness = _prompt_float("Insole thickness (mm)", settings.insert_thickness_mm)
        if thickness is None:
            return Rhino.Commands.Result.Cancel

        top_cover = _prompt_float("Top cover thickness (mm)", settings.insert_top_cover_mm)
        if top_cover is None:
            return Rhino.Commands.Result.Cancel

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating insole...")

        bbox = last_brep.GetBoundingBox(True)
        last_height = bbox.Max.Z - bbox.Min.Z

        # Section the last near the bottom to get the sole outline.
        # Use 5% of the last height as the slice level — high enough to
        # capture the full sole outline, not just the very tip.
        sole_offset = max(last_height * 0.05, 2.0)
        bottom_curves = _create_bottom_outline(last_brep, sole_offset, tol)
        if not bottom_curves:
            # Fallback: create an outline from the bounding box bottom
            center = Rhino.Geometry.Point3d(
                (bbox.Min.X + bbox.Max.X) * 0.5,
                (bbox.Min.Y + bbox.Max.Y) * 0.5,
                bbox.Min.Z,
            )
            length = bbox.Max.Y - bbox.Min.Y
            width = bbox.Max.X - bbox.Min.X
            plane = Rhino.Geometry.Plane(center, Rhino.Geometry.Vector3d.ZAxis)
            ellipse = Rhino.Geometry.Ellipse(plane, width * 0.5, length * 0.5)
            bottom_curves = [ellipse.ToNurbsCurve()]

        # Extrude downward to create the insole body
        direction = Rhino.Geometry.Vector3d(0, 0, -thickness)
        insole_brep = _extrude_curves_to_brep(bottom_curves, direction, cap=True)

        if insole_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to create insole geometry.")
            return Rhino.Commands.Result.Failure

        # Position at bottom of last
        move = Rhino.Geometry.Transform.Translation(0, 0, bbox.Min.Z - top_cover)
        insole_brep.Transform(move)

        guid = _add_component(doc, insole_brep, plugin_constants.CLASS_INSERT, "SLM_Insole")
        if guid == System.Guid.Empty:
            return Rhino.Commands.Result.Failure

        plug.StoreGeometry(doc, "InsoleBrep", insole_brep)
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Insole created: {thickness}mm thick, {top_cover}mm top cover."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateSole
# ---------------------------------------------------------------------------

class CreateSole(Rhino.Commands.Command):
    """Create sole geometry."""

    _instance: CreateSole | None = None

    def __init__(self):
        super().__init__()
        CreateSole._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateSole | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateSole"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)
        tol = doc.ModelAbsoluteTolerance

        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        thickness = _prompt_float("Sole thickness (mm)", settings.bottom_thickness_mm)
        if thickness is None:
            return Rhino.Commands.Result.Cancel

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating sole...")

        bbox = last_brep.GetBoundingBox(True)
        bottom_curves = _create_bottom_outline(last_brep, tol, tol)

        if not bottom_curves:
            center = Rhino.Geometry.Point3d(
                (bbox.Min.X + bbox.Max.X) * 0.5,
                (bbox.Min.Y + bbox.Max.Y) * 0.5,
                bbox.Min.Z,
            )
            length = bbox.Max.Y - bbox.Min.Y
            width = bbox.Max.X - bbox.Min.X
            plane = Rhino.Geometry.Plane(center, Rhino.Geometry.Vector3d.ZAxis)
            ellipse = Rhino.Geometry.Ellipse(plane, width * 0.50, length * 0.50)
            bottom_curves = [ellipse.ToNurbsCurve()]

        # Offset curves outward slightly for sole flange
        offset_curves: List[Rhino.Geometry.Curve] = []
        for crv in bottom_curves:
            offsets = crv.Offset(
                Rhino.Geometry.Plane.WorldXY,
                2.0,  # 2mm flange
                tol,
                Rhino.Geometry.CurveOffsetCornerStyle.Sharp,
            )
            if offsets and len(offsets) > 0:
                offset_curves.extend(offsets)
            else:
                offset_curves.append(crv)

        direction = Rhino.Geometry.Vector3d(0, 0, -thickness)
        sole_brep = _extrude_curves_to_brep(offset_curves, direction, cap=True)

        if sole_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to create sole geometry.")
            return Rhino.Commands.Result.Failure

        # Position below the insole
        insole_bottom = bbox.Min.Z - settings.insert_thickness_mm
        move = Rhino.Geometry.Transform.Translation(0, 0, insole_bottom)
        sole_brep.Transform(move)

        guid = _add_component(doc, sole_brep, plugin_constants.CLASS_BOTTOM, "SLM_Sole")
        if guid == System.Guid.Empty:
            return Rhino.Commands.Result.Failure

        plug.StoreGeometry(doc, "SoleBrep", sole_brep)
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Sole created: {thickness}mm thick.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateHeel
# ---------------------------------------------------------------------------

class CreateHeel(Rhino.Commands.Command):
    """Create heel geometry."""

    _instance: CreateHeel | None = None

    def __init__(self):
        super().__init__()
        CreateHeel._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateHeel | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateHeel"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)
        tol = doc.ModelAbsoluteTolerance

        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        heel_height = _prompt_float("Heel height (mm)", settings.last_heel_height_mm)
        if heel_height is None:
            return Rhino.Commands.Result.Cancel

        if heel_height <= 0:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Heel height must be positive.")
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating heel...")

        bbox = last_brep.GetBoundingBox(True)
        heel_length = (bbox.Max.Y - bbox.Min.Y) * 0.30  # heel region ~30% of length
        heel_width = (bbox.Max.X - bbox.Min.X) * 0.65

        # Create a heel block
        heel_center = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            bbox.Min.Y + heel_length * 0.5,
            bbox.Min.Z - heel_height * 0.5,
        )
        heel_plane = Rhino.Geometry.Plane(heel_center, Rhino.Geometry.Vector3d.ZAxis)

        # Tapered heel: narrower at bottom
        top_ellipse = Rhino.Geometry.Ellipse(
            Rhino.Geometry.Plane(
                Rhino.Geometry.Point3d(heel_center.X, heel_center.Y, bbox.Min.Z),
                Rhino.Geometry.Vector3d.ZAxis,
            ),
            heel_width * 0.5,
            heel_length * 0.5,
        )
        bottom_ellipse = Rhino.Geometry.Ellipse(
            Rhino.Geometry.Plane(
                Rhino.Geometry.Point3d(heel_center.X, heel_center.Y, bbox.Min.Z - heel_height),
                Rhino.Geometry.Vector3d.ZAxis,
            ),
            heel_width * 0.45,  # slight taper
            heel_length * 0.45,
        )

        top_crv = top_ellipse.ToNurbsCurve()
        bottom_crv = bottom_ellipse.ToNurbsCurve()

        if top_crv is None or bottom_crv is None:
            return Rhino.Commands.Result.Failure

        loft = Rhino.Geometry.Brep.CreateFromLoft(
            [bottom_crv, top_crv],
            Rhino.Geometry.Point3d.Unset,
            Rhino.Geometry.Point3d.Unset,
            Rhino.Geometry.LoftType.Straight,
            False,
        )
        if not loft or len(loft) == 0:
            return Rhino.Commands.Result.Failure

        heel_brep = loft[0].CapPlanarHoles(tol)
        if heel_brep is None:
            heel_brep = loft[0]

        guid = _add_component(doc, heel_brep, plugin_constants.CLASS_BOTTOM, "SLM_Heel")
        if guid == System.Guid.Empty:
            return Rhino.Commands.Result.Failure

        plug.StoreGeometry(doc, "HeelBrep", heel_brep)
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Heel created: {heel_height}mm high.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateHeelParts
# ---------------------------------------------------------------------------

class CreateHeelParts(Rhino.Commands.Command):
    """Create heel sub-components (lifts/layers)."""

    _instance: CreateHeelParts | None = None

    def __init__(self):
        super().__init__()
        CreateHeelParts._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateHeelParts | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateHeelParts"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)
        tol = doc.ModelAbsoluteTolerance

        heel_height = settings.last_heel_height_mm
        if heel_height <= 0:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No heel height set. Create a heel first.")
            return Rhino.Commands.Result.Failure

        num_lifts = _prompt_float("Number of heel lifts", 3.0)
        if num_lifts is None:
            return Rhino.Commands.Result.Cancel
        num_lifts = max(1, int(num_lifts))

        lift_height = heel_height / num_lifts

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Creating {num_lifts} heel lifts ({lift_height:.1f}mm each)..."
        )

        # Get the stored heel or approximate from bounding box
        heel_geom = plug.GetGeometryFromStoredString(doc, "HeelBrep")
        if heel_geom is None or not isinstance(heel_geom, Rhino.Geometry.Brep):
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No heel geometry found. Run CreateHeel first.")
            return Rhino.Commands.Result.Failure

        bbox = heel_geom.GetBoundingBox(True)

        for i in range(num_lifts):
            z_bottom = bbox.Min.Z + i * lift_height
            z_top = z_bottom + lift_height

            # Create cross-sections at top and bottom of this lift
            cut_plane_bottom = Rhino.Geometry.Plane(
                Rhino.Geometry.Point3d(0, 0, z_bottom),
                Rhino.Geometry.Vector3d.ZAxis,
            )
            cut_plane_top = Rhino.Geometry.Plane(
                Rhino.Geometry.Point3d(0, 0, z_top),
                Rhino.Geometry.Vector3d.ZAxis,
            )

            # Split and trim the heel brep to this slice
            curves_bottom = Rhino.Geometry.Brep.CreateContourCurves(
                heel_geom,
                Rhino.Geometry.Point3d(0, 0, z_bottom),
                Rhino.Geometry.Point3d(0, 0, z_bottom + 0.01),
                tol,
            )
            if curves_bottom:
                direction = Rhino.Geometry.Vector3d(0, 0, lift_height)
                lift_brep = _extrude_curves_to_brep(list(curves_bottom), direction, cap=True)
                if lift_brep is not None:
                    name = f"SLM_HeelLift_{i + 1:02d}"
                    _add_component(doc, lift_brep, plugin_constants.CLASS_BOTTOM, name)

        plug.MarkDocumentDirty()
        Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] {num_lifts} heel lift(s) created.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateTopPiece
# ---------------------------------------------------------------------------

class CreateTopPiece(Rhino.Commands.Command):
    """Create top piece (heel bottom contact surface)."""

    _instance: CreateTopPiece | None = None

    def __init__(self):
        super().__init__()
        CreateTopPiece._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateTopPiece | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateTopPiece"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        tol = doc.ModelAbsoluteTolerance

        thickness = _prompt_float("Top piece thickness (mm)", 4.0)
        if thickness is None:
            return Rhino.Commands.Result.Cancel

        heel_geom = plug.GetGeometryFromStoredString(doc, "HeelBrep")
        if heel_geom is None or not isinstance(heel_geom, Rhino.Geometry.Brep):
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No heel geometry. Create a heel first.")
            return Rhino.Commands.Result.Failure

        bbox = heel_geom.GetBoundingBox(True)

        # Get bottom outline of heel
        bottom_curves = Rhino.Geometry.Brep.CreateContourCurves(
            heel_geom,
            Rhino.Geometry.Point3d(0, 0, bbox.Min.Z),
            Rhino.Geometry.Point3d(0, 0, bbox.Min.Z + 0.01),
            tol,
        )
        if not bottom_curves:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Cannot extract heel bottom outline.")
            return Rhino.Commands.Result.Failure

        direction = Rhino.Geometry.Vector3d(0, 0, -thickness)
        tp_brep = _extrude_curves_to_brep(list(bottom_curves), direction, cap=True)
        if tp_brep is None:
            return Rhino.Commands.Result.Failure

        move = Rhino.Geometry.Transform.Translation(0, 0, bbox.Min.Z)
        tp_brep.Transform(move)

        _add_component(doc, tp_brep, plugin_constants.CLASS_BOTTOM, "SLM_TopPiece")
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Top piece created: {thickness}mm.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateShankBoard
# ---------------------------------------------------------------------------

class CreateShankBoard(Rhino.Commands.Command):
    """Create shank board (structural support between heel and ball)."""

    _instance: CreateShankBoard | None = None

    def __init__(self):
        super().__init__()
        CreateShankBoard._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateShankBoard | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateShankBoard"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        tol = doc.ModelAbsoluteTolerance

        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        thickness = _prompt_float("Shank board thickness (mm)", 2.0)
        if thickness is None:
            return Rhino.Commands.Result.Cancel

        width = _prompt_float("Shank board width (mm)", 20.0)
        if width is None:
            return Rhino.Commands.Result.Cancel

        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y

        # Shank region: ~30% to ~55% of last length from heel
        y_start = bbox.Min.Y + last_length * 0.30
        y_end = bbox.Min.Y + last_length * 0.55
        shank_length = y_end - y_start

        center_x = (bbox.Min.X + bbox.Max.X) * 0.5
        z_pos = bbox.Min.Z

        # Create a rectangular shank board
        corner = Rhino.Geometry.Point3d(center_x - width / 2, y_start, z_pos)
        plane = Rhino.Geometry.Plane(corner, Rhino.Geometry.Vector3d.ZAxis)
        rect = Rhino.Geometry.Rectangle3d(
            plane, shank_length, width
        )
        # Build from interval
        rect_plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(center_x, (y_start + y_end) / 2, z_pos),
            Rhino.Geometry.Vector3d.ZAxis,
        )
        rect = Rhino.Geometry.Rectangle3d(
            rect_plane,
            Rhino.Geometry.Interval(-width / 2, width / 2),
            Rhino.Geometry.Interval(-shank_length / 2, shank_length / 2),
        )
        rect_curve = rect.ToNurbsCurve()

        direction = Rhino.Geometry.Vector3d(0, 0, -thickness)
        shank_brep = _extrude_curves_to_brep([rect_curve], direction, cap=True)

        if shank_brep is None:
            return Rhino.Commands.Result.Failure

        _add_component(doc, shank_brep, plugin_constants.CLASS_BOTTOM, "SLM_ShankBoard")
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Shank board created: {width}mm x {shank_length:.1f}mm x {thickness}mm."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateMetPad
# ---------------------------------------------------------------------------

class CreateMetPad(Rhino.Commands.Command):
    """Create metatarsal pad."""

    _instance: CreateMetPad | None = None

    def __init__(self):
        super().__init__()
        CreateMetPad._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateMetPad | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateMetPad"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        height = _prompt_float("Met pad height (mm)", 6.0)
        if height is None:
            return Rhino.Commands.Result.Cancel

        diameter = _prompt_float("Met pad diameter (mm)", 30.0)
        if diameter is None:
            return Rhino.Commands.Result.Cancel

        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y

        # Met pad location: ~55% of last length, slightly medial
        met_center = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5 + 2.0,  # slightly medial offset
            bbox.Min.Y + last_length * 0.55,
            bbox.Min.Z,
        )

        # Create a dome shape (hemisphere)
        sphere = Rhino.Geometry.Sphere(met_center, diameter / 2)
        sphere_brep = sphere.ToBrep()

        # Trim to desired height using a cutting plane
        cut_plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(met_center.X, met_center.Y, met_center.Z + height),
            Rhino.Geometry.Vector3d.ZAxis,
        )

        # Split and keep the bottom portion
        if sphere_brep is not None:
            splits = sphere_brep.Trim(cut_plane, doc.ModelAbsoluteTolerance)
            if splits and len(splits) > 0:
                met_brep = splits[0]
                capped = met_brep.CapPlanarHoles(doc.ModelAbsoluteTolerance)
                if capped:
                    met_brep = capped
            else:
                met_brep = sphere_brep
        else:
            return Rhino.Commands.Result.Failure

        _add_component(doc, met_brep, plugin_constants.CLASS_INSERT, "SLM_MetPad")
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Met pad created: {diameter}mm diameter, {height}mm height."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateToeCrest
# ---------------------------------------------------------------------------

class CreateToeCrest(Rhino.Commands.Command):
    """Create toe crest."""

    _instance: CreateToeCrest | None = None

    def __init__(self):
        super().__init__()
        CreateToeCrest._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateToeCrest | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateToeCrest"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        height = _prompt_float("Toe crest height (mm)", 5.0)
        if height is None:
            return Rhino.Commands.Result.Cancel

        width = _prompt_float("Toe crest width (mm)", 40.0)
        if width is None:
            return Rhino.Commands.Result.Cancel

        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y

        # Toe crest: positioned just behind toe area ~75% of length
        center = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            bbox.Min.Y + last_length * 0.75,
            bbox.Min.Z,
        )

        # Create a curved crest shape using an arc cross-section
        plane = Rhino.Geometry.Plane(center, Rhino.Geometry.Vector3d.YAxis)
        arc = Rhino.Geometry.Arc(plane, width / 2, math.pi)
        arc_curve = Rhino.Geometry.ArcCurve(arc)

        # Extrude along Y to create width
        direction = Rhino.Geometry.Vector3d(0, 10.0, 0)  # 10mm depth
        extrusion = Rhino.Geometry.Surface.CreateExtrusion(arc_curve.ToNurbsCurve(), direction)
        if extrusion is not None:
            brep = extrusion.ToBrep()
            if brep is not None:
                capped = brep.CapPlanarHoles(doc.ModelAbsoluteTolerance)
                if capped:
                    brep = capped
                # Scale Z to desired height
                scale = Rhino.Geometry.Transform.Scale(
                    center, 1.0, 1.0, height / (width / 2) if width > 0 else 1.0
                )
                brep.Transform(scale)

                _add_component(doc, brep, plugin_constants.CLASS_INSERT, "SLM_ToeCrest")
                plug.MarkDocumentDirty()

                Rhino.RhinoApp.WriteLine(
                    f"[Feet in Focus Shoe Kit] Toe crest created: {width}mm wide, {height}mm high."
                )
                return Rhino.Commands.Result.Success

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to create toe crest.")
        return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  CreateToeRidge
# ---------------------------------------------------------------------------

class CreateToeRidge(Rhino.Commands.Command):
    """Create toe ridge."""

    _instance: CreateToeRidge | None = None

    def __init__(self):
        super().__init__()
        CreateToeRidge._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateToeRidge | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateToeRidge"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        height = _prompt_float("Toe ridge height (mm)", 3.0)
        if height is None:
            return Rhino.Commands.Result.Cancel

        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y

        # Ridge runs along the top of the toe area
        ridge_start = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            bbox.Min.Y + last_length * 0.70,
            bbox.Min.Z + height,
        )
        ridge_end = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            bbox.Min.Y + last_length * 0.90,
            bbox.Min.Z + height * 0.5,
        )

        # Create a tube along the ridge line
        line = Rhino.Geometry.Line(ridge_start, ridge_end)
        circle = Rhino.Geometry.Circle(
            Rhino.Geometry.Plane(ridge_start, line.Direction),
            height / 2,
        )
        pipe = Rhino.Geometry.Brep.CreatePipe(
            Rhino.Geometry.LineCurve(line),
            height / 2,
            False,
            Rhino.Geometry.PipeCapMode.Round,
            True,
            doc.ModelAbsoluteTolerance,
            doc.ModelAngleToleranceRadians,
        )
        if pipe and len(pipe) > 0:
            _add_component(doc, pipe[0], plugin_constants.CLASS_INSERT, "SLM_ToeRidge")
            plug.MarkDocumentDirty()
            Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Toe ridge created: {height}mm high.")
            return Rhino.Commands.Result.Success

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to create toe ridge.")
        return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  CreateThongHole
# ---------------------------------------------------------------------------

class CreateThongHole(Rhino.Commands.Command):
    """Create thong hole for sandals."""

    _instance: CreateThongHole | None = None

    def __init__(self):
        super().__init__()
        CreateThongHole._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateThongHole | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateThongHole"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        diameter = _prompt_float("Thong hole diameter (mm)", 6.0)
        if diameter is None:
            return Rhino.Commands.Result.Cancel

        # Allow user to pick a point or use default position
        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt("Pick thong hole location (or Enter for default)")
        gp.AcceptNothing(True)
        result = gp.Get()

        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y

        if result == Rhino.Input.GetResult.Point:
            hole_center = gp.Point()
        else:
            # Default: between 1st and 2nd toe ~80% of length
            hole_center = Rhino.Geometry.Point3d(
                (bbox.Min.X + bbox.Max.X) * 0.5,
                bbox.Min.Y + last_length * 0.80,
                bbox.Min.Z,
            )

        # Create a cylinder for the hole (boolean subtraction reference)
        axis = Rhino.Geometry.Vector3d.ZAxis
        circle = Rhino.Geometry.Circle(
            Rhino.Geometry.Plane(hole_center, axis),
            diameter / 2,
        )
        cylinder = Rhino.Geometry.Cylinder(circle, bbox.Max.Z - bbox.Min.Z + 10)
        cyl_brep = cylinder.ToBrep(True, True)

        if cyl_brep is not None:
            _add_component(doc, cyl_brep, "Construction", "SLM_ThongHole")
            plug.MarkDocumentDirty()
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] Thong hole created: {diameter}mm diameter at "
                f"({hole_center.X:.1f}, {hole_center.Y:.1f})."
            )
            return Rhino.Commands.Result.Success

        return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  CreatePinHole
# ---------------------------------------------------------------------------

class CreatePinHole(Rhino.Commands.Command):
    """Create pin hole."""

    _instance: CreatePinHole | None = None

    def __init__(self):
        super().__init__()
        CreatePinHole._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreatePinHole | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreatePinHole"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        diameter = _prompt_float("Pin hole diameter (mm)", 8.0)
        if diameter is None:
            return Rhino.Commands.Result.Cancel

        depth = _prompt_float("Pin hole depth (mm)", 25.0)
        if depth is None:
            return Rhino.Commands.Result.Cancel

        # Pin hole at heel center top
        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y
        pin_center = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            bbox.Min.Y + last_length * 0.10,  # near heel
            bbox.Max.Z,
        )

        # Create cylinder going downward
        axis = Rhino.Geometry.Vector3d(0, 0, -1)
        circle = Rhino.Geometry.Circle(
            Rhino.Geometry.Plane(pin_center, Rhino.Geometry.Vector3d.ZAxis),
            diameter / 2,
        )
        cylinder = Rhino.Geometry.Cylinder(circle, depth)
        cyl_brep = cylinder.ToBrep(True, True)

        if cyl_brep is not None:
            # Move so the cylinder goes downward from the top
            move = Rhino.Geometry.Transform.Translation(0, 0, -depth)
            cyl_brep.Transform(move)

            _add_component(doc, cyl_brep, "Construction", "SLM_PinHole")
            plug.MarkDocumentDirty()
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] Pin hole created: {diameter}mm x {depth}mm."
            )
            return Rhino.Commands.Result.Success

        return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  CreateShoeTree
# ---------------------------------------------------------------------------

class CreateShoeTree(Rhino.Commands.Command):
    """Create shoe tree from last geometry."""

    _instance: CreateShoeTree | None = None

    def __init__(self):
        super().__init__()
        CreateShoeTree._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateShoeTree | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateShoeTree"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        tol = doc.ModelAbsoluteTolerance

        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        clearance = _prompt_float("Shoe tree clearance/offset (mm)", -2.0)
        if clearance is None:
            return Rhino.Commands.Result.Cancel

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating shoe tree...")

        # Offset the last inward to create the tree shape
        tree_brep = _create_offset_surface(last_brep, clearance, tol)
        if tree_brep is None:
            # Fallback: scale slightly smaller
            tree_brep = last_brep.Duplicate()
            bbox = last_brep.GetBoundingBox(True)
            center = bbox.Center
            scale_factor = 1.0 + (clearance / max(bbox.Diagonal.Length, 1.0))
            scale = Rhino.Geometry.Transform.Scale(center, scale_factor)
            tree_brep.Transform(scale)

        # Split the shoe tree at the waist for a two-piece tree
        bbox = tree_brep.GetBoundingBox(True) if isinstance(tree_brep, Rhino.Geometry.Brep) else last_brep.GetBoundingBox(True)
        split_y = bbox.Min.Y + (bbox.Max.Y - bbox.Min.Y) * 0.45

        _add_component(doc, tree_brep, plugin_constants.CLASS_LAST, "SLM_ShoeTree")
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Shoe tree created with {clearance}mm offset."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateUpperBodies
# ---------------------------------------------------------------------------

class CreateUpperBodies(Rhino.Commands.Command):
    """Create upper body components (vamp, quarter, tongue, etc.)."""

    _instance: CreateUpperBodies | None = None

    def __init__(self):
        super().__init__()
        CreateUpperBodies._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateUpperBodies | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateUpperBodies"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)
        tol = doc.ModelAbsoluteTolerance

        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        # Select which upper components to create
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Upper component (Vamp/Quarter/Tongue/Counter/All)")
        gs.SetDefaultString("All")
        gs.AcceptNothing(True)
        gs.Get()

        component = "All"
        if gs.CommandResult() == Rhino.Commands.Result.Success and gs.StringResult():
            component = gs.StringResult().strip()

        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y
        created: List[str] = []

        # Upper components are defined as offset surfaces from the last
        # with specific region masks

        if component in ("Vamp", "All"):
            # Vamp: covers the forefoot
            vamp_brep = _create_offset_surface(last_brep, 1.5, tol)
            if vamp_brep is not None:
                _add_component(doc, vamp_brep, plugin_constants.CLASS_LAST, "SLM_Upper_Vamp")
                created.append("Vamp")

        if component in ("Quarter", "All"):
            # Quarter: covers the sides and back
            quarter_brep = _create_offset_surface(last_brep, 1.5, tol)
            if quarter_brep is not None:
                _add_component(doc, quarter_brep, plugin_constants.CLASS_LAST, "SLM_Upper_Quarter")
                created.append("Quarter")

        if component in ("Tongue", "All"):
            # Tongue: flat piece on top
            tongue_center = Rhino.Geometry.Point3d(
                (bbox.Min.X + bbox.Max.X) * 0.5,
                bbox.Min.Y + last_length * 0.55,
                bbox.Max.Z + 1.5,
            )
            tongue_plane = Rhino.Geometry.Plane(
                tongue_center, Rhino.Geometry.Vector3d.ZAxis
            )
            tongue_width = (bbox.Max.X - bbox.Min.X) * 0.35
            tongue_length = last_length * 0.30
            rect = Rhino.Geometry.Rectangle3d(
                tongue_plane,
                Rhino.Geometry.Interval(-tongue_width / 2, tongue_width / 2),
                Rhino.Geometry.Interval(-tongue_length / 2, tongue_length / 2),
            )
            tongue_curve = rect.ToNurbsCurve()
            tongue_dir = Rhino.Geometry.Vector3d(0, 0, 2.0)
            tongue_brep = _extrude_curves_to_brep([tongue_curve], tongue_dir, cap=True)
            if tongue_brep is not None:
                _add_component(doc, tongue_brep, plugin_constants.CLASS_LAST, "SLM_Upper_Tongue")
                created.append("Tongue")

        if component in ("Counter", "All"):
            # Counter: heel stiffener
            counter_brep = _create_offset_surface(last_brep, 0.8, tol)
            if counter_brep is not None:
                _add_component(doc, counter_brep, plugin_constants.CLASS_LAST, "SLM_Upper_Counter")
                created.append("Counter")

        plug.MarkDocumentDirty()

        if created:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] Upper components created: {', '.join(created)}."
            )
            return Rhino.Commands.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No upper components created.")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  MakeComponent
# ---------------------------------------------------------------------------

class MakeComponent(Rhino.Commands.Command):
    """Generic component creation command."""

    _instance: MakeComponent | None = None

    def __init__(self):
        super().__init__()
        MakeComponent._instance = self

    @classmethod
    @property
    def Instance(cls) -> MakeComponent | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "MakeComponent"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        # Prompt for component type
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Component type name")
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        comp_type = gs.StringResult().strip()
        if not comp_type:
            return Rhino.Commands.Result.Cancel

        # Select source geometry
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt(f"Select geometry for '{comp_type}' component")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.AnyObject
        go.GetMultiple(1, 0)
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        plug = _get_plugin()

        # Prompt for target layer
        layer_suffix = _prompt_string(
            f"Target layer (Last/Insert/Bottom/Foot/Construction)",
            plugin_constants.CLASS_LAST,
        )
        if layer_suffix is None:
            return Rhino.Commands.Result.Cancel

        comp_name = f"SLM_{comp_type}"
        created_count = 0

        for i in range(go.ObjectCount):
            obj_ref = go.Object(i)
            geom = obj_ref.Geometry()
            if geom is not None:
                dup = geom.Duplicate()
                name = f"{comp_name}_{i:02d}" if go.ObjectCount > 1 else comp_name
                _add_component(doc, dup, layer_suffix, name)
                created_count += 1

        plug.MarkDocumentDirty()
        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Component '{comp_type}' created from {created_count} object(s)."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateAlphaJoint
# ---------------------------------------------------------------------------

class CreateAlphaJoint(Rhino.Commands.Command):
    """
    Create alpha joint assembly.

    Alpha joints are mechanical joints used in orthopedic footwear to allow
    ankle articulation. This creates the joint housing with slippage
    compensation, rail recess, and clearance geometry.
    """

    _instance: CreateAlphaJoint | None = None

    def __init__(self):
        super().__init__()
        CreateAlphaJoint._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateAlphaJoint | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateAlphaJoint"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        tol = doc.ModelAbsoluteTolerance

        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        # Joint parameters
        joint_width = _prompt_float("Joint width (mm)", 12.0)
        if joint_width is None:
            return Rhino.Commands.Result.Cancel

        joint_height = _prompt_float("Joint height (mm)", 30.0)
        if joint_height is None:
            return Rhino.Commands.Result.Cancel

        slippage_comp = _prompt_float("Slippage compensation (mm)", 0.5)
        if slippage_comp is None:
            return Rhino.Commands.Result.Cancel

        rail_recess = _prompt_float("Rail recess depth (mm)", 2.0)
        if rail_recess is None:
            return Rhino.Commands.Result.Cancel

        clearance = _prompt_float("Clearance (mm)", 0.3)
        if clearance is None:
            return Rhino.Commands.Result.Cancel

        # Allow point pick or default position
        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt("Pick joint location (or Enter for default medial)")
        gp.AcceptNothing(True)
        result = gp.Get()

        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y

        if result == Rhino.Input.GetResult.Point:
            joint_center = gp.Point()
        else:
            # Default: medial ankle position
            joint_center = Rhino.Geometry.Point3d(
                bbox.Max.X + 1.0,
                bbox.Min.Y + last_length * 0.25,
                bbox.Min.Z + (bbox.Max.Z - bbox.Min.Z) * 0.5,
            )

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating alpha joint assembly...")

        # Main joint housing plate
        plate_plane = Rhino.Geometry.Plane(
            joint_center, Rhino.Geometry.Vector3d.XAxis
        )
        plate_rect = Rhino.Geometry.Rectangle3d(
            plate_plane,
            Rhino.Geometry.Interval(-joint_width / 2, joint_width / 2),
            Rhino.Geometry.Interval(-joint_height / 2, joint_height / 2),
        )
        plate_curve = plate_rect.ToNurbsCurve()
        plate_dir = Rhino.Geometry.Vector3d(3.0, 0, 0)  # 3mm thick plate
        plate_brep = _extrude_curves_to_brep([plate_curve], plate_dir, cap=True)

        if plate_brep is not None:
            _add_component(doc, plate_brep, "Construction", "SLM_AlphaJoint_Plate")

        # Rail recess channel
        recess_center = Rhino.Geometry.Point3d(
            joint_center.X + 3.0,
            joint_center.Y,
            joint_center.Z,
        )
        recess_plane = Rhino.Geometry.Plane(
            recess_center, Rhino.Geometry.Vector3d.XAxis
        )
        recess_rect = Rhino.Geometry.Rectangle3d(
            recess_plane,
            Rhino.Geometry.Interval(-joint_width * 0.3, joint_width * 0.3),
            Rhino.Geometry.Interval(-joint_height * 0.8 / 2, joint_height * 0.8 / 2),
        )
        recess_curve = recess_rect.ToNurbsCurve()
        recess_dir = Rhino.Geometry.Vector3d(rail_recess, 0, 0)
        recess_brep = _extrude_curves_to_brep([recess_curve], recess_dir, cap=True)

        if recess_brep is not None:
            _add_component(doc, recess_brep, "Construction", "SLM_AlphaJoint_RailRecess")

        # Clearance zone (larger bounding volume for boolean operations)
        clearance_box = Rhino.Geometry.Box(
            Rhino.Geometry.Plane(joint_center, Rhino.Geometry.Vector3d.XAxis),
            Rhino.Geometry.Interval(
                -(joint_width / 2 + clearance), joint_width / 2 + clearance
            ),
            Rhino.Geometry.Interval(
                -(joint_height / 2 + clearance), joint_height / 2 + clearance
            ),
            Rhino.Geometry.Interval(-(slippage_comp + clearance), 3.0 + rail_recess + clearance),
        )
        clearance_brep = Rhino.Geometry.Brep.CreateFromBox(clearance_box)
        if clearance_brep is not None:
            _add_component(doc, clearance_brep, "Construction", "SLM_AlphaJoint_Clearance")

        # Pivot pin hole
        pin_circle = Rhino.Geometry.Circle(
            Rhino.Geometry.Plane(joint_center, Rhino.Geometry.Vector3d.XAxis),
            2.5,  # 5mm diameter pivot pin
        )
        pin_cyl = Rhino.Geometry.Cylinder(pin_circle, 10.0)
        pin_brep = pin_cyl.ToBrep(True, True)
        if pin_brep is not None:
            move = Rhino.Geometry.Transform.Translation(-5, 0, 0)
            pin_brep.Transform(move)
            _add_component(doc, pin_brep, "Construction", "SLM_AlphaJoint_PivotHole")

        plug.MarkDocumentDirty()
        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Alpha joint assembly created: "
            f"{joint_width}x{joint_height}mm, "
            f"slippage={slippage_comp}mm, recess={rail_recess}mm, "
            f"clearance={clearance}mm."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateRailGuideJoint
# ---------------------------------------------------------------------------

class CreateRailGuideJoint(Rhino.Commands.Command):
    """
    Create rail guide joint assembly.

    Rail guide joints provide linear motion constraint for AFO/KAFO
    orthopedic devices. Creates the rail channel, guide pin, and mounting
    plate geometry.
    """

    _instance: CreateRailGuideJoint | None = None

    def __init__(self):
        super().__init__()
        CreateRailGuideJoint._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateRailGuideJoint | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateRailGuideJoint"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        tol = doc.ModelAbsoluteTolerance

        last_brep = _get_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        # Parameters
        rail_length = _prompt_float("Rail length (mm)", 50.0)
        if rail_length is None:
            return Rhino.Commands.Result.Cancel

        rail_width = _prompt_float("Rail channel width (mm)", 5.0)
        if rail_width is None:
            return Rhino.Commands.Result.Cancel

        rail_depth = _prompt_float("Rail channel depth (mm)", 3.0)
        if rail_depth is None:
            return Rhino.Commands.Result.Cancel

        # Position
        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt("Pick rail guide location (or Enter for default)")
        gp.AcceptNothing(True)
        result = gp.Get()

        bbox = last_brep.GetBoundingBox(True)
        last_length = bbox.Max.Y - bbox.Min.Y

        if result == Rhino.Input.GetResult.Point:
            rail_center = gp.Point()
        else:
            rail_center = Rhino.Geometry.Point3d(
                bbox.Max.X + 1.0,
                bbox.Min.Y + last_length * 0.25,
                bbox.Min.Z + (bbox.Max.Z - bbox.Min.Z) * 0.5,
            )

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating rail guide joint...")

        # Mounting plate
        plate_plane = Rhino.Geometry.Plane(
            rail_center, Rhino.Geometry.Vector3d.XAxis
        )
        plate_rect = Rhino.Geometry.Rectangle3d(
            plate_plane,
            Rhino.Geometry.Interval(-15, 15),  # 30mm wide plate
            Rhino.Geometry.Interval(-rail_length / 2, rail_length / 2),
        )
        plate_curve = plate_rect.ToNurbsCurve()
        plate_dir = Rhino.Geometry.Vector3d(2.0, 0, 0)
        plate_brep = _extrude_curves_to_brep([plate_curve], plate_dir, cap=True)

        if plate_brep is not None:
            _add_component(doc, plate_brep, "Construction", "SLM_RailGuide_Plate")

        # Rail channel
        channel_plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(rail_center.X + 2.0, rail_center.Y, rail_center.Z),
            Rhino.Geometry.Vector3d.XAxis,
        )
        channel_rect = Rhino.Geometry.Rectangle3d(
            channel_plane,
            Rhino.Geometry.Interval(-rail_width / 2, rail_width / 2),
            Rhino.Geometry.Interval(-rail_length / 2, rail_length / 2),
        )
        channel_curve = channel_rect.ToNurbsCurve()
        channel_dir = Rhino.Geometry.Vector3d(rail_depth, 0, 0)
        channel_brep = _extrude_curves_to_brep([channel_curve], channel_dir, cap=True)

        if channel_brep is not None:
            _add_component(doc, channel_brep, "Construction", "SLM_RailGuide_Channel")

        # Guide pin (cylinder)
        pin_circle = Rhino.Geometry.Circle(
            Rhino.Geometry.Plane(rail_center, Rhino.Geometry.Vector3d.XAxis),
            rail_width * 0.4,
        )
        pin_cyl = Rhino.Geometry.Cylinder(pin_circle, rail_depth + 4.0)
        pin_brep = pin_cyl.ToBrep(True, True)
        if pin_brep is not None:
            _add_component(doc, pin_brep, "Construction", "SLM_RailGuide_Pin")

        plug.MarkDocumentDirty()
        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Rail guide joint created: "
            f"rail {rail_length}x{rail_width}x{rail_depth}mm."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CreateMockup
# ---------------------------------------------------------------------------

class CreateMockup(Rhino.Commands.Command):
    """
    Create a 3D mockup combining last, sole, heel, and insole components.

    Assembles all existing components into a positioned mockup view.
    """

    _instance: CreateMockup | None = None

    def __init__(self):
        super().__init__()
        CreateMockup._instance = self

    @classmethod
    @property
    def Instance(cls) -> CreateMockup | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CreateMockup"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        tol = doc.ModelAbsoluteTolerance

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating 3D Mockup...")

        # Collect all SLM components
        prefix = plugin_constants.SLM_LAYER_PREFIX
        component_count = 0
        mockup_bbox = Rhino.Geometry.BoundingBox.Empty

        enum_settings = Rhino.DocObjects.ObjectEnumeratorSettings()
        enum_settings.DeletedObjects = False

        for obj in doc.Objects.GetObjectList(enum_settings):
            layer = doc.Layers[obj.Attributes.LayerIndex]
            if not layer.FullPath.startswith(prefix):
                continue
            obj_bbox = obj.Geometry.GetBoundingBox(True)
            if obj_bbox.IsValid:
                mockup_bbox.Union(obj_bbox)
            component_count += 1

        if component_count == 0:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No components found for mockup.")
            return Rhino.Commands.Result.Failure

        # Optionally create an exploded/offset mockup copy
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Mockup type (Assembled/Exploded)")
        gs.SetDefaultString("Assembled")
        gs.AcceptNothing(True)
        gs.Get()

        mockup_type = "Assembled"
        if gs.CommandResult() == Rhino.Commands.Result.Success and gs.StringResult():
            mockup_type = gs.StringResult().strip()

        if mockup_type.lower() == "exploded":
            # Create exploded view by duplicating and offsetting each component
            offset_y = 0.0
            spacing = 30.0

            for obj in doc.Objects.GetObjectList(enum_settings):
                layer = doc.Layers[obj.Attributes.LayerIndex]
                if not layer.FullPath.startswith(prefix):
                    continue
                dup = obj.Geometry.Duplicate()
                # Offset each component along X for visibility
                move = Rhino.Geometry.Transform.Translation(
                    mockup_bbox.Diagonal.Length * 1.5, 0, offset_y
                )
                dup.Transform(move)

                attrs = Rhino.DocObjects.ObjectAttributes()
                attrs.Name = f"SLM_Mockup_{obj.Attributes.Name or 'Part'}"
                construction_idx = _get_layer_index(doc, "Construction")
                if construction_idx >= 0:
                    attrs.LayerIndex = construction_idx
                doc.Objects.Add(dup, attrs)
                offset_y += spacing

        # Set view to show the full mockup
        view = doc.Views.ActiveView
        if view is not None and mockup_bbox.IsValid:
            vp = view.ActiveViewport
            target = mockup_bbox.Center
            diag = mockup_bbox.Diagonal.Length
            camera = target + Rhino.Geometry.Vector3d(diag * 0.8, -diag * 1.0, diag * 0.5)
            vp.SetCameraTarget(target, True)
            vp.SetCameraLocation(camera, True)
            vp.Camera35mmLensLength = 50.0

        doc.Views.Redraw()
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Mockup created ({mockup_type}): "
            f"{component_count} component(s) included."
        )
        return Rhino.Commands.Result.Success
