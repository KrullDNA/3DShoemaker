# -*- coding: utf-8 -*-
"""Create a 3D mockup combining last, sole, heel, and insole components.

Assembles all existing components into a positioned mockup view.

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

__commandname__ = "CreateMockup"

# Constants
SLM_LAYER_PREFIX = "SLM"


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


def RunCommand(is_interactive):
    doc = sc.doc
    tol = doc.ModelAbsoluteTolerance

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Creating 3D Mockup...")

    # Collect all SLM components
    prefix = SLM_LAYER_PREFIX
    component_count = 0
    mockup_bbox = Rhino.Geometry.BoundingBox.Empty

    enum_settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    enum_settings.DeletedObjects = False

    for obj in doc.Objects.GetObjectList(enum_settings):
        layer = doc.Layers[obj.Attributes.LayerIndex]
        if not layer.FullPath.startswith(prefix):
            continue
        obj_bbox = obj.Geometry.GetBoundingBox(True)
        if obj_bbox.IsValid:
            mockup_bbox.Union(obj_bbox)
        component_count += 1

    if component_count == 0:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No components found for mockup.")
        return Rhino.Commands.Result.Failure

    # Optionally create an exploded/offset mockup copy
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Mockup type (Assembled/Exploded)")
    gs.SetDefaultString("Assembled")
    gs.AcceptNothing(True)
    gs.Get()

    mockup_type = "Assembled"
    if gs.CommandResult() == Rhino.Commands.Result.Success and gs.StringResult():
        mockup_type = gs.StringResult().strip()

    if mockup_type.lower() == "exploded":
        # Create exploded view by duplicating and offsetting each component
        offset_y = 0.0
        spacing = 30.0

        for obj in doc.Objects.GetObjectList(enum_settings):
            layer = doc.Layers[obj.Attributes.LayerIndex]
            if not layer.FullPath.startswith(prefix):
                continue
            dup = obj.Geometry.Duplicate()
            # Offset each component along X for visibility
            move = Rhino.Geometry.Transform.Translation(
                mockup_bbox.Diagonal.Length * 1.5, 0, offset_y
            )
            dup.Transform(move)

            attrs = Rhino.DocObjects.ObjectAttributes()
            obj_name = obj.Attributes.Name
            if not obj_name:
                obj_name = "Part"
            attrs.Name = "SLM_Mockup_{0}".format(obj_name)
            construction_idx = _get_layer_index(doc, "Construction")
            if construction_idx >= 0:
                attrs.LayerIndex = construction_idx
            doc.Objects.Add(dup, attrs)
            offset_y += spacing

    # Set view to show the full mockup
    view = doc.Views.ActiveView
    if view is not None and mockup_bbox.IsValid:
        vp = view.ActiveViewport
        target = mockup_bbox.Center
        diag = mockup_bbox.Diagonal.Length
        camera = target + Rhino.Geometry.Vector3d(diag * 0.8, -diag * 1.0, diag * 0.5)
        vp.SetCameraTarget(target, True)
        vp.SetCameraLocation(camera, True)
        vp.Camera35mmLensLength = 50.0

    doc.Views.Redraw()

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Mockup created ({0}): {1} component(s) included.".format(
            mockup_type, component_count
        )
    )
    return Rhino.Commands.Result.Success
