# -*- coding: utf-8 -*-
"""Average girth measurement curves.

Selects multiple girth-section curves and creates an averaged
curve that represents the mean cross-sectional profile.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import Rhino.RhinoApp
import scriptcontext as sc
import System.Drawing

__commandname__ = "GirthCurveAveraging"

# Layer prefix used by the plugin
_SLM_LAYER_PREFIX = "SLM"


def RunCommand(is_interactive):
    doc = sc.doc

    # Select multiple curves
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select girth curves to average (minimum 2)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
    go.GetMultiple(2, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return go.CommandResult()

    curves = []
    for i in range(go.ObjectCount):
        crv = go.Object(i).Curve()
        if crv is not None:
            curves.append(crv)

    if len(curves) < 2:
        Rhino.RhinoApp.WriteLine("At least 2 curves are required.")
        return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine(
        "Averaging {0} girth curve(s) ...".format(len(curves))
    )

    # Rebuild all curves to the same point count for averaging
    max_point_count = 0
    for crv in curves:
        nurbs = crv.ToNurbsCurve()
        if nurbs is not None and nurbs.Points.Count > max_point_count:
            max_point_count = nurbs.Points.Count

    target_count = max(max_point_count, 20)

    rebuilt = []
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
    averaged_pts = []

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
    meas_path = "{0}::Measurements".format(_SLM_LAYER_PREFIX)
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
        "Averaged girth curve created.  Length: {0:.2f} mm".format(length)
    )
    return Rhino.Commands.Result.Success
