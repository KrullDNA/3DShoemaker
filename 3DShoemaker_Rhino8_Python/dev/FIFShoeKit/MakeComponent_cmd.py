# -*- coding: utf-8 -*-
"""Generic component creation command.

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

__commandname__ = "MakeComponent"

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


def _prompt_string(prompt, default=""):
    """Prompt the user for a string."""
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


def RunCommand(is_interactive):
    doc = sc.doc

    # Prompt for component type
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Component type name")
    gs.Get()
    if gs.CommandResult() != Rhino.Commands.Result.Success:
        return Rhino.Commands.Result.Cancel

    comp_type = gs.StringResult().strip()
    if not comp_type:
        return Rhino.Commands.Result.Cancel

    # Select source geometry
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select geometry for '{0}' component".format(comp_type))
    go.GeometryFilter = Rhino.DocObjects.ObjectType.AnyObject
    go.GetMultiple(1, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return go.CommandResult()

    # Prompt for target layer
    layer_suffix = _prompt_string(
        "Target layer (Last/Insert/Bottom/Foot/Construction)",
        CLASS_LAST,
    )
    if layer_suffix is None:
        return Rhino.Commands.Result.Cancel

    comp_name = "SLM_{0}".format(comp_type)
    created_count = 0

    for i in range(go.ObjectCount):
        obj_ref = go.Object(i)
        geom = obj_ref.Geometry()
        if geom is not None:
            dup = geom.Duplicate()
            if go.ObjectCount > 1:
                name = "{0}_{1:02d}".format(comp_name, i)
            else:
                name = comp_name
            _add_component(doc, dup, layer_suffix, name)
            created_count += 1

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Component '{0}' created from {1} object(s).".format(comp_type, created_count)
    )
    return Rhino.Commands.Result.Success
