# -*- coding: utf-8 -*-
"""Batch print preparation for multiple orthotics.

Selects all orthotic objects, meshes each, arranges them on a
virtual print bed, and optionally exports a combined STL.

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

__commandname__ = "PrintPrepOrthotics"

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

    # Select multiple orthotics
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select orthotics for batch print prep")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
    go.EnablePreSelect(True, True)
    go.GetMultiple(1, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return go.CommandResult()

    count = go.ObjectCount
    if count == 0:
        Rhino.RhinoApp.WriteLine("No objects selected.")
        return Rhino.Commands.Result.Cancel

    # Options
    go_opt = Rhino.Input.Custom.GetOption()
    go_opt.SetCommandPrompt("Print prep {0} orthotic(s)".format(count))
    opt_tol = Rhino.Input.Custom.OptionDouble(0.05, 0.001, 1.0)
    opt_spacing = Rhino.Input.Custom.OptionDouble(10.0, 1.0, 100.0)
    opt_bed_x = Rhino.Input.Custom.OptionDouble(200.0, 50.0, 1000.0)
    go_opt.AddOptionDouble("MeshTolerance", opt_tol)
    go_opt.AddOptionDouble("Spacing", opt_spacing)
    go_opt.AddOptionDouble("BedWidth", opt_bed_x)

    while True:
        res = go_opt.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            continue
        break

    mesh_tol = opt_tol.CurrentValue
    spacing = opt_spacing.CurrentValue
    bed_width = opt_bed_x.CurrentValue

    Rhino.RhinoApp.WriteLine(
        "Batch print prep for {0} orthotic(s) ...".format(count)
    )

    layer_idx = _ensure_orthotic_layer(doc)
    mp = Rhino.Geometry.MeshingParameters(mesh_tol)

    all_meshes = []
    current_x = 0.0
    current_y = 0.0
    row_max_y = 0.0

    for i in range(count):
        brep = go.Object(i).Brep()
        if brep is None:
            continue

        meshes = Rhino.Geometry.Mesh.CreateFromBrep(brep, mp)
        if not meshes:
            continue

        combined = Rhino.Geometry.Mesh()
        for m in meshes:
            if m and m.IsValid:
                combined.Append(m)
        combined.Normals.ComputeNormals()
        combined.Compact()
        combined.UnifyNormals()

        # Position on print bed
        bbox = combined.GetBoundingBox(True)
        if not bbox.IsValid:
            continue

        obj_width = bbox.Max.X - bbox.Min.X
        obj_length = bbox.Max.Y - bbox.Min.Y

        # Check if fits in current row
        if current_x + obj_width > bed_width and current_x > 0:
            current_x = 0.0
            current_y += row_max_y + spacing
            row_max_y = 0.0

        # Move to position
        move_vec = Rhino.Geometry.Vector3d(
            current_x - bbox.Min.X,
            current_y - bbox.Min.Y,
            -bbox.Min.Z,
        )
        xform = Rhino.Geometry.Transform.Translation(move_vec)
        combined.Transform(xform)

        current_x += obj_width + spacing
        if obj_length > row_max_y:
            row_max_y = obj_length

        # Add to doc
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = layer_idx
        attrs.Name = "Orthotic_PrintReady_{0}".format(i + 1)
        doc.Objects.AddMesh(combined, attrs)
        all_meshes.append(combined)

    if not all_meshes:
        Rhino.RhinoApp.WriteLine("No valid meshes created.")
        return Rhino.Commands.Result.Failure

    # Optionally export
    fd = Rhino.UI.SaveFileDialog()
    fd.Title = "Export All Orthotics STL"
    fd.Filter = "STL Files (*.stl)|*.stl"
    fd.DefaultExt = "stl"
    if fd.ShowSaveDialog():
        export_mesh = Rhino.Geometry.Mesh()
        for m in all_meshes:
            export_mesh.Append(m)
        export_mesh.Compact()
        opts = Rhino.FileIO.FileStlWriteOptions()
        opts.AsciiFormat = False
        Rhino.FileIO.FileStl.Write(fd.FileName, export_mesh, opts)
        Rhino.RhinoApp.WriteLine("Exported: {0}".format(fd.FileName))

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Batch print prep complete: {0} orthotic(s) prepared.".format(len(all_meshes))
    )
    return Rhino.Commands.Result.Success
