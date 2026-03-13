# -*- coding: utf-8 -*-
"""Grade (size) the last to a different size.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc

__commandname__ = "GradeLast"

# ---- Constants ----
_SLM_LAYER_PREFIX = "SLM"
_CLASS_LAST = "Last"

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


# ---- Layer helpers ----

def _get_last_layer_index(doc):
    full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, _CLASS_LAST)
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx < 0:
        parent_idx = doc.Layers.FindByFullPath(_SLM_LAYER_PREFIX, -1)
        if parent_idx < 0:
            parent_layer = Rhino.DocObjects.Layer()
            parent_layer.Name = _SLM_LAYER_PREFIX
            parent_idx = doc.Layers.Add(parent_layer)
        child_layer = Rhino.DocObjects.Layer()
        child_layer.Name = _CLASS_LAST
        child_layer.ParentLayerId = doc.Layers[parent_idx].Id
        idx = doc.Layers.Add(child_layer)
    return idx


def _find_last_objects(doc):
    layer_idx = _get_last_layer_index(doc)
    if layer_idx < 0:
        return []
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    return list(objs) if objs else []


# ---- Prompt helpers ----

def _prompt_float(prompt, default):
    gn = Rhino.Input.Custom.GetNumber()
    gn.SetCommandPrompt(prompt)
    gn.SetDefaultNumber(default)
    gn.AcceptNothing(True)
    if gn.Get() == Rhino.Input.GetResult.Number:
        return gn.Number()
    if gn.CommandResult() == Rhino.Commands.Result.Success:
        return default
    return None


# ---- Command ----

def RunCommand(is_interactive):
    doc = sc.doc
    settings = _get_settings()

    current_size = settings["last_size"]
    if current_size <= 0:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] No current last size set. Build a last first."
        )
        return 1

    # Prompt for target size
    target = _prompt_float(
        "Target size ({0}, current={1})".format(settings["last_size_system"], current_size),
        current_size,
    )
    if target is None or target <= 0:
        return 1

    if abs(target - current_size) < 0.001:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Target size is the same as current. No change."
        )
        return 0

    # Calculate scale factor
    scale_factor = target / current_size

    # Length scales linearly with size; width/height scale at ~85% of length
    scale_x = 1.0 + (scale_factor - 1.0) * 0.85  # width
    scale_y = scale_factor                          # length
    scale_z = 1.0 + (scale_factor - 1.0) * 0.85   # height

    xform = Rhino.Geometry.Transform.Scale(
        Rhino.Geometry.Plane.WorldXY,
        scale_x,
        scale_y,
        scale_z,
    )

    last_objs = _find_last_objects(doc)
    if not last_objs:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last objects found to grade.")
        return 1

    for obj in last_objs:
        doc.Objects.Transform(obj, xform, True)

    # Update settings
    settings["last_size"] = target
    _save_settings(settings)

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Last graded from size {0} to {1} ({2}). Scale factor: {3:.4f}".format(
            current_size, target, settings["last_size_system"], scale_factor
        )
    )
    return 0
