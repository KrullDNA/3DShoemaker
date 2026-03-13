# -*- coding: utf-8 -*-
"""Create a sandal from last/insert data.

Builds the outsole, midsole, and footbed components using the
current insole outline and design parameters.

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

__commandname__ = "BuildSandal"

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
_SLM_LAYER_PREFIX = "SLM"
_SANDAL_LAYER = "Sandal"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _ensure_layer(doc, name, color_r=200, color_g=160, color_b=80):
    """Ensure SLM::<name> exists and return its index."""
    full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, name)
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
    child.Name = name
    child.ParentLayerId = parent_id
    child.Color = System.Drawing.Color.FromArgb(color_r, color_g, color_b)
    return doc.Layers.Add(child)


def _find_named_object(doc, name):
    """Find the first object whose Name matches name."""
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.NameFilter = name
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        return obj
    return None


def _get_outline_curve(doc):
    """Retrieve the last outline curve from the document."""
    for name in ("Outline", "LastOutline", "InsoleOutline"):
        obj = _find_named_object(doc, name)
        if obj is not None:
            geom = obj.Geometry
            if isinstance(geom, Rhino.Geometry.Curve):
                return geom
    return None


def _create_sandal_sole(outline, sole_thickness, midsole_thickness):
    """Create a sandal sole by extruding the outline curve downward."""
    if outline is None or not outline.IsValid:
        return None

    if not outline.IsClosed:
        outline = outline.DuplicateCurve()
        if not outline.MakeClosed(1.0):
            return None

    total = sole_thickness + midsole_thickness
    extrusion_vec = Rhino.Geometry.Vector3d(0, 0, -total)
    srf = Rhino.Geometry.Surface.CreateExtrusion(outline, extrusion_vec)
    if srf is None:
        return None

    brep = srf.ToBrep()
    capped = brep.CapPlanarHoles(0.01)
    if capped is not None:
        return capped
    return brep


def _create_footbed_surface(outline, arch_height, heel_cup_depth):
    """Create a contoured footbed surface within the outline."""
    if outline is None or not outline.IsValid:
        return None

    if not outline.IsClosed:
        outline = outline.DuplicateCurve()
        outline.MakeClosed(1.0)

    breps = Rhino.Geometry.Brep.CreatePlanarBreps([outline], 0.01)
    if not breps or len(breps) == 0:
        return None

    footbed = breps[0]
    bbox = footbed.GetBoundingBox(True)
    if not bbox.IsValid:
        return footbed

    total_length = bbox.Max.Y - bbox.Min.Y
    center_x = (bbox.Min.X + bbox.Max.X) / 2.0

    for face_idx in range(footbed.Faces.Count):
        face = footbed.Faces[face_idx]
        srf = face.UnderlyingSurface()
        if isinstance(srf, Rhino.Geometry.NurbsSurface):
            nurbs = srf.ToNurbsSurface()
            if nurbs is None:
                continue
            for u_idx in range(nurbs.Points.CountU):
                for v_idx in range(nurbs.Points.CountV):
                    cp = nurbs.Points.GetControlPoint(u_idx, v_idx)
                    pt = cp.Location
                    rel_y = (pt.Y - bbox.Min.Y) / max(total_length, 1e-6)
                    dz = 0.0

                    # Arch profile (sinusoidal, 35%-75% of length)
                    if arch_height > 0 and 0.35 < rel_y < 0.75:
                        t = (rel_y - 0.35) / 0.40
                        medial_factor = max(0.0, (center_x - pt.X) / max(
                            center_x - bbox.Min.X, 1e-6
                        ))
                        medial_factor = min(medial_factor * 1.5, 1.0)
                        dz += arch_height * math.sin(t * math.pi) * medial_factor

                    # Heel cup (0%-20% of length)
                    if heel_cup_depth > 0 and rel_y < 0.20:
                        edge_dist = abs(pt.X - center_x) / max(
                            (bbox.Max.X - bbox.Min.X) / 2, 1e-6
                        )
                        heel_factor = 1.0 - rel_y / 0.20
                        dz += heel_cup_depth * min(edge_dist, 1.0) * heel_factor

                    if abs(dz) > 1e-9:
                        new_pt = Rhino.Geometry.Point3d(pt.X, pt.Y, pt.Z + dz)
                        nurbs.Points.SetControlPoint(
                            u_idx, v_idx,
                            Rhino.Geometry.ControlPoint(new_pt, cp.Weight),
                        )

    return footbed


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Try to get outline from document
    outline = _get_outline_curve(doc)
    if outline is None:
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select sandal outline curve")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()
        outline = go.Object(0).Curve()

    if outline is None:
        Rhino.RhinoApp.WriteLine("No valid outline curve found.")
        return Rhino.Commands.Result.Failure

    # Options
    go_opt = Rhino.Input.Custom.GetOption()
    go_opt.SetCommandPrompt("Build sandal parameters")
    opt_sole = Rhino.Input.Custom.OptionDouble(5.0, 1.0, 30.0)
    opt_midsole = Rhino.Input.Custom.OptionDouble(5.0, 0.0, 30.0)
    opt_arch = Rhino.Input.Custom.OptionDouble(6.0, 0.0, 30.0)
    opt_heel_cup = Rhino.Input.Custom.OptionDouble(0.0, 0.0, 20.0)
    go_opt.AddOptionDouble("OutsoleThickness", opt_sole)
    go_opt.AddOptionDouble("MidsoleThickness", opt_midsole)
    go_opt.AddOptionDouble("ArchHeight", opt_arch)
    go_opt.AddOptionDouble("HeelCupDepth", opt_heel_cup)

    while True:
        res = go_opt.Get()
        if res == Rhino.Input.Custom.GetResult.Option:
            continue
        break

    sole_thick = opt_sole.CurrentValue
    midsole_thick = opt_midsole.CurrentValue
    arch_h = opt_arch.CurrentValue
    heel_cup = opt_heel_cup.CurrentValue

    Rhino.RhinoApp.WriteLine("Building sandal ...")

    layer_idx = _ensure_layer(doc, _SANDAL_LAYER)

    # Build sole
    sole = _create_sandal_sole(outline, sole_thick, midsole_thick)
    if sole is not None and sole.IsValid:
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = layer_idx
        attrs.Name = "SandalSole"
        doc.Objects.AddBrep(sole, attrs)
        Rhino.RhinoApp.WriteLine("  Sole created.")
    else:
        Rhino.RhinoApp.WriteLine("  Warning: sole creation failed.")

    # Build footbed
    footbed = _create_footbed_surface(outline, arch_h, heel_cup)
    if footbed is not None and footbed.IsValid:
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = layer_idx
        attrs.Name = "SandalFootbed"
        doc.Objects.AddBrep(footbed, attrs)
        Rhino.RhinoApp.WriteLine("  Footbed created.")

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine("Sandal build complete.")
    return Rhino.Commands.Result.Success
