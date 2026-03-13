# -*- coding: utf-8 -*-
"""Create alpha joint assembly.

Alpha joints are mechanical joints used in orthopedic footwear to allow
ankle articulation. This creates the joint housing with slippage
compensation, rail recess, and clearance geometry.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

__commandname__ = "CreateAlphaJoint"

# Constants
SLM_LAYER_PREFIX = "SLM"
CLASS_LAST = "Last"


def _get_layer_index(doc, layer_suffix):
    """Return the index of a SLM::<suffix> layer, creating it if needed."""
    full_path = "{0}::{1}".format(SLM_LAYER_PREFIX, layer_suffix)
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx < 0:
        parent_idx = doc.Layers.FindByFullPath(SLM_LAYER_PREFIX, -1)
        if parent_idx < 0:
            parent_layer = Rhino.DocObjects.Layer()
            parent_layer.Name = SLM_LAYER_PREFIX
            parent_idx = doc.Layers.Add(parent_layer)
        child_layer = Rhino.DocObjects.Layer()
        child_layer.Name = layer_suffix
        child_layer.ParentLayerId = doc.Layers[parent_idx].Id
        idx = doc.Layers.Add(child_layer)
    return idx


def _add_component(doc, geometry, layer_suffix, name):
    """Add a component geometry to the document on the appropriate layer."""
    layer_idx = _get_layer_index(doc, layer_suffix)
    attrs = Rhino.DocObjects.ObjectAttributes()
    if layer_idx >= 0:
        attrs.LayerIndex = layer_idx
    attrs.Name = name

    if isinstance(geometry, Rhino.Geometry.Brep):
        guid = doc.Objects.AddBrep(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Mesh):
        guid = doc.Objects.AddMesh(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Curve):
        guid = doc.Objects.AddCurve(geometry, attrs)
    elif isinstance(geometry, Rhino.Geometry.Surface):
        guid = doc.Objects.AddSurface(geometry, attrs)
    else:
        guid = doc.Objects.Add(geometry, attrs)

    doc.Views.Redraw()
    return guid


def _get_last_brep(doc):
    """Retrieve the last brep from the document."""
    last_path = "{0}::{1}".format(SLM_LAYER_PREFIX, CLASS_LAST)
    layer_idx = doc.Layers.FindByFullPath(last_path, -1)
    if layer_idx < 0:
        return None
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        for obj in objs:
            if isinstance(obj.Geometry, Rhino.Geometry.Brep):
                return obj.Geometry
    return None


def _prompt_float(prompt, default):
    """Prompt the user for a floating point number."""
    gn = Rhino.Input.Custom.GetNumber()
    gn.SetCommandPrompt(prompt)
    gn.SetDefaultNumber(default)
    gn.AcceptNothing(True)
    if gn.Get() == Rhino.Input.GetResult.Number:
        return gn.Number()
    if gn.CommandResult() == Rhino.Commands.Result.Success:
        return default
    return None


def _extrude_curves_to_brep(curves, direction, cap=True):
    """Extrude curves along a direction to form a brep."""
    breps = []
    for curve in curves:
        surface = Rhino.Geometry.Surface.CreateExtrusion(curve, direction)
        if surface is not None:
            brep = surface.ToBrep()
            if brep is not None:
                if cap:
                    capped = brep.CapPlanarHoles(0.01)
                    breps.append(capped if capped else brep)
                else:
                    breps.append(brep)
    if breps:
        joined = Rhino.Geometry.Brep.JoinBreps(breps, 0.01)
        if joined and len(joined) > 0:
            return joined[0]
        return breps[0]
    return None


def RunCommand(is_interactive):
    doc = sc.doc
    tol = doc.ModelAbsoluteTolerance

    last_brep = _get_last_brep(doc)
    if last_brep is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
        return Rhino.Commands.Result.Failure

    # Joint parameters
    joint_width = _prompt_float("Joint width (mm)", 12.0)
    if joint_width is None:
        return Rhino.Commands.Result.Cancel

    joint_height = _prompt_float("Joint height (mm)", 30.0)
    if joint_height is None:
        return Rhino.Commands.Result.Cancel

    slippage_comp = _prompt_float("Slippage compensation (mm)", 0.5)
    if slippage_comp is None:
        return Rhino.Commands.Result.Cancel

    rail_recess = _prompt_float("Rail recess depth (mm)", 2.0)
    if rail_recess is None:
        return Rhino.Commands.Result.Cancel

    clearance = _prompt_float("Clearance (mm)", 0.3)
    if clearance is None:
        return Rhino.Commands.Result.Cancel

    # Allow point pick or default position
    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt("Pick joint location (or Enter for default medial)")
    gp.AcceptNothing(True)
    result = gp.Get()

    bbox = last_brep.GetBoundingBox(True)
    last_length = bbox.Max.Y - bbox.Min.Y

    if result == Rhino.Input.GetResult.Point:
        joint_center = gp.Point()
    else:
        # Default: medial ankle position
        joint_center = Rhino.Geometry.Point3d(
            bbox.Max.X + 1.0,
            bbox.Min.Y + last_length * 0.25,
            bbox.Min.Z + (bbox.Max.Z - bbox.Min.Z) * 0.5,
        )

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating alpha joint assembly...")

    # Main joint housing plate
    plate_plane = Rhino.Geometry.Plane(
        joint_center, Rhino.Geometry.Vector3d.XAxis
    )
    plate_rect = Rhino.Geometry.Rectangle3d(
        plate_plane,
        Rhino.Geometry.Interval(-joint_width / 2, joint_width / 2),
        Rhino.Geometry.Interval(-joint_height / 2, joint_height / 2),
    )
    plate_curve = plate_rect.ToNurbsCurve()
    plate_dir = Rhino.Geometry.Vector3d(3.0, 0, 0)  # 3mm thick plate
    plate_brep = _extrude_curves_to_brep([plate_curve], plate_dir, cap=True)

    if plate_brep is not None:
        _add_component(doc, plate_brep, "Construction", "SLM_AlphaJoint_Plate")

    # Rail recess channel
    recess_center = Rhino.Geometry.Point3d(
        joint_center.X + 3.0,
        joint_center.Y,
        joint_center.Z,
    )
    recess_plane = Rhino.Geometry.Plane(
        recess_center, Rhino.Geometry.Vector3d.XAxis
    )
    recess_rect = Rhino.Geometry.Rectangle3d(
        recess_plane,
        Rhino.Geometry.Interval(-joint_width * 0.3, joint_width * 0.3),
        Rhino.Geometry.Interval(-joint_height * 0.8 / 2, joint_height * 0.8 / 2),
    )
    recess_curve = recess_rect.ToNurbsCurve()
    recess_dir = Rhino.Geometry.Vector3d(rail_recess, 0, 0)
    recess_brep = _extrude_curves_to_brep([recess_curve], recess_dir, cap=True)

    if recess_brep is not None:
        _add_component(doc, recess_brep, "Construction", "SLM_AlphaJoint_RailRecess")

    # Clearance zone (larger bounding volume for boolean operations)
    clearance_box = Rhino.Geometry.Box(
        Rhino.Geometry.Plane(joint_center, Rhino.Geometry.Vector3d.XAxis),
        Rhino.Geometry.Interval(
            -(joint_width / 2 + clearance), joint_width / 2 + clearance
        ),
        Rhino.Geometry.Interval(
            -(joint_height / 2 + clearance), joint_height / 2 + clearance
        ),
        Rhino.Geometry.Interval(-(slippage_comp + clearance), 3.0 + rail_recess + clearance),
    )
    clearance_brep = Rhino.Geometry.Brep.CreateFromBox(clearance_box)
    if clearance_brep is not None:
        _add_component(doc, clearance_brep, "Construction", "SLM_AlphaJoint_Clearance")

    # Pivot pin hole
    pin_circle = Rhino.Geometry.Circle(
        Rhino.Geometry.Plane(joint_center, Rhino.Geometry.Vector3d.XAxis),
        2.5,  # 5mm diameter pivot pin
    )
    pin_cyl = Rhino.Geometry.Cylinder(pin_circle, 10.0)
    pin_brep = pin_cyl.ToBrep(True, True)
    if pin_brep is not None:
        move = Rhino.Geometry.Transform.Translation(-5, 0, 0)
        pin_brep.Transform(move)
        _add_component(doc, pin_brep, "Construction", "SLM_AlphaJoint_PivotHole")

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Alpha joint assembly created: "
        "{0}x{1}mm, slippage={2}mm, recess={3}mm, clearance={4}mm.".format(
            joint_width, joint_height, slippage_comp, rail_recess, clearance
        )
    )
    return Rhino.Commands.Result.Success
