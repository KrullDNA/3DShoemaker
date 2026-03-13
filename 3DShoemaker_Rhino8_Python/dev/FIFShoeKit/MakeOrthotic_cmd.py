# -*- coding: utf-8 -*-
"""Create an orthotic device from foot/last data.

Builds a 3/4-length orthotic shell using the insole surface as a
base, applying arch support, heel cup, and posting adjustments.

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
import System.Drawing

__commandname__ = "MakeOrthotic"

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


def _find_named_object(doc, name):
    """Find the first object whose Name matches name."""
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.NameFilter = name
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        return obj
    return None


def _get_insole_surface(doc):
    """Retrieve the insole brep from the document (by name convention)."""
    obj = _find_named_object(doc, "Insole")
    if obj is None:
        obj = _find_named_object(doc, "InsoleTop")
    if obj is not None:
        geom = obj.Geometry
        if isinstance(geom, Rhino.Geometry.Brep):
            return geom
    return None


def _create_orthotic_shell(insole_srf, thickness, arch_height, heel_cup_depth, trim_length_ratio):
    """Create an orthotic shell Brep from the insole surface."""
    if insole_srf is None or not insole_srf.IsValid:
        return None

    bbox = insole_srf.GetBoundingBox(True)
    if not bbox.IsValid:
        return None

    # Offset surface to create shell thickness
    offset_breps = Rhino.Geometry.Brep.CreateOffsetBrep(
        insole_srf,
        -thickness,
        solid=True,
        extend=False,
        tolerance=0.01,
    )

    shell = None
    if offset_breps and len(offset_breps) > 0:
        if hasattr(offset_breps[0], "__iter__"):
            for b in offset_breps[0]:
                if isinstance(b, Rhino.Geometry.Brep) and b.IsValid:
                    shell = b
                    break
        elif isinstance(offset_breps[0], Rhino.Geometry.Brep):
            shell = offset_breps[0]

    if shell is None:
        shell = insole_srf.DuplicateBrep()
        xform = Rhino.Geometry.Transform.Translation(
            Rhino.Geometry.Vector3d(0, 0, -thickness)
        )
        shell.Transform(xform)

    # Trim to fraction of length if ratio is set
    if 0.0 < trim_length_ratio < 1.0:
        total_length = bbox.Max.Y - bbox.Min.Y
        cut_y = bbox.Min.Y + total_length * trim_length_ratio
        cut_plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(0, cut_y, 0),
            Rhino.Geometry.Vector3d(0, 1, 0),
        )
        trimmed = shell.Trim(cut_plane, 0.01)
        if trimmed and len(trimmed) > 0:
            shell = trimmed[0]

    return shell


def _apply_arch_profile(shell, arch_height, arch_start_ratio=0.35, arch_end_ratio=0.75):
    """Apply a smooth arch profile to the orthotic shell."""
    if shell is None or arch_height <= 0:
        return shell

    bbox = shell.GetBoundingBox(True)
    total_length = bbox.Max.Y - bbox.Min.Y
    arch_start_y = bbox.Min.Y + total_length * arch_start_ratio
    arch_end_y = bbox.Min.Y + total_length * arch_end_ratio

    for face_idx in range(shell.Faces.Count):
        face = shell.Faces[face_idx]
        srf = face.UnderlyingSurface()
        if isinstance(srf, Rhino.Geometry.NurbsSurface):
            nurbs = srf.ToNurbsSurface()
            if nurbs is not None:
                for u_idx in range(nurbs.Points.CountU):
                    for v_idx in range(nurbs.Points.CountV):
                        cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                        pt = cp.Location
                        if arch_start_y <= pt.Y <= arch_end_y:
                            t = (pt.Y - arch_start_y) / (arch_end_y - arch_start_y)
                            dz = arch_height * math.sin(t * math.pi)
                            new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                            nurbs.Points.SetControlPoint(
                                u_idx, v_idx,
                                Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                            )

    return shell


def _apply_heel_cup(shell, heel_cup_depth, heel_ratio=0.20):
    """Raise heel-cup walls around the rear of the orthotic."""
    if shell is None or heel_cup_depth <= 0:
        return shell

    bbox = shell.GetBoundingBox(True)
    total_length = bbox.Max.Y - bbox.Min.Y
    heel_end_y = bbox.Min.Y + total_length * heel_ratio
    center_x = (bbox.Min.X + bbox.Max.X) / 2.0
    half_width = (bbox.Max.X - bbox.Min.X) / 2.0

    for face_idx in range(shell.Faces.Count):
        face = shell.Faces[face_idx]
        srf = face.UnderlyingSurface()
        if isinstance(srf, Rhino.Geometry.NurbsSurface):
            nurbs = srf.ToNurbsSurface()
            if nurbs is not None:
                for u_idx in range(nurbs.Points.CountU):
                    for v_idx in range(nurbs.Points.CountV):
                        cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                        pt = cp.Location
                        if pt.Y <= heel_end_y:
                            edge_factor = abs(pt.X - center_x) / max(half_width, 1e-6)
                            edge_factor = min(edge_factor, 1.0)
                            heel_factor = 1.0 - (pt.Y - bbox.Min.Y) / max(
                                heel_end_y - bbox.Min.Y, 1e-6
                            )
                            heel_factor = max(0.0, min(1.0, heel_factor))
                            dz = heel_cup_depth * edge_factor * heel_factor
                            new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                            nurbs.Points.SetControlPoint(
                                u_idx, v_idx,
                                Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                            )

    return shell


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Gather parameters
    go = Rhino.Input.Custom.GetOption()
    go.SetCommandPrompt("Create orthotic")

    opt_thickness = Rhino.Input.Custom.OptionDouble(3.0, 0.5, 20.0)
    opt_arch = Rhino.Input.Custom.OptionDouble(8.0, 0.0, 40.0)
    opt_heel_cup = Rhino.Input.Custom.OptionDouble(12.0, 0.0, 30.0)
    opt_trim = Rhino.Input.Custom.OptionDouble(0.75, 0.5, 1.0)

    go.AddOptionDouble("Thickness", opt_thickness)
    go.AddOptionDouble("ArchHeight", opt_arch)
    go.AddOptionDouble("HeelCupDepth", opt_heel_cup)
    go.AddOptionDouble("TrimLengthRatio", opt_trim)

    while True:
        res = go.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            continue
        break

    thickness = opt_thickness.CurrentValue
    arch_height = opt_arch.CurrentValue
    heel_cup_depth = opt_heel_cup.CurrentValue
    trim_ratio = opt_trim.CurrentValue

    # Get insole surface
    insole_srf = _get_insole_surface(doc)
    if insole_srf is None:
        Rhino.RhinoApp.WriteLine(
            "No insole surface found.  Please create an insole first "
            "(CreateInsole) or select one."
        )
        gobj = Rhino.Input.Custom.GetObject()
        gobj.SetCommandPrompt("Select insole surface")
        gobj.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
        gobj.Get()
        if gobj.CommandResult() != Rhino.Commands.Result.Success:
            return gobj.CommandResult()
        insole_srf = gobj.Object(0).Brep()
        if insole_srf is None:
            Rhino.RhinoApp.WriteLine("Invalid surface selected.")
            return Rhino.Commands.Result.Failure

    Rhino.RhinoApp.WriteLine("Creating orthotic shell ...")

    # Create shell
    shell = _create_orthotic_shell(
        insole_srf, thickness, arch_height, heel_cup_depth, trim_ratio
    )
    if shell is None:
        Rhino.RhinoApp.WriteLine("Failed to create orthotic shell.")
        return Rhino.Commands.Result.Failure

    # Apply arch
    shell = _apply_arch_profile(shell, arch_height)

    # Apply heel cup
    shell = _apply_heel_cup(shell, heel_cup_depth)

    # Add to document
    layer_idx = _ensure_orthotic_layer(doc)
    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.LayerIndex = layer_idx
    attrs.Name = "Orthotic"
    attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromLayer

    oid = doc.Objects.AddBrep(shell, attrs)
    if oid == System.Guid.Empty:
        Rhino.RhinoApp.WriteLine("Failed to add orthotic to document.")
        return Rhino.Commands.Result.Failure

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Orthotic created: thickness={0:.1f} mm, "
        "arch={1:.1f} mm, heel cup={2:.1f} mm".format(
            thickness, arch_height, heel_cup_depth
        )
    )
    return Rhino.Commands.Result.Success
