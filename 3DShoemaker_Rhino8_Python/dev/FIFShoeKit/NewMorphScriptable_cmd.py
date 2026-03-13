# -*- coding: utf-8 -*-
"""Scriptable (non-interactive) morph command.

Accepts morph type, source/target object IDs or point arrays via
command-line options.

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

__commandname__ = "NewMorphScriptable"


# ---------------------------------------------------------------------------
#  Inlined helper functions
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


def _compile_points(mesh, sample_count=0):
    vertices = [
        Rhino.Geometry.Point3d(v.X, v.Y, v.Z)
        for v in mesh.Vertices
    ]
    if sample_count > 0 and sample_count < len(vertices):
        step = max(1, len(vertices) // sample_count)
        vertices = vertices[::step]
    return vertices


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


def _morph_mesh_m2p(mesh, source_mesh, target_pts, tolerance=0.1):
    source_pts = _compile_points(source_mesh, len(target_pts))
    n = min(len(source_pts), len(target_pts))
    return _morph_mesh_p2p(mesh, source_pts[:n], target_pts[:n], tolerance)


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


def _morph_nurbs_surfaces_p2p(surfaces, extra_points, source_pts,
                               target_pts, tolerance=0.1):
    morph = _PointToPointMorph(source_pts, target_pts, tolerance)
    morphed_surfaces = []
    for srf in surfaces:
        dup = srf.Duplicate()
        if morph.Morph(dup):
            morphed_surfaces.append(dup)
        else:
            morphed_surfaces.append(srf.Duplicate())
    morphed_points = []
    for pt in extra_points:
        morphed_points.append(morph.MorphPoint(pt))
    return morphed_surfaces, morphed_points


# ---------------------------------------------------------------------------
#  Sub-operations
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


def _run_m2p(doc, tol):
    mesh_ref = _pick_mesh("Select mesh to morph")
    if not mesh_ref:
        return Rhino.Commands.Result.Cancel
    mesh = mesh_ref.Mesh()
    src_ref = _pick_mesh("Select SOURCE reference mesh")
    if not src_ref:
        return Rhino.Commands.Result.Cancel
    src_mesh = src_ref.Mesh()
    target = _pick_points("Target points", 1)
    if not target:
        return Rhino.Commands.Result.Cancel
    morphed = _morph_mesh_m2p(mesh, src_mesh, target, tol)
    if morphed is not None:
        doc.Objects.Replace(mesh_ref.ObjectId, morphed)
        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] M2P morph applied.")
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


def _run_nurbs_p2p(doc, tol):
    obj_refs = _pick_objects(
        "Select NURBS surface(s) to morph",
        Rhino.DocObjects.ObjectType.Surface,
    )
    if not obj_refs:
        return Rhino.Commands.Result.Cancel
    source = _pick_points("Source points", 1)
    if not source:
        return Rhino.Commands.Result.Cancel
    target = _pick_points("Target points ({0} needed)".format(len(source)), len(source))
    if not target or len(target) != len(source):
        return Rhino.Commands.Result.Failure
    surfaces = []
    obj_ids = []
    for ref in obj_refs:
        srf = ref.Surface()
        if srf is not None:
            nurbs = srf.ToNurbsSurface()
            if nurbs is not None:
                surfaces.append(nurbs)
                obj_ids.append(ref.ObjectId)
    morphed_surfaces, _ = _morph_nurbs_surfaces_p2p(
        surfaces, [], source, target, tol
    )
    for i in range(len(obj_ids)):
        brep = morphed_surfaces[i].ToBrep()
        if brep is not None:
            doc.Objects.Replace(obj_ids[i], brep)
    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] NURBS P2P morph applied.")
    return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  RunCommand
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Morph type (P2P/M2M/FFD/ForeFootTwist/RearFootTwist)")
    gs.SetDefaultString("P2P")
    gs.AcceptNothing(True)

    opt_tol = Rhino.Input.Custom.OptionDouble(doc.ModelAbsoluteTolerance)
    gs.AddOptionDouble("Tolerance", opt_tol)

    while True:
        result = gs.Get()
        if result == Rhino.Input.GetResult.Option:
            continue
        break

    if gs.CommandResult() != Rhino.Commands.Result.Success:
        return gs.CommandResult()

    morph_type = (gs.StringResult() or "P2P").strip().upper()
    tol = opt_tol.CurrentValue

    if morph_type == "P2P":
        return _run_p2p(doc, tol)
    elif morph_type == "M2M":
        return _run_m2m(doc, tol)
    elif morph_type == "M2P":
        return _run_m2p(doc, tol)
    elif morph_type == "FFD":
        return _run_ffd(doc, tol)
    elif morph_type in ("FOREFOOTTWIST", "FT"):
        return _run_twist(doc, forefoot=True)
    elif morph_type in ("REARFOOTTWIST", "RT"):
        return _run_twist(doc, forefoot=False)
    elif morph_type == "NURBS":
        return _run_nurbs_p2p(doc, tol)
    else:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Unknown morph type: {0}".format(morph_type)
        )
        return Rhino.Commands.Result.Failure
