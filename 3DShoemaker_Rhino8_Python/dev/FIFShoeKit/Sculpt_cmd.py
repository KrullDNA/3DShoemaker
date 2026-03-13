# -*- coding: utf-8 -*-
"""Sculpting / freeform editing of surfaces.

Provides a brush-based deformation tool that pushes or pulls
surface points within a user-defined radius.

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
import Rhino.RhinoApp
import scriptcontext as sc

__commandname__ = "Sculpt"


def _sculpt_mesh(mesh, center, radius, strength):
    """Deform mesh vertices near *center* within *radius*."""
    for i in range(mesh.Vertices.Count):
        v = mesh.Vertices[i]
        pt = Rhino.Geometry.Point3d(v.X, v.Y, v.Z)
        dist = pt.DistanceTo(center)
        if dist < radius:
            # Gaussian falloff
            falloff = math.exp(-(dist * dist) / (2.0 * (radius / 3.0) ** 2))
            # Get normal at vertex
            n = mesh.Normals[i]
            normal = Rhino.Geometry.Vector3d(n.X, n.Y, n.Z)
            normal.Unitize()
            offset = normal * strength * falloff
            new_pt = Rhino.Geometry.Point3f(
                float(pt.X + offset.X),
                float(pt.Y + offset.Y),
                float(pt.Z + offset.Z),
            )
            mesh.Vertices.SetVertex(i, new_pt)
    mesh.Normals.ComputeNormals()


def _sculpt_brep(doc, rhino_obj, brep, center, radius, strength):
    """Deform brep by adjusting NURBS surface control points."""
    modified = brep.DuplicateBrep()
    changed = False

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
                dist = pt.DistanceTo(center)
                if dist < radius:
                    falloff = math.exp(
                        -(dist * dist) / (2.0 * (radius / 3.0) ** 2)
                    )
                    # Use Z-up as default normal for brep CPs
                    dz = strength * falloff
                    new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                    nurbs.Points.SetControlPoint(
                        u_idx, v_idx,
                        Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                    )
                    changed = True

    if changed:
        doc.Objects.Replace(rhino_obj.Id, modified)


def _sculpt_subd(subd, center, radius, strength):
    """Deform SubD vertices near *center*."""
    for i in range(subd.Vertices.Count):
        v = subd.Vertices[i]
        pt = v.ControlNetPoint
        dist = pt.DistanceTo(center)
        if dist < radius:
            falloff = math.exp(
                -(dist * dist) / (2.0 * (radius / 3.0) ** 2)
            )
            # Use surface normal at vertex if available
            normal = v.SurfaceNormal()
            if normal is None or not normal.IsValid:
                normal = Rhino.Geometry.Vector3d(0, 0, 1)
            normal.Unitize()
            offset = normal * strength * falloff
            new_pt = Rhino.Geometry.Point3d(
                pt.X + offset.X, pt.Y + offset.Y, pt.Z + offset.Z
            )
            v.ControlNetPoint = new_pt


def RunCommand(is_interactive):
    doc = sc.doc

    # Select surface or mesh
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select surface or mesh to sculpt")
    go.GeometryFilter = (
        Rhino.DocObjects.ObjectType.Brep
        | Rhino.DocObjects.ObjectType.Mesh
        | Rhino.DocObjects.ObjectType.SubD
    )
    go.Get()
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return go.CommandResult()

    obj_ref = go.Object(0)
    rhino_obj = obj_ref.Object()
    geom = obj_ref.Geometry()
    if geom is None:
        return Rhino.Commands.Result.Failure

    # Sculpt parameters
    go_opt = Rhino.Input.Custom.GetOption()
    go_opt.SetCommandPrompt("Sculpt settings")
    opt_radius = Rhino.Input.Custom.OptionDouble(10.0, 1.0, 100.0)
    opt_strength = Rhino.Input.Custom.OptionDouble(1.0, 0.1, 10.0)
    opt_direction = Rhino.Input.Custom.OptionToggle(True, "Pull", "Push")

    go_opt.AddOptionDouble("BrushRadius", opt_radius)
    go_opt.AddOptionDouble("Strength", opt_strength)
    go_opt.AddOptionToggle("Direction", opt_direction)

    while True:
        res = go_opt.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            continue
        break

    brush_radius = opt_radius.CurrentValue
    strength = opt_strength.CurrentValue
    push = opt_direction.CurrentValue  # True = Push (outward), False = Pull

    # Interactive sculpting loop: pick points on surface
    Rhino.RhinoApp.WriteLine(
        "Click on surface to sculpt.  Press Enter or Escape to finish."
    )

    sculpt_count = 0

    while True:
        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt("Pick sculpt point (Enter to finish)")
        gp.AcceptNothing(True)
        gp.Constrain(geom, False)

        res = gp.Get()
        if res == Rhino.Input.GetResult.Nothing:
            break
        if res != Rhino.Input.GetResult.Point:
            break

        hit_pt = gp.Point()
        direction_sign = 1.0 if push else -1.0

        # Apply deformation based on geometry type
        if isinstance(geom, Rhino.Geometry.Mesh):
            _sculpt_mesh(
                geom, hit_pt, brush_radius,
                strength * direction_sign,
            )
            doc.Objects.Replace(rhino_obj.Id, geom)
        elif isinstance(geom, Rhino.Geometry.Brep):
            _sculpt_brep(
                doc, rhino_obj, geom, hit_pt,
                brush_radius, strength * direction_sign,
            )
        elif isinstance(geom, Rhino.Geometry.SubD):
            _sculpt_subd(
                geom, hit_pt, brush_radius,
                strength * direction_sign,
            )
            doc.Objects.Replace(rhino_obj.Id, geom)

        sculpt_count += 1
        doc.Views.Redraw()

    Rhino.RhinoApp.WriteLine(
        "Sculpting complete: {0} stroke(s).".format(sculpt_count)
    )
    return Rhino.Commands.Result.Success
