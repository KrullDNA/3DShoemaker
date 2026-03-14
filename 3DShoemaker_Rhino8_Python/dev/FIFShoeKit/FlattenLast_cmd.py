# -*- coding: utf-8 -*-
"""Flatten last bottom to a 2D pattern.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc

__commandname__ = "FlattenLast"

# ---- Constants ----
_SLM_LAYER_PREFIX = "SLM"
_CLASS_LAST = "Last"


# ---- Layer helpers ----

def _get_last_layer_index(doc):
    full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, _CLASS_LAST)
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx < 0:
        parent_idx = doc.Layers.FindByFullPath(_SLM_LAYER_PREFIX, -1)
        if parent_idx < 0:
            parent_layer = Rhino.DocObjects.Layer()
            parent_layer.Name = _SLM_LAYER_PREFIX
            parent_idx = doc.Layers.Add(parent_layer)
        child_layer = Rhino.DocObjects.Layer()
        child_layer.Name = _CLASS_LAST
        child_layer.ParentLayerId = doc.Layers[parent_idx].Id
        idx = doc.Layers.Add(child_layer)
    return idx


def _find_last_objects(doc):
    """Find last objects from selection first, then prompt, then layer."""
    # 1. Check pre-selected objects
    selected = [obj for obj in doc.Objects if obj.IsSelected(False)]
    if selected:
        return selected

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
        return [ref.Object()]

    # 3. Fall back to SLM::Last layer
    layer_idx = _get_last_layer_index(doc)
    if layer_idx < 0:
        return []
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    return list(objs) if objs else []


def _cross_section_curves_at_plane(geom, plane, tol):
    """Get cross-section curves for mesh or brep at a given plane."""
    if isinstance(geom, Rhino.Geometry.Mesh):
        polylines = Rhino.Geometry.Intersect.Intersection.MeshPlane(geom, plane)
        if polylines:
            curves = []
            for pl in polylines:
                if pl and pl.Count > 2:
                    pl.Close()
                    curves.append(pl.ToNurbsCurve())
            return curves
        return []

    # For brep/surface/extrusion
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
            tol,
        )
        if curves:
            return list(curves)
    return []


# ---- Command ----

def RunCommand(is_interactive):
    doc = sc.doc

    last_objs = _find_last_objects(doc)
    if not last_objs:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
        return 1

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Flattening last bottom...")

    tol = doc.ModelAbsoluteTolerance

    # Collect raw geometry from objects
    geometries = []
    for obj in last_objs:
        geom = obj.Geometry
        if isinstance(geom, (Rhino.Geometry.Brep, Rhino.Geometry.Mesh,
                             Rhino.Geometry.Surface, Rhino.Geometry.Extrusion)):
            geometries.append(geom)

    if not geometries:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No suitable geometry to flatten.")
        return 1

    # Create a cutting plane at Z=0
    cut_plane = Rhino.Geometry.Plane.WorldXY

    pattern_curves = []
    for geom in geometries:
        intersections = _cross_section_curves_at_plane(geom, cut_plane, tol)
        for curve in intersections:
            # Project to Z=0
            projected = Rhino.Geometry.Curve.ProjectToPlane(
                curve, Rhino.Geometry.Plane.WorldXY
            )
            if projected is not None:
                pattern_curves.append(projected)

    if not pattern_curves:
        # Fallback: project the bottom outline
        for geom in geometries:
            bbox = geom.GetBoundingBox(True)
            z_min = bbox.Min.Z
            section_plane = Rhino.Geometry.Plane(
                Rhino.Geometry.Point3d(0, 0, z_min + tol),
                Rhino.Geometry.Vector3d.ZAxis,
            )
            sections = _cross_section_curves_at_plane(geom, section_plane, tol)
            for curve in sections:
                projected = Rhino.Geometry.Curve.ProjectToPlane(
                    curve, Rhino.Geometry.Plane.WorldXY
                )
                if projected is not None:
                    pattern_curves.append(projected)

    if not pattern_curves:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Could not generate flatten pattern.")
        return 1

    # Add pattern curves to the Construction layer
    construction_path = "{0}::Construction".format(_SLM_LAYER_PREFIX)
    layer_idx = doc.Layers.FindByFullPath(construction_path, -1)
    attrs = Rhino.DocObjects.ObjectAttributes()
    if layer_idx >= 0:
        attrs.LayerIndex = layer_idx
    attrs.Name = "SLM_FlattenPattern"

    for curve in pattern_curves:
        doc.Objects.AddCurve(curve, attrs)

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Flatten complete. {0} pattern curve(s) added.".format(
            len(pattern_curves)
        )
    )
    return 0
