# -*- coding: utf-8 -*-
"""Create heel geometry.

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

__commandname__ = "CreateHeel"

# Constants
SLM_LAYER_PREFIX = "SLM"
CLASS_BOTTOM = "Bottom"
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
    tol = doc.ModelAbsoluteTolerance

    last_geom = _get_last_geometry(doc)
    if last_geom is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
        return Rhino.Commands.Result.Failure

    heel_height_mm = _prompt_float("Heel height (mm)", 25.0)
    if heel_height_mm is None:
        return Rhino.Commands.Result.Cancel
    heel_height = _mm_to_model(heel_height_mm, doc)

    if heel_height <= 0:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Heel height must be positive.")
        return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating heel...")

    bbox = last_geom.GetBoundingBox(True)
    heel_length = (bbox.Max.Y - bbox.Min.Y) * 0.30
    heel_width = (bbox.Max.X - bbox.Min.X) * 0.65

    heel_center = Rhino.Geometry.Point3d(
        (bbox.Min.X + bbox.Max.X) * 0.5,
        bbox.Min.Y + heel_length * 0.5,
        bbox.Min.Z - heel_height * 0.5,
    )

    # Tapered heel: narrower at bottom
    top_ellipse = Rhino.Geometry.Ellipse(
        Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(heel_center.X, heel_center.Y, bbox.Min.Z),
            Rhino.Geometry.Vector3d.ZAxis,
        ),
        heel_width * 0.5,
        heel_length * 0.5,
    )
    bottom_ellipse = Rhino.Geometry.Ellipse(
        Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(heel_center.X, heel_center.Y, bbox.Min.Z - heel_height),
            Rhino.Geometry.Vector3d.ZAxis,
        ),
        heel_width * 0.45,
        heel_length * 0.45,
    )

    top_crv = top_ellipse.ToNurbsCurve()
    bottom_crv = bottom_ellipse.ToNurbsCurve()

    if top_crv is None or bottom_crv is None:
        return Rhino.Commands.Result.Failure

    loft = Rhino.Geometry.Brep.CreateFromLoft(
        [bottom_crv, top_crv],
        Rhino.Geometry.Point3d.Unset,
        Rhino.Geometry.Point3d.Unset,
        Rhino.Geometry.LoftType.Straight,
        False,
    )
    if not loft or len(loft) == 0:
        return Rhino.Commands.Result.Failure

    heel_brep = loft[0].CapPlanarHoles(tol)
    if heel_brep is None:
        heel_brep = loft[0]

    guid = _add_component(doc, heel_brep, CLASS_BOTTOM, "SLM_Heel")
    if guid == System.Guid.Empty:
        return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Heel created: {0}mm high.".format(heel_height))
    return Rhino.Commands.Result.Success
