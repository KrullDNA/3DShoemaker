# -*- coding: utf-8 -*-
"""Adjust orthotic design to fit within the bounds of a physical blank.

Trims, scales, or repositions the orthotic geometry so that it fits
within a user-specified or standard blank outline.

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

__commandname__ = "AdjustOrthoticToBlank"


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Select orthotic
    go_orth = Rhino.Input.Custom.GetObject()
    go_orth.SetCommandPrompt("Select orthotic to adjust")
    go_orth.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
    go_orth.Get()
    if go_orth.CommandResult() != Rhino.Commands.Result.Success:
        return go_orth.CommandResult()

    orth_ref = go_orth.Object(0)
    orth_brep = orth_ref.Brep()
    orth_obj = orth_ref.Object()
    if orth_brep is None:
        Rhino.RhinoApp.WriteLine("Invalid orthotic geometry.")
        return Rhino.Commands.Result.Failure

    # Select blank outline
    go_blank = Rhino.Input.Custom.GetObject()
    go_blank.SetCommandPrompt("Select blank outline curve")
    go_blank.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
    go_blank.Get()
    if go_blank.CommandResult() != Rhino.Commands.Result.Success:
        return go_blank.CommandResult()

    blank_curve = go_blank.Object(0).Curve()
    if blank_curve is None:
        Rhino.RhinoApp.WriteLine("Invalid blank curve.")
        return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine("Adjusting orthotic to blank ...")

    # Compute bounding boxes
    orth_bbox = orth_brep.GetBoundingBox(True)
    blank_bbox = blank_curve.GetBoundingBox(True)

    if not orth_bbox.IsValid or not blank_bbox.IsValid:
        Rhino.RhinoApp.WriteLine("Cannot compute bounding boxes.")
        return Rhino.Commands.Result.Failure

    # Scale to fit within blank
    orth_length = orth_bbox.Max.Y - orth_bbox.Min.Y
    orth_width = orth_bbox.Max.X - orth_bbox.Min.X
    blank_length = blank_bbox.Max.Y - blank_bbox.Min.Y
    blank_width = blank_bbox.Max.X - blank_bbox.Min.X

    scale_y = blank_length / max(orth_length, 1e-6)
    scale_x = blank_width / max(orth_width, 1e-6)
    scale_factor = min(scale_y, scale_x, 1.0)  # Only scale down

    if scale_factor < 1.0:
        orth_center = orth_bbox.Center
        xform_scale = Rhino.Geometry.Transform.Scale(orth_center, scale_factor)
        doc.Objects.Transform(orth_obj, xform_scale, True)
        Rhino.RhinoApp.WriteLine(
            "  Scaled orthotic by {0:.4f} to fit blank.".format(scale_factor)
        )

    # Center orthotic on blank
    new_orth_bbox = doc.Objects.FindId(orth_obj.Id).Geometry.GetBoundingBox(True)
    offset = blank_bbox.Center - new_orth_bbox.Center
    offset.Z = 0  # Keep Z position
    xform_move = Rhino.Geometry.Transform.Translation(
        Rhino.Geometry.Vector3d(offset)
    )
    doc.Objects.Transform(orth_obj, xform_move, True)

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine("Orthotic adjusted to blank.")
    return Rhino.Commands.Result.Success
