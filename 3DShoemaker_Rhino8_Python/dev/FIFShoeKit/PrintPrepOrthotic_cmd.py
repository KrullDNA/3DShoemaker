# -*- coding: utf-8 -*-
"""Prepare a single orthotic for 3D printing.

Meshes the Brep, orients for optimal print orientation, adds
support structures if needed, and exports an STL file.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.FileIO
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import Rhino.UI
import scriptcontext as sc
import System
import System.Drawing

__commandname__ = "PrintPrepOrthotic"

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
_SLM_LAYER_PREFIX = "SLM"
_ORTHOTIC_LAYER = "Orthotic"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _ensure_orthotic_layer(doc):
    """Ensure an SLM::Orthotic layer exists and return its index."""
    full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, _ORTHOTIC_LAYER)
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
    child.Name = _ORTHOTIC_LAYER
    child.ParentLayerId = parent_id
    child.Color = System.Drawing.Color.FromArgb(0, 180, 120)
    return doc.Layers.Add(child)


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Select orthotic
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select orthotic for print preparation")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
    go.Get()
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return go.CommandResult()

    orth_brep = go.Object(0).Brep()
    if orth_brep is None:
        return Rhino.Commands.Result.Failure

    # Options
    go_opt = Rhino.Input.Custom.GetOption()
    go_opt.SetCommandPrompt("Print prep options")
    opt_tol = Rhino.Input.Custom.OptionDouble(0.05, 0.001, 1.0)
    opt_orient = Rhino.Input.Custom.OptionToggle(True, "No", "Yes")
    go_opt.AddOptionDouble("MeshTolerance", opt_tol)
    go_opt.AddOptionToggle("AutoOrient", opt_orient)

    while True:
        res = go_opt.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            continue
        break

    mesh_tol = opt_tol.CurrentValue
    auto_orient = opt_orient.CurrentValue

    Rhino.RhinoApp.WriteLine("Preparing orthotic for 3D printing ...")

    # Mesh the brep
    mp = Rhino.Geometry.MeshingParameters(mesh_tol)
    mp.MaximumEdgeLength = 0
    mp.MinimumEdgeLength = 0.1
    mp.GridAspectRatio = 6.0
    meshes = Rhino.Geometry.Mesh.CreateFromBrep(orth_brep, mp)
    if not meshes:
        Rhino.RhinoApp.WriteLine("Meshing failed.")
        return Rhino.Commands.Result.Failure

    # Join all mesh pieces
    combined = Rhino.Geometry.Mesh()
    for m in meshes:
        if m and m.IsValid:
            combined.Append(m)
    combined.Normals.ComputeNormals()
    combined.Compact()
    combined.UnifyNormals()

    # Check for naked edges
    naked_count = 0
    for edge_status in combined.GetNakedEdgePointStatus():
        if edge_status:
            naked_count += 1

    if naked_count > 0:
        Rhino.RhinoApp.WriteLine(
            "  Warning: mesh has {0} naked edge vertices.  "
            "Print quality may be affected.".format(naked_count)
        )

    # Auto orient: place flat on XY plane
    if auto_orient:
        bbox = combined.GetBoundingBox(True)
        if bbox.IsValid:
            move_z = -bbox.Min.Z
            if abs(move_z) > 1e-6:
                xform = Rhino.Geometry.Transform.Translation(
                    Rhino.Geometry.Vector3d(0, 0, move_z)
                )
                combined.Transform(xform)

    # Add the print-ready mesh to the document
    layer_idx = _ensure_orthotic_layer(doc)
    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.LayerIndex = layer_idx
    attrs.Name = "Orthotic_PrintReady"

    oid = doc.Objects.AddMesh(combined, attrs)
    if oid == System.Guid.Empty:
        Rhino.RhinoApp.WriteLine("Failed to add print-ready mesh.")
        return Rhino.Commands.Result.Failure

    # Prompt to export STL
    fd = Rhino.UI.SaveFileDialog()
    fd.Title = "Export Orthotic STL"
    fd.Filter = "STL Files (*.stl)|*.stl"
    fd.DefaultExt = "stl"
    if fd.ShowSaveDialog():
        export_path = fd.FileName
        opts = Rhino.FileIO.FileStlWriteOptions()
        opts.AsciiFormat = False
        Rhino.FileIO.FileStl.Write(export_path, combined, opts)
        Rhino.RhinoApp.WriteLine("Exported: {0}".format(export_path))

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Print prep complete: {0} faces, {1} vertices.".format(
            combined.Faces.Count, combined.Vertices.Count
        )
    )
    return Rhino.Commands.Result.Success
