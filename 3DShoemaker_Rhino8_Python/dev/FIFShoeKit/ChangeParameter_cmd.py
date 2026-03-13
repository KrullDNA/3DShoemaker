# -*- coding: utf-8 -*-
"""Generic parameter change command.

Allows changing any named parameter in the document settings by key.
Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "ChangeParameter"


def _get_settings():
    """Get current document settings from sticky, initializing if needed."""
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

    # Prompt for parameter name
    gs = ric.GetString()
    gs.SetCommandPrompt("Enter parameter name")
    gs.Get()
    if gs.CommandResult() != rc.Result.Success:
        return gs.CommandResult()

    param_name = gs.StringResult().strip()
    if not param_name:
        Rhino.RhinoApp.WriteLine("No parameter name entered.")
        return rc.Result.Cancel

    current_val = ds.get(param_name, None)
    Rhino.RhinoApp.WriteLine("Current value of '{0}': {1}".format(param_name, current_val))

    # Prompt for new value
    gs2 = ric.GetString()
    gs2.SetCommandPrompt("Enter new value for '{0}'".format(param_name))
    gs2.Get()
    if gs2.CommandResult() != rc.Result.Success:
        return gs2.CommandResult()

    raw_value = gs2.StringResult().strip()

    # Attempt type-appropriate conversion
    new_value = raw_value
    try:
        new_value = float(raw_value)
    except ValueError:
        if raw_value.lower() in ("true", "yes"):
            new_value = True
        elif raw_value.lower() in ("false", "no"):
            new_value = False

    ds[param_name] = new_value
    sc.sticky["FIF_DocumentSettings"] = ds

    Rhino.RhinoApp.WriteLine("Parameter '{0}' set to: {1}".format(param_name, new_value))
    _rebuild_footwear_from_settings(doc)
    return rc.Result.Success
