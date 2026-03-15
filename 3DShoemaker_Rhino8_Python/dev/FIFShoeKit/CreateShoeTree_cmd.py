# -*- coding: utf-8 -*-
"""Create shoe tree from last geometry.

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

__commandname__ = "CreateShoeTree"

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


def _ensure_brep(geom):
    """Convert geometry to brep. For meshes, decimates first to avoid hang."""
    if isinstance(geom, Rhino.Geometry.Brep):
        return geom
    if isinstance(geom, Rhino.Geometry.Extrusion):
        return geom.ToBrep()
    if isinstance(geom, Rhino.Geometry.Surface):
        return geom.ToBrep()
    if isinstance(geom, Rhino.Geometry.Mesh):
        work_mesh = geom.DuplicateMesh()
        if work_mesh.Faces.Count > 5000:
            work_mesh.Reduce(5000, True, 5, True)
        brep = Rhino.Geometry.Brep.CreateFromMesh(work_mesh, False)
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


def _mm_to_model(value, doc):
    """Convert a value in millimetres to model units."""
    scale = Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Millimeters, doc.ModelUnitSystem)
    return value * scale


def _create_offset_surface(geom, offset_distance, tolerance):
    """Create an offset surface from geometry at the given distance."""
    if isinstance(geom, Rhino.Geometry.Mesh):
        offset_mesh = geom.Offset(offset_distance)
        if offset_mesh is not None:
            return offset_mesh
        # Fallback: convert decimated mesh to brep and offset
        brep = _ensure_brep(geom)
        if brep is not None:
            offsets = Rhino.Geometry.Brep.CreateOffsetBrep(
                brep, offset_distance, True, True, tolerance
            )
            if offsets and len(offsets) > 0:
                return offsets[0]
        return None

    brep = geom
    if isinstance(geom, Rhino.Geometry.Extrusion):
        brep = geom.ToBrep()
    elif isinstance(geom, Rhino.Geometry.Surface):
        brep = geom.ToBrep()

    if brep is not None and isinstance(brep, Rhino.Geometry.Brep):
        offsets = Rhino.Geometry.Brep.CreateOffsetBrep(
            brep, offset_distance, True, True, tolerance
        )
        if offsets and len(offsets) > 0:
            return offsets[0]
    return None


def RunCommand(is_interactive):
    doc = sc.doc
    tol = doc.ModelAbsoluteTolerance

    last_geom = _get_last_geometry(doc)
    if last_geom is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
        return Rhino.Commands.Result.Failure

    clearance_mm = _prompt_float("Shoe tree clearance/offset (mm)", -2.0)
    if clearance_mm is None:
        return Rhino.Commands.Result.Cancel
    clearance = _mm_to_model(clearance_mm, doc)

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating shoe tree...")

    # Offset the last inward to create the tree shape
    tree_brep = _create_offset_surface(last_geom, clearance, tol)
    if tree_brep is None:
        # Fallback: scale slightly smaller
        tree_brep = last_geom.Duplicate()
        bbox = last_geom.GetBoundingBox(True)
        center = bbox.Center
        diag_len = bbox.Diagonal.Length
        if diag_len < 1.0:
            diag_len = 1.0
        scale_factor = 1.0 + (clearance / diag_len)
        scale = Rhino.Geometry.Transform.Scale(center, scale_factor)
        tree_brep.Transform(scale)

    _add_component(doc, tree_brep, CLASS_LAST, "SLM_ShoeTree")

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Shoe tree created with {0}mm offset.".format(clearance)
    )
    return Rhino.Commands.Result.Success
