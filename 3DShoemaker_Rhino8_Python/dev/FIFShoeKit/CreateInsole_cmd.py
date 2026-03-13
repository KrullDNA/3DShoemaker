# -*- coding: utf-8 -*-
"""Create insole geometry from last.

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

__commandname__ = "CreateInsole"

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


def _create_bottom_outline(brep, z_offset, tolerance):
    """Extract the bottom outline of a brep at the given Z level."""
    bbox = brep.GetBoundingBox(True)
    z_level = bbox.Min.Z + z_offset

    curves = Rhino.Geometry.Brep.CreateContourCurves(
        brep,
        Rhino.Geometry.Point3d(0, 0, z_level),
        Rhino.Geometry.Point3d(0, 0, z_level + 1),
        tolerance,
    )
    if curves:
        return list(curves)
    return []


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

    last_brep = _get_last_brep(doc)
    if last_brep is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found. Build a last first.")
        return Rhino.Commands.Result.Failure

    thickness = _prompt_float("Insole thickness (mm)", 3.0)
    if thickness is None:
        return Rhino.Commands.Result.Cancel

    top_cover = _prompt_float("Top cover thickness (mm)", 1.0)
    if top_cover is None:
        return Rhino.Commands.Result.Cancel

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating insole...")

    bbox = last_brep.GetBoundingBox(True)

    # Extract bottom contour of the last
    bottom_curves = _create_bottom_outline(last_brep, tol, tol)
    if not bottom_curves:
        # Fallback: create an outline from the bounding box bottom
        center = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            (bbox.Min.Y + bbox.Max.Y) * 0.5,
            bbox.Min.Z,
        )
        length = bbox.Max.Y - bbox.Min.Y
        width = bbox.Max.X - bbox.Min.X
        plane = Rhino.Geometry.Plane(center, Rhino.Geometry.Vector3d.ZAxis)
        ellipse = Rhino.Geometry.Ellipse(plane, width * 0.48, length * 0.48)
        bottom_curves = [ellipse.ToNurbsCurve()]

    # Extrude downward to create the insole body
    direction = Rhino.Geometry.Vector3d(0, 0, -thickness)
    insole_brep = _extrude_curves_to_brep(bottom_curves, direction, cap=True)

    if insole_brep is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to create insole geometry.")
        return Rhino.Commands.Result.Failure

    # Position at bottom of last
    move = Rhino.Geometry.Transform.Translation(0, 0, bbox.Min.Z - top_cover)
    insole_brep.Transform(move)

    guid = _add_component(doc, insole_brep, CLASS_INSERT, "SLM_Insole")
    if guid == System.Guid.Empty:
        return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Insole created: {0}mm thick, {1}mm top cover.".format(thickness, top_cover)
    )
    return Rhino.Commands.Result.Success
