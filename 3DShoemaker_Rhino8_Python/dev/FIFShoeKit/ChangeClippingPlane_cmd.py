# -*- coding: utf-8 -*-
"""Modifies clipping plane position and orientation.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import scriptcontext as sc

__commandname__ = "ChangeClippingPlane"


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        go = ric.GetObject()
        go.SetCommandPrompt("Select clipping plane to modify")
        go.GeometryFilter = rdo.ObjectType.ClipPlane
        go.Get()
        if go.CommandResult() != rc.Result.Success:
            return go.CommandResult()

        obj_ref = go.Object(0)
        clip_obj = obj_ref.Object()

        if clip_obj is None:
            return rc.Result.Failure

        gp = ric.GetPoint()
        gp.SetCommandPrompt("New clipping plane origin")
        gp.Get()
        if gp.CommandResult() != rc.Result.Success:
            return gp.CommandResult()

        new_origin = gp.Point()
        old_bbox = clip_obj.Geometry.GetBoundingBox(True)
        old_center = old_bbox.Center

        move_vec = new_origin - old_center
        xform = rg.Transform.Translation(move_vec)

        doc.Objects.Transform(obj_ref.ObjectId, xform, True)
        doc.Views.Redraw()

        Rhino.RhinoApp.WriteLine("Clipping plane moved.")
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error changing clipping plane: {0}".format(e))
        return rc.Result.Failure
