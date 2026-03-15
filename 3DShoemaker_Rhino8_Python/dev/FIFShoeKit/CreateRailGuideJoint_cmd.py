# -*- coding: utf-8 -*-
"""Create rail guide joint assembly.

Rail guide joints provide linear motion constraint for AFO/KAFO
orthopedic devices. Creates the rail channel, guide pin, and mounting
plate geometry.

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

__commandname__ = "CreateRailGuideJoint"

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

    last_geom = _get_last_geometry(doc)
    if last_geom is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
        return Rhino.Commands.Result.Failure

    # Parameters
    rail_length_mm = _prompt_float("Rail length (mm)", 50.0)
    if rail_length_mm is None:
        return Rhino.Commands.Result.Cancel

    rail_width_mm = _prompt_float("Rail channel width (mm)", 5.0)
    if rail_width_mm is None:
        return Rhino.Commands.Result.Cancel

    rail_depth_mm = _prompt_float("Rail channel depth (mm)", 3.0)
    if rail_depth_mm is None:
        return Rhino.Commands.Result.Cancel

    rail_length = _mm_to_model(rail_length_mm, doc)
    rail_width = _mm_to_model(rail_width_mm, doc)
    rail_depth = _mm_to_model(rail_depth_mm, doc)

    # Position
    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt("Pick rail guide location (or Enter for default)")
    gp.AcceptNothing(True)
    result = gp.Get()

    bbox = last_geom.GetBoundingBox(True)
    last_length = bbox.Max.Y - bbox.Min.Y

    if result == Rhino.Input.GetResult.Point:
        rail_center = gp.Point()
    else:
        rail_center = Rhino.Geometry.Point3d(
            bbox.Max.X + 1.0,
            bbox.Min.Y + last_length * 0.25,
            bbox.Min.Z + (bbox.Max.Z - bbox.Min.Z) * 0.5,
        )

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating rail guide joint...")

    # Mounting plate
    plate_plane = Rhino.Geometry.Plane(
        rail_center, Rhino.Geometry.Vector3d.XAxis
    )
    plate_rect = Rhino.Geometry.Rectangle3d(
        plate_plane,
        Rhino.Geometry.Interval(-15, 15),  # 30mm wide plate
        Rhino.Geometry.Interval(-rail_length / 2, rail_length / 2),
    )
    plate_curve = plate_rect.ToNurbsCurve()
    plate_dir = Rhino.Geometry.Vector3d(2.0, 0, 0)
    plate_brep = _extrude_curves_to_brep([plate_curve], plate_dir, cap=True)

    if plate_brep is not None:
        _add_component(doc, plate_brep, "Construction", "SLM_RailGuide_Plate")

    # Rail channel
    channel_plane = Rhino.Geometry.Plane(
        Rhino.Geometry.Point3d(rail_center.X + 2.0, rail_center.Y, rail_center.Z),
        Rhino.Geometry.Vector3d.XAxis,
    )
    channel_rect = Rhino.Geometry.Rectangle3d(
        channel_plane,
        Rhino.Geometry.Interval(-rail_width / 2, rail_width / 2),
        Rhino.Geometry.Interval(-rail_length / 2, rail_length / 2),
    )
    channel_curve = channel_rect.ToNurbsCurve()
    channel_dir = Rhino.Geometry.Vector3d(rail_depth, 0, 0)
    channel_brep = _extrude_curves_to_brep([channel_curve], channel_dir, cap=True)

    if channel_brep is not None:
        _add_component(doc, channel_brep, "Construction", "SLM_RailGuide_Channel")

    # Guide pin (cylinder)
    pin_circle = Rhino.Geometry.Circle(
        Rhino.Geometry.Plane(rail_center, Rhino.Geometry.Vector3d.XAxis),
        rail_width * 0.4,
    )
    pin_cyl = Rhino.Geometry.Cylinder(pin_circle, rail_depth + 4.0)
    pin_brep = pin_cyl.ToBrep(True, True)
    if pin_brep is not None:
        _add_component(doc, pin_brep, "Construction", "SLM_RailGuide_Pin")

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Rail guide joint created: "
        "rail {0}x{1}x{2}mm.".format(rail_length, rail_width, rail_depth)
    )
    return Rhino.Commands.Result.Success
