# -*- coding: utf-8 -*-
"""Create sole geometry.

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

__commandname__ = "CreateSole"

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


def _cross_section_curves(geom, plane, tolerance):
    """Get cross-section curves from mesh or brep geometry."""
    if isinstance(geom, Rhino.Geometry.Mesh):
        polylines = Rhino.Geometry.Intersect.Intersection.MeshPlane(geom, plane)
        if polylines:
            curves = []
            for pl in polylines:
                if pl and pl.Count > 2:
                    if pl[0].DistanceTo(pl[pl.Count - 1]) > tolerance:
                        pl.Add(pl[0])
                    curves.append(Rhino.Geometry.PolylineCurve(pl))
            return curves
        return []

    brep = geom
    if isinstance(geom, Rhino.Geometry.Extrusion):
        brep = geom.ToBrep()
    elif isinstance(geom, Rhino.Geometry.Surface):
        brep = geom.ToBrep()

    if brep is not None and isinstance(brep, Rhino.Geometry.Brep):
        curves = Rhino.Geometry.Brep.CreateContourCurves(
            brep,
            plane.Origin,
            plane.Origin + Rhino.Geometry.Vector3d.ZAxis,
            tolerance,
        )
        if curves:
            return list(curves)
    return []


def _create_bottom_outline(geom, z_offset, tolerance):
    """Extract the bottom outline of geometry at a suitable Z level.

    For meshes, a single slice right at bbox.Min can produce a degenerate
    sliver, so we try several heights in the bottom 5 % and keep the best.
    """
    bbox = geom.GetBoundingBox(True)
    height = bbox.Max.Z - bbox.Min.Z

    if not isinstance(geom, Rhino.Geometry.Mesh) or height <= 0:
        z_level = bbox.Min.Z + z_offset
        plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(0, 0, z_level),
            Rhino.Geometry.Vector3d.ZAxis,
        )
        return _cross_section_curves(geom, plane, tolerance)

    offsets = [z_offset, height * 0.01, height * 0.02, height * 0.03, height * 0.05]
    best_curves = []
    best_length = 0.0
    for off in offsets:
        z_level = bbox.Min.Z + off
        plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(0, 0, z_level),
            Rhino.Geometry.Vector3d.ZAxis,
        )
        curves = _cross_section_curves(geom, plane, tolerance)
        if curves:
            total_len = sum(c.GetLength() for c in curves)
            if total_len > best_length:
                best_length = total_len
                best_curves = curves
    return best_curves


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

    thickness_mm = _prompt_float("Sole thickness (mm)", 5.0)
    if thickness_mm is None:
        return Rhino.Commands.Result.Cancel
    thickness = _mm_to_model(thickness_mm, doc)

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating sole...")

    bbox = last_geom.GetBoundingBox(True)
    bottom_curves = _create_bottom_outline(last_geom, tol, tol)

    if not bottom_curves:
        center = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) * 0.5,
            (bbox.Min.Y + bbox.Max.Y) * 0.5,
            bbox.Min.Z,
        )
        length = bbox.Max.Y - bbox.Min.Y
        width = bbox.Max.X - bbox.Min.X
        plane = Rhino.Geometry.Plane(center, Rhino.Geometry.Vector3d.ZAxis)
        ellipse = Rhino.Geometry.Ellipse(plane, width * 0.50, length * 0.50)
        bottom_curves = [ellipse.ToNurbsCurve()]

    # Offset curves outward slightly for sole flange
    offset_curves = []
    for crv in bottom_curves:
        offsets = crv.Offset(
            Rhino.Geometry.Plane.WorldXY,
            2.0,  # 2mm flange
            tol,
            Rhino.Geometry.CurveOffsetCornerStyle.Sharp,
        )
        if offsets and len(offsets) > 0:
            for o in offsets:
                offset_curves.append(o)
        else:
            offset_curves.append(crv)

    direction = Rhino.Geometry.Vector3d(0, 0, -thickness)
    sole_brep = _extrude_curves_to_brep(offset_curves, direction, cap=True)

    if sole_brep is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to create sole geometry.")
        return Rhino.Commands.Result.Failure

    # Position below the insole
    sole_bbox = sole_brep.GetBoundingBox(True)
    desired_top_z = bbox.Min.Z - 3.0  # default insole thickness
    move = Rhino.Geometry.Transform.Translation(0, 0, desired_top_z - sole_bbox.Max.Z)
    sole_brep.Transform(move)

    guid = _add_component(doc, sole_brep, CLASS_BOTTOM, "SLM_Sole")
    if guid == System.Guid.Empty:
        return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Sole created: {0}mm thick.".format(thickness))
    return Rhino.Commands.Result.Success
