# -*- coding: utf-8 -*-
"""Fine-tune the position of control points on a surfacing curve.

Allows numeric entry of coordinates for precise CP placement, as
opposed to the interactive grip-dragging approach.

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

__commandname__ = "AdjustSurfacingCurveControlPointPosition"


def RunCommand(is_interactive):
    doc = sc.doc

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
    Rhino.RhinoApp.WriteLine(
        "Curve has {0} control point(s).".format(cp_count)
    )

    # List CPs
    for i in range(cp_count):
        cp = nurbs.Points[i]
        Rhino.RhinoApp.WriteLine(
            "  CP[{0}]: ({1:.3f}, {2:.3f}, {3:.3f})".format(
                i, cp.Location.X, cp.Location.Y, cp.Location.Z
            )
        )

    # Ask which CP to adjust
    gi = Rhino.Input.Custom.GetInteger()
    gi.SetCommandPrompt(
        "Enter control point index (0-{0})".format(cp_count - 1)
    )
    gi.SetLowerLimit(0, True)
    gi.SetUpperLimit(cp_count - 1, True)
    gi.Get()
    if gi.CommandResult() != Rhino.Commands.Result.Success:
        return gi.CommandResult()

    cp_index = gi.Number()
    current_cp = nurbs.Points[cp_index]
    current_loc = current_cp.Location

    Rhino.RhinoApp.WriteLine(
        "Current position: ({0:.3f}, {1:.3f}, {2:.3f})".format(
            current_loc.X, current_loc.Y, current_loc.Z
        )
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

    new_pt = None
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
        "CP[{0}] moved to ({1:.3f}, {2:.3f}, {3:.3f}).".format(
            cp_index, new_pt.X, new_pt.Y, new_pt.Z
        )
    )
    return Rhino.Commands.Result.Success
