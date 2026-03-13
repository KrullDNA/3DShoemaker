# -*- coding: utf-8 -*-
"""Flattens sole geometry to a 2D pattern.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import scriptcontext as sc
import System

__commandname__ = "FlattenSole"


def _flatten_geometry(doc, geom, name):
    """Flatten a 3D geometry to a 2D pattern by projecting Z to 0."""
    brep = None
    if isinstance(geom, rg.Brep):
        brep = geom
    elif isinstance(geom, rg.SubD):
        brep = geom.ToBrep(rg.SubDToBrepOptions())
    elif isinstance(geom, rg.Surface):
        brep = geom.ToBrep()

    if brep is None:
        return False

    mesh_list = rg.Mesh.CreateFromBrep(brep, rg.MeshingParameters.Default)
    if not mesh_list or len(mesh_list) == 0:
        return False

    combined = rg.Mesh()
    for m in mesh_list:
        combined.Append(m)

    bbox = combined.GetBoundingBox(True)

    flat_mesh = rg.Mesh()
    for i in range(combined.Vertices.Count):
        pt = combined.Vertices[i]
        flat_mesh.Vertices.Add(rg.Point3d(pt.X, pt.Y, 0))

    for i in range(combined.Faces.Count):
        face = combined.Faces[i]
        if face.IsQuad:
            flat_mesh.Faces.AddFace(face.A, face.B, face.C, face.D)
        else:
            flat_mesh.Faces.AddFace(face.A, face.B, face.C)

    flat_mesh.Normals.ComputeNormals()
    flat_mesh.Compact()

    offset = rg.Vector3d(bbox.Diagonal.X * 1.5, 0, 0)
    flat_mesh.Translate(offset)

    layer_name = "Feet in Focus Shoe Kit::Flattened"
    layer_index = doc.Layers.FindByFullPath(layer_name, -1)
    if layer_index < 0:
        layer = rdo.Layer()
        layer.Name = "Flattened"
        parent_idx = doc.Layers.FindByFullPath("Feet in Focus Shoe Kit", -1)
        if parent_idx >= 0:
            layer.ParentLayerId = doc.Layers[parent_idx].Id
        layer_index = doc.Layers.Add(layer)

    attrs = rdo.ObjectAttributes()
    attrs.LayerIndex = layer_index
    attrs.Name = name

    outline_curves = flat_mesh.GetNakedEdges()
    if outline_curves:
        for curve in outline_curves:
            doc.Objects.AddCurve(curve, attrs)

    doc.Objects.AddMesh(flat_mesh, attrs)
    return True


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        go = ric.GetObject()
        go.SetCommandPrompt("Select sole surface to flatten")
        go.GeometryFilter = rdo.ObjectType.Surface | rdo.ObjectType.Brep | rdo.ObjectType.SubD
        go.Get()
        if go.CommandResult() != rc.Result.Success:
            return go.CommandResult()

        geom = go.Object(0).Geometry()
        if geom is None:
            return rc.Result.Failure

        if _flatten_geometry(doc, geom, "FlattenedSole"):
            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Sole flattened successfully.")
            return rc.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("Could not flatten sole.")
            return rc.Result.Failure

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error flattening sole: {0}".format(e))
        return rc.Result.Failure
