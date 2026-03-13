# -*- coding: utf-8 -*-
"""Create a new shoe last build from interactively prompted parameters.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import math
import Rhino
import Rhino.Commands
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

__commandname__ = "NewBuild"

# ---- Constants ----
_SLM_LAYER_PREFIX = "SLM"
_CLASS_LAST = "Last"
_SIZE_SYSTEMS = ("EU", "US", "UK", "Mondopoint")
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
    """Return a dict of last settings from sticky, filling defaults."""
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
    """Return the index of the SLM::Last layer, creating it if needed."""
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


# ---- Build helpers ----

def _build_last_from_settings(doc, settings):
    """Build a parametric shoe last Brep from settings dict."""
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
    """Add a last brep to the document on the correct layer."""
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

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] New Last Build")
    Rhino.RhinoApp.WriteLine("Enter last measurements (press Enter for defaults):")

    # Size system
    sys_str = _prompt_string(
        "Size system ({0})".format("/".join(_SIZE_SYSTEMS)),
        settings["last_size_system"],
    )
    if sys_str is None:
        return 1
    if sys_str in _SIZE_SYSTEMS:
        settings["last_size_system"] = sys_str

    # Size
    size = _prompt_float(
        "Last size ({0})".format(settings["last_size_system"]),
        settings["last_size"] if settings["last_size"] > 0 else 42.0,
    )
    if size is None:
        return 1
    settings["last_size"] = size

    # Heel height
    heel = _prompt_float("Heel height (mm)", settings["last_heel_height_mm"])
    if heel is None:
        return 1
    settings["last_heel_height_mm"] = heel

    # Toe shape
    toe = _prompt_string(
        "Toe shape ({0})".format("/".join(_TOE_SHAPES)),
        settings["last_toe_shape"],
    )
    if toe is None:
        return 1
    if toe in _TOE_SHAPES:
        settings["last_toe_shape"] = toe

    # Style
    style = _prompt_string(
        "Last style ({0})".format("/".join(_LAST_STYLES)),
        settings["last_style"],
    )
    if style is None:
        return 1
    if style in _LAST_STYLES:
        settings["last_style"] = style

    # Width
    width = _prompt_string(
        "Width designation (e.g. D, E, EE)",
        settings["last_width"] or "D",
    )
    if width is None:
        return 1
    settings["last_width"] = width

    # Symmetry
    sym = _prompt_string("Symmetry (Right/Left/Symmetric)", settings["last_symmetry"])
    if sym is None:
        return 1
    if sym in ("Right", "Left", "Symmetric"):
        settings["last_symmetry"] = sym

    # Build the last
    Rhino.RhinoApp.WriteLine("Building last geometry...")
    brep = _build_last_from_settings(doc, settings)
    if brep is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to build last.")
        return 1

    # Mirror for left foot if needed
    if settings["last_symmetry"] == "Left":
        mirror_plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d.Origin,
            Rhino.Geometry.Vector3d.YAxis,
            Rhino.Geometry.Vector3d.ZAxis,
        )
        xform = Rhino.Geometry.Transform.Mirror(mirror_plane)
        brep.Transform(xform)

    guid = _add_last_to_doc(doc, brep)
    if guid == System.Guid.Empty:
        return 1

    _save_settings(settings)

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Last built: size {0} {1}, heel {2}mm, {3} toe, {4} style.".format(
            settings["last_size"],
            settings["last_size_system"],
            settings["last_heel_height_mm"],
            settings["last_toe_shape"],
            settings["last_style"],
        )
    )
    return 0
