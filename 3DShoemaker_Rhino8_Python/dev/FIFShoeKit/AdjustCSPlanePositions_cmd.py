# -*- coding: utf-8 -*-
"""Adjust cross-section plane positions along the last.

Repositions the measurement/construction planes used to define
cross-sectional profiles (ball, waist, instep, heel, etc.).
Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import scriptcontext as sc

__commandname__ = "AdjustCSPlanePositions"


def _get_settings():
    """Get current document settings from sticky."""
    ds = sc.sticky.get("FIF_DocumentSettings", None)
    if ds is None:
        ds = {}
        sc.sticky["FIF_DocumentSettings"] = ds
    return ds


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

    # Standard cross-section names and their default position ratios
    # (proportion of total last length from the heel)
    cs_sections = [
        ("Heel",    "cs_heel_ratio",    0.00),
        ("Seat",    "cs_seat_ratio",    0.10),
        ("Instep",  "cs_instep_ratio",  0.40),
        ("Waist",   "cs_waist_ratio",   0.50),
        ("Ball",    "cs_ball_ratio",    0.68),
        ("Toe",     "cs_toe_ratio",     0.90),
        ("TipToe",  "cs_tiptoe_ratio",  1.00),
    ]

    # Display current positions
    Rhino.RhinoApp.WriteLine("Cross-section plane positions (ratio of last length):")
    for name, key, default in cs_sections:
        current = ds.get(key, default)
        Rhino.RhinoApp.WriteLine("  {0}: {1:.2%}".format(name, current))

    # Select section to adjust
    section_names = [item[0] for item in cs_sections]
    go = ric.GetOption()
    go.SetCommandPrompt("Select cross-section to adjust")
    go.AddOptionList("Section", section_names, 0)

    section_idx = 0
    while True:
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            section_idx = go.Option().CurrentListOptionIndex
            continue
        break

    section_name, key, default = cs_sections[section_idx]
    current_val = ds.get(key, default)

    gn = ric.GetNumber()
    gn.SetCommandPrompt(
        "New position ratio for {0} (0.0=heel, 1.0=toe, current={1:.3f})".format(
            section_name, current_val
        )
    )
    gn.SetDefaultNumber(current_val)
    gn.SetLowerLimit(0.0, True)
    gn.SetUpperLimit(1.0, True)
    gn.Get()
    if gn.CommandResult() != rc.Result.Success:
        return gn.CommandResult()

    new_val = gn.Number()
    ds[key] = new_val
    sc.sticky["FIF_DocumentSettings"] = ds

    # Update clipping/CS plane if it exists
    plane_obj = _find_named_object(doc, "CSPlane_{0}".format(section_name))
    if plane_obj is not None:
        # Move the plane to the new position
        last_obj = _find_named_object(doc, "Last")
        if last_obj is not None:
            last_bbox = last_obj.Geometry.GetBoundingBox(True)
            if last_bbox.IsValid:
                total_length = last_bbox.Max.Y - last_bbox.Min.Y
                new_y = last_bbox.Min.Y + total_length * new_val
                old_bbox = plane_obj.Geometry.GetBoundingBox(True)
                if old_bbox.IsValid:
                    old_y = (old_bbox.Min.Y + old_bbox.Max.Y) / 2.0
                    delta_y = new_y - old_y
                    xform = rg.Transform.Translation(
                        rg.Vector3d(0, delta_y, 0)
                    )
                    doc.Objects.Transform(plane_obj, xform, True)

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "{0} cross-section position set to {1:.3f}.".format(section_name, new_val)
    )
    return rc.Result.Success
