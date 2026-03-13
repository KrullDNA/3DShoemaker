"""
3DShoemaker Rhino 8 Plugin - Orthotic creation commands.

Commands:
    MakeOrthotic                        - Creates orthotic device from foot/last data.
    AdjustOrthoticToBlank               - Adjusts orthotic design to fit a blank.
    AdjustOrthoticArchHeightAndLength   - Modifies orthotic arch parameters.
    AdjustOrthoticFeature               - Adjusts specific orthotic features.
    TwistOrthotic                       - Applies twist deformation to orthotic.
    PrintPrepOrthotic                   - Prepares a single orthotic for 3D printing.
    PrintPrepOrthotics                  - Batch print prep for multiple orthotics.
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
#  Orthotic helpers
# ---------------------------------------------------------------------------

_ORTHOTIC_LAYER = "Orthotic"


def _ensure_orthotic_layer(doc: Rhino.RhinoDoc) -> int:
    """Ensure an SLM::Orthotic layer exists and return its index."""
    full_path = f"{plugin_constants.SLM_LAYER_PREFIX}::{_ORTHOTIC_LAYER}"
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
    child.Name = _ORTHOTIC_LAYER
    child.ParentLayerId = parent_id
    child.Color = System.Drawing.Color.FromArgb(0, 180, 120)
    return doc.Layers.Add(child)


def _find_named_object(
    doc: Rhino.RhinoDoc, name: str
) -> Optional[Rhino.DocObjects.RhinoObject]:
    """Find the first object whose Name matches *name*."""
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.NameFilter = name
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        return obj
    return None


def _find_objects_by_name_prefix(
    doc: Rhino.RhinoDoc, prefix: str
) -> List[Rhino.DocObjects.RhinoObject]:
    """Return all objects whose name starts with *prefix*."""
    results: List[Rhino.DocObjects.RhinoObject] = []
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.DeletedObjects = False
    settings.HiddenObjects = True
    for obj in doc.Objects.GetObjectList(settings):
        name = obj.Attributes.Name or ""
        if name.startswith(prefix):
            results.append(obj)
    return results


def _get_insole_surface(
    doc: Rhino.RhinoDoc,
) -> Optional[Rhino.Geometry.Brep]:
    """Retrieve the insole brep from the document (by name convention)."""
    obj = _find_named_object(doc, "Insole")
    if obj is None:
        obj = _find_named_object(doc, "InsoleTop")
    if obj is not None:
        geom = obj.Geometry
        if isinstance(geom, Rhino.Geometry.Brep):
            return geom
    return None


def _get_foot_mesh(
    doc: Rhino.RhinoDoc,
) -> Optional[Rhino.Geometry.Mesh]:
    """Retrieve the foot-scan mesh from the document."""
    for obj in _find_objects_by_name_prefix(doc, "FootScan"):
        geom = obj.Geometry
        if isinstance(geom, Rhino.Geometry.Mesh):
            return geom
    return None


def _create_orthotic_shell(
    insole_srf: Rhino.Geometry.Brep,
    thickness: float,
    arch_height: float,
    heel_cup_depth: float,
    trim_length_ratio: float,
) -> Optional[Rhino.Geometry.Brep]:
    """Create an orthotic shell Brep from the insole surface.

    The shell is built by offsetting the insole surface downward by
    *thickness*, trimming to *trim_length_ratio* of total length,
    and shaping the arch and heel cup regions.
    """
    if insole_srf is None or not insole_srf.IsValid:
        return None

    bbox = insole_srf.GetBoundingBox(True)
    if not bbox.IsValid:
        return None

    # Offset surface to create shell thickness
    offset_breps = Rhino.Geometry.Brep.CreateOffsetBrep(
        insole_srf,
        -thickness,
        solid=True,
        extend=False,
        tolerance=0.01,
    )

    shell: Optional[Rhino.Geometry.Brep] = None
    if offset_breps and len(offset_breps) > 0:
        # CreateOffsetBrep returns (Brep[], BrepFace[]) tuple or list
        if hasattr(offset_breps[0], "__iter__"):
            for b in offset_breps[0]:
                if isinstance(b, Rhino.Geometry.Brep) and b.IsValid:
                    shell = b
                    break
        elif isinstance(offset_breps[0], Rhino.Geometry.Brep):
            shell = offset_breps[0]

    if shell is None:
        # Fallback: duplicate the insole and move it down
        shell = insole_srf.DuplicateBrep()
        xform = Rhino.Geometry.Transform.Translation(
            Rhino.Geometry.Vector3d(0, 0, -thickness)
        )
        shell.Transform(xform)

    # Trim to 3/4 length if ratio is set
    if 0.0 < trim_length_ratio < 1.0:
        total_length = bbox.Max.Y - bbox.Min.Y
        cut_y = bbox.Min.Y + total_length * trim_length_ratio
        cut_plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(0, cut_y, 0),
            Rhino.Geometry.Vector3d(0, 1, 0),
        )
        trimmed = shell.Trim(cut_plane, 0.01)
        if trimmed and len(trimmed) > 0:
            shell = trimmed[0]

    return shell


def _apply_arch_profile(
    shell: Rhino.Geometry.Brep,
    arch_height: float,
    arch_start_ratio: float = 0.35,
    arch_end_ratio: float = 0.75,
) -> Rhino.Geometry.Brep:
    """Apply a smooth arch profile to the orthotic shell by cage-editing
    control points in the arch region upward by *arch_height*.
    """
    if shell is None or arch_height <= 0:
        return shell

    bbox = shell.GetBoundingBox(True)
    total_length = bbox.Max.Y - bbox.Min.Y
    arch_start_y = bbox.Min.Y + total_length * arch_start_ratio
    arch_end_y = bbox.Min.Y + total_length * arch_end_ratio
    arch_mid_y = (arch_start_y + arch_end_y) / 2.0

    # Convert to mesh, adjust vertices, then convert back to NURBS
    # For a brep, we attempt a point-based morph
    for face_idx in range(shell.Faces.Count):
        face = shell.Faces[face_idx]
        srf = face.UnderlyingSurface()
        if isinstance(srf, Rhino.Geometry.NurbsSurface):
            nurbs = srf.ToNurbsSurface()
            if nurbs is not None:
                for u_idx in range(nurbs.Points.CountU):
                    for v_idx in range(nurbs.Points.CountV):
                        cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                        pt = cp.Location
                        if arch_start_y <= pt.Y <= arch_end_y:
                            # Sinusoidal arch profile
                            t = (pt.Y - arch_start_y) / (arch_end_y - arch_start_y)
                            dz = arch_height * math.sin(t * math.pi)
                            new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                            nurbs.Points.SetControlPoint(
                                u_idx, v_idx,
                                Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                            )

    return shell


def _apply_heel_cup(
    shell: Rhino.Geometry.Brep,
    heel_cup_depth: float,
    heel_ratio: float = 0.20,
) -> Rhino.Geometry.Brep:
    """Raise heel-cup walls around the rear of the orthotic."""
    if shell is None or heel_cup_depth <= 0:
        return shell

    bbox = shell.GetBoundingBox(True)
    total_length = bbox.Max.Y - bbox.Min.Y
    heel_end_y = bbox.Min.Y + total_length * heel_ratio
    center_x = (bbox.Min.X + bbox.Max.X) / 2.0
    half_width = (bbox.Max.X - bbox.Min.X) / 2.0

    for face_idx in range(shell.Faces.Count):
        face = shell.Faces[face_idx]
        srf = face.UnderlyingSurface()
        if isinstance(srf, Rhino.Geometry.NurbsSurface):
            nurbs = srf.ToNurbsSurface()
            if nurbs is not None:
                for u_idx in range(nurbs.Points.CountU):
                    for v_idx in range(nurbs.Points.CountV):
                        cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                        pt = cp.Location
                        if pt.Y <= heel_end_y:
                            # Raise edges more than center
                            edge_factor = abs(pt.X - center_x) / max(half_width, 1e-6)
                            edge_factor = min(edge_factor, 1.0)
                            # Fade from heel end
                            heel_factor = 1.0 - (pt.Y - bbox.Min.Y) / max(
                                heel_end_y - bbox.Min.Y, 1e-6
                            )
                            heel_factor = max(0.0, min(1.0, heel_factor))
                            dz = heel_cup_depth * edge_factor * heel_factor
                            new_pt = Rhino.Geometry.Point3d(
                                pt.X, pt.Y, pt.Z + dz
                            )
                            nurbs.Points.SetControlPoint(
                                u_idx, v_idx,
                                Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                            )

    return shell


# ---------------------------------------------------------------------------
#  MakeOrthotic
# ---------------------------------------------------------------------------

class MakeOrthotic(Rhino.Commands.Command):
    """Create an orthotic device from foot/last data.

    Builds a 3/4-length orthotic shell using the insole surface as a
    base, applying arch support, heel cup, and posting adjustments.
    """

    _instance: MakeOrthotic | None = None

    def __init__(self):
        super().__init__()
        MakeOrthotic._instance = self

    @classmethod
    @property
    def Instance(cls) -> MakeOrthotic | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "MakeOrthotic"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)

        # Gather parameters
        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Create orthotic")

        opt_thickness = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_thickness_mm", 3.0), 0.5, 20.0
        )
        opt_arch = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_arch_height_mm", 8.0), 0.0, 40.0
        )
        opt_heel_cup = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_heel_cup_depth_mm", 12.0), 0.0, 30.0
        )
        opt_trim = Rhino.Input.Custom.OptionDouble(0.75, 0.5, 1.0)

        go.AddOptionDouble("Thickness", opt_thickness)
        go.AddOptionDouble("ArchHeight", opt_arch)
        go.AddOptionDouble("HeelCupDepth", opt_heel_cup)
        go.AddOptionDouble("TrimLengthRatio", opt_trim)

        while True:
            res = go.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        thickness = opt_thickness.CurrentValue
        arch_height = opt_arch.CurrentValue
        heel_cup_depth = opt_heel_cup.CurrentValue
        trim_ratio = opt_trim.CurrentValue

        # Get insole surface
        insole_srf = _get_insole_surface(doc)
        if insole_srf is None:
            Rhino.RhinoApp.WriteLine(
                "No insole surface found.  Please create an insole first "
                "(CreateInsole) or select one."
            )
            # Allow user to select
            gobj = Rhino.Input.Custom.GetObject()
            gobj.SetCommandPrompt("Select insole surface")
            gobj.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
            gobj.Get()
            if gobj.CommandResult() != Rhino.Commands.Result.Success:
                return gobj.CommandResult()
            insole_srf = gobj.Object(0).Brep()
            if insole_srf is None:
                Rhino.RhinoApp.WriteLine("Invalid surface selected.")
                return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("Creating orthotic shell ...")

        # Create shell
        shell = _create_orthotic_shell(
            insole_srf, thickness, arch_height, heel_cup_depth, trim_ratio
        )
        if shell is None:
            Rhino.RhinoApp.WriteLine("Failed to create orthotic shell.")
            return Rhino.Commands.Result.Failure

        # Apply arch
        shell = _apply_arch_profile(shell, arch_height)

        # Apply heel cup
        shell = _apply_heel_cup(shell, heel_cup_depth)

        # Add to document
        layer_idx = _ensure_orthotic_layer(doc)
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = layer_idx
        attrs.Name = "Orthotic"
        attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromLayer

        oid = doc.Objects.AddBrep(shell, attrs)
        if oid == System.Guid.Empty:
            Rhino.RhinoApp.WriteLine("Failed to add orthotic to document.")
            return Rhino.Commands.Result.Failure

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Orthotic created: thickness={thickness:.1f} mm, "
            f"arch={arch_height:.1f} mm, heel cup={heel_cup_depth:.1f} mm"
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustOrthoticToBlank
# ---------------------------------------------------------------------------

class AdjustOrthoticToBlank(Rhino.Commands.Command):
    """Adjust orthotic design to fit within the bounds of a physical blank.

    Trims, scales, or repositions the orthotic geometry so that it fits
    within a user-specified or standard blank outline.
    """

    _instance: AdjustOrthoticToBlank | None = None

    def __init__(self):
        super().__init__()
        AdjustOrthoticToBlank._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustOrthoticToBlank | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustOrthoticToBlank"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select orthotic
        go_orth = Rhino.Input.Custom.GetObject()
        go_orth.SetCommandPrompt("Select orthotic to adjust")
        go_orth.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go_orth.Get()
        if go_orth.CommandResult() != Rhino.Commands.Result.Success:
            return go_orth.CommandResult()

        orth_ref = go_orth.Object(0)
        orth_brep = orth_ref.Brep()
        orth_obj = orth_ref.Object()
        if orth_brep is None:
            Rhino.RhinoApp.WriteLine("Invalid orthotic geometry.")
            return Rhino.Commands.Result.Failure

        # Select blank outline
        go_blank = Rhino.Input.Custom.GetObject()
        go_blank.SetCommandPrompt("Select blank outline curve")
        go_blank.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
        go_blank.Get()
        if go_blank.CommandResult() != Rhino.Commands.Result.Success:
            return go_blank.CommandResult()

        blank_curve = go_blank.Object(0).Curve()
        if blank_curve is None:
            Rhino.RhinoApp.WriteLine("Invalid blank curve.")
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("Adjusting orthotic to blank ...")

        # Compute bounding boxes
        orth_bbox = orth_brep.GetBoundingBox(True)
        blank_bbox = blank_curve.GetBoundingBox(True)

        if not orth_bbox.IsValid or not blank_bbox.IsValid:
            Rhino.RhinoApp.WriteLine("Cannot compute bounding boxes.")
            return Rhino.Commands.Result.Failure

        # Scale to fit within blank
        orth_length = orth_bbox.Max.Y - orth_bbox.Min.Y
        orth_width = orth_bbox.Max.X - orth_bbox.Min.X
        blank_length = blank_bbox.Max.Y - blank_bbox.Min.Y
        blank_width = blank_bbox.Max.X - blank_bbox.Min.X

        scale_y = blank_length / max(orth_length, 1e-6)
        scale_x = blank_width / max(orth_width, 1e-6)
        scale_factor = min(scale_y, scale_x, 1.0)  # Only scale down

        if scale_factor < 1.0:
            orth_center = orth_bbox.Center
            xform_scale = Rhino.Geometry.Transform.Scale(orth_center, scale_factor)
            doc.Objects.Transform(orth_obj, xform_scale, True)
            Rhino.RhinoApp.WriteLine(
                f"  Scaled orthotic by {scale_factor:.4f} to fit blank."
            )

        # Center orthotic on blank
        new_orth_bbox = doc.Objects.FindId(orth_obj.Id).Geometry.GetBoundingBox(True)
        offset = blank_bbox.Center - new_orth_bbox.Center
        offset.Z = 0  # Keep Z position
        xform_move = Rhino.Geometry.Transform.Translation(
            Rhino.Geometry.Vector3d(offset)
        )
        doc.Objects.Transform(orth_obj, xform_move, True)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Orthotic adjusted to blank.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustOrthoticArchHeightAndLength
# ---------------------------------------------------------------------------

class AdjustOrthoticArchHeightAndLength(Rhino.Commands.Command):
    """Modify orthotic arch height and arch length parameters.

    Interactively adjust the medial longitudinal arch support height and
    the longitudinal extent of the arch region.
    """

    _instance: AdjustOrthoticArchHeightAndLength | None = None

    def __init__(self):
        super().__init__()
        AdjustOrthoticArchHeightAndLength._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustOrthoticArchHeightAndLength | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustOrthoticArchHeightAndLength"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select orthotic
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select orthotic to adjust arch")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        orth_ref = go.Object(0)
        orth_brep = orth_ref.Brep()
        orth_obj = orth_ref.Object()
        if orth_brep is None:
            Rhino.RhinoApp.WriteLine("Invalid orthotic geometry.")
            return Rhino.Commands.Result.Failure

        # Options
        go_opt = Rhino.Input.Custom.GetOption()
        go_opt.SetCommandPrompt("Adjust arch height and length")

        opt_height = Rhino.Input.Custom.OptionDouble(8.0, 0.0, 40.0)
        opt_start = Rhino.Input.Custom.OptionDouble(0.35, 0.1, 0.6)
        opt_end = Rhino.Input.Custom.OptionDouble(0.75, 0.5, 0.95)

        go_opt.AddOptionDouble("ArchHeight", opt_height)
        go_opt.AddOptionDouble("ArchStartRatio", opt_start)
        go_opt.AddOptionDouble("ArchEndRatio", opt_end)

        while True:
            res = go_opt.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        arch_height = opt_height.CurrentValue
        arch_start = opt_start.CurrentValue
        arch_end = opt_end.CurrentValue

        Rhino.RhinoApp.WriteLine(
            f"Applying arch: height={arch_height:.1f} mm, "
            f"start={arch_start:.0%}, end={arch_end:.0%}"
        )

        new_brep = _apply_arch_profile(orth_brep, arch_height, arch_start, arch_end)
        if new_brep is not None and new_brep.IsValid:
            doc.Objects.Replace(orth_obj.Id, new_brep)
            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Arch adjustment applied.")
            return Rhino.Commands.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("Arch adjustment failed.")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  AdjustOrthoticFeature
# ---------------------------------------------------------------------------

class AdjustOrthoticFeature(Rhino.Commands.Command):
    """Adjust a specific orthotic feature (posting, met pad, heel lift, etc.).

    Presents a list of adjustable features and applies the selected
    modification to the orthotic geometry.
    """

    _instance: AdjustOrthoticFeature | None = None

    def __init__(self):
        super().__init__()
        AdjustOrthoticFeature._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustOrthoticFeature | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustOrthoticFeature"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select orthotic
        go_sel = Rhino.Input.Custom.GetObject()
        go_sel.SetCommandPrompt("Select orthotic to modify")
        go_sel.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go_sel.Get()
        if go_sel.CommandResult() != Rhino.Commands.Result.Success:
            return go_sel.CommandResult()

        orth_ref = go_sel.Object(0)
        orth_brep = orth_ref.Brep()
        orth_obj = orth_ref.Object()
        if orth_brep is None:
            return Rhino.Commands.Result.Failure

        # Choose feature
        features = [
            "MedialPosting", "LateralPosting", "HeelLift",
            "MetPad", "HeelCup", "ForefootExtension",
            "RearfootExtension", "TopCover",
        ]

        go_feat = Rhino.Input.Custom.GetOption()
        go_feat.SetCommandPrompt("Select feature to adjust")
        go_feat.AddOptionList("Feature", features, 0)
        opt_value = Rhino.Input.Custom.OptionDouble(0.0, -20.0, 40.0)
        go_feat.AddOptionDouble("Value", opt_value)

        feature_idx = 0
        while True:
            res = go_feat.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                idx = go_feat.OptionIndex()
                if idx == 0:
                    feature_idx = go_feat.Option().CurrentListOptionIndex
                continue
            break

        feature_name = features[feature_idx] if feature_idx < len(features) else features[0]
        value = opt_value.CurrentValue

        Rhino.RhinoApp.WriteLine(f"Adjusting {feature_name} by {value:.2f} mm ...")

        bbox = orth_brep.GetBoundingBox(True)
        if not bbox.IsValid:
            return Rhino.Commands.Result.Failure

        total_length = bbox.Max.Y - bbox.Min.Y
        center_x = (bbox.Min.X + bbox.Max.X) / 2.0
        modified = orth_brep.DuplicateBrep()

        # Apply feature-specific modifications via control point manipulation
        for face_idx in range(modified.Faces.Count):
            face = modified.Faces[face_idx]
            srf = face.UnderlyingSurface()
            if not isinstance(srf, Rhino.Geometry.NurbsSurface):
                continue
            nurbs = srf.ToNurbsSurface()
            if nurbs is None:
                continue

            for u_idx in range(nurbs.Points.CountU):
                for v_idx in range(nurbs.Points.CountV):
                    cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                    pt = cp.Location
                    dz = 0.0
                    rel_y = (pt.Y - bbox.Min.Y) / max(total_length, 1e-6)

                    if feature_name == "MedialPosting":
                        if pt.X < center_x and 0.2 < rel_y < 0.8:
                            medial_factor = (center_x - pt.X) / max(
                                center_x - bbox.Min.X, 1e-6
                            )
                            dz = value * min(medial_factor, 1.0)

                    elif feature_name == "LateralPosting":
                        if pt.X > center_x and 0.2 < rel_y < 0.8:
                            lateral_factor = (pt.X - center_x) / max(
                                bbox.Max.X - center_x, 1e-6
                            )
                            dz = value * min(lateral_factor, 1.0)

                    elif feature_name == "HeelLift":
                        if rel_y < 0.25:
                            dz = value * (1.0 - rel_y / 0.25)

                    elif feature_name == "MetPad":
                        if 0.55 < rel_y < 0.75:
                            t = (rel_y - 0.55) / 0.20
                            dz = value * math.sin(t * math.pi)

                    elif feature_name == "HeelCup":
                        if rel_y < 0.20:
                            edge_dist = abs(pt.X - center_x) / max(
                                (bbox.Max.X - bbox.Min.X) / 2, 1e-6
                            )
                            dz = value * min(edge_dist, 1.0) * (1.0 - rel_y / 0.20)

                    elif feature_name == "ForefootExtension":
                        if rel_y > 0.75:
                            dz = value * ((rel_y - 0.75) / 0.25)

                    elif feature_name == "RearfootExtension":
                        if rel_y < 0.30:
                            dz = value * (1.0 - rel_y / 0.30)

                    elif feature_name == "TopCover":
                        dz = value  # Uniform offset

                    if abs(dz) > 1e-9:
                        new_pt = Rhino.Geometry.Point3d(
                            pt.X, pt.Y, pt.Z + dz
                        )
                        nurbs.Points.SetControlPoint(
                            u_idx, v_idx,
                            Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                        )

        if modified.IsValid:
            doc.Objects.Replace(orth_obj.Id, modified)
            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(
                f"{feature_name} adjusted by {value:.2f} mm."
            )
            return Rhino.Commands.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("Feature adjustment produced invalid geometry.")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  TwistOrthotic
# ---------------------------------------------------------------------------

class TwistOrthotic(Rhino.Commands.Command):
    """Apply twist deformation to an orthotic.

    Rotates the forefoot relative to the rearfoot about the longitudinal
    axis, simulating forefoot varus/valgus correction.
    """

    _instance: TwistOrthotic | None = None

    def __init__(self):
        super().__init__()
        TwistOrthotic._instance = self

    @classmethod
    @property
    def Instance(cls) -> TwistOrthotic | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "TwistOrthotic"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select orthotic
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select orthotic to twist")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        orth_ref = go.Object(0)
        orth_brep = orth_ref.Brep()
        orth_obj = orth_ref.Object()
        if orth_brep is None:
            return Rhino.Commands.Result.Failure

        # Get twist angle
        go_angle = Rhino.Input.Custom.GetOption()
        go_angle.SetCommandPrompt("Twist orthotic")
        opt_angle = Rhino.Input.Custom.OptionDouble(5.0, -30.0, 30.0)
        opt_pivot_ratio = Rhino.Input.Custom.OptionDouble(0.50, 0.2, 0.8)
        go_angle.AddOptionDouble("TwistAngleDegrees", opt_angle)
        go_angle.AddOptionDouble("PivotRatio", opt_pivot_ratio)

        while True:
            res = go_angle.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        angle_deg = opt_angle.CurrentValue
        pivot_ratio = opt_pivot_ratio.CurrentValue

        if abs(angle_deg) < 0.01:
            Rhino.RhinoApp.WriteLine("Twist angle is zero.  Nothing to do.")
            return Rhino.Commands.Result.Nothing

        Rhino.RhinoApp.WriteLine(
            f"Applying {angle_deg:.1f} degree twist at {pivot_ratio:.0%} pivot ..."
        )

        bbox = orth_brep.GetBoundingBox(True)
        if not bbox.IsValid:
            return Rhino.Commands.Result.Failure

        total_length = bbox.Max.Y - bbox.Min.Y
        pivot_y = bbox.Min.Y + total_length * pivot_ratio
        center_x = (bbox.Min.X + bbox.Max.X) / 2.0
        center_z = (bbox.Min.Z + bbox.Max.Z) / 2.0

        # Apply twist by rotating control points proportionally
        modified = orth_brep.DuplicateBrep()
        angle_rad = math.radians(angle_deg)

        for face_idx in range(modified.Faces.Count):
            face = modified.Faces[face_idx]
            srf = face.UnderlyingSurface()
            if not isinstance(srf, Rhino.Geometry.NurbsSurface):
                continue
            nurbs = srf.ToNurbsSurface()
            if nurbs is None:
                continue

            for u_idx in range(nurbs.Points.CountU):
                for v_idx in range(nurbs.Points.CountV):
                    cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                    pt = cp.Location

                    # Twist factor: 0 at pivot, +-1 at extremes
                    if pt.Y > pivot_y:
                        t = (pt.Y - pivot_y) / max(
                            bbox.Max.Y - pivot_y, 1e-6
                        )
                    else:
                        t = -(pivot_y - pt.Y) / max(
                            pivot_y - bbox.Min.Y, 1e-6
                        )

                    local_angle = angle_rad * t
                    # Rotate in the XZ plane about the center line
                    dx = pt.X - center_x
                    dz = pt.Z - center_z
                    cos_a = math.cos(local_angle)
                    sin_a = math.sin(local_angle)
                    new_x = center_x + dx * cos_a - dz * sin_a
                    new_z = center_z + dx * sin_a + dz * cos_a
                    new_pt = Rhino.Geometry.Point3d(new_x, pt.Y, new_z)
                    nurbs.Points.SetControlPoint(
                        u_idx, v_idx,
                        Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                    )

        if modified.IsValid:
            doc.Objects.Replace(orth_obj.Id, modified)
            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(f"Twist of {angle_deg:.1f} degrees applied.")
            return Rhino.Commands.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("Twist produced invalid geometry.")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  PrintPrepOrthotic
# ---------------------------------------------------------------------------

class PrintPrepOrthotic(Rhino.Commands.Command):
    """Prepare a single orthotic for 3D printing.

    Meshes the Brep, orients for optimal print orientation, adds
    support structures if needed, and exports an STL file.
    """

    _instance: PrintPrepOrthotic | None = None

    def __init__(self):
        super().__init__()
        PrintPrepOrthotic._instance = self

    @classmethod
    @property
    def Instance(cls) -> PrintPrepOrthotic | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "PrintPrepOrthotic"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select orthotic
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select orthotic for print preparation")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        orth_brep = go.Object(0).Brep()
        if orth_brep is None:
            return Rhino.Commands.Result.Failure

        # Options
        go_opt = Rhino.Input.Custom.GetOption()
        go_opt.SetCommandPrompt("Print prep options")
        opt_tol = Rhino.Input.Custom.OptionDouble(0.05, 0.001, 1.0)
        opt_orient = Rhino.Input.Custom.OptionToggle(True, "No", "Yes")
        go_opt.AddOptionDouble("MeshTolerance", opt_tol)
        go_opt.AddOptionToggle("AutoOrient", opt_orient)

        while True:
            res = go_opt.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        mesh_tol = opt_tol.CurrentValue
        auto_orient = opt_orient.CurrentValue

        Rhino.RhinoApp.WriteLine("Preparing orthotic for 3D printing ...")

        # Mesh the brep
        mp = Rhino.Geometry.MeshingParameters(mesh_tol)
        mp.MaximumEdgeLength = 0
        mp.MinimumEdgeLength = 0.1
        mp.GridAspectRatio = 6.0
        meshes = Rhino.Geometry.Mesh.CreateFromBrep(orth_brep, mp)
        if not meshes:
            Rhino.RhinoApp.WriteLine("Meshing failed.")
            return Rhino.Commands.Result.Failure

        # Join all mesh pieces
        combined = Rhino.Geometry.Mesh()
        for m in meshes:
            if m and m.IsValid:
                combined.Append(m)
        combined.Normals.ComputeNormals()
        combined.Compact()
        combined.UnifyNormals()

        # Check for non-manifold / open edges
        naked_count = 0
        for edge_status in combined.GetNakedEdgePointStatus():
            if edge_status:
                naked_count += 1

        if naked_count > 0:
            Rhino.RhinoApp.WriteLine(
                f"  Warning: mesh has {naked_count} naked edge vertices.  "
                f"Print quality may be affected."
            )

        # Auto orient: place flat on XY plane
        if auto_orient:
            bbox = combined.GetBoundingBox(True)
            if bbox.IsValid:
                move_z = -bbox.Min.Z
                if abs(move_z) > 1e-6:
                    xform = Rhino.Geometry.Transform.Translation(
                        Rhino.Geometry.Vector3d(0, 0, move_z)
                    )
                    combined.Transform(xform)

        # Add the print-ready mesh to the document
        layer_idx = _ensure_orthotic_layer(doc)
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = layer_idx
        attrs.Name = "Orthotic_PrintReady"

        oid = doc.Objects.AddMesh(combined, attrs)
        if oid == System.Guid.Empty:
            Rhino.RhinoApp.WriteLine("Failed to add print-ready mesh.")
            return Rhino.Commands.Result.Failure

        # Prompt to export STL
        fd = Rhino.UI.SaveFileDialog()
        fd.Title = "Export Orthotic STL"
        fd.Filter = "STL Files (*.stl)|*.stl"
        fd.DefaultExt = "stl"
        if fd.ShowSaveDialog():
            export_path = fd.FileName
            opts = Rhino.FileIO.FileStlWriteOptions()
            opts.AsciiFormat = False
            Rhino.FileIO.FileStl.Write(export_path, combined, opts)
            Rhino.RhinoApp.WriteLine(f"Exported: {export_path}")

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Print prep complete: {combined.Faces.Count} faces, "
            f"{combined.Vertices.Count} vertices."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  PrintPrepOrthotics
# ---------------------------------------------------------------------------

class PrintPrepOrthotics(Rhino.Commands.Command):
    """Batch print preparation for multiple orthotics.

    Selects all orthotic objects, meshes each, arranges them on a
    virtual print bed, and optionally exports.
    """

    _instance: PrintPrepOrthotics | None = None

    def __init__(self):
        super().__init__()
        PrintPrepOrthotics._instance = self

    @classmethod
    @property
    def Instance(cls) -> PrintPrepOrthotics | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "PrintPrepOrthotics"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select multiple orthotics
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select orthotics for batch print prep")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        go.EnablePreSelect(True, True)
        go.GetMultiple(1, 0)
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        count = go.ObjectCount
        if count == 0:
            Rhino.RhinoApp.WriteLine("No objects selected.")
            return Rhino.Commands.Result.Cancel

        # Options
        go_opt = Rhino.Input.Custom.GetOption()
        go_opt.SetCommandPrompt(f"Print prep {count} orthotic(s)")
        opt_tol = Rhino.Input.Custom.OptionDouble(0.05, 0.001, 1.0)
        opt_spacing = Rhino.Input.Custom.OptionDouble(10.0, 1.0, 100.0)
        opt_bed_x = Rhino.Input.Custom.OptionDouble(200.0, 50.0, 1000.0)
        go_opt.AddOptionDouble("MeshTolerance", opt_tol)
        go_opt.AddOptionDouble("Spacing", opt_spacing)
        go_opt.AddOptionDouble("BedWidth", opt_bed_x)

        while True:
            res = go_opt.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        mesh_tol = opt_tol.CurrentValue
        spacing = opt_spacing.CurrentValue
        bed_width = opt_bed_x.CurrentValue

        Rhino.RhinoApp.WriteLine(f"Batch print prep for {count} orthotic(s) ...")

        layer_idx = _ensure_orthotic_layer(doc)
        mp = Rhino.Geometry.MeshingParameters(mesh_tol)

        all_meshes: List[Rhino.Geometry.Mesh] = []
        current_x = 0.0
        current_y = 0.0
        row_max_y = 0.0

        for i in range(count):
            brep = go.Object(i).Brep()
            if brep is None:
                continue

            meshes = Rhino.Geometry.Mesh.CreateFromBrep(brep, mp)
            if not meshes:
                continue

            combined = Rhino.Geometry.Mesh()
            for m in meshes:
                if m and m.IsValid:
                    combined.Append(m)
            combined.Normals.ComputeNormals()
            combined.Compact()
            combined.UnifyNormals()

            # Position on print bed
            bbox = combined.GetBoundingBox(True)
            if not bbox.IsValid:
                continue

            obj_width = bbox.Max.X - bbox.Min.X
            obj_length = bbox.Max.Y - bbox.Min.Y

            # Check if fits in current row
            if current_x + obj_width > bed_width and current_x > 0:
                current_x = 0.0
                current_y += row_max_y + spacing
                row_max_y = 0.0

            # Move to position
            move_vec = Rhino.Geometry.Vector3d(
                current_x - bbox.Min.X,
                current_y - bbox.Min.Y,
                -bbox.Min.Z,
            )
            xform = Rhino.Geometry.Transform.Translation(move_vec)
            combined.Transform(xform)

            current_x += obj_width + spacing
            row_max_y = max(row_max_y, obj_length)

            # Add to doc
            attrs = Rhino.DocObjects.ObjectAttributes()
            attrs.LayerIndex = layer_idx
            attrs.Name = f"Orthotic_PrintReady_{i + 1}"
            doc.Objects.AddMesh(combined, attrs)
            all_meshes.append(combined)

        if not all_meshes:
            Rhino.RhinoApp.WriteLine("No valid meshes created.")
            return Rhino.Commands.Result.Failure

        # Optionally export
        fd = Rhino.UI.SaveFileDialog()
        fd.Title = "Export All Orthotics STL"
        fd.Filter = "STL Files (*.stl)|*.stl"
        fd.DefaultExt = "stl"
        if fd.ShowSaveDialog():
            export_mesh = Rhino.Geometry.Mesh()
            for m in all_meshes:
                export_mesh.Append(m)
            export_mesh.Compact()
            opts = Rhino.FileIO.FileStlWriteOptions()
            opts.AsciiFormat = False
            Rhino.FileIO.FileStl.Write(fd.FileName, export_mesh, opts)
            Rhino.RhinoApp.WriteLine(f"Exported: {fd.FileName}")

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Batch print prep complete: {len(all_meshes)} orthotic(s) prepared."
        )
        return Rhino.Commands.Result.Success
