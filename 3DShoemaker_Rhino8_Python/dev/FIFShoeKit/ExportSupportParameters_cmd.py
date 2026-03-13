# -*- coding: utf-8 -*-
"""Exports support/bottom parameters to a JSON file.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.DocObjects as rdo
import scriptcontext as sc
import System
import json

__commandname__ = "ExportSupportParameters"


def _collect_support_params(doc):
    """Collect bottom/support parameters from document user strings and sticky."""
    params = {}

    # Gather from sc.sticky settings dict
    ds = sc.sticky.get("FIF_DocumentSettings", {})
    bottom_keys = [
        "bottom_thickness_mm", "bottom_material", "bottom_profile",
    ]
    for key in bottom_keys:
        if key in ds:
            params[key] = ds[key]

    # Gather from material thicknesses sticky
    mt = sc.sticky.get("FIF_MaterialThicknesses", {})
    mt_keys = [
        "bottom_outsole", "bottom_midsole", "bottom_insole_board",
        "bottom_shank", "bottom_welt",
        "medial_wedge", "lateral_wedge", "heel_lift",
        "forefoot_rocker", "toe_spring",
    ]
    for key in mt_keys:
        if key in mt:
            params[key] = mt[key]

    # Also gather any bottom-related document user strings
    doc_strings = doc.Strings
    if doc_strings is not None:
        for i in range(doc_strings.Count):
            key = doc_strings.GetKey(i)
            if key and key.startswith("bottom_"):
                val = doc_strings.GetValue(key)
                if val is not None:
                    try:
                        params[key] = float(val)
                    except ValueError:
                        params[key] = val

    return params


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        params = _collect_support_params(doc)
        if not params:
            Rhino.RhinoApp.WriteLine("No support parameters found. Configure bottom parameters first.")

        save_dialog = Rhino.UI.SaveFileDialog()
        save_dialog.Title = "Export Support Parameters"
        save_dialog.Filter = "JSON Files (*.json)|*.json|All Files (*.*)|*.*"
        save_dialog.DefaultExt = "json"

        if not save_dialog.ShowSaveDialog():
            return rc.Result.Cancel

        filepath = save_dialog.FileName

        with open(filepath, "w") as f:
            json.dump(params, f, indent=2, sort_keys=True)

        Rhino.RhinoApp.WriteLine("Support parameters exported to: {0}".format(filepath))
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error exporting support parameters: {0}".format(e))
        return rc.Result.Failure
