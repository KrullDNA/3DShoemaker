# -*- coding: utf-8 -*-
"""Snaps curves to mesh or surface geometry.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import scriptcontext as sc

__commandname__ = "SnapCurves"


def _snap_curve_to_surface(curve, target_geom, tolerance):
    """Snap a curve's control points to the nearest point on the target geometry."""
    if not isinstance(curve, rg.NurbsCurve):
        curve = curve.ToNurbsCurve()
    if curve is None:
        return None

    new_curve = curve.Duplicate()
    if not isinstance(new_curve, rg.NurbsCurve):
        return None

    moved = False
    for i in range(new_curve.Points.Count):
        cp = new_curve.Points[i]
        pt = cp.Location

        closest_pt = None
        if isinstance(target_geom, rg.Mesh):
            mesh_pt = target_geom.ClosestPoint(pt)
            if mesh_pt is not None:
                closest_pt = mesh_pt
        elif isinstance(target_geom, rg.Brep):
            result = target_geom.ClosestPoint(pt)
            if result is not None and len(result) > 0:
                closest_pt = result[0]
        elif isinstance(target_geom, rg.Surface):
            found, u, v = target_geom.ClosestPoint(pt)
            if found:
                closest_pt = target_geom.PointAt(u, v)

        if closest_pt is not None:
            new_curve.Points.SetPoint(i, closest_pt)
            moved = True

    if moved:
        return new_curve
    return None


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        go_curve = ric.GetObject()
        go_curve.SetCommandPrompt("Select curves to snap")
        go_curve.GeometryFilter = rdo.ObjectType.Curve
        go_curve.GetMultiple(1, 0)
        if go_curve.CommandResult() != rc.Result.Success:
            return go_curve.CommandResult()

        go_target = ric.GetObject()
        go_target.SetCommandPrompt("Select target mesh or surface")
        go_target.GeometryFilter = (
            rdo.ObjectType.Mesh | rdo.ObjectType.Brep | rdo.ObjectType.Surface
        )
        go_target.Get()
        if go_target.CommandResult() != rc.Result.Success:
            return go_target.CommandResult()

        target_geom = go_target.Object(0).Geometry()
        tolerance = doc.ModelAbsoluteTolerance

        snapped_count = 0
        for i in range(go_curve.ObjectCount):
            curve = go_curve.Object(i).Curve()
            if curve is None:
                continue

            snapped = _snap_curve_to_surface(curve, target_geom, tolerance)
            if snapped is not None:
                doc.Objects.AddCurve(snapped)
                snapped_count += 1

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Snapped {0} curve(s) to target.".format(snapped_count))
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error snapping curves: {0}".format(e))
        return rc.Result.Failure
