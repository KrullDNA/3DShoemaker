# -*- coding: utf-8 -*-
"""Prepares model for 3D printing with shell creation and support generation.

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
import math

__commandname__ = "PrintPrep"


def _get_or_create_layer(doc, parent_name, child_name):
    """Return layer index for parent::child, creating if needed."""
    full_path = "{0}::{1}".format(parent_name, child_name)
    layer_index = doc.Layers.FindByFullPath(full_path, -1)
    if layer_index < 0:
        layer = rdo.Layer()
        layer.Name = child_name
        parent_idx = doc.Layers.FindByFullPath(parent_name, -1)
        if parent_idx >= 0:
            layer.ParentLayerId = doc.Layers[parent_idx].Id
        layer_index = doc.Layers.Add(layer)
    return layer_index


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        # Prompt for print prep options via command-line options
        go_opts = ric.GetOption()
        go_opts.SetCommandPrompt("Print preparation options (Enter when done)")
        go_opts.AcceptNothing(True)

        opt_thickness = ric.OptionDouble(2.0, 0.0, 20.0)
        opt_maximize = ric.OptionToggle(False, "No", "Yes")
        opt_postprocess = ric.OptionToggle(False, "No", "Yes")

        go_opts.AddOptionDouble("ShellThickness", opt_thickness)
        go_opts.AddOptionToggle("MaximizePrintable", opt_maximize)
        go_opts.AddOptionToggle("PostProcess", opt_postprocess)

        while True:
            res = go_opts.Get()
            if res == Rhino.Input.GetResult.Option:
                continue
            break

        # Select objects to prepare
        go = ric.GetObject()
        go.SetCommandPrompt("Select objects to prepare for printing")
        go.GeometryFilter = rdo.ObjectType.Brep | rdo.ObjectType.Mesh | rdo.ObjectType.SubD
        go.EnablePreSelect(True, True)
        go.GetMultiple(1, 0)
        if go.CommandResult() != rc.Result.Success:
            return go.CommandResult()

        shell_thickness = opt_thickness.CurrentValue
        maximize_printable = opt_maximize.CurrentValue
        post_process = opt_postprocess.CurrentValue

        layer_index = _get_or_create_layer(doc, "Feet in Focus Shoe Kit", "PrintPrep")
        attrs = rdo.ObjectAttributes()
        attrs.LayerIndex = layer_index

        processed = 0
        for i in range(go.ObjectCount):
            geom = go.Object(i).Geometry()
            mesh = None
            if isinstance(geom, rg.Mesh):
                mesh = geom.DuplicateMesh()
            elif isinstance(geom, rg.Brep):
                mesh_list = rg.Mesh.CreateFromBrep(geom, rg.MeshingParameters.Default)
                if mesh_list:
                    mesh = rg.Mesh()
                    for m in mesh_list:
                        mesh.Append(m)
            elif isinstance(geom, rg.SubD):
                brep = geom.ToBrep(rg.SubDToBrepOptions())
                if brep:
                    mesh_list = rg.Mesh.CreateFromBrep(brep, rg.MeshingParameters.Default)
                    if mesh_list:
                        mesh = rg.Mesh()
                        for m in mesh_list:
                            mesh.Append(m)

            if mesh is None:
                continue

            mesh.Normals.ComputeNormals()
            mesh.Compact()
            mesh.FillHoles()

            if shell_thickness > 0:
                offset_mesh = mesh.Offset(shell_thickness)
                if offset_mesh:
                    mesh.Normals.Flip(True)
                    combined = rg.Mesh()
                    combined.Append(mesh)
                    combined.Append(offset_mesh)
                    mesh = combined

            if maximize_printable:
                bbox = mesh.GetBoundingBox(True)
                center = bbox.Center
                move = rg.Vector3d(-center.X, -center.Y, -bbox.Min.Z)
                mesh.Translate(move)
                diagonal = bbox.Diagonal
                if diagonal.X > diagonal.Y:
                    rotation = rg.Transform.Rotation(
                        math.pi / 2, rg.Vector3d.ZAxis, rg.Point3d.Origin
                    )
                    mesh.Transform(rotation)

            if post_process:
                mesh.Compact()
                mesh.Normals.ComputeNormals()
                mesh.UnifyNormals()

            attrs.Name = "PrintReady_{0}".format(processed)
            doc.Objects.AddMesh(mesh, attrs)
            processed += 1

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Prepared {0} object(s) for printing.".format(processed))
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error in print preparation: {0}".format(e))
        return rc.Result.Failure
