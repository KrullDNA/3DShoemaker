# -*- coding: utf-8 -*-
"""Exports insert parameters to a JSON file.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.DocObjects as rdo
import scriptcontext as sc
import System
import json

__commandname__ = "ExportInsertParameters"


def _collect_insert_params(doc):
    """Collect insert parameters from document user strings and sticky."""
    params = {}

    # Gather from sc.sticky settings dict
    ds = sc.sticky.get("FIF_DocumentSettings", {})
    insert_keys = [
        "insert_thickness_mm", "insert_top_cover_mm",
        "insert_bottom_cover_mm", "insert_posting_medial_mm",
        "insert_posting_lateral_mm", "insert_arch_height_mm",
        "insert_heel_cup_depth_mm", "insert_material",
    ]
    for key in insert_keys:
        if key in ds:
            params[key] = ds[key]

    # Gather from material thicknesses sticky
    mt = sc.sticky.get("FIF_MaterialThicknesses", {})
    mt_keys = [
        "insole_base", "insole_top_cover", "insole_bottom_cover",
        "insole_posting_medial", "insole_posting_lateral",
        "insole_arch_fill", "insole_heel_pad", "insole_met_pad",
        "insole_forefoot_extension", "insole_rearfoot_extension",
    ]
    for key in mt_keys:
        if key in mt:
            params[key] = mt[key]

    # Also gather any insert-related document user strings
    doc_strings = doc.Strings
    if doc_strings is not None:
        for i in range(doc_strings.Count):
            key = doc_strings.GetKey(i)
            if key and key.startswith("insert_"):
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
        params = _collect_insert_params(doc)
        if not params:
            Rhino.RhinoApp.WriteLine("No insert parameters found. Configure insert parameters first.")

        save_dialog = Rhino.UI.SaveFileDialog()
        save_dialog.Title = "Export Insert Parameters"
        save_dialog.Filter = "JSON Files (*.json)|*.json|All Files (*.*)|*.*"
        save_dialog.DefaultExt = "json"

        if not save_dialog.ShowSaveDialog():
            return rc.Result.Cancel

        filepath = save_dialog.FileName

        with open(filepath, "w") as f:
            json.dump(params, f, indent=2, sort_keys=True)

        Rhino.RhinoApp.WriteLine("Insert parameters exported to: {0}".format(filepath))
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error exporting insert parameters: {0}".format(e))
        return rc.Result.Failure
