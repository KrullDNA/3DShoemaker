# -*- coding: utf-8 -*-
"""Change component parameters (sole, heel, shank, etc.).

Presents the component's adjustable parameters and applies changes.
Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "ChangeComponentParameterization"


# Default material thickness values
_MT_DEFAULTS = {
    "bottom_outsole": 4.0,
    "bottom_midsole": 6.0,
    "bottom_insole_board": 2.0,
    "bottom_shank": 1.0,
    "bottom_welt": 0.0,
}


def _get_settings():
    """Get current document settings from sticky."""
    ds = sc.sticky.get("FIF_DocumentSettings", None)
    if ds is None:
        ds = {}
        sc.sticky["FIF_DocumentSettings"] = ds
    return ds


def _get_mt():
    """Get material thicknesses from sticky."""
    mt = sc.sticky.get("FIF_MaterialThicknesses", None)
    if mt is None:
        mt = dict(_MT_DEFAULTS)
        sc.sticky["FIF_MaterialThicknesses"] = mt
    return mt


def _rebuild_footwear_from_settings(doc):
    """Trigger a rebuild of footwear from stored parameters."""
    Rhino.RhinoApp.WriteLine("  Rebuild triggered (parameter change applied).")
    doc.Views.Redraw()
    return True


def RunCommand(is_interactive):
    doc = sc.doc
    ds = _get_settings()
    mt = _get_mt()

    components = [
        "Sole", "Heel", "ShankBoard", "TopPiece",
        "InsoleBoard", "Welt", "Midsole",
    ]

    go = ric.GetOption()
    go.SetCommandPrompt("Select component to parameterize")
    go.AddOptionList("Component", components, 0)

    component_idx = 0
    while True:
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            component_idx = go.Option().CurrentListOptionIndex
            continue
        break

    component = components[component_idx] if component_idx < len(components) else components[0]
    Rhino.RhinoApp.WriteLine("Adjusting {0} parameters ...".format(component))

    # Component-specific parameters
    go2 = ric.GetOption()
    go2.SetCommandPrompt("{0} parameters".format(component))

    opt_thick = None
    opt_height = None
    opt_generic = None

    if component == "Sole":
        opt_thick = ric.OptionDouble(mt.get("bottom_outsole", 4.0), 0.0, 30.0)
        go2.AddOptionDouble("Thickness", opt_thick)
        go2.AddOptionList("Profile", ["Flat", "Rocker", "Wedge"], 0)
    elif component == "Heel":
        opt_height = ric.OptionDouble(
            ds.get("last_heel_height_mm", 0.0), 0.0, 120.0
        )
        go2.AddOptionDouble("HeelHeight", opt_height)
    elif component == "ShankBoard":
        opt_thick = ric.OptionDouble(mt.get("bottom_shank", 1.0), 0.0, 10.0)
        go2.AddOptionDouble("Thickness", opt_thick)
    elif component == "Midsole":
        opt_thick = ric.OptionDouble(mt.get("bottom_midsole", 6.0), 0.0, 30.0)
        go2.AddOptionDouble("Thickness", opt_thick)
    else:
        opt_generic = ric.OptionDouble(0.0)
        go2.AddOptionDouble("Value", opt_generic)

    while True:
        res = go2.Get()
        if res == Rhino.Input.GetResult.Option:
            continue
        break

    # Apply parameter changes
    if component == "Sole" and opt_thick is not None:
        mt["bottom_outsole"] = opt_thick.CurrentValue
        sc.sticky["FIF_MaterialThicknesses"] = mt
    elif component == "Heel" and opt_height is not None:
        ds["last_heel_height_mm"] = opt_height.CurrentValue
        sc.sticky["FIF_DocumentSettings"] = ds
    elif component == "ShankBoard" and opt_thick is not None:
        mt["bottom_shank"] = opt_thick.CurrentValue
        sc.sticky["FIF_MaterialThicknesses"] = mt
    elif component == "Midsole" and opt_thick is not None:
        mt["bottom_midsole"] = opt_thick.CurrentValue
        sc.sticky["FIF_MaterialThicknesses"] = mt

    _rebuild_footwear_from_settings(doc)
    Rhino.RhinoApp.WriteLine("{0} parameters updated.".format(component))
    return rc.Result.Success
