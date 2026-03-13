# -*- coding: utf-8 -*-
"""Create heel sub-components (lifts/layers).

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

__commandname__ = "CreateHeelParts"

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

    heel_geom = _find_heel_brep(doc)
    if heel_geom is None or not isinstance(heel_geom, Rhino.Geometry.Brep):
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No heel geometry found. Run CreateHeel first.")
        return Rhino.Commands.Result.Failure

    bbox = heel_geom.GetBoundingBox(True)
    heel_height = bbox.Max.Z - bbox.Min.Z
    if heel_height <= 0:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No heel height set. Create a heel first.")
        return Rhino.Commands.Result.Failure

    num_lifts = _prompt_float("Number of heel lifts", 3.0)
    if num_lifts is None:
        return Rhino.Commands.Result.Cancel
    num_lifts = max(1, int(num_lifts))

    lift_height = heel_height / num_lifts

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Creating {0} heel lifts ({1:.1f}mm each)...".format(num_lifts, lift_height)
    )

    for i in range(num_lifts):
        z_bottom = bbox.Min.Z + i * lift_height

        curves_bottom = Rhino.Geometry.Brep.CreateContourCurves(
            heel_geom,
            Rhino.Geometry.Point3d(0, 0, z_bottom),
            Rhino.Geometry.Point3d(0, 0, z_bottom + 0.01),
            tol,
        )
        if curves_bottom:
            direction = Rhino.Geometry.Vector3d(0, 0, lift_height)
            lift_brep = _extrude_curves_to_brep(list(curves_bottom), direction, cap=True)
            if lift_brep is not None:
                name = "SLM_HeelLift_{0:02d}".format(i + 1)
                _add_component(doc, lift_brep, CLASS_BOTTOM, name)

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] {0} heel lift(s) created.".format(num_lifts))
    return Rhino.Commands.Result.Success
