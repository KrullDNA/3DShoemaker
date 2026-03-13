# -*- coding: utf-8 -*-
"""Import parameters from JSON.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import json
import os
import Rhino
import Rhino.Commands
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc

__commandname__ = "ImportParameters"

# ---- Settings helpers ----

_SETTINGS_DEFAULTS = {
    "last_size": 0.0,
    "last_size_system": "EU",
    "last_width": "",
    "last_style": "Standard",
    "last_toe_shape": "Round",
    "last_heel_height_mm": 0.0,
    "last_cone_angle_degrees": 0.0,
    "last_symmetry": "Right",
}


def _get_settings():
    if "FIF_LastSettings" not in sc.sticky:
        sc.sticky["FIF_LastSettings"] = dict(_SETTINGS_DEFAULTS)
    s = sc.sticky["FIF_LastSettings"]
    for k, v in _SETTINGS_DEFAULTS.items():
        if k not in s:
            s[k] = v
    return s


def _save_settings(s):
    sc.sticky["FIF_LastSettings"] = s


# ---- Command ----

def RunCommand(is_interactive):
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("JSON file path to import")
    gs.Get()
    if gs.CommandResult() != Rhino.Commands.Result.Success:
        return 1

    file_path = gs.StringResult().strip().strip('"')
    if not file_path or not os.path.isfile(file_path):
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] File not found: {0}".format(file_path)
        )
        return 1

    try:
        fp = open(file_path, "r")
        try:
            data = json.load(fp)
        finally:
            fp.close()

        current = _get_settings()
        # Merge imported data into current settings
        for k, v in data.items():
            if k in _SETTINGS_DEFAULTS:
                current[k] = v
        _save_settings(current)

        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Parameters imported from: {0}".format(file_path)
        )
        Rhino.RhinoApp.WriteLine("  Run UpdateLast to apply changes to geometry.")
        return 0
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Import error: {0}".format(str(ex))
        )
        return 1
