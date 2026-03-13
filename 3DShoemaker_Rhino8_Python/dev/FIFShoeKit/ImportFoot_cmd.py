# -*- coding: utf-8 -*-
"""Import a foot scan file (STL, OBJ, PLY, 3MF, XYZ, PTS, CSV, etc.)

Places imported geometry on the SLM::Foot layer.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import os
import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.FileIO
import Rhino.Geometry
import Rhino.Input
import Rhino.UI
import scriptcontext as sc
import System
import System.Drawing

__commandname__ = "ImportFoot"

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
_SLM_LAYER_PREFIX = "SLM"
_CLASS_FOOT = "Foot"
_FOOT_LAYER_COLOR = (255, 80, 80)

_SUPPORTED_MESH_EXTENSIONS = (
    ".stl", ".obj", ".ply", ".3mf", ".off", ".3dm",
)

_SUPPORTED_POINT_CLOUD_EXTENSIONS = (
    ".xyz", ".pts", ".csv", ".txt", ".asc",
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _ensure_foot_layer(doc):
    """Ensure the SLM::Foot layer exists and return its index."""
    full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, _CLASS_FOOT)
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
    child.Name = _CLASS_FOOT
    child.ParentLayerId = parent_id
    child.Color = System.Drawing.Color.FromArgb(
        _FOOT_LAYER_COLOR[0], _FOOT_LAYER_COLOR[1], _FOOT_LAYER_COLOR[2]
    )
    return doc.Layers.Add(child)


def _open_file_dialog(title, filter_str):
    """Open a file dialog and return the selected path or None."""
    fd = Rhino.UI.OpenFileDialog()
    fd.Title = title
    fd.Filter = filter_str
    if fd.ShowOpenDialog():
        return fd.FileName
    return None


def _import_mesh_file(doc, file_path, layer_index):
    """Import a mesh file and add it to doc on layer_index.

    Returns the Guid of the added object, or None on failure.
    """
    ext = os.path.splitext(file_path)[1].lower()
    mesh = None

    if ext == ".stl":
        opts = Rhino.FileIO.FileStlReadOptions()
        meshes = Rhino.FileIO.FileStl.Read(file_path, opts)
        if meshes and len(meshes) > 0:
            mesh = meshes[0]
    elif ext == ".obj":
        result = Rhino.FileIO.FileObj.Read(file_path)
        if result and result.Meshes and len(result.Meshes) > 0:
            mesh = result.Meshes[0]
    elif ext == ".ply":
        result = Rhino.FileIO.FilePly.Read(file_path)
        if result is not None:
            mesh = result
    elif ext == ".3dm":
        file3dm = Rhino.FileIO.File3dm.Read(file_path)
        if file3dm is not None:
            for obj in file3dm.Objects:
                geom = obj.Geometry
                if isinstance(geom, Rhino.Geometry.Mesh):
                    mesh = geom
                    break
    else:
        try:
            script = '_-Import "{0}" _Enter'.format(file_path)
            Rhino.RhinoApp.RunScript(script, False)
            return None
        except Exception:
            return None

    if mesh is None or not mesh.IsValid:
        return None

    mesh.Normals.ComputeNormals()
    mesh.Compact()

    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.LayerIndex = layer_index
    attrs.Name = "FootScan_{0}".format(os.path.basename(file_path))
    attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromLayer

    oid = doc.Objects.AddMesh(mesh, attrs)
    if oid != System.Guid.Empty:
        return oid
    return None


def _import_point_cloud_file(doc, file_path, layer_index):
    """Import a point-cloud text file (xyz/csv/pts) into doc.

    Returns the Guid of the added PointCloud object, or None.
    """
    points = []

    try:
        fh = open(file_path, "r")
        try:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                parts = line.replace(",", " ").replace("\t", " ").split()
                if len(parts) < 3:
                    continue
                try:
                    x = float(parts[0])
                    y = float(parts[1])
                    z = float(parts[2])
                    points.append(Rhino.Geometry.Point3d(x, y, z))
                except ValueError:
                    continue
        finally:
            fh.close()
    except (OSError, IOError) as exc:
        Rhino.RhinoApp.WriteLine("Error reading file: {0}".format(exc))
        return None

    if not points:
        Rhino.RhinoApp.WriteLine("No valid points found in file.")
        return None

    cloud = Rhino.Geometry.PointCloud(points)

    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.LayerIndex = layer_index
    attrs.Name = "FootScanCloud_{0}".format(os.path.basename(file_path))

    oid = doc.Objects.AddPointCloud(cloud, attrs)
    Rhino.RhinoApp.WriteLine(
        "Imported {0} points from {1}.".format(len(points), os.path.basename(file_path))
    )
    if oid != System.Guid.Empty:
        return oid
    return None


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Build filter string
    mesh_exts = " ".join("*" + e for e in _SUPPORTED_MESH_EXTENSIONS)
    cloud_exts = " ".join("*" + e for e in _SUPPORTED_POINT_CLOUD_EXTENSIONS)
    all_exts = "{0} {1}".format(mesh_exts, cloud_exts)
    filter_str = (
        "All Supported|{0}|"
        "Mesh Files|{1}|"
        "Point Cloud Files|{2}|"
        "All Files|*.*"
    ).format(all_exts, mesh_exts, cloud_exts)

    file_path = _open_file_dialog("Import Foot Scan", filter_str)
    if not file_path:
        return Rhino.Commands.Result.Cancel

    if not os.path.isfile(file_path):
        Rhino.RhinoApp.WriteLine("File not found: {0}".format(file_path))
        return Rhino.Commands.Result.Failure

    layer_idx = _ensure_foot_layer(doc)
    ext = os.path.splitext(file_path)[1].lower()

    Rhino.RhinoApp.WriteLine(
        "Importing foot scan: {0} ...".format(os.path.basename(file_path))
    )

    oid = None

    if ext in _SUPPORTED_MESH_EXTENSIONS:
        oid = _import_mesh_file(doc, file_path, layer_idx)
    elif ext in _SUPPORTED_POINT_CLOUD_EXTENSIONS:
        oid = _import_point_cloud_file(doc, file_path, layer_idx)
    else:
        Rhino.RhinoApp.RunScript('_-Import "{0}" _Enter'.format(file_path), False)
        Rhino.RhinoApp.WriteLine("File imported via Rhino native importer.")
        doc.Views.Redraw()
        return Rhino.Commands.Result.Success

    if oid is None:
        Rhino.RhinoApp.WriteLine("Failed to import foot scan file.")
        return Rhino.Commands.Result.Failure

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine("Foot scan imported successfully.")
    return Rhino.Commands.Result.Success
