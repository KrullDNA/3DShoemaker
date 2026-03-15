# -*- coding: utf-8 -*-
"""Create top piece (heel bottom contact surface).

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

__commandname__ = "CreateTopPiece"

# Constants
SLM_LAYER_PREFIX = "SLM"
CLASS_BOTTOM = "Bottom"


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


def _find_heel_brep(doc):
    """Find heel brep on the Bottom layer by name."""
    bottom_path = "{0}::{1}".format(SLM_LAYER_PREFIX, CLASS_BOTTOM)
    layer_idx = doc.Layers.FindByFullPath(bottom_path, -1)
    if layer_idx < 0:
        return None
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        for obj in objs:
            if obj.Attributes.Name == "SLM_Heel" and isinstance(obj.Geometry, Rhino.Geometry.Brep):
                return obj.Geometry
    return None


def _extrude_curves_to_brep(curves, direction, cap=True):
    """Extrude curves along a direction to form a brep."""
    breps = []
    for curve in curves:
        surface = Rhino.Geometry.Surface.CreateExtrusion(curve, direction)
        if surface is not None:
            brep = surface.ToBrep()
            if brep is not None:
                if cap:
                    capped = brep.CapPlanarHoles(0.01)
                    breps.append(capped if capped else brep)
                else:
                    breps.append(brep)
    if breps:
        joined = Rhino.Geometry.Brep.JoinBreps(breps, 0.01)
        if joined and len(joined) > 0:
            return joined[0]
        return breps[0]
    return None


def RunCommand(is_interactive):
    doc = sc.doc
    tol = doc.ModelAbsoluteTolerance

    thickness_mm = _prompt_float("Top piece thickness (mm)", 4.0)
    if thickness_mm is None:
        return Rhino.Commands.Result.Cancel
    thickness = _mm_to_model(thickness_mm, doc)

    heel_geom = _find_heel_brep(doc)
    if heel_geom is None or not isinstance(heel_geom, Rhino.Geometry.Brep):
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No heel geometry. Create a heel first.")
        return Rhino.Commands.Result.Failure

    bbox = heel_geom.GetBoundingBox(True)

    # Get bottom outline of heel
    bottom_curves = Rhino.Geometry.Brep.CreateContourCurves(
        heel_geom,
        Rhino.Geometry.Point3d(0, 0, bbox.Min.Z),
        Rhino.Geometry.Point3d(0, 0, bbox.Min.Z + 0.01),
        tol,
    )
    if not bottom_curves:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Cannot extract heel bottom outline.")
        return Rhino.Commands.Result.Failure

    direction = Rhino.Geometry.Vector3d(0, 0, -thickness)
    tp_brep = _extrude_curves_to_brep(list(bottom_curves), direction, cap=True)
    if tp_brep is None:
        return Rhino.Commands.Result.Failure

    tp_bbox = tp_brep.GetBoundingBox(True)
    move = Rhino.Geometry.Transform.Translation(0, 0, bbox.Min.Z - tp_bbox.Max.Z)
    tp_brep.Transform(move)

    _add_component(doc, tp_brep, CLASS_BOTTOM, "SLM_TopPiece")

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Top piece created: {0}mm.".format(thickness))
    return Rhino.Commands.Result.Success
