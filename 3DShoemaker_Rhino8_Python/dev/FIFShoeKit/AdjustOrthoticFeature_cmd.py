# -*- coding: utf-8 -*-
"""Adjust a specific orthotic feature (posting, met pad, heel lift, etc.).

Presents a list of adjustable features and applies the selected
modification to the orthotic geometry via control point manipulation.

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

__commandname__ = "AdjustOrthoticFeature"


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Select orthotic
    go_sel = Rhino.Input.Custom.GetObject()
    go_sel.SetCommandPrompt("Select orthotic to modify")
    go_sel.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
    go_sel.Get()
    if go_sel.CommandResult() != Rhino.Commands.Result.Success:
        return go_sel.CommandResult()

    orth_ref = go_sel.Object(0)
    orth_brep = orth_ref.Brep()
    orth_obj = orth_ref.Object()
    if orth_brep is None:
        return Rhino.Commands.Result.Failure

    # Choose feature
    features = [
        "MedialPosting", "LateralPosting", "HeelLift",
        "MetPad", "HeelCup", "ForefootExtension",
        "RearfootExtension", "TopCover",
    ]

    go_feat = Rhino.Input.Custom.GetOption()
    go_feat.SetCommandPrompt("Select feature to adjust")
    go_feat.AddOptionList("Feature", features, 0)
    opt_value = Rhino.Input.Custom.OptionDouble(0.0, -20.0, 40.0)
    go_feat.AddOptionDouble("Value", opt_value)

    feature_idx = 0
    while True:
        res = go_feat.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            idx = go_feat.OptionIndex()
            if idx == 0:
                feature_idx = go_feat.Option().CurrentListOptionIndex
            continue
        break

    if feature_idx < len(features):
        feature_name = features[feature_idx]
    else:
        feature_name = features[0]
    value = opt_value.CurrentValue

    Rhino.RhinoApp.WriteLine(
        "Adjusting {0} by {1:.2f} mm ...".format(feature_name, value)
    )

    bbox = orth_brep.GetBoundingBox(True)
    if not bbox.IsValid:
        return Rhino.Commands.Result.Failure

    total_length = bbox.Max.Y - bbox.Min.Y
    center_x = (bbox.Min.X + bbox.Max.X) / 2.0
    modified = orth_brep.DuplicateBrep()

    # Apply feature-specific modifications via control point manipulation
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
                dz = 0.0
                rel_y = (pt.Y - bbox.Min.Y) / max(total_length, 1e-6)

                if feature_name == "MedialPosting":
                    if pt.X < center_x and 0.2 < rel_y < 0.8:
                        medial_factor = (center_x - pt.X) / max(
                            center_x - bbox.Min.X, 1e-6
                        )
                        dz = value * min(medial_factor, 1.0)

                elif feature_name == "LateralPosting":
                    if pt.X > center_x and 0.2 < rel_y < 0.8:
                        lateral_factor = (pt.X - center_x) / max(
                            bbox.Max.X - center_x, 1e-6
                        )
                        dz = value * min(lateral_factor, 1.0)

                elif feature_name == "HeelLift":
                    if rel_y < 0.25:
                        dz = value * (1.0 - rel_y / 0.25)

                elif feature_name == "MetPad":
                    if 0.55 < rel_y < 0.75:
                        t = (rel_y - 0.55) / 0.20
                        dz = value * math.sin(t * math.pi)

                elif feature_name == "HeelCup":
                    if rel_y < 0.20:
                        edge_dist = abs(pt.X - center_x) / max(
                            (bbox.Max.X - bbox.Min.X) / 2, 1e-6
                        )
                        dz = value * min(edge_dist, 1.0) * (1.0 - rel_y / 0.20)

                elif feature_name == "ForefootExtension":
                    if rel_y > 0.75:
                        dz = value * ((rel_y - 0.75) / 0.25)

                elif feature_name == "RearfootExtension":
                    if rel_y < 0.30:
                        dz = value * (1.0 - rel_y / 0.30)

                elif feature_name == "TopCover":
                    dz = value  # Uniform offset

                if abs(dz) > 1e-9:
                    new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                    nurbs.Points.SetControlPoint(
                        u_idx, v_idx,
                        Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                    )

    if modified.IsValid:
        doc.Objects.Replace(orth_obj.Id, modified)
        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            "{0} adjusted by {1:.2f} mm.".format(feature_name, value)
        )
        return Rhino.Commands.Result.Success
    else:
        Rhino.RhinoApp.WriteLine("Feature adjustment produced invalid geometry.")
        return Rhino.Commands.Result.Failure
