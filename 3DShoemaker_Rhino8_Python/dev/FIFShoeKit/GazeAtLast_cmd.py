# -*- coding: utf-8 -*-
"""Set viewport to look at last from standard angles.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import scriptcontext as sc

__commandname__ = "GazeAtLast"

# ---- Constants ----
_SLM_LAYER_PREFIX = "SLM"
_CLASS_LAST = "Last"

_VIEW_ANGLES = {
    "Top":    (Rhino.Geometry.Point3d(0, 0, 500), Rhino.Geometry.Point3d(0, 0, 0)),
    "Bottom": (Rhino.Geometry.Point3d(0, 0, -500), Rhino.Geometry.Point3d(0, 0, 0)),
    "Medial": (Rhino.Geometry.Point3d(500, 0, 30), Rhino.Geometry.Point3d(0, 0, 30)),
    "Lateral": (Rhino.Geometry.Point3d(-500, 0, 30), Rhino.Geometry.Point3d(0, 0, 30)),
    "Front":  (Rhino.Geometry.Point3d(0, -500, 30), Rhino.Geometry.Point3d(0, 0, 30)),
    "Back":   (Rhino.Geometry.Point3d(0, 500, 30), Rhino.Geometry.Point3d(0, 0, 30)),
    "Perspective": (Rhino.Geometry.Point3d(250, -300, 150), Rhino.Geometry.Point3d(0, 0, 30)),
}


# ---- Layer helpers ----

def _get_last_layer_index(doc):
    full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, _CLASS_LAST)
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx < 0:
        parent_idx = doc.Layers.FindByFullPath(_SLM_LAYER_PREFIX, -1)
        if parent_idx < 0:
            parent_layer = Rhino.DocObjects.Layer()
            parent_layer.Name = _SLM_LAYER_PREFIX
            parent_idx = doc.Layers.Add(parent_layer)
        child_layer = Rhino.DocObjects.Layer()
        child_layer.Name = _CLASS_LAST
        child_layer.ParentLayerId = doc.Layers[parent_idx].Id
        idx = doc.Layers.Add(child_layer)
    return idx


def _find_last_objects(doc):
    layer_idx = _get_last_layer_index(doc)
    if layer_idx < 0:
        return []
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    return list(objs) if objs else []


# ---- Command ----

def RunCommand(is_interactive):
    doc = sc.doc

    # Select view angle
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("View angle")
    for name in _VIEW_ANGLES:
        gs.AddOption(Rhino.Input.Custom.OptionToggle(False, "No", "Yes"), name)
    gs.SetDefaultString("Perspective")
    gs.AcceptNothing(True)

    result = gs.Get()
    view_name = "Perspective"
    if result == Rhino.Input.GetResult.String:
        user_val = gs.StringResult().strip()
        if user_val in _VIEW_ANGLES:
            view_name = user_val
    elif result == Rhino.Input.GetResult.Option:
        view_name = gs.Option().EnglishName

    if gs.CommandResult() != Rhino.Commands.Result.Success:
        if result != Rhino.Input.GetResult.Option:
            return 1

    camera, target = _VIEW_ANGLES[view_name]

    # Adjust target to center of last bounding box if a last exists
    last_objs = _find_last_objects(doc)
    if last_objs:
        bbox = Rhino.Geometry.BoundingBox.Empty
        for obj in last_objs:
            obj_bbox = obj.Geometry.GetBoundingBox(True)
            bbox.Union(obj_bbox)
        if bbox.IsValid:
            center = bbox.Center
            offset = center - target
            target = center
            camera = camera + offset

    # Apply to the active viewport
    view = doc.Views.ActiveView
    if view is None:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No active view.")
        return 1

    vp = view.ActiveViewport
    vp.SetCameraTarget(target, True)
    vp.SetCameraLocation(camera, True)
    vp.Camera35mmLensLength = 50.0
    view.Redraw()

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] View set to '{0}'.".format(view_name)
    )
    return 0
