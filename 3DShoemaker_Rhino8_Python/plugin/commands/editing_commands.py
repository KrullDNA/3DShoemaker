"""
3DShoemaker Rhino 8 Plugin - Geometry editing commands.

Commands:
    EditCurve                                  - Enters curve editing mode with grips.
    EndEdit                                    - Ends editing mode, commits changes.
    MoveObjectGrips                            - Moves object control points.
    Sculpt                                     - Sculpting/freeform editing of surfaces.
    BlendSurfaceToSurface                      - Creates smooth blend between surfaces.
    GirthCurveAveraging                        - Averages girth measurement curves.
    AdjustSurfacingCurveControlPointPosition   - Fine-tunes surfacing curve CPs.
    CopyObjectToMultiplePoints                 - Copies geometry to multiple locations.
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
#  Module-level editing state
# ---------------------------------------------------------------------------

class _EditingState:
    """Tracks active editing sessions across commands."""
    active: bool = False
    editing_object_id: Optional[System.Guid] = None
    original_geometry: Optional[Rhino.Geometry.GeometryBase] = None
    conduit: Optional[PreviewConduitClass] = None

_state = _EditingState()


# ---------------------------------------------------------------------------
#  EditCurve
# ---------------------------------------------------------------------------

class EditCurve(Rhino.Commands.Command):
    """Enter curve editing mode with grip points enabled.

    Selects a curve, turns on its control-point grips, and sets up a
    preview conduit so edits are visible in real time.
    """

    _instance: EditCurve | None = None

    def __init__(self):
        super().__init__()
        EditCurve._instance = self

    @classmethod
    @property
    def Instance(cls) -> EditCurve | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "EditCurve"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if _state.active:
            Rhino.RhinoApp.WriteLine(
                "An editing session is already active.  "
                "Use EndEdit to commit or cancel first."
            )
            return Rhino.Commands.Result.Nothing

        # Select curve
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select curve to edit")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
        go.SubObjectSelect = False
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        obj_ref = go.Object(0)
        curve_obj = obj_ref.Object()
        curve = obj_ref.Curve()
        if curve_obj is None or curve is None:
            return Rhino.Commands.Result.Failure

        # Store original for undo
        _state.original_geometry = curve.DuplicateCurve()
        _state.editing_object_id = curve_obj.Id
        _state.active = True

        # Enable grips
        curve_obj.GripsOn = True
        doc.Views.Redraw()

        # Set up preview conduit
        _state.conduit = PreviewConduitClass()
        preview = PreviewObject(
            curve.DuplicateCurve(),
            color=System.Drawing.Color.FromArgb(255, 100, 100),
            style=PreviewStyle.WIREFRAME,
            thickness=2,
            tag="edit_preview",
        )
        _state.conduit.AddPreviewObject(preview)
        _state.conduit.Enabled = True
        doc.Views.Redraw()

        Rhino.RhinoApp.WriteLine(
            "Curve editing mode active.  Drag grip points to edit.  "
            "Run EndEdit to commit changes."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  EndEdit
# ---------------------------------------------------------------------------

class EndEdit(Rhino.Commands.Command):
    """End editing mode and commit or discard changes.

    Turns off grips, disables the preview conduit, and optionally
    reverts to the original geometry.
    """

    _instance: EndEdit | None = None

    def __init__(self):
        super().__init__()
        EndEdit._instance = self

    @classmethod
    @property
    def Instance(cls) -> EndEdit | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "EndEdit"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _state.active:
            Rhino.RhinoApp.WriteLine("No editing session is active.")
            return Rhino.Commands.Result.Nothing

        # Ask commit or revert
        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Commit or revert changes?")
        go.AddOption("Commit")
        go.AddOption("Revert")
        res = go.Get()

        revert = False
        if res == Rhino.Input.GetResult.Option:
            if go.Option().EnglishName == "Revert":
                revert = True

        if revert and _state.editing_object_id is not None and _state.original_geometry is not None:
            obj = doc.Objects.FindId(_state.editing_object_id)
            if obj is not None:
                doc.Objects.Replace(_state.editing_object_id, _state.original_geometry)
                Rhino.RhinoApp.WriteLine("Changes reverted.")

        # Turn off grips
        if _state.editing_object_id is not None:
            obj = doc.Objects.FindId(_state.editing_object_id)
            if obj is not None:
                obj.GripsOn = False

        # Disable conduit
        if _state.conduit is not None:
            _state.conduit.ClearPreview()
            _state.conduit.Enabled = False
            _state.conduit = None

        # Reset state
        _state.active = False
        _state.editing_object_id = None
        _state.original_geometry = None

        doc.Views.Redraw()

        if not revert:
            Rhino.RhinoApp.WriteLine("Editing complete. Changes committed.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  MoveObjectGrips
# ---------------------------------------------------------------------------

class MoveObjectGrips(Rhino.Commands.Command):
    """Move object control points (grips) by a specified vector.

    Selects grip points on an object and translates them by a user-
    supplied distance and direction.
    """

    _instance: MoveObjectGrips | None = None

    def __init__(self):
        super().__init__()
        MoveObjectGrips._instance = self

    @classmethod
    @property
    def Instance(cls) -> MoveObjectGrips | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "MoveObjectGrips"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        # Select object
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select object with grips to move")
        go.GeometryFilter = (
            Rhino.DocObjects.ObjectType.Curve
            | Rhino.DocObjects.ObjectType.Surface
            | Rhino.DocObjects.ObjectType.Brep
        )
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        obj_ref = go.Object(0)
        rhino_obj = obj_ref.Object()
        if rhino_obj is None:
            return Rhino.Commands.Result.Failure

        # Ensure grips are on
        if not rhino_obj.GripsOn:
            rhino_obj.GripsOn = True
            doc.Views.Redraw()

        grips = rhino_obj.GetGrips()
        if grips is None or len(grips) == 0:
            Rhino.RhinoApp.WriteLine("Object has no grips.")
            return Rhino.Commands.Result.Failure

        # Select grips to move
        go_grips = Rhino.Input.Custom.GetObject()
        go_grips.SetCommandPrompt(
            "Select grip points to move (or Enter for all)"
        )
        go_grips.GeometryFilter = Rhino.DocObjects.ObjectType.Grip
        go_grips.EnablePreSelect(True, True)
        go_grips.AcceptNothing(True)
        go_grips.GetMultiple(0, 0)

        selected_indices: List[int] = []
        if go_grips.ObjectCount > 0:
            for i in range(go_grips.ObjectCount):
                grip_obj = go_grips.Object(i).Object()
                if grip_obj is not None:
                    for idx, g in enumerate(grips):
                        if g.Id == grip_obj.Id:
                            selected_indices.append(idx)
                            break
        else:
            # Move all grips
            selected_indices = list(range(len(grips)))

        if not selected_indices:
            Rhino.RhinoApp.WriteLine("No grips selected.")
            return Rhino.Commands.Result.Cancel

        # Get movement vector
        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt("Pick base point for move")
        gp.Get()
        if gp.CommandResult() != Rhino.Commands.Result.Success:
            return gp.CommandResult()
        base_pt = gp.Point()

        gp2 = Rhino.Input.Custom.GetPoint()
        gp2.SetCommandPrompt("Pick destination point")
        gp2.SetBasePoint(base_pt, True)
        gp2.DrawLineFromPoint(base_pt, True)
        gp2.Get()
        if gp2.CommandResult() != Rhino.Commands.Result.Success:
            return gp2.CommandResult()
        dest_pt = gp2.Point()

        move_vec = dest_pt - base_pt

        Rhino.RhinoApp.WriteLine(
            f"Moving {len(selected_indices)} grip(s) by "
            f"({move_vec.X:.3f}, {move_vec.Y:.3f}, {move_vec.Z:.3f}) ..."
        )

        # Move selected grips
        xform = Rhino.Geometry.Transform.Translation(move_vec)
        for idx in selected_indices:
            if idx < len(grips):
                grips[idx].Move(xform)

        doc.Objects.GripUpdate(rhino_obj, True)
        doc.Views.Redraw()

        Rhino.RhinoApp.WriteLine(
            f"Moved {len(selected_indices)} grip point(s)."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  Sculpt
# ---------------------------------------------------------------------------

class Sculpt(Rhino.Commands.Command):
    """Sculpting / freeform editing of surfaces.

    Provides a brush-based deformation tool that pushes or pulls
    surface points within a user-defined radius.
    """

    _instance: Sculpt | None = None

    def __init__(self):
        super().__init__()
        Sculpt._instance = self

    @classmethod
    @property
    def Instance(cls) -> Sculpt | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "Sculpt"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select surface or mesh
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select surface or mesh to sculpt")
        go.GeometryFilter = (
            Rhino.DocObjects.ObjectType.Brep
            | Rhino.DocObjects.ObjectType.Mesh
            | Rhino.DocObjects.ObjectType.SubD
        )
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        obj_ref = go.Object(0)
        rhino_obj = obj_ref.Object()
        geom = obj_ref.Geometry()
        if geom is None:
            return Rhino.Commands.Result.Failure

        # Sculpt parameters
        go_opt = Rhino.Input.Custom.GetOption()
        go_opt.SetCommandPrompt("Sculpt settings")
        opt_radius = Rhino.Input.Custom.OptionDouble(10.0, 1.0, 100.0)
        opt_strength = Rhino.Input.Custom.OptionDouble(1.0, 0.1, 10.0)
        opt_direction = Rhino.Input.Custom.OptionToggle(True, "Pull", "Push")

        go_opt.AddOptionDouble("BrushRadius", opt_radius)
        go_opt.AddOptionDouble("Strength", opt_strength)
        go_opt.AddOptionToggle("Direction", opt_direction)

        while True:
            res = go_opt.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        brush_radius = opt_radius.CurrentValue
        strength = opt_strength.CurrentValue
        push = opt_direction.CurrentValue  # True = Push (outward), False = Pull

        # Interactive sculpting loop: pick points on surface
        Rhino.RhinoApp.WriteLine(
            "Click on surface to sculpt.  Press Enter or Escape to finish."
        )

        sculpt_count = 0

        while True:
            gp = Rhino.Input.Custom.GetPoint()
            gp.SetCommandPrompt("Pick sculpt point (Enter to finish)")
            gp.AcceptNothing(True)
            gp.Constrain(geom, False)

            res = gp.Get()
            if res == Rhino.Input.GetResult.Nothing:
                break
            if res != Rhino.Input.GetResult.Point:
                break

            hit_pt = gp.Point()
            direction_sign = 1.0 if push else -1.0

            # Apply deformation based on geometry type
            if isinstance(geom, Rhino.Geometry.Mesh):
                self._sculpt_mesh(
                    geom, hit_pt, brush_radius,
                    strength * direction_sign,
                )
                doc.Objects.Replace(rhino_obj.Id, geom)
            elif isinstance(geom, Rhino.Geometry.Brep):
                self._sculpt_brep(
                    doc, rhino_obj, geom, hit_pt,
                    brush_radius, strength * direction_sign,
                )
            elif isinstance(geom, Rhino.Geometry.SubD):
                self._sculpt_subd(
                    geom, hit_pt, brush_radius,
                    strength * direction_sign,
                )
                doc.Objects.Replace(rhino_obj.Id, geom)

            sculpt_count += 1
            doc.Views.Redraw()

        Rhino.RhinoApp.WriteLine(f"Sculpting complete: {sculpt_count} stroke(s).")
        return Rhino.Commands.Result.Success

    def _sculpt_mesh(
        self,
        mesh: Rhino.Geometry.Mesh,
        center: Rhino.Geometry.Point3d,
        radius: float,
        strength: float,
    ) -> None:
        """Deform mesh vertices near *center* within *radius*."""
        for i in range(mesh.Vertices.Count):
            v = mesh.Vertices[i]
            pt = Rhino.Geometry.Point3d(v.X, v.Y, v.Z)
            dist = pt.DistanceTo(center)
            if dist < radius:
                # Gaussian falloff
                falloff = math.exp(-(dist * dist) / (2.0 * (radius / 3.0) ** 2))
                # Get normal at vertex
                n = mesh.Normals[i]
                normal = Rhino.Geometry.Vector3d(n.X, n.Y, n.Z)
                normal.Unitize()
                offset = normal * strength * falloff
                new_pt = Rhino.Geometry.Point3f(
                    float(pt.X + offset.X),
                    float(pt.Y + offset.Y),
                    float(pt.Z + offset.Z),
                )
                mesh.Vertices.SetVertex(i, new_pt)

        mesh.Normals.ComputeNormals()

    def _sculpt_brep(
        self,
        doc: Rhino.RhinoDoc,
        rhino_obj: Rhino.DocObjects.RhinoObject,
        brep: Rhino.Geometry.Brep,
        center: Rhino.Geometry.Point3d,
        radius: float,
        strength: float,
    ) -> None:
        """Deform brep by adjusting NURBS surface control points."""
        modified = brep.DuplicateBrep()
        changed = False

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
                    dist = pt.DistanceTo(center)
                    if dist < radius:
                        falloff = math.exp(
                            -(dist * dist) / (2.0 * (radius / 3.0) ** 2)
                        )
                        # Use Z-up as default normal for brep CPs
                        dz = strength * falloff
                        new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                        nurbs.Points.SetControlPoint(
                            u_idx, v_idx,
                            Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                        )
                        changed = True

        if changed:
            doc.Objects.Replace(rhino_obj.Id, modified)

    def _sculpt_subd(
        self,
        subd: Rhino.Geometry.SubD,
        center: Rhino.Geometry.Point3d,
        radius: float,
        strength: float,
    ) -> None:
        """Deform SubD vertices near *center*."""
        for i in range(subd.Vertices.Count):
            v = subd.Vertices[i]
            pt = v.ControlNetPoint
            dist = pt.DistanceTo(center)
            if dist < radius:
                falloff = math.exp(
                    -(dist * dist) / (2.0 * (radius / 3.0) ** 2)
                )
                # Use surface normal at vertex if available
                normal = v.SurfaceNormal()
                if normal is None or not normal.IsValid:
                    normal = Rhino.Geometry.Vector3d(0, 0, 1)
                normal.Unitize()
                offset = normal * strength * falloff
                new_pt = Rhino.Geometry.Point3d(
                    pt.X + offset.X, pt.Y + offset.Y, pt.Z + offset.Z
                )
                v.ControlNetPoint = new_pt


# ---------------------------------------------------------------------------
#  BlendSurfaceToSurface
# ---------------------------------------------------------------------------

class BlendSurfaceToSurface(Rhino.Commands.Command):
    """Create a smooth blend surface between two surfaces.

    Picks an edge on each surface and creates a G2-continuous blend
    surface connecting them.
    """

    _instance: BlendSurfaceToSurface | None = None

    def __init__(self):
        super().__init__()
        BlendSurfaceToSurface._instance = self

    @classmethod
    @property
    def Instance(cls) -> BlendSurfaceToSurface | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "BlendSurfaceToSurface"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select first surface edge
        go1 = Rhino.Input.Custom.GetObject()
        go1.SetCommandPrompt("Select first surface edge")
        go1.GeometryFilter = Rhino.DocObjects.ObjectType.EdgeFilter
        go1.Get()
        if go1.CommandResult() != Rhino.Commands.Result.Success:
            return go1.CommandResult()

        edge1_ref = go1.Object(0)
        face1 = edge1_ref.Face()
        edge1 = edge1_ref.Edge()
        if face1 is None or edge1 is None:
            Rhino.RhinoApp.WriteLine("Invalid first edge selection.")
            return Rhino.Commands.Result.Failure

        # Select second surface edge
        go2 = Rhino.Input.Custom.GetObject()
        go2.SetCommandPrompt("Select second surface edge")
        go2.GeometryFilter = Rhino.DocObjects.ObjectType.EdgeFilter
        go2.EnablePreSelect(False, True)
        go2.Get()
        if go2.CommandResult() != Rhino.Commands.Result.Success:
            return go2.CommandResult()

        edge2_ref = go2.Object(0)
        face2 = edge2_ref.Face()
        edge2 = edge2_ref.Edge()
        if face2 is None or edge2 is None:
            Rhino.RhinoApp.WriteLine("Invalid second edge selection.")
            return Rhino.Commands.Result.Failure

        # Blend options
        go_opt = Rhino.Input.Custom.GetOption()
        go_opt.SetCommandPrompt("Blend options")
        continuity_list = ["Position", "Tangent", "Curvature"]
        go_opt.AddOptionList("Continuity", continuity_list, 2)

        while True:
            res = go_opt.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        Rhino.RhinoApp.WriteLine("Creating blend surface ...")

        # Use Rhino's built-in BlendSurface
        blend_continuity = Rhino.Geometry.BlendContinuity.Curvature

        breps = Rhino.Geometry.Brep.CreateBlendSurface(
            face1, edge1, face1.Domain(0), False,
            face2, edge2, face2.Domain(0), False,
            blend_continuity, blend_continuity,
            0.01,
        )

        if breps and len(breps) > 0:
            for b in breps:
                if b is not None and b.IsValid:
                    attrs = Rhino.DocObjects.ObjectAttributes()
                    attrs.Name = "BlendSurface"
                    doc.Objects.AddBrep(b, attrs)

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Blend surface created.")
            return Rhino.Commands.Result.Success
        else:
            # Fallback: create a loft between the edge curves
            Rhino.RhinoApp.WriteLine(
                "  Native blend failed; attempting loft fallback ..."
            )
            curve1 = edge1.EdgeCurve
            curve2 = edge2.EdgeCurve
            if curve1 is not None and curve2 is not None:
                loft_breps = Rhino.Geometry.Brep.CreateFromLoft(
                    [curve1, curve2],
                    Rhino.Geometry.Point3d.Unset,
                    Rhino.Geometry.Point3d.Unset,
                    Rhino.Geometry.LoftType.Normal,
                    False,
                )
                if loft_breps and len(loft_breps) > 0:
                    for b in loft_breps:
                        if b is not None and b.IsValid:
                            attrs = Rhino.DocObjects.ObjectAttributes()
                            attrs.Name = "BlendSurface_Loft"
                            doc.Objects.AddBrep(b, attrs)
                    doc.Views.Redraw()
                    Rhino.RhinoApp.WriteLine("Loft blend surface created.")
                    return Rhino.Commands.Result.Success

            Rhino.RhinoApp.WriteLine("Blend surface creation failed.")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  GirthCurveAveraging
# ---------------------------------------------------------------------------

class GirthCurveAveraging(Rhino.Commands.Command):
    """Average girth measurement curves.

    Selects multiple girth-section curves and creates an averaged
    curve that represents the mean cross-sectional profile.
    """

    _instance: GirthCurveAveraging | None = None

    def __init__(self):
        super().__init__()
        GirthCurveAveraging._instance = self

    @classmethod
    @property
    def Instance(cls) -> GirthCurveAveraging | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "GirthCurveAveraging"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select multiple curves
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select girth curves to average (minimum 2)")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
        go.GetMultiple(2, 0)
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        curves: List[Rhino.Geometry.Curve] = []
        for i in range(go.ObjectCount):
            crv = go.Object(i).Curve()
            if crv is not None:
                curves.append(crv)

        if len(curves) < 2:
            Rhino.RhinoApp.WriteLine("At least 2 curves are required.")
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine(f"Averaging {len(curves)} girth curve(s) ...")

        # Rebuild all curves to the same point count for averaging
        max_point_count = 0
        for crv in curves:
            nurbs = crv.ToNurbsCurve()
            if nurbs is not None and nurbs.Points.Count > max_point_count:
                max_point_count = nurbs.Points.Count

        target_count = max(max_point_count, 20)

        rebuilt: List[Rhino.Geometry.NurbsCurve] = []
        for crv in curves:
            r = crv.Rebuild(target_count, 3, True)
            if r is not None:
                rebuilt.append(r.ToNurbsCurve())
            else:
                nurbs = crv.ToNurbsCurve()
                if nurbs is not None:
                    rebuilt.append(nurbs)

        if len(rebuilt) < 2:
            Rhino.RhinoApp.WriteLine("Could not rebuild curves for averaging.")
            return Rhino.Commands.Result.Failure

        # Average the control points
        ref_curve = rebuilt[0]
        num_pts = ref_curve.Points.Count
        averaged_pts: List[Rhino.Geometry.Point3d] = []

        for pt_idx in range(num_pts):
            avg_x = 0.0
            avg_y = 0.0
            avg_z = 0.0
            count = 0
            for crv in rebuilt:
                if pt_idx < crv.Points.Count:
                    cp = crv.Points[pt_idx]
                    avg_x += cp.Location.X
                    avg_y += cp.Location.Y
                    avg_z += cp.Location.Z
                    count += 1
            if count > 0:
                averaged_pts.append(Rhino.Geometry.Point3d(
                    avg_x / count, avg_y / count, avg_z / count
                ))

        if len(averaged_pts) < 2:
            Rhino.RhinoApp.WriteLine("Not enough points for averaged curve.")
            return Rhino.Commands.Result.Failure

        # Create the averaged curve
        is_closed = curves[0].IsClosed
        degree = min(3, len(averaged_pts) - 1)
        avg_curve = Rhino.Geometry.Curve.CreateInterpolatedCurve(
            averaged_pts, degree
        )
        if avg_curve is None:
            Rhino.RhinoApp.WriteLine("Failed to create averaged curve.")
            return Rhino.Commands.Result.Failure

        if is_closed and not avg_curve.IsClosed:
            avg_curve.MakeClosed(0.1)

        # Ensure measurement layer
        meas_path = f"{plugin_constants.SLM_LAYER_PREFIX}::Measurements"
        meas_idx = doc.Layers.FindByFullPath(meas_path, -1)
        if meas_idx < 0:
            meas_idx = 0

        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = meas_idx
        attrs.Name = "AveragedGirthCurve"
        attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        attrs.ObjectColor = System.Drawing.Color.FromArgb(0, 200, 200)

        doc.Objects.AddCurve(avg_curve, attrs)
        doc.Views.Redraw()

        # Report girth length
        length = avg_curve.GetLength()
        Rhino.RhinoApp.WriteLine(
            f"Averaged girth curve created.  Length: {length:.2f} mm"
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustSurfacingCurveControlPointPosition
# ---------------------------------------------------------------------------

class AdjustSurfacingCurveControlPointPosition(Rhino.Commands.Command):
    """Fine-tune the position of control points on a surfacing curve.

    Allows numeric entry of coordinates for precise CP placement, as
    opposed to the interactive grip-dragging approach.
    """

    _instance: AdjustSurfacingCurveControlPointPosition | None = None

    def __init__(self):
        super().__init__()
        AdjustSurfacingCurveControlPointPosition._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustSurfacingCurveControlPointPosition | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustSurfacingCurveControlPointPosition"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("3DShoemaker: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select curve
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select surfacing curve")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        obj_ref = go.Object(0)
        curve = obj_ref.Curve()
        rhino_obj = obj_ref.Object()
        if curve is None:
            return Rhino.Commands.Result.Failure

        nurbs = curve.ToNurbsCurve()
        if nurbs is None:
            Rhino.RhinoApp.WriteLine("Cannot convert to NURBS curve.")
            return Rhino.Commands.Result.Failure

        cp_count = nurbs.Points.Count
        Rhino.RhinoApp.WriteLine(f"Curve has {cp_count} control point(s).")

        # List CPs
        for i in range(cp_count):
            cp = nurbs.Points[i]
            Rhino.RhinoApp.WriteLine(
                f"  CP[{i}]: ({cp.Location.X:.3f}, {cp.Location.Y:.3f}, {cp.Location.Z:.3f})"
            )

        # Ask which CP to adjust
        gi = Rhino.Input.Custom.GetInteger()
        gi.SetCommandPrompt(f"Enter control point index (0-{cp_count - 1})")
        gi.SetLowerLimit(0, True)
        gi.SetUpperLimit(cp_count - 1, True)
        gi.Get()
        if gi.CommandResult() != Rhino.Commands.Result.Success:
            return gi.CommandResult()

        cp_index = gi.Number()
        current_cp = nurbs.Points[cp_index]
        current_loc = current_cp.Location

        Rhino.RhinoApp.WriteLine(
            f"Current position: ({current_loc.X:.3f}, {current_loc.Y:.3f}, {current_loc.Z:.3f})"
        )

        # Get new position via options or point pick
        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt("Pick new CP position or enter coordinates")
        gp.SetBasePoint(current_loc, True)
        gp.DrawLineFromPoint(current_loc, True)

        opt_x = Rhino.Input.Custom.OptionDouble(current_loc.X)
        opt_y = Rhino.Input.Custom.OptionDouble(current_loc.Y)
        opt_z = Rhino.Input.Custom.OptionDouble(current_loc.Z)
        gp.AddOptionDouble("X", opt_x)
        gp.AddOptionDouble("Y", opt_y)
        gp.AddOptionDouble("Z", opt_z)

        new_pt: Optional[Rhino.Geometry.Point3d] = None
        while True:
            res = gp.Get()
            if res == Rhino.Input.GetResult.Point:
                new_pt = gp.Point()
                break
            elif res == Rhino.Input.GetResult.Option:
                continue
            else:
                # Use typed-in values
                new_pt = Rhino.Geometry.Point3d(
                    opt_x.CurrentValue,
                    opt_y.CurrentValue,
                    opt_z.CurrentValue,
                )
                break

        if new_pt is None:
            return Rhino.Commands.Result.Cancel

        # Apply the change
        nurbs.Points.SetControlPoint(
            cp_index,
            Rhino.Geometry.ControlPoint(new_pt, current_cp.Weight),
        )

        doc.Objects.Replace(rhino_obj.Id, nurbs)
        doc.Views.Redraw()

        Rhino.RhinoApp.WriteLine(
            f"CP[{cp_index}] moved to ({new_pt.X:.3f}, {new_pt.Y:.3f}, {new_pt.Z:.3f})."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  CopyObjectToMultiplePoints
# ---------------------------------------------------------------------------

class CopyObjectToMultiplePoints(Rhino.Commands.Command):
    """Copy geometry to multiple user-specified locations.

    Selects a source object, then picks or types multiple destination
    points.  A duplicate of the source is placed at each point.
    """

    _instance: CopyObjectToMultiplePoints | None = None

    def __init__(self):
        super().__init__()
        CopyObjectToMultiplePoints._instance = self

    @classmethod
    @property
    def Instance(cls) -> CopyObjectToMultiplePoints | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "CopyObjectToMultiplePoints"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        # Select source object
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select object to copy")
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        obj_ref = go.Object(0)
        src_obj = obj_ref.Object()
        if src_obj is None:
            return Rhino.Commands.Result.Failure

        src_geom = src_obj.Geometry
        src_attrs = src_obj.Attributes

        # Get base point
        gp_base = Rhino.Input.Custom.GetPoint()
        gp_base.SetCommandPrompt("Pick base point (reference origin)")
        gp_base.Get()
        if gp_base.CommandResult() != Rhino.Commands.Result.Success:
            return gp_base.CommandResult()

        base_pt = gp_base.Point()

        # Collect destination points
        Rhino.RhinoApp.WriteLine(
            "Pick destination points.  Press Enter when done."
        )

        dest_points: List[Rhino.Geometry.Point3d] = []

        while True:
            gp = Rhino.Input.Custom.GetPoint()
            gp.SetCommandPrompt(
                f"Pick destination point ({len(dest_points)} placed, Enter to finish)"
            )
            gp.AcceptNothing(True)
            gp.SetBasePoint(base_pt, True)

            res = gp.Get()
            if res == Rhino.Input.GetResult.Point:
                dest_points.append(gp.Point())
            elif res == Rhino.Input.GetResult.Nothing:
                break
            else:
                break

        if not dest_points:
            Rhino.RhinoApp.WriteLine("No destination points specified.")
            return Rhino.Commands.Result.Cancel

        # Copy to each destination
        copied = 0
        for dest_pt in dest_points:
            move_vec = dest_pt - base_pt
            xform = Rhino.Geometry.Transform.Translation(move_vec)

            dup_geom = src_geom.Duplicate()
            dup_geom.Transform(xform)

            dup_attrs = src_attrs.Duplicate()
            name = dup_attrs.Name or ""
            dup_attrs.Name = f"{name}_Copy{copied + 1}" if name else f"Copy{copied + 1}"

            oid = doc.Objects.Add(dup_geom, dup_attrs)
            if oid != System.Guid.Empty:
                copied += 1

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Copied object to {copied} location(s)."
        )
        return Rhino.Commands.Result.Success
