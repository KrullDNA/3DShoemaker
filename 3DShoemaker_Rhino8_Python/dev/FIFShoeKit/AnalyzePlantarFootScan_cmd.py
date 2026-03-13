# -*- coding: utf-8 -*-
"""Analyze plantar (bottom-of-foot) scan data.

Computes foot-length, ball width, heel width, arch height, and other
metrics from a selected foot-scan mesh.  Results are written to the
command line and stored as measurement annotations.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc
import System
import System.Drawing

__commandname__ = "AnalyzePlantarFootScan"

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
_SLM_LAYER_PREFIX = "SLM"
_MEASUREMENTS_LAYER_COLOR = (0, 200, 0)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _compute_plantar_metrics(mesh):
    """Compute basic plantar-surface metrics from a foot-scan mesh."""
    bbox = mesh.GetBoundingBox(True)
    if not bbox.IsValid:
        return {}

    foot_length = bbox.Max.Y - bbox.Min.Y
    ball_width = bbox.Max.X - bbox.Min.X
    foot_height = bbox.Max.Z - bbox.Min.Z

    # Approximate arch height at ~60% of foot length from the heel
    arch_sample_y = bbox.Min.Y + foot_length * 0.60
    min_z_at_arch = float("inf")

    for i in range(mesh.Vertices.Count):
        v = mesh.Vertices[i]
        if abs(v.Y - arch_sample_y) < foot_length * 0.05:
            if v.Z < min_z_at_arch:
                min_z_at_arch = v.Z

    arch_height = 0.0
    if min_z_at_arch < float("inf"):
        arch_height = min_z_at_arch - bbox.Min.Z

    # Heel width at ~10% from rear
    heel_sample_y = bbox.Min.Y + foot_length * 0.10
    heel_xs = []
    for i in range(mesh.Vertices.Count):
        v = mesh.Vertices[i]
        if abs(v.Y - heel_sample_y) < foot_length * 0.05:
            heel_xs.append(v.X)

    heel_width = 0.0
    if heel_xs:
        heel_width = max(heel_xs) - min(heel_xs)

    # Ball width at ~72% from heel
    ball_sample_y = bbox.Min.Y + foot_length * 0.72
    ball_xs = []
    for i in range(mesh.Vertices.Count):
        v = mesh.Vertices[i]
        if abs(v.Y - ball_sample_y) < foot_length * 0.05:
            ball_xs.append(v.X)

    measured_ball_width = ball_width
    if ball_xs:
        measured_ball_width = max(ball_xs) - min(ball_xs)

    return {
        "foot_length": round(foot_length, 2),
        "ball_width": round(measured_ball_width, 2),
        "heel_width": round(heel_width, 2),
        "arch_height": round(arch_height, 2),
        "foot_height": round(foot_height, 2),
        "bbox_width": round(ball_width, 2),
    }


def _create_measurement_annotations(doc, mesh, metrics):
    """Create visual measurement lines on the Measurements layer."""
    meas_path = "{0}::Measurements".format(_SLM_LAYER_PREFIX)
    meas_idx = doc.Layers.FindByFullPath(meas_path, -1)
    if meas_idx < 0:
        parent_idx = doc.Layers.FindByFullPath(_SLM_LAYER_PREFIX, -1)
        if parent_idx < 0:
            return
        lyr = Rhino.DocObjects.Layer()
        lyr.Name = "Measurements"
        lyr.ParentLayerId = doc.Layers[parent_idx].Id
        lyr.Color = System.Drawing.Color.FromArgb(
            _MEASUREMENTS_LAYER_COLOR[0],
            _MEASUREMENTS_LAYER_COLOR[1],
            _MEASUREMENTS_LAYER_COLOR[2],
        )
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
    mid_x = (bbox.Min.X + bbox.Max.X) / 2.0
    length_start = Rhino.Geometry.Point3d(mid_x, bbox.Min.Y, bbox.Min.Z)
    length_end = Rhino.Geometry.Point3d(mid_x, bbox.Max.Y, bbox.Min.Z)
    length_line = Rhino.Geometry.Line(length_start, length_end)
    attrs_l = attrs.Duplicate()
    attrs_l.Name = "FootLength_Measurement"
    doc.Objects.AddLine(length_line, attrs_l)

    # Ball width line at ~72% from heel
    foot_length = metrics.get("foot_length", 0.0)
    ball_y = bbox.Min.Y + foot_length * 0.72
    ball_start = Rhino.Geometry.Point3d(bbox.Min.X, ball_y, bbox.Min.Z)
    ball_end = Rhino.Geometry.Point3d(bbox.Max.X, ball_y, bbox.Min.Z)
    ball_line = Rhino.Geometry.Line(ball_start, ball_end)
    attrs_b = attrs.Duplicate()
    attrs_b.Name = "BallWidth_Measurement"
    doc.Objects.AddLine(ball_line, attrs_b)

    # Heel width line at ~10% from rear
    heel_y = bbox.Min.Y + foot_length * 0.10
    hw = metrics.get("heel_width", 0.0)
    center_x = (bbox.Min.X + bbox.Max.X) / 2.0
    heel_start = Rhino.Geometry.Point3d(center_x - hw / 2.0, heel_y, bbox.Min.Z)
    heel_end = Rhino.Geometry.Point3d(center_x + hw / 2.0, heel_y, bbox.Min.Z)
    heel_line = Rhino.Geometry.Line(heel_start, heel_end)
    attrs_h = attrs.Duplicate()
    attrs_h.Name = "HeelWidth_Measurement"
    doc.Objects.AddLine(heel_line, attrs_h)


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

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
        Rhino.RhinoApp.WriteLine(
            "Could not compute metrics (mesh may be empty or invalid)."
        )
        return Rhino.Commands.Result.Failure

    # Display results
    Rhino.RhinoApp.WriteLine("=" * 50)
    Rhino.RhinoApp.WriteLine("  Plantar Foot Scan Analysis Results")
    Rhino.RhinoApp.WriteLine("=" * 50)
    for key in metrics:
        value = metrics[key]
        label = key.replace("_", " ").title()
        Rhino.RhinoApp.WriteLine("  {0}: {1:.2f} mm".format(label, value))
    Rhino.RhinoApp.WriteLine("=" * 50)

    # Create visual annotations
    _create_measurement_annotations(doc, mesh, metrics)

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine("Plantar analysis complete.")
    return Rhino.Commands.Result.Success
