# -*- coding: utf-8 -*-
"""Add a metatarsal pad to an insert or footbed.

Creates a dome-shaped pad at the metatarsal head region and unions
it with the existing insert surface.

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

__commandname__ = "AddMetpad"

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
_SLM_LAYER_PREFIX = "SLM"
_CLASS_INSERT = "Insert"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _ensure_layer(doc, name, color_r=255, color_g=165, color_b=0):
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


def _create_met_pad(footbed, center, radius, height):
    """Create a dome-shaped metatarsal pad at center."""
    sphere = Rhino.Geometry.Sphere(center, radius)
    sphere_brep = sphere.ToBrep()

    if sphere_brep is None:
        return None

    # Cut the sphere in half at the footbed surface level
    cut_plane = Rhino.Geometry.Plane(
        center,
        Rhino.Geometry.Vector3d(0, 0, 1),
    )

    trimmed = sphere_brep.Trim(cut_plane, 0.01)
    if trimmed and len(trimmed) > 0:
        dome = trimmed[0]
    else:
        dome = sphere_brep

    # Scale Z to desired height
    if radius > 0:
        z_scale = height / radius
        xform = Rhino.Geometry.Transform.Scale(
            Rhino.Geometry.Plane(center, Rhino.Geometry.Vector3d.ZAxis),
            1.0, 1.0, z_scale,
        )
        dome.Transform(xform)

    return dome


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Select insert/footbed
    go_insert = Rhino.Input.Custom.GetObject()
    go_insert.SetCommandPrompt("Select insert or footbed")
    go_insert.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
    go_insert.Get()
    if go_insert.CommandResult() != Rhino.Commands.Result.Success:
        return go_insert.CommandResult()

    insert_ref = go_insert.Object(0)
    insert_brep = insert_ref.Brep()
    insert_obj = insert_ref.Object()
    if insert_brep is None:
        return Rhino.Commands.Result.Failure

    # Get pad position
    go_pt = Rhino.Input.Custom.GetPoint()
    go_pt.SetCommandPrompt(
        "Pick met pad center (Enter for auto-position)"
    )
    go_pt.AcceptNothing(True)

    opt_radius = Rhino.Input.Custom.OptionDouble(12.0, 3.0, 30.0)
    opt_height = Rhino.Input.Custom.OptionDouble(3.0, 0.5, 10.0)
    go_pt.AddOptionDouble("Radius", opt_radius)
    go_pt.AddOptionDouble("Height", opt_height)

    pad_center = None

    while True:
        res = go_pt.Get()
        if res == Rhino.Input.GetResult.Point:
            pad_center = go_pt.Point()
            break
        elif res == Rhino.Input.GetResult.Nothing:
            # Auto-position at ~65% length, medial offset
            bbox = insert_brep.GetBoundingBox(True)
            if bbox.IsValid:
                pad_center = Rhino.Geometry.Point3d(
                    (bbox.Min.X + bbox.Max.X) / 2.0 - 5.0,
                    bbox.Min.Y + (bbox.Max.Y - bbox.Min.Y) * 0.65,
                    bbox.Max.Z,
                )
            break
        elif res == Rhino.Input.GetResult.Option:
            continue
        else:
            return Rhino.Commands.Result.Cancel

    if pad_center is None:
        return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine("Adding metatarsal pad ...")

    pad = _create_met_pad(
        insert_brep, pad_center,
        opt_radius.CurrentValue, opt_height.CurrentValue,
    )

    if pad is not None and pad.IsValid:
        # Try boolean union
        results = Rhino.Geometry.Brep.CreateBooleanUnion(
            [insert_brep, pad], 0.01
        )
        if results and len(results) > 0 and results[0].IsValid:
            doc.Objects.Replace(insert_obj.Id, results[0])
        else:
            # If union fails, add pad as separate object
            layer_idx = _ensure_layer(doc, _CLASS_INSERT, 255, 165, 0)
            attrs = Rhino.DocObjects.ObjectAttributes()
            attrs.LayerIndex = layer_idx
            attrs.Name = "MetPad"
            doc.Objects.AddBrep(pad, attrs)
            Rhino.RhinoApp.WriteLine(
                "  Boolean union failed; pad added as separate object."
            )

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Metatarsal pad added.")
        return Rhino.Commands.Result.Success
    else:
        Rhino.RhinoApp.WriteLine("Met pad creation failed.")
        return Rhino.Commands.Result.Failure
