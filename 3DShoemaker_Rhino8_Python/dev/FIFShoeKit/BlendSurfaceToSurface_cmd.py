# -*- coding: utf-8 -*-
"""Create a smooth blend surface between two surfaces.

Picks an edge on each surface and creates a G2-continuous blend
surface connecting them.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import Rhino.RhinoApp
import scriptcontext as sc

__commandname__ = "BlendSurfaceToSurface"


def RunCommand(is_interactive):
    doc = sc.doc

    # Select first surface edge
    go1 = Rhino.Input.Custom.GetObject()
    go1.SetCommandPrompt("Select first surface edge")
    go1.GeometryFilter = Rhino.DocObjects.ObjectType.EdgeFilter
    go1.Get()
    if go1.CommandResult() != Rhino.Commands.Result.Success:
        return go1.CommandResult()

    edge1_ref = go1.Object(0)
    face1 = edge1_ref.Face()
    edge1 = edge1_ref.Edge()
    if face1 is None or edge1 is None:
        Rhino.RhinoApp.WriteLine("Invalid first edge selection.")
        return Rhino.Commands.Result.Failure

    # Select second surface edge
    go2 = Rhino.Input.Custom.GetObject()
    go2.SetCommandPrompt("Select second surface edge")
    go2.GeometryFilter = Rhino.DocObjects.ObjectType.EdgeFilter
    go2.EnablePreSelect(False, True)
    go2.Get()
    if go2.CommandResult() != Rhino.Commands.Result.Success:
        return go2.CommandResult()

    edge2_ref = go2.Object(0)
    face2 = edge2_ref.Face()
    edge2 = edge2_ref.Edge()
    if face2 is None or edge2 is None:
        Rhino.RhinoApp.WriteLine("Invalid second edge selection.")
        return Rhino.Commands.Result.Failure

    # Blend options
    go_opt = Rhino.Input.Custom.GetOption()
    go_opt.SetCommandPrompt("Blend options")
    continuity_list = ["Position", "Tangent", "Curvature"]
    go_opt.AddOptionList("Continuity", continuity_list, 2)

    while True:
        res = go_opt.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            continue
        break

    Rhino.RhinoApp.WriteLine("Creating blend surface ...")

    # Use Rhino's built-in BlendSurface
    blend_continuity = Rhino.Geometry.BlendContinuity.Curvature

    breps = Rhino.Geometry.Brep.CreateBlendSurface(
        face1, edge1, face1.Domain(0), False,
        face2, edge2, face2.Domain(0), False,
        blend_continuity, blend_continuity,
        0.01,
    )

    if breps and len(breps) > 0:
        for b in breps:
            if b is not None and b.IsValid:
                attrs = Rhino.DocObjects.ObjectAttributes()
                attrs.Name = "BlendSurface"
                doc.Objects.AddBrep(b, attrs)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Blend surface created.")
        return Rhino.Commands.Result.Success
    else:
        # Fallback: create a loft between the edge curves
        Rhino.RhinoApp.WriteLine(
            "  Native blend failed; attempting loft fallback ..."
        )
        curve1 = edge1.EdgeCurve
        curve2 = edge2.EdgeCurve
        if curve1 is not None and curve2 is not None:
            loft_breps = Rhino.Geometry.Brep.CreateFromLoft(
                [curve1, curve2],
                Rhino.Geometry.Point3d.Unset,
                Rhino.Geometry.Point3d.Unset,
                Rhino.Geometry.LoftType.Normal,
                False,
            )
            if loft_breps and len(loft_breps) > 0:
                for b in loft_breps:
                    if b is not None and b.IsValid:
                        attrs = Rhino.DocObjects.ObjectAttributes()
                        attrs.Name = "BlendSurface_Loft"
                        doc.Objects.AddBrep(b, attrs)
                doc.Views.Redraw()
                Rhino.RhinoApp.WriteLine("Loft blend surface created.")
                return Rhino.Commands.Result.Success

        Rhino.RhinoApp.WriteLine("Blend surface creation failed.")
        return Rhino.Commands.Result.Failure
