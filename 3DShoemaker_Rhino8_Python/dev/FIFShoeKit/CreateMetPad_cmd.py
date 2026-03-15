# -*- coding: utf-8 -*-
"""Create metatarsal pad.

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

__commandname__ = "CreateMetPad"

# Constants
SLM_LAYER_PREFIX = "SLM"
CLASS_INSERT = "Insert"
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


def _get_last_geometry(doc):
    """Retrieve last geometry from selection or SLM::Last layer.

    Returns the raw geometry (Mesh, Brep, etc.) without conversion.
    """
    # 1. Check pre-selected objects
    selected = [obj for obj in doc.Objects if obj.IsSelected(False)]
    for obj in selected:
        geom = obj.Geometry
        if isinstance(geom, (Rhino.Geometry.Mesh, Rhino.Geometry.Brep,
                             Rhino.Geometry.Surface, Rhino.Geometry.Extrusion)):
            return geom

    # 2. Prompt user to pick
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select last geometry (mesh or brep)")
    go.GeometryFilter = (
        Rhino.DocObjects.ObjectType.Brep
        | Rhino.DocObjects.ObjectType.Mesh
        | Rhino.DocObjects.ObjectType.Surface
        | Rhino.DocObjects.ObjectType.Extrusion
    )
    go.AcceptNothing(True)
    if go.Get() == Rhino.Input.GetResult.Object:
        ref = go.Object(0)
        geom = ref.Geometry()
        if geom is not None:
            return geom

    # 3. Fall back to SLM::Last layer
    last_path = "{0}::{1}".format(SLM_LAYER_PREFIX, CLASS_LAST)
    layer_idx = doc.Layers.FindByFullPath(last_path, -1)
    if layer_idx < 0:
        return None
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        for obj in objs:
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


def _mm_to_model(value, doc):
    """Convert a value in millimetres to model units."""
    scale = Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Millimeters, doc.ModelUnitSystem)
    return value * scale


def RunCommand(is_interactive):
    doc = sc.doc

    last_geom = _get_last_geometry(doc)
    if last_geom is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
        return Rhino.Commands.Result.Failure

    height_mm = _prompt_float("Met pad height (mm)", 6.0)
    if height_mm is None:
        return Rhino.Commands.Result.Cancel

    diameter_mm = _prompt_float("Met pad diameter (mm)", 30.0)
    if diameter_mm is None:
        return Rhino.Commands.Result.Cancel

    height = _mm_to_model(height_mm, doc)
    diameter = _mm_to_model(diameter_mm, doc)

    bbox = last_geom.GetBoundingBox(True)
    last_length = bbox.Max.Y - bbox.Min.Y

    # Met pad location: ~55% of last length, slightly medial
    met_center = Rhino.Geometry.Point3d(
        (bbox.Min.X + bbox.Max.X) * 0.5 + 2.0,  # slightly medial offset
        bbox.Min.Y + last_length * 0.55,
        bbox.Min.Z,
    )

    # Create a dome shape (hemisphere)
    sphere = Rhino.Geometry.Sphere(met_center, diameter / 2)
    sphere_brep = sphere.ToBrep()

    # Trim to desired height using a cutting plane
    cut_plane = Rhino.Geometry.Plane(
        Rhino.Geometry.Point3d(met_center.X, met_center.Y, met_center.Z + height),
        Rhino.Geometry.Vector3d.ZAxis,
    )

    # Split and keep the bottom portion
    if sphere_brep is not None:
        splits = sphere_brep.Trim(cut_plane, doc.ModelAbsoluteTolerance)
        if splits and len(splits) > 0:
            met_brep = splits[0]
            capped = met_brep.CapPlanarHoles(doc.ModelAbsoluteTolerance)
            if capped:
                met_brep = capped
        else:
            met_brep = sphere_brep
    else:
        return Rhino.Commands.Result.Failure

    _add_component(doc, met_brep, CLASS_INSERT, "SLM_MetPad")

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Met pad created: {0}mm diameter, {1}mm height.".format(diameter, height)
    )
    return Rhino.Commands.Result.Success
