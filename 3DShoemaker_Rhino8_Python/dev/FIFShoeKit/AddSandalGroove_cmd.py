# -*- coding: utf-8 -*-
"""Add a groove to a sandal sole.

The groove follows a user-selected curve on the sole surface.
Typically used for strap attachment channels.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc
import System

__commandname__ = "AddSandalGroove"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _create_groove(sole_brep, groove_curve, groove_width, groove_depth):
    """Create a groove in a sole brep along a curve.

    Builds a thin cutter volume along groove_curve and performs a
    boolean difference from sole_brep.
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


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

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
