# -*- coding: utf-8 -*-
"""Create thong hole for sandals.

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

__commandname__ = "CreateThongHole"

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


def _geometry_as_brep(geom):
    """Convert geometry to Brep if possible (handles Mesh, Brep, Surface, Extrusion)."""
    if isinstance(geom, Rhino.Geometry.Brep):
        return geom
    if isinstance(geom, Rhino.Geometry.Extrusion):
        return geom.ToBrep()
    if isinstance(geom, Rhino.Geometry.Surface):
        return geom.ToBrep()
    if isinstance(geom, Rhino.Geometry.Mesh):
        brep = Rhino.Geometry.Brep.CreateFromMesh(geom, False)
        if brep is not None:
            return brep
    return None


def _get_last_brep(doc):
    """Retrieve last geometry from selection or SLM::Last layer."""
    selected = [obj for obj in doc.Objects if obj.IsSelected(False)]
    for obj in selected:
        brep = _geometry_as_brep(obj.Geometry)
        if brep is not None:
            return brep

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
            brep = _geometry_as_brep(geom)
            if brep is not None:
                return brep

    last_path = "{0}::{1}".format(SLM_LAYER_PREFIX, CLASS_LAST)
    layer_idx = doc.Layers.FindByFullPath(last_path, -1)
    if layer_idx < 0:
        return None
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        for obj in objs:
            brep = _geometry_as_brep(obj.Geometry)
            if brep is not None:
                return brep
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

    diameter = _prompt_float("Thong hole diameter (mm)", 6.0)
    if diameter is None:
        return Rhino.Commands.Result.Cancel

    # Allow user to pick a point or use default position
    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt("Pick thong hole location (or Enter for default)")
    gp.AcceptNothing(True)
    result = gp.Get()

    bbox = last_brep.GetBoundingBox(True)
    last_length = bbox.Max.Y - bbox.Min.Y

    if result == Rhino.Input.GetResult.Point:
        hole_center = gp.Point()
    else:
        # Default: between 1st and 2nd toe ~80% of length
        hole_center = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            bbox.Min.Y + last_length * 0.80,
            bbox.Min.Z,
        )

    # Create a cylinder for the hole (boolean subtraction reference)
    axis = Rhino.Geometry.Vector3d.ZAxis
    circle = Rhino.Geometry.Circle(
        Rhino.Geometry.Plane(hole_center, axis),
        diameter / 2,
    )
    cylinder = Rhino.Geometry.Cylinder(circle, bbox.Max.Z - bbox.Min.Z + 10)
    cyl_brep = cylinder.ToBrep(True, True)

    if cyl_brep is not None:
        _add_component(doc, cyl_brep, "Construction", "SLM_ThongHole")
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Thong hole created: {0}mm diameter at ({1:.1f}, {2:.1f}).".format(
                diameter, hole_center.X, hole_center.Y
            )
        )
        return Rhino.Commands.Result.Success

    return Rhino.Commands.Result.Failure
