# -*- coding: utf-8 -*-
"""Apply twist deformation to an orthotic.

Rotates the forefoot relative to the rearfoot about the longitudinal
axis, simulating forefoot varus/valgus correction.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import math
import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc
import System

__commandname__ = "TwistOrthotic"


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Select orthotic
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select orthotic to twist")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
    go.Get()
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return go.CommandResult()

    orth_ref = go.Object(0)
    orth_brep = orth_ref.Brep()
    orth_obj = orth_ref.Object()
    if orth_brep is None:
        return Rhino.Commands.Result.Failure

    # Get twist angle
    go_angle = Rhino.Input.Custom.GetOption()
    go_angle.SetCommandPrompt("Twist orthotic")
    opt_angle = Rhino.Input.Custom.OptionDouble(5.0, -30.0, 30.0)
    opt_pivot_ratio = Rhino.Input.Custom.OptionDouble(0.50, 0.2, 0.8)
    go_angle.AddOptionDouble("TwistAngleDegrees", opt_angle)
    go_angle.AddOptionDouble("PivotRatio", opt_pivot_ratio)

    while True:
        res = go_angle.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            continue
        break

    angle_deg = opt_angle.CurrentValue
    pivot_ratio = opt_pivot_ratio.CurrentValue

    if abs(angle_deg) < 0.01:
        Rhino.RhinoApp.WriteLine("Twist angle is zero.  Nothing to do.")
        return Rhino.Commands.Result.Nothing

    Rhino.RhinoApp.WriteLine(
        "Applying {0:.1f} degree twist at {1:.0%} pivot ...".format(
            angle_deg, pivot_ratio
        )
    )

    bbox = orth_brep.GetBoundingBox(True)
    if not bbox.IsValid:
        return Rhino.Commands.Result.Failure

    total_length = bbox.Max.Y - bbox.Min.Y
    pivot_y = bbox.Min.Y + total_length * pivot_ratio
    center_x = (bbox.Min.X + bbox.Max.X) / 2.0
    center_z = (bbox.Min.Z + bbox.Max.Z) / 2.0

    # Apply twist by rotating control points proportionally
    modified = orth_brep.DuplicateBrep()
    angle_rad = math.radians(angle_deg)

    for face_idx in range(modified.Faces.Count):
        face = modified.Faces[face_idx]
        srf = face.UnderlyingSurface()
        if not isinstance(srf, Rhino.Geometry.NurbsSurface):
            continue
        nurbs = srf.ToNurbsSurface()
        if nurbs is None:
            continue

        for u_idx in range(nurbs.Points.CountU):
            for v_idx in range(nurbs.Points.CountV):
                cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                pt = cp.Location

                # Twist factor: 0 at pivot, +-1 at extremes
                if pt.Y > pivot_y:
                    t = (pt.Y - pivot_y) / max(bbox.Max.Y - pivot_y, 1e-6)
                else:
                    t = -(pivot_y - pt.Y) / max(pivot_y - bbox.Min.Y, 1e-6)

                local_angle = angle_rad * t
                # Rotate in the XZ plane about the center line
                dx = pt.X - center_x
                dz = pt.Z - center_z
                cos_a = math.cos(local_angle)
                sin_a = math.sin(local_angle)
                new_x = center_x + dx * cos_a - dz * sin_a
                new_z = center_z + dx * sin_a + dz * cos_a
                new_pt = Rhino.Geometry.Point3d(new_x, pt.Y, new_z)
                nurbs.Points.SetControlPoint(
                    u_idx, v_idx,
                    Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                )

    if modified.IsValid:
        doc.Objects.Replace(orth_obj.Id, modified)
        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            "Twist of {0:.1f} degrees applied.".format(angle_deg)
        )
        return Rhino.Commands.Result.Success
    else:
        Rhino.RhinoApp.WriteLine("Twist produced invalid geometry.")
        return Rhino.Commands.Result.Failure
