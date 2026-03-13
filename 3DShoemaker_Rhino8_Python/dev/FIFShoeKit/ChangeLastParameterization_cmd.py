# -*- coding: utf-8 -*-
"""Open dialog to modify last parameters.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc

__commandname__ = "ChangeLastParameterization"

# ---- Constants ----
_TOE_SHAPES = ("Round", "Pointed", "Square", "Almond", "Oblique")
_LAST_STYLES = ("Standard", "Sport", "Dress", "Casual", "Orthopedic")

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
    settings = _get_settings()

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Current Last Parameters:")
    Rhino.RhinoApp.WriteLine("  Size: {0} {1}".format(settings["last_size"], settings["last_size_system"]))
    Rhino.RhinoApp.WriteLine("  Width: {0}".format(settings["last_width"]))
    Rhino.RhinoApp.WriteLine("  Heel Height: {0} mm".format(settings["last_heel_height_mm"]))
    Rhino.RhinoApp.WriteLine("  Toe Shape: {0}".format(settings["last_toe_shape"]))
    Rhino.RhinoApp.WriteLine("  Style: {0}".format(settings["last_style"]))
    Rhino.RhinoApp.WriteLine("  Symmetry: {0}".format(settings["last_symmetry"]))

    # Interactive parameter modification via GetString with options
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Select parameter to modify (or Enter to finish)")
    gs.AcceptNothing(True)

    opt_size = Rhino.Input.Custom.OptionDouble(settings["last_size"])
    opt_heel = Rhino.Input.Custom.OptionDouble(settings["last_heel_height_mm"])

    gs.AddOptionDouble("Size", opt_size)
    gs.AddOptionDouble("HeelHeight", opt_heel)

    changed = False
    while True:
        result = gs.Get()
        if result == Rhino.Input.GetResult.Option:
            changed = True
            continue
        elif result == Rhino.Input.GetResult.String:
            val = gs.StringResult().strip()
            if val:
                # Allow setting toe shape or style by typing it
                if val in _TOE_SHAPES:
                    settings["last_toe_shape"] = val
                    changed = True
                    Rhino.RhinoApp.WriteLine("  Toe shape set to: {0}".format(val))
                    continue
                if val in _LAST_STYLES:
                    settings["last_style"] = val
                    changed = True
                    Rhino.RhinoApp.WriteLine("  Style set to: {0}".format(val))
                    continue
            break
        else:
            break

    if changed:
        settings["last_size"] = opt_size.CurrentValue
        settings["last_heel_height_mm"] = opt_heel.CurrentValue
        _save_settings(settings)
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Parameters updated. Run UpdateLast to rebuild."
        )
    else:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No changes made.")

    return 0
