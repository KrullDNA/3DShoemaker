# -*- coding: utf-8 -*-
"""Creates clipping planes at cross-section locations on the last.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.DocObjects as rdo
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

__commandname__ = "DrawClippingPlanes"


def _get_or_create_layer(doc, parent_name, child_name):
    """Return layer index for parent::child, creating if needed."""
    full_path = "{0}::{1}".format(parent_name, child_name)
    layer_index = doc.Layers.FindByFullPath(full_path, -1)
    if layer_index < 0:
        layer = rdo.Layer()
        layer.Name = child_name
        parent_idx = doc.Layers.FindByFullPath(parent_name, -1)
        if parent_idx >= 0:
            layer.ParentLayerId = doc.Layers[parent_idx].Id
        layer.Color = System.Drawing.Color.FromArgb(128, 128, 128)
        layer_index = doc.Layers.Add(layer)
    return layer_index


def RunCommand(is_interactive):
    doc = sc.doc

    # Look for cross-section plane objects stored in document user text
    # or named objects with known CS plane prefixes
    plane_names = ["Ball", "Instep", "Waist", "Waist2", "Arch", "Arch2", "Heel"]

    layer_index = _get_or_create_layer(doc, "Feet in Focus Shoe Kit", "ClippingPlanes")
    attrs = rdo.ObjectAttributes()
    attrs.LayerIndex = layer_index

    active_view = doc.Views.ActiveView
    if active_view is None:
        Rhino.RhinoApp.WriteLine("No active view found.")
        return rc.Result.Failure

    viewport = active_view.ActiveViewport

    # Compute bounding box of all objects
    bbox = rg.BoundingBox.Empty
    for obj in doc.Objects:
        if obj.Geometry is not None:
            bbox.Union(obj.Geometry.GetBoundingBox(True))

    if not bbox.IsValid:
        bbox = rg.BoundingBox(
            rg.Point3d(-100, -100, -100),
            rg.Point3d(100, 100, 100)
        )

    clip_size = bbox.Diagonal.Length * 0.5
    count = 0

    # Try to find plane data from named objects or stored parameters
    for name in plane_names:
        # Look for named objects that encode plane positions
        settings = rdo.ObjectEnumeratorSettings()
        settings.NameFilter = "CSPlane_{0}".format(name)
        settings.DeletedObjects = False
        plane_obj = None
        for obj in doc.Objects.GetObjectList(settings):
            plane_obj = obj
            break

        plane = None
        if plane_obj is not None:
            obj_bbox = plane_obj.Geometry.GetBoundingBox(True)
            if obj_bbox.IsValid:
                center = obj_bbox.Center
                plane = rg.Plane(center, rg.Vector3d.XAxis, rg.Vector3d.YAxis)
        else:
            # Check sc.sticky for stored plane Z values
            key = "FIF_CSPlane_{0}_Z".format(name)
            z_val = sc.sticky.get(key, None)
            if z_val is not None:
                plane = rg.Plane.WorldXY
                plane.Origin = rg.Point3d(0, 0, float(z_val))

        if plane is not None:
            clip_id = doc.Objects.AddClippingPlane(
                plane, clip_size, clip_size, viewport.Id, attrs
            )
            if clip_id != System.Guid.Empty:
                obj = doc.Objects.FindId(clip_id)
                if obj is not None:
                    obj.Attributes.Name = "CP_{0}".format(name)
                    obj.CommitChanges()
                count += 1

    if count == 0:
        # Create a default clipping plane at origin
        ball_plane = rg.Plane.WorldYZ
        ball_plane.Origin = rg.Point3d(0, 0, 0)
        doc.Objects.AddClippingPlane(
            ball_plane, clip_size, clip_size, viewport.Id, attrs
        )
        count = 1

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine("Created {0} clipping plane(s).".format(count))
    return rc.Result.Success
