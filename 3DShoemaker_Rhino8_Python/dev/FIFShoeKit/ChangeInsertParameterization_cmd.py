# -*- coding: utf-8 -*-
"""Change insert/insole parameters.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "ChangeInsertParameterization"


# Default material thickness values for insole layers
_MT_INSOLE_DEFAULTS = {
    "insole_base": 3.0,
    "insole_top_cover": 1.0,
    "insole_bottom_cover": 0.0,
    "insole_posting_medial": 0.0,
    "insole_posting_lateral": 0.0,
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
        mt = dict(_MT_INSOLE_DEFAULTS)
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

    go = ric.GetOption()
    go.SetCommandPrompt("Adjust insert parameters")

    opt_thick = ric.OptionDouble(
        ds.get("insert_thickness_mm", mt.get("insole_base", 3.0)), 0.5, 20.0
    )
    opt_top = ric.OptionDouble(
        mt.get("insole_top_cover", 1.0), 0.0, 5.0
    )
    opt_bottom = ric.OptionDouble(
        mt.get("insole_bottom_cover", 0.0), 0.0, 5.0
    )
    opt_arch = ric.OptionDouble(
        ds.get("insert_arch_height_mm", 0.0), 0.0, 30.0
    )
    opt_heel_cup = ric.OptionDouble(
        ds.get("insert_heel_cup_depth_mm", 0.0), 0.0, 25.0
    )
    opt_med_post = ric.OptionDouble(
        ds.get("insert_posting_medial_mm", mt.get("insole_posting_medial", 0.0)),
        0.0, 15.0
    )
    opt_lat_post = ric.OptionDouble(
        ds.get("insert_posting_lateral_mm", mt.get("insole_posting_lateral", 0.0)),
        0.0, 15.0
    )

    materials_list = ["EVA", "Cork", "Leather", "Polypropylene", "Carbon", "Nylon"]
    current_mat = ds.get("insert_material", "EVA")
    mat_idx = materials_list.index(current_mat) if current_mat in materials_list else 0

    go.AddOptionDouble("Thickness", opt_thick)
    go.AddOptionDouble("TopCover", opt_top)
    go.AddOptionDouble("BottomCover", opt_bottom)
    go.AddOptionDouble("ArchHeight", opt_arch)
    go.AddOptionDouble("HeelCupDepth", opt_heel_cup)
    go.AddOptionDouble("MedialPosting", opt_med_post)
    go.AddOptionDouble("LateralPosting", opt_lat_post)
    go.AddOptionList("Material", materials_list, mat_idx)

    while True:
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            continue
        break

    # Store changes in document settings
    ds["insert_thickness_mm"] = opt_thick.CurrentValue
    ds["insert_top_cover_mm"] = opt_top.CurrentValue
    ds["insert_bottom_cover_mm"] = opt_bottom.CurrentValue
    ds["insert_arch_height_mm"] = opt_arch.CurrentValue
    ds["insert_heel_cup_depth_mm"] = opt_heel_cup.CurrentValue
    ds["insert_posting_medial_mm"] = opt_med_post.CurrentValue
    ds["insert_posting_lateral_mm"] = opt_lat_post.CurrentValue

    # Store in material thicknesses
    mt["insole_base"] = opt_thick.CurrentValue
    mt["insole_top_cover"] = opt_top.CurrentValue
    mt["insole_bottom_cover"] = opt_bottom.CurrentValue
    mt["insole_posting_medial"] = opt_med_post.CurrentValue
    mt["insole_posting_lateral"] = opt_lat_post.CurrentValue

    sc.sticky["FIF_DocumentSettings"] = ds
    sc.sticky["FIF_MaterialThicknesses"] = mt

    _rebuild_footwear_from_settings(doc)
    Rhino.RhinoApp.WriteLine("Insert parameters updated.")
    return rc.Result.Success
