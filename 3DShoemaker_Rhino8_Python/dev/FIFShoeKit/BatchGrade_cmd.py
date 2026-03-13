# -*- coding: utf-8 -*-
"""Batch-grade footwear to multiple target sizes in one operation.

Creates a copy of all SLM-layer geometry for each target size and
grades each copy independently.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import json

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import Rhino.RhinoApp
import scriptcontext as sc
import System

__commandname__ = "BatchGrade"


# ---------------------------------------------------------------------------
#  Constants (inlined from plugin)
# ---------------------------------------------------------------------------

_SLM_LAYER_PREFIX = "SLM"
_ALL_CLASSES = ["Last", "Insert", "Bottom", "Foot"]

_EU_GRADE_INCREMENT_LENGTH = 6.667

_SIZE_SYSTEMS = {
    "EU": {"base_size": 40.0, "base_stick_length": 260.0,
           "increment": _EU_GRADE_INCREMENT_LENGTH},
    "US": {"base_size": 8.0, "base_stick_length": 260.0,
           "increment": 8.467},
    "UK": {"base_size": 7.0, "base_stick_length": 260.0,
           "increment": 8.467},
    "Mondopoint": {"base_size": 260.0, "base_stick_length": 260.0,
                   "increment": 5.0},
}

_DOC_KEY_PREFIX = "FIFShoeKit"
_DOC_KEY_SETTINGS = _DOC_KEY_PREFIX + "_Settings"


# ---------------------------------------------------------------------------
#  Helpers (inlined)
# ---------------------------------------------------------------------------

def _get_doc_setting(doc, key, default=None):
    """Read a setting from document user text."""
    raw = doc.Strings.GetValue(_DOC_KEY_SETTINGS, key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _compute_scale_factor(from_size, to_size, size_system):
    """Return the uniform length scale factor for grading between two sizes."""
    info = _SIZE_SYSTEMS.get(size_system, _SIZE_SYSTEMS["EU"])
    from_length = info["base_stick_length"] + (from_size - info["base_size"]) * info["increment"]
    to_length = info["base_stick_length"] + (to_size - info["base_size"]) * info["increment"]
    if abs(from_length) < 1e-9:
        return 1.0
    return to_length / from_length


def _build_grade_transform(scale_factor, origin):
    """Build a uniform scale transform about *origin*."""
    return Rhino.Geometry.Transform.Scale(origin, scale_factor)


def _find_objects_on_layer(doc, layer_name):
    """Return all doc objects residing on *layer_name*."""
    layer_index = doc.Layers.FindByFullPath(layer_name, -1)
    if layer_index < 0:
        for i in range(doc.Layers.Count):
            lyr = doc.Layers[i]
            if not lyr.IsDeleted and lyr.Name == layer_name:
                layer_index = i
                break
    if layer_index < 0:
        return []
    layer = doc.Layers[layer_index]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        return list(objs)
    return []


def _get_orientation_origin(doc):
    """Try to locate the heel-centre point stored on the document."""
    origin = Rhino.Geometry.Point3d.Origin
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        name = obj.Attributes.Name or ""
        if name == "HeelCentre":
            pt_geom = obj.Geometry
            if isinstance(pt_geom, Rhino.Geometry.Point):
                origin = pt_geom.Location
            elif hasattr(pt_geom, "PointAtStart"):
                origin = pt_geom.PointAtStart
            break
    return origin


# ---------------------------------------------------------------------------
#  RunCommand
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    current_size = _get_doc_setting(doc, "last_size", 0.0)
    size_system = _get_doc_setting(doc, "last_size_system", "EU")

    if current_size is None or current_size <= 0:
        Rhino.RhinoApp.WriteLine(
            "No current size is set.  Please run NewBuild first."
        )
        return Rhino.Commands.Result.Failure

    # Prompt for a comma-separated list of target sizes
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt(
        "Enter target sizes (comma-separated, {0} system, current={1})".format(
            size_system, current_size
        )
    )
    gs.Get()
    if gs.CommandResult() != Rhino.Commands.Result.Success:
        return Rhino.Commands.Result.Cancel

    raw = gs.StringResult().strip()
    if not raw:
        Rhino.RhinoApp.WriteLine("No sizes entered.")
        return Rhino.Commands.Result.Cancel

    # Parse sizes
    target_sizes = []
    for token in raw.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            val = float(token)
            if val > 0:
                target_sizes.append(val)
        except ValueError:
            Rhino.RhinoApp.WriteLine(
                "  Skipping invalid size: '{0}'".format(token)
            )

    if not target_sizes:
        Rhino.RhinoApp.WriteLine("No valid sizes provided.")
        return Rhino.Commands.Result.Cancel

    Rhino.RhinoApp.WriteLine(
        "Batch grading from {0} {1} to {2} size(s): {3}".format(
            size_system, current_size, len(target_sizes), target_sizes
        )
    )

    # Gather all objects on SLM layers
    original_ids = []
    for cls in _ALL_CLASSES:
        full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, cls)
        objs = _find_objects_on_layer(doc, full_path)
        for obj in objs:
            original_ids.append(obj.Id)

    if not original_ids:
        Rhino.RhinoApp.WriteLine("No SLM objects found to grade.")
        return Rhino.Commands.Result.Failure

    origin_pt = _get_orientation_origin(doc)

    success_count = 0
    spacing_x = 0.0

    for target_size in target_sizes:
        if abs(target_size - current_size) < 1e-6:
            Rhino.RhinoApp.WriteLine(
                "  Skipping size {0} (same as current).".format(target_size)
            )
            continue

        scale_factor = _compute_scale_factor(
            current_size, target_size, size_system
        )

        # Duplicate objects
        dup_ids = []
        for oid in original_ids:
            src_obj = doc.Objects.FindId(oid)
            if src_obj is None:
                continue
            geom = src_obj.Geometry.Duplicate()
            attrs = src_obj.Attributes.Duplicate()
            name = attrs.Name or ""
            attrs.Name = "{0}_Size{1}".format(name, target_size)
            new_id = doc.Objects.Add(geom, attrs)
            if new_id != System.Guid.Empty:
                dup_ids.append(new_id)

        if not dup_ids:
            Rhino.RhinoApp.WriteLine(
                "  Failed to duplicate objects for size {0}.".format(
                    target_size
                )
            )
            continue

        # Scale the duplicates
        xform_scale = _build_grade_transform(scale_factor, origin_pt)

        # Offset laterally so graded sizes don't overlap
        spacing_x += 350.0
        xform_move = Rhino.Geometry.Transform.Translation(
            Rhino.Geometry.Vector3d(spacing_x, 0, 0)
        )
        xform_combined = xform_move * xform_scale

        transformed = 0
        for oid in dup_ids:
            obj = doc.Objects.FindId(oid)
            if obj is not None:
                if doc.Objects.Transform(obj, xform_combined, True):
                    transformed += 1

        Rhino.RhinoApp.WriteLine(
            "  Size {0}: duplicated and graded {1} object(s) "
            "(scale={2:.4f}).".format(target_size, transformed, scale_factor)
        )
        success_count += 1

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Batch grading complete: {0} size(s) created.".format(success_count)
    )
    return Rhino.Commands.Result.Success
