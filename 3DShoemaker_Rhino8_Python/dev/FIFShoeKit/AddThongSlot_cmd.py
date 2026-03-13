# -*- coding: utf-8 -*-
"""Add a thong slot to a sandal.

Creates a rectangular slot at the toe area for thong-strap insertion.

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
import System
import System.Drawing

__commandname__ = "AddThongSlot"

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
_SLM_LAYER_PREFIX = "SLM"
_SANDAL_LAYER = "Sandal"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _ensure_layer(doc, name, color_r=200, color_g=160, color_b=80):
    """Ensure SLM::<name> exists and return its index."""
    full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, name)
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx >= 0:
        return idx

    parent_idx = doc.Layers.FindByFullPath(_SLM_LAYER_PREFIX, -1)
    if parent_idx < 0:
        parent_layer = Rhino.DocObjects.Layer()
        parent_layer.Name = _SLM_LAYER_PREFIX
        parent_idx = doc.Layers.Add(parent_layer)

    parent_id = doc.Layers[parent_idx].Id
    child = Rhino.DocObjects.Layer()
    child.Name = name
    child.ParentLayerId = parent_id
    child.Color = System.Drawing.Color.FromArgb(color_r, color_g, color_b)
    return doc.Layers.Add(child)


def _create_thong_slot(sole_brep, slot_position, slot_width, slot_depth, slot_length):
    """Create a thong slot cut into the sole at slot_position.

    Returns (modified_sole, slot_geometry) tuple.
    """
    if sole_brep is None:
        return None, None

    half_w = slot_width / 2.0
    half_l = slot_length / 2.0

    box_brep = Rhino.Geometry.Brep.CreateFromBox(
        Rhino.Geometry.BoundingBox(
            Rhino.Geometry.Point3d(
                slot_position.X - half_w,
                slot_position.Y - half_l,
                slot_position.Z - slot_depth,
            ),
            Rhino.Geometry.Point3d(
                slot_position.X + half_w,
                slot_position.Y + half_l,
                slot_position.Z,
            ),
        )
    )

    if box_brep is None:
        return sole_brep, None

    slot_geom = box_brep.DuplicateBrep()

    results = Rhino.Geometry.Brep.CreateBooleanDifference(
        sole_brep, box_brep, 0.01
    )
    if results and len(results) > 0:
        return results[0], slot_geom

    return sole_brep, slot_geom


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Select sole
    go_sole = Rhino.Input.Custom.GetObject()
    go_sole.SetCommandPrompt("Select sandal sole for thong slot")
    go_sole.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
    go_sole.Get()
    if go_sole.CommandResult() != Rhino.Commands.Result.Success:
        return go_sole.CommandResult()

    sole_ref = go_sole.Object(0)
    sole_brep = sole_ref.Brep()
    sole_obj = sole_ref.Object()
    if sole_brep is None:
        return Rhino.Commands.Result.Failure

    # Get slot position
    go_pt = Rhino.Input.Custom.GetPoint()
    go_pt.SetCommandPrompt(
        "Pick thong slot location (Enter for auto-position at toe)"
    )
    go_pt.AcceptNothing(True)

    opt_width = Rhino.Input.Custom.OptionDouble(6.0, 2.0, 20.0)
    opt_depth = Rhino.Input.Custom.OptionDouble(4.0, 1.0, 15.0)
    opt_length = Rhino.Input.Custom.OptionDouble(12.0, 4.0, 40.0)
    go_pt.AddOptionDouble("SlotWidth", opt_width)
    go_pt.AddOptionDouble("SlotDepth", opt_depth)
    go_pt.AddOptionDouble("SlotLength", opt_length)

    slot_position = None

    while True:
        res = go_pt.Get()
        if res == Rhino.Input.GetResult.Point:
            slot_position = go_pt.Point()
            break
        elif res == Rhino.Input.GetResult.Nothing:
            # Auto-position at toe
            bbox = sole_brep.GetBoundingBox(True)
            if bbox.IsValid:
                slot_position = Rhino.Geometry.Point3d(
                    (bbox.Min.X + bbox.Max.X) / 2.0,
                    bbox.Max.Y - (bbox.Max.Y - bbox.Min.Y) * 0.12,
                    bbox.Max.Z,
                )
            break
        elif res == Rhino.Input.GetResult.Option:
            continue
        else:
            return Rhino.Commands.Result.Cancel

    if slot_position is None:
        Rhino.RhinoApp.WriteLine("Could not determine slot position.")
        return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine("Adding thong slot ...")

    modified, slot_geom = _create_thong_slot(
        sole_brep, slot_position,
        opt_width.CurrentValue,
        opt_depth.CurrentValue,
        opt_length.CurrentValue,
    )

    if modified is not None and modified.IsValid:
        doc.Objects.Replace(sole_obj.Id, modified)

        # Add slot geometry as reference object
        if slot_geom is not None:
            layer_idx = _ensure_layer(doc, _SANDAL_LAYER)
            attrs = Rhino.DocObjects.ObjectAttributes()
            attrs.LayerIndex = layer_idx
            attrs.Name = "ThongSlot"
            doc.Objects.AddBrep(slot_geom, attrs)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Thong slot added.")
        return Rhino.Commands.Result.Success
    else:
        Rhino.RhinoApp.WriteLine("Thong slot creation failed.")
        return Rhino.Commands.Result.Failure
