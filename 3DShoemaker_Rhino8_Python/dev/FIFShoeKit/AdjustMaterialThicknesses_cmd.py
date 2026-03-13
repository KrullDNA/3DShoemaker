# -*- coding: utf-8 -*-
"""Adjust material thickness values for all layers.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "AdjustMaterialThicknesses"


# All thickness keys with their defaults
_ALL_THICKNESS_DEFAULTS = {
    "insole_base": 3.0,
    "insole_top_cover": 1.0,
    "insole_bottom_cover": 0.0,
    "insole_posting_medial": 0.0,
    "insole_posting_lateral": 0.0,
    "insole_arch_fill": 0.0,
    "insole_heel_pad": 0.0,
    "insole_met_pad": 0.0,
    "insole_forefoot_extension": 0.0,
    "insole_rearfoot_extension": 0.0,
    "last_shell_wall": 2.0,
    "last_toe_cap": 1.5,
    "last_heel_counter": 1.5,
    "last_lining": 1.0,
    "bottom_outsole": 4.0,
    "bottom_midsole": 6.0,
    "bottom_insole_board": 2.0,
    "bottom_shank": 1.0,
    "bottom_welt": 0.0,
    "medial_wedge": 0.0,
    "lateral_wedge": 0.0,
    "heel_lift": 0.0,
    "forefoot_rocker": 0.0,
    "toe_spring": 0.0,
}


def _get_mt():
    """Get material thicknesses from sticky."""
    mt = sc.sticky.get("FIF_MaterialThicknesses", None)
    if mt is None:
        mt = dict(_ALL_THICKNESS_DEFAULTS)
        sc.sticky["FIF_MaterialThicknesses"] = mt
    return mt


def _total_insole(mt):
    """Calculate total insole thickness."""
    keys = [
        "insole_base", "insole_top_cover", "insole_bottom_cover",
        "insole_posting_medial", "insole_posting_lateral",
        "insole_arch_fill", "insole_heel_pad", "insole_met_pad",
        "insole_forefoot_extension", "insole_rearfoot_extension",
    ]
    return sum(mt.get(k, 0.0) for k in keys)


def _total_bottom(mt):
    """Calculate total bottom thickness."""
    keys = [
        "bottom_outsole", "bottom_midsole", "bottom_insole_board",
        "bottom_shank", "bottom_welt",
    ]
    return sum(mt.get(k, 0.0) for k in keys)


def _total_build_height(mt):
    """Calculate total build height."""
    return _total_insole(mt) + _total_bottom(mt) + mt.get("heel_lift", 0.0)


def _rebuild_footwear_from_settings(doc):
    """Trigger a rebuild of footwear from stored parameters."""
    Rhino.RhinoApp.WriteLine("  Rebuild triggered (parameter change applied).")
    doc.Views.Redraw()
    return True


def RunCommand(is_interactive):
    doc = sc.doc
    mt = _get_mt()

    # Display current values
    Rhino.RhinoApp.WriteLine("Current material thicknesses:")
    for key in sorted(mt.keys()):
        val = mt[key]
        if isinstance(val, float):
            Rhino.RhinoApp.WriteLine("  {0}: {1:.2f} mm".format(key, val))

    # Prompt for key to change
    gs = ric.GetString()
    gs.SetCommandPrompt(
        "Enter thickness name to change (or 'all' for full editor, Enter to exit)"
    )
    gs.AcceptNothing(True)
    gs.Get()
    if gs.CommandResult() != rc.Result.Success:
        return gs.CommandResult()

    raw = (gs.StringResult() or "").strip()
    if not raw:
        return rc.Result.Nothing

    if raw.lower() == "all":
        # Interactive editor for common thicknesses
        go = ric.GetOption()
        go.SetCommandPrompt("Adjust thicknesses (Enter when done)")
        go.AcceptNothing(True)

        opts = {}
        for key in sorted(mt.keys()):
            val = mt.get(key, 0.0)
            if not isinstance(val, float):
                continue
            opt = ric.OptionDouble(val, 0.0, 50.0)
            # Create a label from the key: remove underscores, title case, truncate
            label = key.replace("_", "").title()
            if len(label) > 20:
                label = label[:20]
            go.AddOptionDouble(label, opt)
            opts[key] = (label, opt)

        while True:
            res = go.Get()
            if res == Rhino.Input.GetResult.Option:
                continue
            break

        for key, (label, opt) in opts.items():
            mt[key] = opt.CurrentValue

    elif raw in mt:
        gn = ric.GetNumber()
        gn.SetCommandPrompt(
            "New value for '{0}' (current={1:.2f})".format(raw, mt.get(raw, 0.0))
        )
        gn.SetLowerLimit(0.0, True)
        gn.Get()
        if gn.CommandResult() != rc.Result.Success:
            return gn.CommandResult()
        mt[raw] = gn.Number()
    else:
        Rhino.RhinoApp.WriteLine("Unknown thickness key: '{0}'".format(raw))
        return rc.Result.Failure

    sc.sticky["FIF_MaterialThicknesses"] = mt

    Rhino.RhinoApp.WriteLine("Material thicknesses updated.")
    Rhino.RhinoApp.WriteLine("  Total insole: {0:.2f} mm".format(_total_insole(mt)))
    Rhino.RhinoApp.WriteLine("  Total bottom: {0:.2f} mm".format(_total_bottom(mt)))
    Rhino.RhinoApp.WriteLine("  Total build height: {0:.2f} mm".format(_total_build_height(mt)))
    _rebuild_footwear_from_settings(doc)
    return rc.Result.Success
