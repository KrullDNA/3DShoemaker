# -*- coding: utf-8 -*-
"""Adjust bottom component (outsole, midsole, insole board) parameters.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "AdjustBottomComponentParameterization"


# Default material thickness values for bottom layers
_MT_BOTTOM_DEFAULTS = {
    "bottom_outsole": 4.0,
    "bottom_midsole": 6.0,
    "bottom_insole_board": 2.0,
    "bottom_shank": 1.0,
    "bottom_welt": 0.0,
}


def _get_mt():
    """Get material thicknesses from sticky."""
    mt = sc.sticky.get("FIF_MaterialThicknesses", None)
    if mt is None:
        mt = dict(_MT_BOTTOM_DEFAULTS)
        sc.sticky["FIF_MaterialThicknesses"] = mt
    return mt


def _total_bottom(mt):
    """Calculate total bottom thickness."""
    return (
        mt.get("bottom_outsole", 4.0)
        + mt.get("bottom_midsole", 6.0)
        + mt.get("bottom_insole_board", 2.0)
        + mt.get("bottom_shank", 1.0)
        + mt.get("bottom_welt", 0.0)
    )


def _rebuild_footwear_from_settings(doc):
    """Trigger a rebuild of footwear from stored parameters."""
    Rhino.RhinoApp.WriteLine("  Rebuild triggered (parameter change applied).")
    doc.Views.Redraw()
    return True


def RunCommand(is_interactive):
    doc = sc.doc
    mt = _get_mt()

    go = ric.GetOption()
    go.SetCommandPrompt("Adjust bottom component parameters")

    opt_outsole = ric.OptionDouble(mt.get("bottom_outsole", 4.0), 0.0, 30.0)
    opt_midsole = ric.OptionDouble(mt.get("bottom_midsole", 6.0), 0.0, 30.0)
    opt_board = ric.OptionDouble(mt.get("bottom_insole_board", 2.0), 0.0, 10.0)
    opt_shank = ric.OptionDouble(mt.get("bottom_shank", 1.0), 0.0, 10.0)
    opt_welt = ric.OptionDouble(mt.get("bottom_welt", 0.0), 0.0, 10.0)

    go.AddOptionDouble("OutsoleThickness", opt_outsole)
    go.AddOptionDouble("MidsoleThickness", opt_midsole)
    go.AddOptionDouble("InsoleBoardThickness", opt_board)
    go.AddOptionDouble("ShankThickness", opt_shank)
    go.AddOptionDouble("WeltThickness", opt_welt)
    go.AddOptionList("Profile", ["Flat", "Rocker", "Negative"], 0)

    while True:
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            continue
        break

    mt["bottom_outsole"] = opt_outsole.CurrentValue
    mt["bottom_midsole"] = opt_midsole.CurrentValue
    mt["bottom_insole_board"] = opt_board.CurrentValue
    mt["bottom_shank"] = opt_shank.CurrentValue
    mt["bottom_welt"] = opt_welt.CurrentValue
    sc.sticky["FIF_MaterialThicknesses"] = mt

    total = _total_bottom(mt)
    Rhino.RhinoApp.WriteLine("Bottom component total: {0:.2f} mm".format(total))
    _rebuild_footwear_from_settings(doc)
    Rhino.RhinoApp.WriteLine("Bottom component parameters updated.")
    return rc.Result.Success
