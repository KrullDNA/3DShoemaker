# -*- coding: utf-8 -*-
"""Create pin hole.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

__commandname__ = "CreatePinHole"

# Constants
SLM_LAYER_PREFIX = "SLM"
CLASS_LAST = "Last"


def _get_layer_index(doc, layer_suffix):
    """Return the index of a SLM::<suffix> layer, creating it if needed."""
    full_path = "{0}::{1}".format(SLM_LAYER_PREFIX, layer_suffix)
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx < 0:
        parent_idx = doc.Layers.FindByFullPath(SLM_LAYER_PREFIX, -1)
        if parent_idx < 0:
            parent_layer = Rhino.DocObjects.Layer()
            parent_layer.Name = SLM_LAYER_PREFIX
            parent_idx = doc.Layers.Add(parent_layer)
        child_layer = Rhino.DocObjects.Layer()
        child_layer.Name = layer_suffix
        child_layer.ParentLayerId = doc.Layers[parent_idx].Id
        idx = doc.Layers.Add(child_layer)
    return idx


def _add_component(doc, geometry, layer_suffix, name):
    """Add a component geometry to the document on the appropriate layer."""
    layer_idx = _get_layer_index(doc, layer_suffix)
    attrs = Rhino.DocObjects.ObjectAttributes()
    if layer_idx >= 0:
        attrs.LayerIndex = layer_idx
    attrs.Name = name

    if isinstance(geometry, Rhino.Geometry.Brep):
        guid = doc.Objects.AddBrep(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Mesh):
        guid = doc.Objects.AddMesh(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Curve):
        guid = doc.Objects.AddCurve(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Surface):
        guid = doc.Objects.AddSurface(geometry, attrs)
    else:
        guid = doc.Objects.Add(geometry, attrs)

    doc.Views.Redraw()
    return guid


def _get_last_brep(doc):
    """Retrieve the last brep from the document."""
    last_path = "{0}::{1}".format(SLM_LAYER_PREFIX, CLASS_LAST)
    layer_idx = doc.Layers.FindByFullPath(last_path, -1)
    if layer_idx < 0:
        return None
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        for obj in objs:
            if isinstance(obj.Geometry, Rhino.Geometry.Brep):
                return obj.Geometry
    return None


def _prompt_float(prompt, default):
    """Prompt the user for a floating point number."""
    gn = Rhino.Input.Custom.GetNumber()
    gn.SetCommandPrompt(prompt)
    gn.SetDefaultNumber(default)
    gn.AcceptNothing(True)
    if gn.Get() == Rhino.Input.GetResult.Number:
        return gn.Number()
    if gn.CommandResult() == Rhino.Commands.Result.Success:
        return default
    return None


def RunCommand(is_interactive):
    doc = sc.doc

    last_brep = _get_last_brep(doc)
    if last_brep is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
        return Rhino.Commands.Result.Failure

    diameter = _prompt_float("Pin hole diameter (mm)", 8.0)
    if diameter is None:
        return Rhino.Commands.Result.Cancel

    depth = _prompt_float("Pin hole depth (mm)", 25.0)
    if depth is None:
        return Rhino.Commands.Result.Cancel

    # Pin hole at heel center top
    bbox = last_brep.GetBoundingBox(True)
    last_length = bbox.Max.Y - bbox.Min.Y
    pin_center = Rhino.Geometry.Point3d(
        (bbox.Min.X + bbox.Max.X) * 0.5,
        bbox.Min.Y + last_length * 0.10,  # near heel
        bbox.Max.Z,
    )

    # Create cylinder going downward
    circle = Rhino.Geometry.Circle(
        Rhino.Geometry.Plane(pin_center, Rhino.Geometry.Vector3d.ZAxis),
        diameter / 2,
    )
    cylinder = Rhino.Geometry.Cylinder(circle, depth)
    cyl_brep = cylinder.ToBrep(True, True)

    if cyl_brep is not None:
        # Move so the cylinder goes downward from the top
        move = Rhino.Geometry.Transform.Translation(0, 0, -depth)
        cyl_brep.Transform(move)

        _add_component(doc, cyl_brep, "Construction", "SLM_PinHole")
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Pin hole created: {0}mm x {1}mm.".format(diameter, depth)
        )
        return Rhino.Commands.Result.Success

    return Rhino.Commands.Result.Failure
