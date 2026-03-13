# -*- coding: utf-8 -*-
"""Move object control points (grips) by a specified vector.

Selects grip points on an object and translates them by a user-
supplied distance and direction.

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

__commandname__ = "MoveObjectGrips"


def RunCommand(is_interactive):
    doc = sc.doc

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

    selected_indices = []
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
        "Moving {0} grip(s) by ({1:.3f}, {2:.3f}, {3:.3f}) ...".format(
            len(selected_indices), move_vec.X, move_vec.Y, move_vec.Z
        )
    )

    # Move selected grips
    xform = Rhino.Geometry.Transform.Translation(move_vec)
    for idx in selected_indices:
        if idx < len(grips):
            grips[idx].Move(xform)

    doc.Objects.GripUpdate(rhino_obj, True)
    doc.Views.Redraw()

    Rhino.RhinoApp.WriteLine(
        "Moved {0} grip point(s).".format(len(selected_indices))
    )
    return Rhino.Commands.Result.Success
