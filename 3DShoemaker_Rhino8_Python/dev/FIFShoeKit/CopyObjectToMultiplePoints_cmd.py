# -*- coding: utf-8 -*-
"""Copy geometry to multiple user-specified locations.

Selects a source object, then picks or types multiple destination
points.  A duplicate of the source is placed at each point.

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

__commandname__ = "CopyObjectToMultiplePoints"


def RunCommand(is_interactive):
    doc = sc.doc

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

    dest_points = []

    while True:
        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt(
            "Pick destination point ({0} placed, Enter to finish)".format(
                len(dest_points)
            )
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
        if name:
            dup_attrs.Name = "{0}_Copy{1}".format(name, copied + 1)
        else:
            dup_attrs.Name = "Copy{0}".format(copied + 1)

        oid = doc.Objects.Add(dup_geom, dup_attrs)
        if oid != System.Guid.Empty:
            copied += 1

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Copied object to {0} location(s).".format(copied)
    )
    return Rhino.Commands.Result.Success
