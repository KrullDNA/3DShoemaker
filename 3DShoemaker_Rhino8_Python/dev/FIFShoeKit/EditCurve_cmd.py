# -*- coding: utf-8 -*-
"""Enter curve editing mode with grip points enabled.

Selects a curve, turns on its control-point grips, and stores the
original geometry so it can be reverted by EndEdit.

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
import System
import System.Drawing

__commandname__ = "EditCurve"


def RunCommand(is_interactive):
    doc = sc.doc

    # Check if an editing session is already active
    if sc.sticky.get("FIF_EDIT_ACTIVE", False):
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
    sc.sticky["FIF_EDIT_ORIGINAL_GEOMETRY"] = curve.DuplicateCurve()
    sc.sticky["FIF_EDIT_OBJECT_ID"] = curve_obj.Id
    sc.sticky["FIF_EDIT_ACTIVE"] = True

    # Enable grips
    curve_obj.GripsOn = True
    doc.Views.Redraw()

    Rhino.RhinoApp.WriteLine(
        "Curve editing mode active.  Drag grip points to edit.  "
        "Run EndEdit to commit changes."
    )
    return Rhino.Commands.Result.Success
