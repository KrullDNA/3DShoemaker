# -*- coding: utf-8 -*-
"""End editing mode and commit or discard changes.

Turns off grips and optionally reverts to the original geometry
stored by EditCurve.

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

__commandname__ = "EndEdit"


def RunCommand(is_interactive):
    doc = sc.doc

    if not sc.sticky.get("FIF_EDIT_ACTIVE", False):
        Rhino.RhinoApp.WriteLine("No editing session is active.")
        return Rhino.Commands.Result.Nothing

    # Ask commit or revert
    go = Rhino.Input.Custom.GetOption()
    go.SetCommandPrompt("Commit or revert changes?")
    go.AddOption("Commit")
    go.AddOption("Revert")
    res = go.Get()

    revert = False
    if res == Rhino.Input.GetResult.Option:
        if go.Option().EnglishName == "Revert":
            revert = True

    editing_id = sc.sticky.get("FIF_EDIT_OBJECT_ID", None)
    original_geom = sc.sticky.get("FIF_EDIT_ORIGINAL_GEOMETRY", None)

    if revert and editing_id is not None and original_geom is not None:
        obj = doc.Objects.FindId(editing_id)
        if obj is not None:
            doc.Objects.Replace(editing_id, original_geom)
            Rhino.RhinoApp.WriteLine("Changes reverted.")

    # Turn off grips
    if editing_id is not None:
        obj = doc.Objects.FindId(editing_id)
        if obj is not None:
            obj.GripsOn = False

    # Reset state
    sc.sticky["FIF_EDIT_ACTIVE"] = False
    sc.sticky["FIF_EDIT_OBJECT_ID"] = None
    sc.sticky["FIF_EDIT_ORIGINAL_GEOMETRY"] = None

    doc.Views.Redraw()

    if not revert:
        Rhino.RhinoApp.WriteLine("Editing complete. Changes committed.")
    return Rhino.Commands.Result.Success
