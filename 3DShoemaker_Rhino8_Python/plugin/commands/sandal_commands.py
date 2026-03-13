"""
Feet in Focus Shoe Kit Rhino 8 Plugin - Sandal-specific commands.

Commands:
    BuildSandal             - Creates sandal from last/insert data.
    BuildInsert             - Creates custom insert/footbed.
    AddSandalGroove         - Adds groove to sandal sole.
    AddThongSlot            - Adds thong slot to sandal.
    ToggleThongSlotInclusion - Toggles thong slot visibility/inclusion.
    AddMetpad               - Adds metatarsal pad to insert.
"""

from __future__ import annotations

import math
import traceback
from typing import Any, Dict, List, Optional, Tuple

import Rhino  # type: ignore
import Rhino.Commands  # type: ignore
import Rhino.DocObjects  # type: ignore
import Rhino.Geometry  # type: ignore
import Rhino.Input  # type: ignore
import Rhino.Input.Custom  # type: ignore
import Rhino.RhinoApp  # type: ignore
import Rhino.RhinoDoc  # type: ignore
import scriptcontext as sc  # type: ignore
import System  # type: ignore
import System.Drawing  # type: ignore

import plugin as plugin_constants
from plugin.plugin_main import PodoCADPlugIn
from plugin.preview_module import PreviewConduitClass, PreviewObject, PreviewStyle


# ---------------------------------------------------------------------------
#  Layer / object helpers
# ---------------------------------------------------------------------------

_SANDAL_LAYER = "Sandal"


def _ensure_layer(doc: Rhino.RhinoDoc, name: str, color: Tuple[int, int, int] = (200, 160, 80)) -> int:
    """Ensure SLM::<name> exists and return its index."""
    full_path = f"{plugin_constants.SLM_LAYER_PREFIX}::{name}"
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx >= 0:
        return idx

    parent_idx = doc.Layers.FindByFullPath(plugin_constants.SLM_LAYER_PREFIX, -1)
    if parent_idx < 0:
        parent_layer = Rhino.DocObjects.Layer()
        parent_layer.Name = plugin_constants.SLM_LAYER_PREFIX
        parent_idx = doc.Layers.Add(parent_layer)

    parent_id = doc.Layers[parent_idx].Id
    child = Rhino.DocObjects.Layer()
    child.Name = name
    child.ParentLayerId = parent_id
    child.Color = System.Drawing.Color.FromArgb(*color)
    return doc.Layers.Add(child)


def _find_named_object(
    doc: Rhino.RhinoDoc, name: str
) -> Optional[Rhino.DocObjects.RhinoObject]:
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.NameFilter = name
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        return obj
    return None


def _find_objects_by_prefix(
    doc: Rhino.RhinoDoc, prefix: str
) -> List[Rhino.DocObjects.RhinoObject]:
    results: List[Rhino.DocObjects.RhinoObject] = []
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.DeletedObjects = False
    settings.HiddenObjects = True
    for obj in doc.Objects.GetObjectList(settings):
        name = obj.Attributes.Name or ""
        if name.startswith(prefix):
            results.append(obj)
    return results


def _get_insole_brep(doc: Rhino.RhinoDoc) -> Optional[Rhino.Geometry.Brep]:
    """Retrieve the insole brep from the document."""
    for name in ("Insole", "InsoleTop", "InsoleBottom", "Insert"):
        obj = _find_named_object(doc, name)
        if obj is not None:
            geom = obj.Geometry
            if isinstance(geom, Rhino.Geometry.Brep):
                return geom
    return None


def _get_outline_curve(doc: Rhino.RhinoDoc) -> Optional[Rhino.Geometry.Curve]:
    """Retrieve the last outline curve from the document."""
    for name in ("Outline", "LastOutline", "InsoleOutline"):
        obj = _find_named_object(doc, name)
        if obj is not None:
            geom = obj.Geometry
            if isinstance(geom, Rhino.Geometry.Curve):
                return geom
    return None


# ---------------------------------------------------------------------------
#  Sandal geometry builders
# ---------------------------------------------------------------------------

def _create_sandal_sole(
    outline: Rhino.Geometry.Curve,
    sole_thickness: float,
    midsole_thickness: float,
) -> Optional[Rhino.Geometry.Brep]:
    """Create a sandal sole by extruding the outline curve downward."""
    if outline is None or not outline.IsValid:
        return None

    if not outline.IsClosed:
        outline = outline.DuplicateCurve()
        if not outline.MakeClosed(1.0):
            return None

    # Extrude total sole thickness (outsole + midsole)
    total = sole_thickness + midsole_thickness
    extrusion_vec = Rhino.Geometry.Vector3d(0, 0, -total)
    srf = Rhino.Geometry.Surface.CreateExtrusion(outline, extrusion_vec)
    if srf is None:
        return None

    brep = srf.ToBrep()
    # Cap planar holes
    capped = brep.CapPlanarHoles(0.01)
    return capped if capped is not None else brep


def _create_footbed_surface(
    outline: Rhino.Geometry.Curve,
    arch_height: float,
    heel_cup_depth: float,
) -> Optional[Rhino.Geometry.Brep]:
    """Create a contoured footbed surface within the outline.

    Builds a planar surface from the outline, then deforms it to add
    arch support and heel cupping.
    """
    if outline is None or not outline.IsValid:
        return None

    if not outline.IsClosed:
        outline = outline.DuplicateCurve()
        outline.MakeClosed(1.0)

    # Create planar surface from outline
    breps = Rhino.Geometry.Brep.CreatePlanarBreps(
        [outline], 0.01
    )
    if not breps or len(breps) == 0:
        return None

    footbed = breps[0]
    bbox = footbed.GetBoundingBox(True)
    if not bbox.IsValid:
        return footbed

    total_length = bbox.Max.Y - bbox.Min.Y
    center_x = (bbox.Min.X + bbox.Max.X) / 2.0

    # Deform via control points if it's a NURBS surface
    for face_idx in range(footbed.Faces.Count):
        face = footbed.Faces[face_idx]
        srf = face.UnderlyingSurface()
        if isinstance(srf, Rhino.Geometry.NurbsSurface):
            nurbs = srf.ToNurbsSurface()
            if nurbs is None:
                continue
            for u_idx in range(nurbs.Points.CountU):
                for v_idx in range(nurbs.Points.CountV):
                    cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                    pt = cp.Location
                    rel_y = (pt.Y - bbox.Min.Y) / max(total_length, 1e-6)
                    dz = 0.0

                    # Arch profile (sinusoidal, 35%-75% of length)
                    if arch_height > 0 and 0.35 < rel_y < 0.75:
                        t = (rel_y - 0.35) / 0.40
                        # Medial bias
                        medial_factor = max(0.0, (center_x - pt.X) / max(
                            center_x - bbox.Min.X, 1e-6
                        ))
                        medial_factor = min(medial_factor * 1.5, 1.0)
                        dz += arch_height * math.sin(t * math.pi) * medial_factor

                    # Heel cup (0%-20% of length)
                    if heel_cup_depth > 0 and rel_y < 0.20:
                        edge_dist = abs(pt.X - center_x) / max(
                            (bbox.Max.X - bbox.Min.X) / 2, 1e-6
                        )
                        heel_factor = 1.0 - rel_y / 0.20
                        dz += heel_cup_depth * min(edge_dist, 1.0) * heel_factor

                    if abs(dz) > 1e-9:
                        new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                        nurbs.Points.SetControlPoint(
                            u_idx, v_idx,
                            Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                        )

    return footbed


def _create_groove(
    sole_brep: Rhino.Geometry.Brep,
    groove_curve: Rhino.Geometry.Curve,
    groove_width: float,
    groove_depth: float,
) -> Optional[Rhino.Geometry.Brep]:
    """Create a groove in a sole brep along a curve.

    Builds a thin cutter volume along *groove_curve* and performs a
    boolean difference from *sole_brep*.
    """
    if sole_brep is None or groove_curve is None:
        return sole_brep

    # Build a rectangular cross section for the groove
    plane = Rhino.Geometry.Plane.WorldXY
    half_w = groove_width / 2.0
    rect = Rhino.Geometry.Rectangle3d(
        plane,
        Rhino.Geometry.Interval(-half_w, half_w),
        Rhino.Geometry.Interval(0, groove_depth),
    )
    section_curve = rect.ToNurbsCurve()

    # Sweep along groove_curve
    sweep = Rhino.Geometry.SweepOneRail()
    sweep_breps = sweep.PerformSweep(groove_curve, section_curve)
    if not sweep_breps or len(sweep_breps) == 0:
        return sole_brep

    cutter = sweep_breps[0]
    capped = cutter.CapPlanarHoles(0.01)
    if capped is not None:
        cutter = capped

    # Boolean difference
    results = Rhino.Geometry.Brep.CreateBooleanDifference(
        sole_brep, cutter, 0.01
    )
    if results and len(results) > 0:
        return results[0]

    return sole_brep


def _create_thong_slot(
    sole_brep: Rhino.Geometry.Brep,
    slot_position: Rhino.Geometry.Point3d,
    slot_width: float,
    slot_depth: float,
    slot_length: float,
) -> Tuple[Optional[Rhino.Geometry.Brep], Optional[Rhino.Geometry.Brep]]:
    """Create a thong slot cut into the sole at *slot_position*.

    Returns (modified_sole, slot_geometry) tuple.
    """
    if sole_brep is None:
        return None, None

    # Create a box cutter for the slot
    half_w = slot_width / 2.0
    half_l = slot_length / 2.0
    corners = [
        Rhino.Geometry.Point3d(slot_position.X - half_w, slot_position.Y - half_l, slot_position.Z),
        Rhino.Geometry.Point3d(slot_position.X + half_w, slot_position.Y - half_l, slot_position.Z),
        Rhino.Geometry.Point3d(slot_position.X + half_w, slot_position.Y + half_l, slot_position.Z),
        Rhino.Geometry.Point3d(slot_position.X - half_w, slot_position.Y + half_l, slot_position.Z),
    ]

    bottom_corners = [
        Rhino.Geometry.Point3d(c.X, c.Y, c.Z - slot_depth) for c in corners
    ]

    box_brep = Rhino.Geometry.Brep.CreateFromBox(
        Rhino.Geometry.BoundingBox(
            Rhino.Geometry.Point3d(
                slot_position.X - half_w,
                slot_position.Y - half_l,
                slot_position.Z - slot_depth,
            ),
            Rhino.Geometry.Point3d(
                slot_position.X + half_w,
                slot_position.Y + half_l,
                slot_position.Z,
            ),
        )
    )

    if box_brep is None:
        return sole_brep, None

    slot_geom = box_brep.DuplicateBrep()

    results = Rhino.Geometry.Brep.CreateBooleanDifference(
        sole_brep, box_brep, 0.01
    )
    if results and len(results) > 0:
        return results[0], slot_geom

    return sole_brep, slot_geom


def _create_met_pad(
    footbed: Rhino.Geometry.Brep,
    center: Rhino.Geometry.Point3d,
    radius: float,
    height: float,
) -> Optional[Rhino.Geometry.Brep]:
    """Create a dome-shaped metatarsal pad at *center*.

    Returns a Brep dome that can be boolean-unioned with the footbed.
    """
    sphere = Rhino.Geometry.Sphere(center, radius)
    sphere_brep = sphere.ToBrep()

    if sphere_brep is None:
        return None

    # Cut the sphere in half at the footbed surface level
    cut_plane = Rhino.Geometry.Plane(
        center,
        Rhino.Geometry.Vector3d(0, 0, 1),
    )

    trimmed = sphere_brep.Trim(cut_plane, 0.01)
    if trimmed and len(trimmed) > 0:
        dome = trimmed[0]
    else:
        dome = sphere_brep

    # Scale Z to desired height
    if radius > 0:
        z_scale = height / radius
        xform = Rhino.Geometry.Transform.Scale(
            Rhino.Geometry.Plane(center, Rhino.Geometry.Vector3d.ZAxis),
            1.0, 1.0, z_scale,
        )
        dome.Transform(xform)

    return dome


# ---------------------------------------------------------------------------
#  BuildSandal
# ---------------------------------------------------------------------------

class BuildSandal(Rhino.Commands.Command):
    """Create a sandal from last/insert data.

    Builds the outsole, midsole, and footbed components using the
    current insole outline and design parameters.
    """

    _instance: BuildSandal | None = None

    def __init__(self):
        super().__init__()
        BuildSandal._instance = self

    @classmethod
    @property
    def Instance(cls) -> BuildSandal | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "BuildSandal"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)
        mt = plug.GetMaterialThicknesses(doc)

        # Try to get outline from document
        outline = _get_outline_curve(doc)
        if outline is None:
            go = Rhino.Input.Custom.GetObject()
            go.SetCommandPrompt("Select sandal outline curve")
            go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
            go.Get()
            if go.CommandResult() != Rhino.Commands.Result.Success:
                return go.CommandResult()
            outline = go.Object(0).Curve()

        if outline is None:
            Rhino.RhinoApp.WriteLine("No valid outline curve found.")
            return Rhino.Commands.Result.Failure

        # Options
        go_opt = Rhino.Input.Custom.GetOption()
        go_opt.SetCommandPrompt("Build sandal parameters")
        opt_sole = Rhino.Input.Custom.OptionDouble(mt.bottom_outsole, 1.0, 30.0)
        opt_midsole = Rhino.Input.Custom.OptionDouble(mt.bottom_midsole, 0.0, 30.0)
        opt_arch = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_arch_height_mm", 6.0), 0.0, 30.0
        )
        opt_heel_cup = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_heel_cup_depth_mm", 0.0), 0.0, 20.0
        )
        go_opt.AddOptionDouble("OutsoleThickness", opt_sole)
        go_opt.AddOptionDouble("MidsoleThickness", opt_midsole)
        go_opt.AddOptionDouble("ArchHeight", opt_arch)
        go_opt.AddOptionDouble("HeelCupDepth", opt_heel_cup)

        while True:
            res = go_opt.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        sole_thick = opt_sole.CurrentValue
        midsole_thick = opt_midsole.CurrentValue
        arch_h = opt_arch.CurrentValue
        heel_cup = opt_heel_cup.CurrentValue

        Rhino.RhinoApp.WriteLine("Building sandal ...")

        layer_idx = _ensure_layer(doc, _SANDAL_LAYER)

        # Build sole
        sole = _create_sandal_sole(outline, sole_thick, midsole_thick)
        if sole is not None and sole.IsValid:
            attrs = Rhino.DocObjects.ObjectAttributes()
            attrs.LayerIndex = layer_idx
            attrs.Name = "SandalSole"
            doc.Objects.AddBrep(sole, attrs)
            Rhino.RhinoApp.WriteLine("  Sole created.")
        else:
            Rhino.RhinoApp.WriteLine("  Warning: sole creation failed.")

        # Build footbed
        footbed = _create_footbed_surface(outline, arch_h, heel_cup)
        if footbed is not None and footbed.IsValid:
            attrs = Rhino.DocObjects.ObjectAttributes()
            attrs.LayerIndex = layer_idx
            attrs.Name = "SandalFootbed"
            doc.Objects.AddBrep(footbed, attrs)
            Rhino.RhinoApp.WriteLine("  Footbed created.")

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Sandal build complete.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  BuildInsert
# ---------------------------------------------------------------------------

class BuildInsert(Rhino.Commands.Command):
    """Create a custom insert/footbed for a sandal.

    Uses the insole outline and foot data to generate a contoured
    insert with optional arch support, heel cupping, and met pad.
    """

    _instance: BuildInsert | None = None

    def __init__(self):
        super().__init__()
        BuildInsert._instance = self

    @classmethod
    @property
    def Instance(cls) -> BuildInsert | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "BuildInsert"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)
        mt = plug.GetMaterialThicknesses(doc)

        # Get outline
        outline = _get_outline_curve(doc)
        if outline is None:
            go = Rhino.Input.Custom.GetObject()
            go.SetCommandPrompt("Select insert outline curve")
            go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
            go.Get()
            if go.CommandResult() != Rhino.Commands.Result.Success:
                return go.CommandResult()
            outline = go.Object(0).Curve()

        if outline is None:
            Rhino.RhinoApp.WriteLine("No valid outline curve.")
            return Rhino.Commands.Result.Failure

        # Options
        go_opt = Rhino.Input.Custom.GetOption()
        go_opt.SetCommandPrompt("Build insert parameters")
        opt_thick = Rhino.Input.Custom.OptionDouble(mt.insole_base, 1.0, 20.0)
        opt_arch = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_arch_height_mm", 6.0), 0.0, 30.0
        )
        opt_heel_cup = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_heel_cup_depth_mm", 8.0), 0.0, 25.0
        )
        opt_top_cover = Rhino.Input.Custom.OptionDouble(mt.insole_top_cover, 0.0, 5.0)

        go_opt.AddOptionDouble("Thickness", opt_thick)
        go_opt.AddOptionDouble("ArchHeight", opt_arch)
        go_opt.AddOptionDouble("HeelCupDepth", opt_heel_cup)
        go_opt.AddOptionDouble("TopCover", opt_top_cover)

        while True:
            res = go_opt.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        Rhino.RhinoApp.WriteLine("Building insert ...")

        # Create contoured top surface
        footbed = _create_footbed_surface(
            outline, opt_arch.CurrentValue, opt_heel_cup.CurrentValue
        )
        if footbed is None:
            Rhino.RhinoApp.WriteLine("Failed to create insert surface.")
            return Rhino.Commands.Result.Failure

        # Offset to create thickness
        total_thick = opt_thick.CurrentValue + opt_top_cover.CurrentValue
        offset_results = Rhino.Geometry.Brep.CreateOffsetBrep(
            footbed, -total_thick, solid=True, extend=False, tolerance=0.01
        )

        insert_brep = footbed
        if offset_results and len(offset_results) > 0:
            if hasattr(offset_results[0], "__iter__"):
                for b in offset_results[0]:
                    if isinstance(b, Rhino.Geometry.Brep) and b.IsValid:
                        insert_brep = b
                        break
            elif isinstance(offset_results[0], Rhino.Geometry.Brep):
                insert_brep = offset_results[0]

        layer_idx = _ensure_layer(doc, plugin_constants.CLASS_INSERT, (255, 165, 0))
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = layer_idx
        attrs.Name = "Insert"
        doc.Objects.AddBrep(insert_brep, attrs)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Insert built successfully.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AddSandalGroove
# ---------------------------------------------------------------------------

class AddSandalGroove(Rhino.Commands.Command):
    """Add a groove to a sandal sole.

    The groove follows a user-drawn or auto-generated curve on the
    sole surface.  Typically used for strap attachment channels.
    """

    _instance: AddSandalGroove | None = None

    def __init__(self):
        super().__init__()
        AddSandalGroove._instance = self

    @classmethod
    @property
    def Instance(cls) -> AddSandalGroove | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AddSandalGroove"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select sole
        go_sole = Rhino.Input.Custom.GetObject()
        go_sole.SetCommandPrompt("Select sandal sole")
        go_sole.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go_sole.Get()
        if go_sole.CommandResult() != Rhino.Commands.Result.Success:
            return go_sole.CommandResult()

        sole_ref = go_sole.Object(0)
        sole_brep = sole_ref.Brep()
        sole_obj = sole_ref.Object()
        if sole_brep is None:
            return Rhino.Commands.Result.Failure

        # Select groove path curve
        go_crv = Rhino.Input.Custom.GetObject()
        go_crv.SetCommandPrompt("Select groove path curve")
        go_crv.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
        go_crv.Get()
        if go_crv.CommandResult() != Rhino.Commands.Result.Success:
            return go_crv.CommandResult()

        groove_curve = go_crv.Object(0).Curve()
        if groove_curve is None:
            return Rhino.Commands.Result.Failure

        # Options
        go_opt = Rhino.Input.Custom.GetOption()
        go_opt.SetCommandPrompt("Groove parameters")
        opt_width = Rhino.Input.Custom.OptionDouble(3.0, 0.5, 20.0)
        opt_depth = Rhino.Input.Custom.OptionDouble(2.0, 0.5, 15.0)
        go_opt.AddOptionDouble("Width", opt_width)
        go_opt.AddOptionDouble("Depth", opt_depth)

        while True:
            res = go_opt.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        Rhino.RhinoApp.WriteLine("Adding groove ...")

        result = _create_groove(
            sole_brep, groove_curve,
            opt_width.CurrentValue, opt_depth.CurrentValue,
        )

        if result is not None and result.IsValid:
            doc.Objects.Replace(sole_obj.Id, result)
            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Groove added successfully.")
            return Rhino.Commands.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("Groove creation failed.")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  AddThongSlot
# ---------------------------------------------------------------------------

class AddThongSlot(Rhino.Commands.Command):
    """Add a thong slot to a sandal.

    Creates a rectangular slot at the toe area for thong-strap insertion.
    """

    _instance: AddThongSlot | None = None

    def __init__(self):
        super().__init__()
        AddThongSlot._instance = self

    @classmethod
    @property
    def Instance(cls) -> AddThongSlot | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AddThongSlot"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select sole
        go_sole = Rhino.Input.Custom.GetObject()
        go_sole.SetCommandPrompt("Select sandal sole for thong slot")
        go_sole.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go_sole.Get()
        if go_sole.CommandResult() != Rhino.Commands.Result.Success:
            return go_sole.CommandResult()

        sole_ref = go_sole.Object(0)
        sole_brep = sole_ref.Brep()
        sole_obj = sole_ref.Object()
        if sole_brep is None:
            return Rhino.Commands.Result.Failure

        # Get slot position -- either pick a point or auto-compute from bbox
        go_pt = Rhino.Input.Custom.GetPoint()
        go_pt.SetCommandPrompt(
            "Pick thong slot location (Enter for auto-position at toe)"
        )
        go_pt.AcceptNothing(True)

        opt_width = Rhino.Input.Custom.OptionDouble(6.0, 2.0, 20.0)
        opt_depth = Rhino.Input.Custom.OptionDouble(4.0, 1.0, 15.0)
        opt_length = Rhino.Input.Custom.OptionDouble(12.0, 4.0, 40.0)
        go_pt.AddOptionDouble("SlotWidth", opt_width)
        go_pt.AddOptionDouble("SlotDepth", opt_depth)
        go_pt.AddOptionDouble("SlotLength", opt_length)

        slot_position: Optional[Rhino.Geometry.Point3d] = None

        while True:
            res = go_pt.Get()
            if res == Rhino.Input.GetResult.Point:
                slot_position = go_pt.Point()
                break
            elif res == Rhino.Input.GetResult.Nothing:
                # Auto-position at toe
                bbox = sole_brep.GetBoundingBox(True)
                if bbox.IsValid:
                    slot_position = Rhino.Geometry.Point3d(
                        (bbox.Min.X + bbox.Max.X) / 2.0,
                        bbox.Max.Y - (bbox.Max.Y - bbox.Min.Y) * 0.12,
                        bbox.Max.Z,
                    )
                break
            elif res == Rhino.Input.GetResult.Option:
                continue
            else:
                return Rhino.Commands.Result.Cancel

        if slot_position is None:
            Rhino.RhinoApp.WriteLine("Could not determine slot position.")
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("Adding thong slot ...")

        modified, slot_geom = _create_thong_slot(
            sole_brep, slot_position,
            opt_width.CurrentValue,
            opt_depth.CurrentValue,
            opt_length.CurrentValue,
        )

        if modified is not None and modified.IsValid:
            doc.Objects.Replace(sole_obj.Id, modified)

            # Add slot geometry as reference object
            if slot_geom is not None:
                layer_idx = _ensure_layer(doc, _SANDAL_LAYER)
                attrs = Rhino.DocObjects.ObjectAttributes()
                attrs.LayerIndex = layer_idx
                attrs.Name = "ThongSlot"
                doc.Objects.AddBrep(slot_geom, attrs)

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Thong slot added.")
            return Rhino.Commands.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("Thong slot creation failed.")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  ToggleThongSlotInclusion
# ---------------------------------------------------------------------------

class ToggleThongSlotInclusion(Rhino.Commands.Command):
    """Toggle thong slot visibility/inclusion in the sandal model.

    Shows or hides the thong slot object and optionally fills or
    re-cuts the slot in the sole.
    """

    _instance: ToggleThongSlotInclusion | None = None

    def __init__(self):
        super().__init__()
        ToggleThongSlotInclusion._instance = self

    @classmethod
    @property
    def Instance(cls) -> ToggleThongSlotInclusion | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ToggleThongSlotInclusion"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Find thong slot objects
        slot_objs = _find_objects_by_prefix(doc, "ThongSlot")
        if not slot_objs:
            Rhino.RhinoApp.WriteLine(
                "No thong slot found.  Use AddThongSlot first."
            )
            return Rhino.Commands.Result.Nothing

        # Toggle visibility
        toggled = 0
        for obj in slot_objs:
            is_hidden = obj.Attributes.Visible is False or obj.IsHidden
            if is_hidden:
                doc.Objects.Show(obj, True)
                Rhino.RhinoApp.WriteLine(f"  Showing: {obj.Attributes.Name}")
            else:
                doc.Objects.Hide(obj, True)
                Rhino.RhinoApp.WriteLine(f"  Hiding: {obj.Attributes.Name}")
            toggled += 1

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Toggled {toggled} thong slot object(s)."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AddMetpad
# ---------------------------------------------------------------------------

class AddMetpad(Rhino.Commands.Command):
    """Add a metatarsal pad to an insert or footbed.

    Creates a dome-shaped pad at the metatarsal head region and unions
    it with the existing insert surface.
    """

    _instance: AddMetpad | None = None

    def __init__(self):
        super().__init__()
        AddMetpad._instance = self

    @classmethod
    @property
    def Instance(cls) -> AddMetpad | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AddMetpad"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select insert/footbed
        go_insert = Rhino.Input.Custom.GetObject()
        go_insert.SetCommandPrompt("Select insert or footbed")
        go_insert.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go_insert.Get()
        if go_insert.CommandResult() != Rhino.Commands.Result.Success:
            return go_insert.CommandResult()

        insert_ref = go_insert.Object(0)
        insert_brep = insert_ref.Brep()
        insert_obj = insert_ref.Object()
        if insert_brep is None:
            return Rhino.Commands.Result.Failure

        # Get pad position
        go_pt = Rhino.Input.Custom.GetPoint()
        go_pt.SetCommandPrompt(
            "Pick met pad center (Enter for auto-position)"
        )
        go_pt.AcceptNothing(True)

        opt_radius = Rhino.Input.Custom.OptionDouble(12.0, 3.0, 30.0)
        opt_height = Rhino.Input.Custom.OptionDouble(3.0, 0.5, 10.0)
        go_pt.AddOptionDouble("Radius", opt_radius)
        go_pt.AddOptionDouble("Height", opt_height)

        pad_center: Optional[Rhino.Geometry.Point3d] = None

        while True:
            res = go_pt.Get()
            if res == Rhino.Input.GetResult.Point:
                pad_center = go_pt.Point()
                break
            elif res == Rhino.Input.GetResult.Nothing:
                # Auto-position at ~65% length, medial offset
                bbox = insert_brep.GetBoundingBox(True)
                if bbox.IsValid:
                    pad_center = Rhino.Geometry.Point3d(
                        (bbox.Min.X + bbox.Max.X) / 2.0 - 5.0,
                        bbox.Min.Y + (bbox.Max.Y - bbox.Min.Y) * 0.65,
                        bbox.Max.Z,
                    )
                break
            elif res == Rhino.Input.GetResult.Option:
                continue
            else:
                return Rhino.Commands.Result.Cancel

        if pad_center is None:
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("Adding metatarsal pad ...")

        pad = _create_met_pad(
            insert_brep, pad_center,
            opt_radius.CurrentValue, opt_height.CurrentValue,
        )

        if pad is not None and pad.IsValid:
            # Try boolean union
            results = Rhino.Geometry.Brep.CreateBooleanUnion(
                [insert_brep, pad], 0.01
            )
            if results and len(results) > 0 and results[0].IsValid:
                doc.Objects.Replace(insert_obj.Id, results[0])
            else:
                # If union fails, add pad as separate object
                layer_idx = _ensure_layer(doc, plugin_constants.CLASS_INSERT, (255, 165, 0))
                attrs = Rhino.DocObjects.ObjectAttributes()
                attrs.LayerIndex = layer_idx
                attrs.Name = "MetPad"
                doc.Objects.AddBrep(pad, attrs)
                Rhino.RhinoApp.WriteLine(
                    "  Boolean union failed; pad added as separate object."
                )

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Metatarsal pad added.")
            return Rhino.Commands.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("Met pad creation failed.")
            return Rhino.Commands.Result.Failure
