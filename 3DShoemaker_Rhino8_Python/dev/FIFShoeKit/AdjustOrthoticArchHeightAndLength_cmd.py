# -*- coding: utf-8 -*-
"""Modify orthotic arch height and arch length parameters.

Interactively adjust the medial longitudinal arch support height and
the longitudinal extent of the arch region.

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

__commandname__ = "AdjustOrthoticArchHeightAndLength"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _apply_arch_profile(shell, arch_height, arch_start_ratio=0.35, arch_end_ratio=0.75):
    """Apply a smooth arch profile to the orthotic shell by adjusting
    control points in the arch region upward by arch_height.
    """
    if shell is None or arch_height <= 0:
        return shell

    bbox = shell.GetBoundingBox(True)
    total_length = bbox.Max.Y - bbox.Min.Y
    arch_start_y = bbox.Min.Y + total_length * arch_start_ratio
    arch_end_y = bbox.Min.Y + total_length * arch_end_ratio

    for face_idx in range(shell.Faces.Count):
        face = shell.Faces[face_idx]
        srf = face.UnderlyingSurface()
        if isinstance(srf, Rhino.Geometry.NurbsSurface):
            nurbs = srf.ToNurbsSurface()
            if nurbs is not None:
                for u_idx in range(nurbs.Points.CountU):
                    for v_idx in range(nurbs.Points.CountV):
                        cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                        pt = cp.Location
                        if arch_start_y <= pt.Y <= arch_end_y:
                            t = (pt.Y - arch_start_y) / (arch_end_y - arch_start_y)
                            dz = arch_height * math.sin(t * math.pi)
                            new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                            nurbs.Points.SetControlPoint(
                                u_idx, v_idx,
                                Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                            )

    return shell


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Select orthotic
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select orthotic to adjust arch")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
    go.Get()
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return go.CommandResult()

    orth_ref = go.Object(0)
    orth_brep = orth_ref.Brep()
    orth_obj = orth_ref.Object()
    if orth_brep is None:
        Rhino.RhinoApp.WriteLine("Invalid orthotic geometry.")
        return Rhino.Commands.Result.Failure

    # Options
    go_opt = Rhino.Input.Custom.GetOption()
    go_opt.SetCommandPrompt("Adjust arch height and length")

    opt_height = Rhino.Input.Custom.OptionDouble(8.0, 0.0, 40.0)
    opt_start = Rhino.Input.Custom.OptionDouble(0.35, 0.1, 0.6)
    opt_end = Rhino.Input.Custom.OptionDouble(0.75, 0.5, 0.95)

    go_opt.AddOptionDouble("ArchHeight", opt_height)
    go_opt.AddOptionDouble("ArchStartRatio", opt_start)
    go_opt.AddOptionDouble("ArchEndRatio", opt_end)

    while True:
        res = go_opt.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            continue
        break

    arch_height = opt_height.CurrentValue
    arch_start = opt_start.CurrentValue
    arch_end = opt_end.CurrentValue

    Rhino.RhinoApp.WriteLine(
        "Applying arch: height={0:.1f} mm, start={1:.0%}, end={2:.0%}".format(
            arch_height, arch_start, arch_end
        )
    )

    new_brep = _apply_arch_profile(orth_brep, arch_height, arch_start, arch_end)
    if new_brep is not None and new_brep.IsValid:
        doc.Objects.Replace(orth_obj.Id, new_brep)
        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Arch adjustment applied.")
        return Rhino.Commands.Result.Success
    else:
        Rhino.RhinoApp.WriteLine("Arch adjustment failed.")
        return Rhino.Commands.Result.Failure
