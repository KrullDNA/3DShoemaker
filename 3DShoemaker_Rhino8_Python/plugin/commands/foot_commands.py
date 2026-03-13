"""
Feet in Focus Shoe Kit Rhino 8 Plugin - Foot analysis commands.

Commands:
    ImportFoot              - Opens ImportFootForm for foot scan import.
    OpenImportFootForm      - Alternative entry point to the foot import UI.
    AnalyzePlantarFootScan  - Analyzes plantar (bottom-of-foot) scan data.
"""

from __future__ import annotations

import math
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple

import Rhino  # type: ignore
import Rhino.Commands  # type: ignore
import Rhino.DocObjects  # type: ignore
import Rhino.FileIO  # type: ignore
import Rhino.Geometry  # type: ignore
import Rhino.Input  # type: ignore
import Rhino.Input.Custom  # type: ignore
import Rhino.RhinoApp  # type: ignore
import Rhino.RhinoDoc  # type: ignore
import Rhino.UI  # type: ignore
import scriptcontext as sc  # type: ignore
import System  # type: ignore
import System.Drawing  # type: ignore

import plugin as plugin_constants
from plugin.plugin_main import PodoCADPlugIn


# ---------------------------------------------------------------------------
#  Foot-scan import helpers
# ---------------------------------------------------------------------------

_SUPPORTED_MESH_EXTENSIONS = (
    ".stl", ".obj", ".ply", ".3mf", ".off", ".3dm",
)

_SUPPORTED_POINT_CLOUD_EXTENSIONS = (
    ".xyz", ".pts", ".csv", ".txt", ".asc",
)


def _import_mesh_file(
    doc: Rhino.RhinoDoc,
    file_path: str,
    layer_index: int,
) -> Optional[System.Guid]:
    """Import a mesh file and add it to *doc* on *layer_index*.

    Returns the Guid of the added object, or None on failure.
    """
    ext = os.path.splitext(file_path)[1].lower()

    mesh: Optional[Rhino.Geometry.Mesh] = None

    if ext == ".stl":
        # Use Rhino's STL reader
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
        # Attempt generic import via scripting
        try:
            script = f'_-Import "{file_path}" _Enter'
            Rhino.RhinoApp.RunScript(script, False)
            return None  # Cannot reliably capture the ID from RunScript
        except Exception:
            return None

    if mesh is None or not mesh.IsValid:
        return None

    # Clean up the mesh
    mesh.Normals.ComputeNormals()
    mesh.Compact()

    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.LayerIndex = layer_index
    attrs.Name = f"FootScan_{os.path.basename(file_path)}"
    attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromLayer

    oid = doc.Objects.AddMesh(mesh, attrs)
    return oid if oid != System.Guid.Empty else None


def _import_point_cloud_file(
    doc: Rhino.RhinoDoc,
    file_path: str,
    layer_index: int,
) -> Optional[System.Guid]:
    """Import a point-cloud text file (xyz/csv/pts) into *doc*.

    Returns the Guid of the added PointCloud object, or None.
    """
    points: List[Rhino.Geometry.Point3d] = []

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, 1):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                # Support comma, space, tab separators
                parts = line.replace(",", " ").replace("\t", " ").split()
                if len(parts) < 3:
                    continue
                try:
                    x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                    points.append(Rhino.Geometry.Point3d(x, y, z))
                except ValueError:
                    continue
    except (OSError, IOError) as exc:
        Rhino.RhinoApp.WriteLine(f"Error reading file: {exc}")
        return None

    if not points:
        Rhino.RhinoApp.WriteLine("No valid points found in file.")
        return None

    cloud = Rhino.Geometry.PointCloud(points)

    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.LayerIndex = layer_index
    attrs.Name = f"FootScanCloud_{os.path.basename(file_path)}"

    oid = doc.Objects.AddPointCloud(cloud, attrs)
    Rhino.RhinoApp.WriteLine(f"Imported {len(points)} points from {os.path.basename(file_path)}.")
    return oid if oid != System.Guid.Empty else None


def _ensure_foot_layer(doc: Rhino.RhinoDoc) -> int:
    """Ensure the SLM::Foot layer exists and return its index."""
    full_path = f"{plugin_constants.SLM_LAYER_PREFIX}::{plugin_constants.CLASS_FOOT}"
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx >= 0:
        return idx

    # Try to find/create SLM parent first
    parent_idx = doc.Layers.FindByFullPath(plugin_constants.SLM_LAYER_PREFIX, -1)
    if parent_idx < 0:
        parent_layer = Rhino.DocObjects.Layer()
        parent_layer.Name = plugin_constants.SLM_LAYER_PREFIX
        parent_idx = doc.Layers.Add(parent_layer)

    parent_id = doc.Layers[parent_idx].Id

    child = Rhino.DocObjects.Layer()
    child.Name = plugin_constants.CLASS_FOOT
    child.ParentLayerId = parent_id
    color_tuple = plugin_constants.DEFAULT_LAYER_COLORS.get("Foot", (255, 80, 80))
    child.Color = System.Drawing.Color.FromArgb(*color_tuple)
    return doc.Layers.Add(child)


def _open_file_dialog(
    title: str,
    filter_str: str,
) -> Optional[str]:
    """Open a file dialog and return the selected path or None."""
    fd = Rhino.UI.OpenFileDialog()
    fd.Title = title
    fd.Filter = filter_str
    if fd.ShowOpenDialog():
        return fd.FileName
    return None


# ---------------------------------------------------------------------------
#  Plantar analysis helpers
# ---------------------------------------------------------------------------

def _compute_plantar_metrics(
    mesh: Rhino.Geometry.Mesh,
) -> Dict[str, float]:
    """Compute basic plantar-surface metrics from a foot-scan mesh.

    Returns a dict with keys like foot_length, ball_width, arch_height,
    heel_width, etc. (all in document units, typically mm).
    """
    bbox = mesh.GetBoundingBox(True)
    if not bbox.IsValid:
        return {}

    foot_length = bbox.Max.Y - bbox.Min.Y
    ball_width = bbox.Max.X - bbox.Min.X
    foot_height = bbox.Max.Z - bbox.Min.Z

    # Approximate arch height: sample Z values along the medial midline
    # at ~60% of foot length from the heel.
    arch_sample_y = bbox.Min.Y + foot_length * 0.60
    arch_height = 0.0
    min_z_at_arch = float("inf")

    for i in range(mesh.Vertices.Count):
        v = mesh.Vertices[i]
        if abs(v.Y - arch_sample_y) < foot_length * 0.05:
            if v.Z < min_z_at_arch:
                min_z_at_arch = v.Z

    if min_z_at_arch < float("inf"):
        arch_height = min_z_at_arch - bbox.Min.Z

    # Heel width: measure width at ~10% from rear of bbox
    heel_sample_y = bbox.Min.Y + foot_length * 0.10
    heel_xs: List[float] = []
    for i in range(mesh.Vertices.Count):
        v = mesh.Vertices[i]
        if abs(v.Y - heel_sample_y) < foot_length * 0.05:
            heel_xs.append(v.X)

    heel_width = (max(heel_xs) - min(heel_xs)) if heel_xs else 0.0

    # Ball width at ~72% from heel
    ball_sample_y = bbox.Min.Y + foot_length * 0.72
    ball_xs: List[float] = []
    for i in range(mesh.Vertices.Count):
        v = mesh.Vertices[i]
        if abs(v.Y - ball_sample_y) < foot_length * 0.05:
            ball_xs.append(v.X)

    measured_ball_width = (max(ball_xs) - min(ball_xs)) if ball_xs else ball_width

    return {
        "foot_length": round(foot_length, 2),
        "ball_width": round(measured_ball_width, 2),
        "heel_width": round(heel_width, 2),
        "arch_height": round(arch_height, 2),
        "foot_height": round(foot_height, 2),
        "bbox_width": round(ball_width, 2),
    }


# ---------------------------------------------------------------------------
#  ImportFoot
# ---------------------------------------------------------------------------

class ImportFoot(Rhino.Commands.Command):
    """Opens ImportFootForm for importing a foot scan file.

    Supports STL, OBJ, PLY, 3MF, XYZ, PTS, CSV, and other common
    3D-scan formats.  The imported geometry is placed on the SLM::Foot
    layer.
    """

    _instance: ImportFoot | None = None

    def __init__(self):
        super().__init__()
        ImportFoot._instance = self

    @classmethod
    @property
    def Instance(cls) -> ImportFoot | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ImportFoot"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        # Build a filter string for all supported types
        mesh_exts = " ".join(f"*{e}" for e in _SUPPORTED_MESH_EXTENSIONS)
        cloud_exts = " ".join(f"*{e}" for e in _SUPPORTED_POINT_CLOUD_EXTENSIONS)
        all_exts = f"{mesh_exts} {cloud_exts}"
        filter_str = (
            f"All Supported|{all_exts}|"
            f"Mesh Files|{mesh_exts}|"
            f"Point Cloud Files|{cloud_exts}|"
            f"All Files|*.*"
        )

        file_path = _open_file_dialog("Import Foot Scan", filter_str)
        if not file_path:
            return Rhino.Commands.Result.Cancel

        if not os.path.isfile(file_path):
            Rhino.RhinoApp.WriteLine(f"File not found: {file_path}")
            return Rhino.Commands.Result.Failure

        layer_idx = _ensure_foot_layer(doc)
        ext = os.path.splitext(file_path)[1].lower()

        Rhino.RhinoApp.WriteLine(f"Importing foot scan: {os.path.basename(file_path)} ...")

        oid: Optional[System.Guid] = None

        if ext in _SUPPORTED_MESH_EXTENSIONS:
            oid = _import_mesh_file(doc, file_path, layer_idx)
        elif ext in _SUPPORTED_POINT_CLOUD_EXTENSIONS:
            oid = _import_point_cloud_file(doc, file_path, layer_idx)
        else:
            # Fall back to RunScript import
            Rhino.RhinoApp.RunScript(f'_-Import "{file_path}" _Enter', False)
            Rhino.RhinoApp.WriteLine("File imported via Rhino native importer.")
            doc.Views.Redraw()
            return Rhino.Commands.Result.Success

        if oid is None:
            Rhino.RhinoApp.WriteLine("Failed to import foot scan file.")
            return Rhino.Commands.Result.Failure

        # Store the scan path in settings
        ds = plug.GetDocumentSettings(doc)
        ds.set("foot_scan_path", file_path)
        plug.SetDocumentSettings(doc, ds)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Foot scan imported successfully.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  OpenImportFootForm
# ---------------------------------------------------------------------------

class OpenImportFootForm(Rhino.Commands.Command):
    """Alternative entry point to the foot import UI.

    Delegates to ImportFoot; provided as a separate command name for
    toolbar / alias compatibility.
    """

    _instance: OpenImportFootForm | None = None

    def __init__(self):
        super().__init__()
        OpenImportFootForm._instance = self

    @classmethod
    @property
    def Instance(cls) -> OpenImportFootForm | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "OpenImportFootForm"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        # Delegate to ImportFoot
        importer = ImportFoot.Instance
        if importer is not None:
            return importer.RunCommand(doc, mode)

        # Fall back if ImportFoot has not been instantiated yet
        Rhino.RhinoApp.WriteLine("ImportFoot command is not available. Running inline import.")
        plug = PodoCADPlugIn.instance()
        mesh_exts = " ".join(f"*{e}" for e in _SUPPORTED_MESH_EXTENSIONS)
        cloud_exts = " ".join(f"*{e}" for e in _SUPPORTED_POINT_CLOUD_EXTENSIONS)
        all_exts = f"{mesh_exts} {cloud_exts}"
        filter_str = f"All Supported|{all_exts}|All Files|*.*"

        file_path = _open_file_dialog("Import Foot Scan", filter_str)
        if not file_path or not os.path.isfile(file_path):
            return Rhino.Commands.Result.Cancel

        layer_idx = _ensure_foot_layer(doc)
        ext = os.path.splitext(file_path)[1].lower()

        if ext in _SUPPORTED_MESH_EXTENSIONS:
            oid = _import_mesh_file(doc, file_path, layer_idx)
        elif ext in _SUPPORTED_POINT_CLOUD_EXTENSIONS:
            oid = _import_point_cloud_file(doc, file_path, layer_idx)
        else:
            Rhino.RhinoApp.RunScript(f'_-Import "{file_path}" _Enter', False)
            doc.Views.Redraw()
            return Rhino.Commands.Result.Success

        if oid is None:
            Rhino.RhinoApp.WriteLine("Import failed.")
            return Rhino.Commands.Result.Failure

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Foot scan imported successfully.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AnalyzePlantarFootScan
# ---------------------------------------------------------------------------

class AnalyzePlantarFootScan(Rhino.Commands.Command):
    """Analyze plantar foot scan data.

    Computes foot-length, ball width, heel width, arch height, and
    other metrics from a selected foot-scan mesh.  Results are written
    to the command line and stored in the document settings.
    """

    _instance: AnalyzePlantarFootScan | None = None

    def __init__(self):
        super().__init__()
        AnalyzePlantarFootScan._instance = self

    @classmethod
    @property
    def Instance(cls) -> AnalyzePlantarFootScan | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AnalyzePlantarFootScan"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        # Ask user to select a mesh
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select foot scan mesh to analyze")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Mesh
        go.SubObjectSelect = False
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        obj_ref = go.Object(0)
        mesh = obj_ref.Mesh()
        if mesh is None:
            Rhino.RhinoApp.WriteLine("Selected object is not a valid mesh.")
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("Analyzing plantar foot scan ...")

        metrics = _compute_plantar_metrics(mesh)
        if not metrics:
            Rhino.RhinoApp.WriteLine("Could not compute metrics (mesh may be empty or invalid).")
            return Rhino.Commands.Result.Failure

        # Display results
        Rhino.RhinoApp.WriteLine("=" * 50)
        Rhino.RhinoApp.WriteLine("  Plantar Foot Scan Analysis Results")
        Rhino.RhinoApp.WriteLine("=" * 50)
        for key, value in metrics.items():
            label = key.replace("_", " ").title()
            Rhino.RhinoApp.WriteLine(f"  {label}: {value:.2f} mm")
        Rhino.RhinoApp.WriteLine("=" * 50)

        # Store metrics in document settings
        ds = plug.GetDocumentSettings(doc)
        for key, value in metrics.items():
            ds.set(f"plantar_{key}", value)
        plug.SetDocumentSettings(doc, ds)

        # Optionally create visual annotations
        self._create_measurement_annotations(doc, mesh, metrics)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Plantar analysis complete.")
        return Rhino.Commands.Result.Success

    def _create_measurement_annotations(
        self,
        doc: Rhino.RhinoDoc,
        mesh: Rhino.Geometry.Mesh,
        metrics: Dict[str, float],
    ) -> None:
        """Create visual measurement lines on the Measurements layer."""
        # Ensure measurement layer
        meas_path = f"{plugin_constants.SLM_LAYER_PREFIX}::Measurements"
        meas_idx = doc.Layers.FindByFullPath(meas_path, -1)
        if meas_idx < 0:
            parent_idx = doc.Layers.FindByFullPath(
                plugin_constants.SLM_LAYER_PREFIX, -1
            )
            if parent_idx < 0:
                return
            lyr = Rhino.DocObjects.Layer()
            lyr.Name = "Measurements"
            lyr.ParentLayerId = doc.Layers[parent_idx].Id
            color_tuple = plugin_constants.DEFAULT_LAYER_COLORS.get(
                "Measurements", (0, 200, 0)
            )
            lyr.Color = System.Drawing.Color.FromArgb(*color_tuple)
            meas_idx = doc.Layers.Add(lyr)

        if meas_idx < 0:
            return

        bbox = mesh.GetBoundingBox(True)
        if not bbox.IsValid:
            return

        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = meas_idx
        attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromLayer

        # Foot length line (heel to toe along Y axis)
        length_start = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) / 2, bbox.Min.Y, bbox.Min.Z
        )
        length_end = Rhino.Geometry.Point3d(
            (bbox.Min.X + bbox.Max.X) / 2, bbox.Max.Y, bbox.Min.Z
        )
        length_line = Rhino.Geometry.Line(length_start, length_end)
        attrs_l = attrs.Duplicate()
        attrs_l.Name = "FootLength_Measurement"
        doc.Objects.AddLine(length_line, attrs_l)

        # Ball width line at ~72% from heel
        ball_y = bbox.Min.Y + metrics.get("foot_length", 0.0) * 0.72
        ball_start = Rhino.Geometry.Point3d(bbox.Min.X, ball_y, bbox.Min.Z)
        ball_end = Rhino.Geometry.Point3d(bbox.Max.X, ball_y, bbox.Min.Z)
        ball_line = Rhino.Geometry.Line(ball_start, ball_end)
        attrs_b = attrs.Duplicate()
        attrs_b.Name = "BallWidth_Measurement"
        doc.Objects.AddLine(ball_line, attrs_b)

        # Heel width line at ~10% from rear
        heel_y = bbox.Min.Y + metrics.get("foot_length", 0.0) * 0.10
        hw = metrics.get("heel_width", 0.0)
        center_x = (bbox.Min.X + bbox.Max.X) / 2
        heel_start = Rhino.Geometry.Point3d(center_x - hw / 2, heel_y, bbox.Min.Z)
        heel_end = Rhino.Geometry.Point3d(center_x + hw / 2, heel_y, bbox.Min.Z)
        heel_line = Rhino.Geometry.Line(heel_start, heel_end)
        attrs_h = attrs.Duplicate()
        attrs_h.Name = "HeelWidth_Measurement"
        doc.Objects.AddLine(heel_line, attrs_h)
