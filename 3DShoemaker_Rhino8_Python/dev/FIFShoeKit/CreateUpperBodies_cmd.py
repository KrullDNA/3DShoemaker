# -*- coding: utf-8 -*-
"""Create upper body components (vamp, quarter, tongue, etc.).

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

__commandname__ = "CreateUpperBodies"

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


def _create_offset_surface(brep, offset_distance, tolerance):
    """Create an offset surface from a brep at the given distance."""
    offsets = Rhino.Geometry.Brep.CreateOffsetBrep(
        brep, offset_distance, True, True, tolerance
    )
    if offsets and len(offsets) > 0:
        return offsets[0]
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

    last_brep = _get_last_brep(doc)
    if last_brep is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
        return Rhino.Commands.Result.Failure

    # Select which upper components to create
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Upper component (Vamp/Quarter/Tongue/Counter/All)")
    gs.SetDefaultString("All")
    gs.AcceptNothing(True)
    gs.Get()

    component = "All"
    if gs.CommandResult() == Rhino.Commands.Result.Success and gs.StringResult():
        component = gs.StringResult().strip()

    bbox = last_brep.GetBoundingBox(True)
    last_length = bbox.Max.Y - bbox.Min.Y
    created = []

    if component in ("Vamp", "All"):
        vamp_brep = _create_offset_surface(last_brep, 1.5, tol)
        if vamp_brep is not None:
            _add_component(doc, vamp_brep, CLASS_LAST, "SLM_Upper_Vamp")
            created.append("Vamp")

    if component in ("Quarter", "All"):
        quarter_brep = _create_offset_surface(last_brep, 1.5, tol)
        if quarter_brep is not None:
            _add_component(doc, quarter_brep, CLASS_LAST, "SLM_Upper_Quarter")
            created.append("Quarter")

    if component in ("Tongue", "All"):
        tongue_center = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            bbox.Min.Y + last_length * 0.55,
            bbox.Max.Z + 1.5,
        )
        tongue_plane = Rhino.Geometry.Plane(
            tongue_center, Rhino.Geometry.Vector3d.ZAxis
        )
        tongue_width = (bbox.Max.X - bbox.Min.X) * 0.35
        tongue_length = last_length * 0.30
        rect = Rhino.Geometry.Rectangle3d(
            tongue_plane,
            Rhino.Geometry.Interval(-tongue_width / 2, tongue_width / 2),
            Rhino.Geometry.Interval(-tongue_length / 2, tongue_length / 2),
        )
        tongue_curve = rect.ToNurbsCurve()
        tongue_dir = Rhino.Geometry.Vector3d(0, 0, 2.0)
        tongue_brep = _extrude_curves_to_brep([tongue_curve], tongue_dir, cap=True)
        if tongue_brep is not None:
            _add_component(doc, tongue_brep, CLASS_LAST, "SLM_Upper_Tongue")
            created.append("Tongue")

    if component in ("Counter", "All"):
        counter_brep = _create_offset_surface(last_brep, 0.8, tol)
        if counter_brep is not None:
            _add_component(doc, counter_brep, CLASS_LAST, "SLM_Upper_Counter")
            created.append("Counter")

    if created:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Upper components created: {0}.".format(", ".join(created))
        )
        return Rhino.Commands.Result.Success
    else:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No upper components created.")
        return Rhino.Commands.Result.Failure
