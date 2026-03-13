# -*- coding: utf-8 -*-
"""Adjust last depth to accommodate a footbed.

Increases or decreases the volume inside the last to account for
the footbed thickness and contour.
Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import scriptcontext as sc

__commandname__ = "AdjustLastDepthForFootbeds"


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
        mt = {}
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


def _find_named_object(doc, name):
    """Find a named object in the document."""
    settings = rdo.ObjectEnumeratorSettings()
    settings.NameFilter = name
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        return obj
    return None


def RunCommand(is_interactive):
    doc = sc.doc
    ds = _get_settings()
    mt = _get_mt()

    current_adj = ds.get("last_footbed_depth_adjustment_mm", 0.0)
    footbed_thick = _total_insole(mt)

    go = ric.GetOption()
    go.SetCommandPrompt("Adjust last depth for footbed")

    opt_adj = ric.OptionDouble(current_adj, -20.0, 20.0)
    opt_auto = ric.OptionToggle(False, "Manual", "Auto")

    go.AddOptionDouble("DepthAdjustment", opt_adj)
    go.AddOptionToggle("Mode", opt_auto)

    while True:
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            continue
        break

    if opt_auto.CurrentValue:
        # Auto-calculate from footbed thickness
        adjustment = footbed_thick
        Rhino.RhinoApp.WriteLine(
            "  Auto-calculated depth adjustment from footbed thickness: {0:.2f} mm".format(
                adjustment
            )
        )
    else:
        adjustment = opt_adj.CurrentValue

    ds["last_footbed_depth_adjustment_mm"] = adjustment
    sc.sticky["FIF_DocumentSettings"] = ds

    # Apply to last geometry if present
    last_obj = _find_named_object(doc, "Last")
    if last_obj is not None:
        last_geom = last_obj.Geometry
        if isinstance(last_geom, rg.Brep):
            # Offset the bottom surface of the last downward
            offset_results = rg.Brep.CreateOffsetBrep(
                last_geom, -adjustment, False, False, 0.01
            )
            if offset_results and len(offset_results) > 0:
                new_brep = None
                first_result = offset_results[0]
                if hasattr(first_result, "__iter__"):
                    for b in first_result:
                        if isinstance(b, rg.Brep) and b.IsValid:
                            new_brep = b
                            break
                elif isinstance(first_result, rg.Brep):
                    new_brep = first_result
                if new_brep is not None:
                    doc.Objects.Replace(last_obj.Id, new_brep)

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Last depth adjusted by {0:.2f} mm for footbed.".format(adjustment)
    )
    return rc.Result.Success
