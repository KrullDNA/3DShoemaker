# -*- coding: utf-8 -*-
"""Scriptable (non-interactive) version of NewBuild.

Accepts parameters via command-line options so it can be called from
scripts and macros without user prompts.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import math
import Rhino
import Rhino.Commands
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc
import System

__commandname__ = "NewBuildScriptable"

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


# ---- Build helpers ----

def _build_last_from_settings(doc, settings):
    size_mm = settings["last_size"]
    heel_height = settings["last_heel_height_mm"]
    toe_shape = settings["last_toe_shape"]

    size_system = settings["last_size_system"]
    if size_system == "EU":
        length = size_mm * 6.67
    elif size_system == "US":
        length = (size_mm + 23.5) * 6.67
    elif size_system == "UK":
        length = (size_mm + 24.0) * 6.67
    else:
        length = size_mm

    if length <= 0:
        length = 260.0

    width = length * 0.38
    height = length * 0.24

    sections = []
    num_sections = 8
    for i in range(num_sections):
        t = i / float(num_sections - 1)
        y = t * length

        if t < 0.15:
            w = width * (0.55 + t * 2.0)
        elif t < 0.55:
            w = width * (0.85 + 0.15 * math.sin((t - 0.15) / 0.4 * math.pi))
        else:
            toe_factor = (1.0 - t) / 0.45
            if toe_shape == "Pointed":
                w = width * toe_factor ** 1.8
            elif toe_shape == "Square":
                w = width * max(toe_factor, 0.25)
            elif toe_shape == "Almond":
                w = width * toe_factor ** 1.3
            elif toe_shape == "Oblique":
                w = width * toe_factor ** 1.1
            else:
                w = width * toe_factor ** 1.4

        w = max(w, 2.0)

        heel_lift = heel_height * (1.0 - t) ** 2 if t < 0.6 else 0.0
        h = height * (0.6 + 0.4 * math.sin(t * math.pi)) + heel_lift
        h = max(h, 2.0)

        plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(0, y, heel_lift + h * 0.5),
            Rhino.Geometry.Vector3d.XAxis,
            Rhino.Geometry.Vector3d.ZAxis,
        )
        ellipse = Rhino.Geometry.Ellipse(plane, w * 0.5, h * 0.5)
        curve = ellipse.ToNurbsCurve()
        if curve is not None:
            sections.append(curve)

    if len(sections) < 2:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to generate last sections.")
        return None

    breps = Rhino.Geometry.Brep.CreateFromLoft(
        sections,
        Rhino.Geometry.Point3d.Unset,
        Rhino.Geometry.Point3d.Unset,
        Rhino.Geometry.LoftType.Normal,
        False,
    )
    if not breps or len(breps) == 0:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Loft operation failed.")
        return None

    last_brep = breps[0].CapPlanarHoles(doc.ModelAbsoluteTolerance)
    if last_brep is None:
        last_brep = breps[0]

    return last_brep


def _add_last_to_doc(doc, brep, name="SLM_Last"):
    layer_idx = _get_last_layer_index(doc)
    attrs = Rhino.DocObjects.ObjectAttributes()
    if layer_idx >= 0:
        attrs.LayerIndex = layer_idx
    attrs.Name = name
    guid = doc.Objects.AddBrep(brep, attrs)
    doc.Views.Redraw()
    return guid


# ---- Command ----

def RunCommand(is_interactive):
    doc = sc.doc
    settings = _get_settings()

    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("NewBuildScriptable")
    gs.AcceptNothing(True)

    opt_size = Rhino.Input.Custom.OptionDouble(
        settings["last_size"] if settings["last_size"] > 0 else 42.0
    )
    opt_heel = Rhino.Input.Custom.OptionDouble(settings["last_heel_height_mm"])
    opt_system = Rhino.Input.Custom.OptionToggle(
        settings["last_size_system"] == "US", "EU", "US"
    )

    gs.AddOptionDouble("Size", opt_size)
    gs.AddOptionDouble("HeelHeight", opt_heel)
    gs.AddOptionToggle("SizeSystem", opt_system)

    while True:
        result = gs.Get()
        if result == Rhino.Input.GetResult.Option:
            continue
        break

    if gs.CommandResult() != Rhino.Commands.Result.Success:
        return 1

    settings["last_size"] = opt_size.CurrentValue
    settings["last_heel_height_mm"] = opt_heel.CurrentValue
    settings["last_size_system"] = "US" if opt_system.CurrentValue else "EU"

    brep = _build_last_from_settings(doc, settings)
    if brep is None:
        return 1

    guid = _add_last_to_doc(doc, brep)
    if guid == System.Guid.Empty:
        return 1

    _save_settings(settings)

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Scriptable build complete: size {0} {1}.".format(
            settings["last_size"], settings["last_size_system"]
        )
    )
    return 0
