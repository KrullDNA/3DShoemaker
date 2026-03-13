# -*- coding: utf-8 -*-
"""Get the name/ID of a selected object.

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

__commandname__ = "GetObjectIDName"


# ---- Command ----

def RunCommand(is_interactive):
    doc = sc.doc

    # Prompt user to select an object
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select object to identify")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.AnyObject
    go.Get()
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return 1

    obj_ref = go.Object(0)
    obj = obj_ref.Object()
    if obj is None:
        return 1

    obj_id = obj.Id
    obj_name = obj.Attributes.Name or "(unnamed)"
    layer = doc.Layers[obj.Attributes.LayerIndex]
    layer_name = layer.FullPath

    geom = obj.Geometry
    if geom:
        geom_type = type(geom).__name__
    else:
        geom_type = "Unknown"

    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Object Info:")
    Rhino.RhinoApp.WriteLine("  ID:    {0}".format(obj_id))
    Rhino.RhinoApp.WriteLine("  Name:  {0}".format(obj_name))
    Rhino.RhinoApp.WriteLine("  Layer: {0}".format(layer_name))
    Rhino.RhinoApp.WriteLine("  Type:  {0}".format(geom_type))

    if isinstance(geom, Rhino.Geometry.Brep):
        Rhino.RhinoApp.WriteLine(
            "  Faces: {0}, Edges: {1}".format(geom.Faces.Count, geom.Edges.Count)
        )
    elif isinstance(geom, Rhino.Geometry.Mesh):
        Rhino.RhinoApp.WriteLine(
            "  Vertices: {0}, Faces: {1}".format(geom.Vertices.Count, geom.Faces.Count)
        )

    return 0
