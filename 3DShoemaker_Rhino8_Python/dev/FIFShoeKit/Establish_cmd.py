# -*- coding: utf-8 -*-
"""Establish/initialize a new shoe last project.

Sets up layers, rendering, views, document settings and units.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import rhinoscriptsyntax as rs
import scriptcontext as sc

__commandname__ = "Establish"

# ---- Constants ----
_SLM_LAYER_PREFIX = "SLM"
_CLASS_LAST = "Last"
_CLASS_INSERT = "Insert"
_CLASS_BOTTOM = "Bottom"
_CLASS_FOOT = "Foot"
_ALL_CLASSES = [_CLASS_LAST, _CLASS_INSERT, _CLASS_BOTTOM, _CLASS_FOOT]

# ---- Settings helpers ----

_SETTINGS_DEFAULTS = {
    "project_name": "",
    "customer_name": "",
    "foot_side": "Right",
    "last_size": 0.0,
    "last_size_system": "EU",
    "last_width": "",
    "last_style": "Standard",
    "last_toe_shape": "Round",
    "last_heel_height_mm": 0.0,
    "last_cone_angle_degrees": 0.0,
    "last_symmetry": "Right",
}


def _save_settings(s):
    sc.sticky["FIF_LastSettings"] = s


# ---- Prompt helpers ----

def _prompt_string(prompt, default=""):
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt(prompt)
    if default:
        gs.SetDefaultString(default)
    gs.AcceptNothing(True)
    result = gs.Get()
    if result == Rhino.Input.GetResult.String:
        return gs.StringResult().strip()
    if gs.CommandResult() == Rhino.Commands.Result.Success:
        return default
    return None


# ---- Layer setup ----

def _setup_layers(doc):
    """Create the SLM layer hierarchy if it does not already exist."""
    parent_idx = doc.Layers.FindByFullPath(_SLM_LAYER_PREFIX, -1)
    if parent_idx < 0:
        parent_layer = Rhino.DocObjects.Layer()
        parent_layer.Name = _SLM_LAYER_PREFIX
        parent_idx = doc.Layers.Add(parent_layer)

    parent_id = doc.Layers[parent_idx].Id

    for cls_name in _ALL_CLASSES:
        full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, cls_name)
        idx = doc.Layers.FindByFullPath(full_path, -1)
        if idx < 0:
            child = Rhino.DocObjects.Layer()
            child.Name = cls_name
            child.ParentLayerId = parent_id
            doc.Layers.Add(child)

    # Also add Construction sub-layer
    construction_path = "{0}::Construction".format(_SLM_LAYER_PREFIX)
    if doc.Layers.FindByFullPath(construction_path, -1) < 0:
        c_layer = Rhino.DocObjects.Layer()
        c_layer.Name = "Construction"
        c_layer.ParentLayerId = parent_id
        doc.Layers.Add(c_layer)


# ---- Command ----

def RunCommand(is_interactive):
    doc = sc.doc

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Establishing new shoe last project...")

    # Prompt for project name
    project_name = _prompt_string("Project name", "")
    if project_name is None:
        return 1

    # Prompt for customer name
    customer_name = _prompt_string("Customer name", "")
    if customer_name is None:
        return 1

    # Prompt for foot side
    side = _prompt_string("Foot side (Right/Left)", "Right")
    if side is None:
        return 1
    if side not in ("Right", "Left"):
        side = "Right"

    # Set up layers
    _setup_layers(doc)

    # Initialize document settings
    settings = dict(_SETTINGS_DEFAULTS)
    settings["project_name"] = project_name or ""
    settings["customer_name"] = customer_name or ""
    settings["foot_side"] = side
    settings["last_symmetry"] = side
    _save_settings(settings)

    # Set document units to millimeters
    doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
    doc.ModelAbsoluteTolerance = 0.01
    doc.ModelRelativeTolerance = 0.01
    doc.ModelAngleToleranceDegrees = 1.0

    doc.Views.Redraw()

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Project established:")
    Rhino.RhinoApp.WriteLine("  Project: {0}".format(project_name or "(unnamed)"))
    Rhino.RhinoApp.WriteLine("  Customer: {0}".format(customer_name or "(none)"))
    Rhino.RhinoApp.WriteLine("  Side: {0}".format(side))
    Rhino.RhinoApp.WriteLine("  Layers, rendering, and views configured.")
    Rhino.RhinoApp.WriteLine("  Use NewBuild to create a shoe last.")
    return 0
