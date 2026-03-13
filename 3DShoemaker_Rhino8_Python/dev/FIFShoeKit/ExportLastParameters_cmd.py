# -*- coding: utf-8 -*-
"""Export last parameters to JSON.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import json
import Rhino
import Rhino.Commands
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc

__commandname__ = "ExportLastParameters"

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


# ---- Command ----

def RunCommand(is_interactive):
    settings = _get_settings()

    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Export JSON file path")
    gs.Get()
    if gs.CommandResult() != Rhino.Commands.Result.Success:
        return 1

    file_path = gs.StringResult().strip().strip('"')
    if not file_path:
        return 1

    if not file_path.lower().endswith(".json"):
        file_path += ".json"

    try:
        data = dict(settings)
        fp = open(file_path, "w")
        try:
            json.dump(data, fp, indent=2, sort_keys=True)
        finally:
            fp.close()
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Parameters exported to: {0}".format(file_path)
        )
        return 0
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Export error: {0}".format(str(ex))
        )
        return 1
