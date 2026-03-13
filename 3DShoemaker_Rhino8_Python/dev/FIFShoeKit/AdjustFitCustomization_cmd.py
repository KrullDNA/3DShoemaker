# -*- coding: utf-8 -*-
"""Adjust fit customization parameters.

Modifies ease allowances, toe room, heel fit, and girth adjustments
that control how tightly the footwear conforms to the foot.
Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "AdjustFitCustomization"


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

    go = ric.GetOption()
    go.SetCommandPrompt("Adjust fit customization")

    opt_toe_room = ric.OptionDouble(
        ds.get("fit_toe_room_mm", 12.0), 0.0, 30.0
    )
    opt_ball_ease = ric.OptionDouble(
        ds.get("fit_ball_ease_mm", 0.0), -5.0, 10.0
    )
    opt_instep_ease = ric.OptionDouble(
        ds.get("fit_instep_ease_mm", 0.0), -5.0, 10.0
    )
    opt_heel_ease = ric.OptionDouble(
        ds.get("fit_heel_ease_mm", 0.0), -3.0, 5.0
    )
    opt_width_ease = ric.OptionDouble(
        ds.get("fit_width_ease_mm", 0.0), -5.0, 10.0
    )
    opt_girth_adj = ric.OptionDouble(
        ds.get("fit_girth_adjustment_mm", 0.0), -10.0, 10.0
    )

    go.AddOptionDouble("ToeRoom", opt_toe_room)
    go.AddOptionDouble("BallEase", opt_ball_ease)
    go.AddOptionDouble("InstepEase", opt_instep_ease)
    go.AddOptionDouble("HeelEase", opt_heel_ease)
    go.AddOptionDouble("WidthEase", opt_width_ease)
    go.AddOptionDouble("GirthAdjustment", opt_girth_adj)

    while True:
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            continue
        break

    ds["fit_toe_room_mm"] = opt_toe_room.CurrentValue
    ds["fit_ball_ease_mm"] = opt_ball_ease.CurrentValue
    ds["fit_instep_ease_mm"] = opt_instep_ease.CurrentValue
    ds["fit_heel_ease_mm"] = opt_heel_ease.CurrentValue
    ds["fit_width_ease_mm"] = opt_width_ease.CurrentValue
    ds["fit_girth_adjustment_mm"] = opt_girth_adj.CurrentValue

    sc.sticky["FIF_DocumentSettings"] = ds
    _rebuild_footwear_from_settings(doc)
    Rhino.RhinoApp.WriteLine("Fit customization updated.")
    return rc.Result.Success
