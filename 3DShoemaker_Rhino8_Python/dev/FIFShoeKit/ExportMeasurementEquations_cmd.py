# -*- coding: utf-8 -*-
"""Export measurement equations to JSON.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import json
import math
import Rhino
import Rhino.Commands
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc

__commandname__ = "ExportMeasurementEquations"

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
    gs.SetCommandPrompt("Export equations file path (JSON)")
    gs.Get()
    if gs.CommandResult() != Rhino.Commands.Result.Success:
        return 1

    file_path = gs.StringResult().strip().strip('"')
    if not file_path:
        return 1

    if not file_path.lower().endswith(".json"):
        file_path += ".json"

    # Compute measurement equations from current settings
    size = settings["last_size"]
    size_system = settings["last_size_system"]

    if size_system == "EU":
        foot_length = size * 6.67
    elif size_system == "US":
        foot_length = (size + 23.5) * 6.67
    elif size_system == "UK":
        foot_length = (size + 24.0) * 6.67
    else:
        foot_length = size

    equations = {
        "size": size,
        "size_system": size_system,
        "foot_length_mm": round(foot_length, 2),
        "ball_width_mm": round(foot_length * 0.38, 2),
        "ball_girth_mm": round(foot_length * 0.38 * math.pi, 2),
        "waist_girth_mm": round(foot_length * 0.30 * math.pi, 2),
        "instep_girth_mm": round(foot_length * 0.34 * math.pi, 2),
        "heel_girth_mm": round(foot_length * 0.32 * math.pi + settings["last_heel_height_mm"] * 0.5, 2),
        "toe_spring_mm": round(foot_length * 0.04, 2),
        "heel_height_mm": settings["last_heel_height_mm"],
        "cone_angle_deg": settings["last_cone_angle_degrees"],
        "stick_length_mm": round(foot_length * 1.02, 2),
        "last_length_mm": round(foot_length * 1.03, 2),
    }

    try:
        fp = open(file_path, "w")
        try:
            json.dump(equations, fp, indent=2)
        finally:
            fp.close()
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Measurement equations exported to: {0}".format(file_path)
        )
        return 0
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Export error: {0}".format(str(ex))
        )
        return 1
