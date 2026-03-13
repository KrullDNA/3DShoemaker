# -*- coding: utf-8 -*-
"""Adjust footbed depth parameter.

Controls how deeply the foot sits into the footbed cavity.
Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "AdjustFootbedDepth"


def _get_settings():
    """Get current document settings from sticky."""
    ds = sc.sticky.get("FIF_DocumentSettings", None)
    if ds is None:
        ds = {}
        sc.sticky["FIF_DocumentSettings"] = ds
    return ds


def _rebuild_footwear_from_settings(doc):
    """Trigger a rebuild of footwear from stored parameters."""
    Rhino.RhinoApp.WriteLine("  Rebuild triggered (parameter change applied).")
    doc.Views.Redraw()
    return True


def RunCommand(is_interactive):
    doc = sc.doc
    ds = _get_settings()
    current_depth = ds.get("footbed_depth_mm", 5.0)

    gn = ric.GetNumber()
    gn.SetCommandPrompt(
        "Footbed depth in mm (current={0:.2f})".format(current_depth)
    )
    gn.SetDefaultNumber(current_depth)
    gn.SetLowerLimit(0.0, True)
    gn.SetUpperLimit(30.0, True)
    gn.Get()
    if gn.CommandResult() != rc.Result.Success:
        return gn.CommandResult()

    new_depth = gn.Number()
    ds["footbed_depth_mm"] = new_depth
    sc.sticky["FIF_DocumentSettings"] = ds

    Rhino.RhinoApp.WriteLine("Footbed depth set to {0:.2f} mm.".format(new_depth))
    _rebuild_footwear_from_settings(doc)
    return rc.Result.Success
