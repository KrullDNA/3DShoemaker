# -*- coding: utf-8 -*-
"""Open interactive morph form for visual morphing.

Presents an Eto dialog where the user can pick source/target
references and adjust morph parameters before applying.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import math

import Rhino
import Rhino.Commands
import Rhino.Display
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Geometry.Morphs
import Rhino.Input
import Rhino.Input.Custom
import Rhino.RhinoApp
import scriptcontext as sc
import System

__commandname__ = "NewMorph"


# ---------------------------------------------------------------------------
#  Inlined helper functions (same as Morph_cmd.py)
# ---------------------------------------------------------------------------

def _pick_points(prompt, min_count=1):
    """Prompt the user to pick one or more points."""
    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt(prompt)
    gp.AcceptNothing(True)
    points = []
    while True:
        if points:
            gp.SetCommandPrompt(
                "{0} ({1} picked, Enter to finish)".format(prompt, len(points))
            )
        result = gp.Get()
        if result == Rhino.Input.GetResult.Point:
            points.append(gp.Point())
        elif result == Rhino.Input.GetResult.Nothing:
            break
        else:
            if len(points) < min_count:
                return None
            break
    if len(points) >= min_count:
        return points
    return None


def _pick_objects(prompt, filter_type=None, allow_multiple=True):
    """Prompt the user to select one or more objects."""
    if filter_type is None:
        filter_type = Rhino.DocObjects.ObjectType.AnyObject
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(prompt)
    go.GeometryFilter = filter_type
    if allow_multiple:
        go.GetMultiple(1, 0)
    else:
        go.Get()
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return None
    return [go.Object(i) for i in range(go.ObjectCount)]


def _pick_mesh(prompt):
    """Prompt the user to select a single mesh."""
    refs = _pick_objects(prompt, Rhino.DocObjects.ObjectType.Mesh, allow_multiple=False)
    if refs:
        return refs[0]
    return None


class _PointToPointMorph(Rhino.Geometry.SpaceMorph):
    """Weighted inverse-distance SpaceMorph."""

    def __init__(self, source_pts, target_pts, tolerance=0.1):
        super(_PointToPointMorph, self).__init__()
        self._sources = list(source_pts)
        self._targets = list(target_pts)
        self._tol = tolerance
        self.Tolerance = tolerance

    def MorphPoint(self, point):
        displacement = Rhino.Geometry.Vector3d.Zero
        total_weight = 0.0
        for i in range(len(self._sources)):
            dist = point.DistanceTo(self._sources[i])
            weight = 1.0 / (dist + self._tol) ** 2
            total_weight += weight
            delta = self._targets[i] - self._sources[i]
            displacement += delta * weight
        if total_weight > 0:
            displacement /= total_weight
        return point + displacement


def _get_sources_and_targets(source_mesh, target_mesh):
    sources = []
    targets = []
    for v in source_mesh.Vertices:
        src_pt = Rhino.Geometry.Point3d(v.X, v.Y, v.Z)
        closest = target_mesh.ClosestPoint(src_pt)
        if closest is not None:
            sources.append(src_pt)
            targets.append(closest)
    return sources, targets


def _ffd(geometry, source_points, target_points, tolerance=0.1):
    if len(source_points) != len(target_points):
        return None
    if len(source_points) == 0:
        return geometry.Duplicate()
    morph = _PointToPointMorph(source_points, target_points, tolerance)
    result = geometry.Duplicate()
    if morph.Morph(result):
        return result
    return None


def _morph_mesh_p2p(mesh, source_pts, target_pts, tolerance=0.1):
    if len(source_pts) != len(target_pts) or len(source_pts) == 0:
        return None
    result_mesh = mesh.Duplicate()
    vertices = result_mesh.Vertices
    for vi in range(vertices.Count):
        v = Rhino.Geometry.Point3d(vertices[vi].X, vertices[vi].Y, vertices[vi].Z)
        displacement = Rhino.Geometry.Vector3d.Zero
        total_weight = 0.0
        for si in range(len(source_pts)):
            dist = v.DistanceTo(source_pts[si])
            weight = 1.0 / (dist + tolerance) ** 2
            total_weight += weight
            delta = target_pts[si] - source_pts[si]
            displacement += delta * weight
        if total_weight > 0:
            displacement /= total_weight
            new_pt = v + displacement
            vertices.SetVertex(vi, new_pt.X, new_pt.Y, new_pt.Z)
    result_mesh.Normals.ComputeNormals()
    return result_mesh


def _morph_mesh_m2m(mesh, source_mesh, target_mesh, tolerance=0.1):
    sources, targets = _get_sources_and_targets(source_mesh, target_mesh)
    if not sources:
        return None
    return _morph_mesh_p2p(mesh, sources, targets, tolerance)


def _forefoot_twist_morph(geometry, axis_origin, axis_direction,
                          angle_radians, start_distance=0.0,
                          end_distance=100.0):
    axis_line = Rhino.Geometry.Line(
        axis_origin,
        axis_origin + axis_direction * end_distance,
    )
    twist = Rhino.Geometry.Morphs.TwistSpaceMorph()
    twist.TwistAxis = axis_line
    twist.TwistAngleRadians = angle_radians
    result = geometry.Duplicate()
    if twist.Morph(result):
        return result
    return None


def _rearfoot_twist_morph(geometry, axis_origin, axis_direction,
                          angle_radians, start_distance=0.0,
                          end_distance=100.0):
    axis_line = Rhino.Geometry.Line(
        axis_origin,
        axis_origin - axis_direction * end_distance,
    )
    twist = Rhino.Geometry.Morphs.TwistSpaceMorph()
    twist.TwistAxis = axis_line
    twist.TwistAngleRadians = angle_radians
    result = geometry.Duplicate()
    if twist.Morph(result):
        return result
    return None


# ---------------------------------------------------------------------------
#  Sub-operations (same logic as Morph_cmd.py)
# ---------------------------------------------------------------------------

def _run_ffd(doc, tol):
    obj_refs = _pick_objects("Select object(s) to deform")
    if not obj_refs:
        return Rhino.Commands.Result.Cancel
    Rhino.RhinoApp.WriteLine("Pick source control points:")
    source = _pick_points("Source points", 1)
    if not source:
        return Rhino.Commands.Result.Cancel
    Rhino.RhinoApp.WriteLine("Pick {0} target control points:".format(len(source)))
    target = _pick_points("Target points", len(source))
    if not target or len(target) != len(source):
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Source/target point count mismatch.")
        return Rhino.Commands.Result.Failure
    for ref in obj_refs:
        geom = ref.Geometry()
        if geom is None:
            continue
        morphed = _ffd(geom, source, target, tol)
        if morphed is not None:
            doc.Objects.Replace(ref.ObjectId, morphed)
    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] FFD morph applied.")
    return Rhino.Commands.Result.Success


def _run_p2p(doc, tol):
    mesh_ref = _pick_mesh("Select mesh to morph")
    if not mesh_ref:
        return Rhino.Commands.Result.Cancel
    mesh = mesh_ref.Mesh()
    if mesh is None:
        return Rhino.Commands.Result.Failure
    source = _pick_points("Source points", 1)
    if not source:
        return Rhino.Commands.Result.Cancel
    target = _pick_points("Target points ({0} needed)".format(len(source)), len(source))
    if not target or len(target) != len(source):
        return Rhino.Commands.Result.Failure
    morphed = _morph_mesh_p2p(mesh, source, target, tol)
    if morphed is not None:
        doc.Objects.Replace(mesh_ref.ObjectId, morphed)
        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] P2P morph applied.")
        return Rhino.Commands.Result.Success
    return Rhino.Commands.Result.Failure


def _run_m2m(doc, tol):
    mesh_ref = _pick_mesh("Select mesh to morph")
    if not mesh_ref:
        return Rhino.Commands.Result.Cancel
    mesh = mesh_ref.Mesh()
    src_ref = _pick_mesh("Select SOURCE reference mesh")
    if not src_ref:
        return Rhino.Commands.Result.Cancel
    src_mesh = src_ref.Mesh()
    tgt_ref = _pick_mesh("Select TARGET reference mesh")
    if not tgt_ref:
        return Rhino.Commands.Result.Cancel
    tgt_mesh = tgt_ref.Mesh()
    morphed = _morph_mesh_m2m(mesh, src_mesh, tgt_mesh, tol)
    if morphed is not None:
        doc.Objects.Replace(mesh_ref.ObjectId, morphed)
        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] M2M morph applied.")
        return Rhino.Commands.Result.Success
    return Rhino.Commands.Result.Failure


def _run_twist(doc, forefoot=True):
    obj_refs = _pick_objects("Select object(s) to twist")
    if not obj_refs:
        return Rhino.Commands.Result.Cancel
    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt("Twist axis origin")
    if gp.Get() != Rhino.Input.GetResult.Point:
        return Rhino.Commands.Result.Cancel
    axis_origin = gp.Point()
    gn = Rhino.Input.Custom.GetNumber()
    gn.SetCommandPrompt("Twist angle (degrees)")
    gn.SetDefaultNumber(5.0)
    if gn.Get() != Rhino.Input.GetResult.Number:
        return Rhino.Commands.Result.Cancel
    angle_deg = gn.Number()
    angle_rad = math.radians(angle_deg)
    gn2 = Rhino.Input.Custom.GetNumber()
    gn2.SetCommandPrompt("Twist end distance (mm)")
    gn2.SetDefaultNumber(100.0)
    if gn2.Get() != Rhino.Input.GetResult.Number:
        return Rhino.Commands.Result.Cancel
    end_dist = gn2.Number()
    axis_dir = Rhino.Geometry.Vector3d.YAxis
    if forefoot:
        morph_fn = _forefoot_twist_morph
    else:
        morph_fn = _rearfoot_twist_morph
    for ref in obj_refs:
        geom = ref.Geometry()
        if geom is None:
            continue
        morphed = morph_fn(geom, axis_origin, axis_dir, angle_rad, 0.0, end_dist)
        if morphed is not None:
            doc.Objects.Replace(ref.ObjectId, morphed)
    doc.Views.Redraw()
    if forefoot:
        label = "ForeFootTwist"
    else:
        label = "RearFootTwist"
    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] {0} morph applied ({1} deg).".format(label, angle_deg)
    )
    return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  RunCommand
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Interactive Morph")

    # Try to show Eto-based morph form
    try:
        import Eto.Forms as ef
        import Eto.Drawing as ed

        dlg = ef.Dialog()
        dlg.Title = "Feet in Focus Shoe Kit - Morph"
        dlg.ClientSize = ed.Size(450, 380)
        dlg.Padding = ef.Padding(10)

        layout = ef.DynamicLayout()
        layout.DefaultSpacing = ed.Size(5, 5)

        layout.AddRow(ef.Label(Text="Morph Operation:"))

        op_dropdown = ef.DropDown()
        op_dropdown.Items.Add(ef.ListItem(Text="Point-to-Point", Key="P2P"))
        op_dropdown.Items.Add(ef.ListItem(Text="Mesh-to-Mesh", Key="M2M"))
        op_dropdown.Items.Add(ef.ListItem(Text="Free-Form Deformation", Key="FFD"))
        op_dropdown.Items.Add(ef.ListItem(Text="ForeFootTwist", Key="FT"))
        op_dropdown.Items.Add(ef.ListItem(Text="RearFootTwist", Key="RT"))
        op_dropdown.SelectedIndex = 0
        layout.AddRow(op_dropdown)

        layout.AddRow(ef.Label(Text="Tolerance:"))
        tol_input = ef.NumericStepper()
        tol_input.Value = doc.ModelAbsoluteTolerance
        tol_input.MinValue = 0.001
        tol_input.MaxValue = 10.0
        tol_input.DecimalPlaces = 4
        tol_input.Increment = 0.01
        layout.AddRow(tol_input)

        layout.AddRow(ef.Label(Text="Twist Angle (degrees, for twist ops):"))
        angle_input = ef.NumericStepper()
        angle_input.Value = 5.0
        angle_input.MinValue = -90.0
        angle_input.MaxValue = 90.0
        angle_input.DecimalPlaces = 1
        angle_input.Increment = 1.0
        layout.AddRow(angle_input)

        layout.AddSpace()

        morph_result = [Rhino.Commands.Result.Cancel]
        selected_op = ["P2P"]

        def on_apply(sender, e):
            idx = op_dropdown.SelectedIndex
            if idx >= 0:
                selected_op[0] = op_dropdown.Items[idx].Key
            morph_result[0] = Rhino.Commands.Result.Success
            dlg.Close()

        def on_cancel(sender, e):
            dlg.Close()

        btn_apply = ef.Button(Text="Apply Morph")
        btn_cancel = ef.Button(Text="Cancel")
        btn_apply.Click += on_apply
        btn_cancel.Click += on_cancel

        btn_row = ef.DynamicLayout()
        btn_row.AddRow(None, btn_cancel, btn_apply)
        layout.AddRow(btn_row)

        dlg.Content = layout
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

        if morph_result[0] != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        # Delegate to the appropriate sub-operation
        op = selected_op[0]
        tol = tol_input.Value

        if op == "P2P":
            return _run_p2p(doc, tol)
        elif op == "M2M":
            return _run_m2m(doc, tol)
        elif op == "FFD":
            return _run_ffd(doc, tol)
        elif op == "FT":
            return _run_twist(doc, forefoot=True)
        elif op == "RT":
            return _run_twist(doc, forefoot=False)

        return Rhino.Commands.Result.Nothing

    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Morph form error: {0}. "
            "Falling back to command-line interface.".format(ex)
        )
        # Fall back to command-line morph selection
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Morph operation")
        gs.AcceptNothing(False)
        opt_ffd = gs.AddOption("FFD")
        opt_p2p = gs.AddOption("PointToPoint")
        opt_m2m = gs.AddOption("MeshToMesh")
        opt_twist_fore = gs.AddOption("ForeFootTwist")
        opt_twist_rear = gs.AddOption("RearFootTwist")

        result = gs.Get()
        if result != Rhino.Input.GetResult.Option:
            return Rhino.Commands.Result.Cancel

        option_idx = gs.OptionIndex()
        tol = doc.ModelAbsoluteTolerance

        if option_idx == opt_ffd:
            return _run_ffd(doc, tol)
        if option_idx == opt_p2p:
            return _run_p2p(doc, tol)
        if option_idx == opt_m2m:
            return _run_m2m(doc, tol)
        if option_idx == opt_twist_fore:
            return _run_twist(doc, forefoot=True)
        if option_idx == opt_twist_rear:
            return _run_twist(doc, forefoot=False)

        return Rhino.Commands.Result.Nothing
