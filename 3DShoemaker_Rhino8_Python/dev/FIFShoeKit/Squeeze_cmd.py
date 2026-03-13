# -*- coding: utf-8 -*-
"""Applies squeeze deformation to geometry.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import scriptcontext as sc

__commandname__ = "Squeeze"


def _squeeze_geometry(geom, factor):
    """Apply a squeeze deformation by scaling in X relative to the bounding box center."""
    bbox = geom.GetBoundingBox(True)
    if not bbox.IsValid:
        return None

    center = bbox.Center
    duplicated = geom.Duplicate()
    if duplicated is None:
        return None

    # Create a non-uniform scale: squeeze in X, leave Y and Z unchanged
    scale = rg.Transform.Scale(
        rg.Plane(center, rg.Vector3d.ZAxis),
        factor, 1.0, 1.0
    )
    if duplicated.Transform(scale):
        return duplicated
    return None


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        go = ric.GetObject()
        go.SetCommandPrompt("Select objects to squeeze")
        go.GeometryFilter = (
            rdo.ObjectType.Mesh | rdo.ObjectType.Brep |
            rdo.ObjectType.Surface | rdo.ObjectType.SubD
        )
        go.GetMultiple(1, 0)
        if go.CommandResult() != rc.Result.Success:
            return go.CommandResult()

        gn = ric.GetNumber()
        gn.SetCommandPrompt("Squeeze factor (0.5 = half, 2.0 = double)")
        gn.SetDefaultNumber(1.0)
        gn.SetLowerLimit(0.01, False)
        gn.SetUpperLimit(10.0, False)
        gn.Get()
        if gn.CommandResult() != rc.Result.Success:
            return gn.CommandResult()

        factor = gn.Number()

        count = 0
        for i in range(go.ObjectCount):
            obj_ref = go.Object(i)
            geom = obj_ref.Geometry()
            if geom is None:
                continue

            squeezed = _squeeze_geometry(geom, factor)
            if squeezed is not None:
                doc.Objects.Replace(obj_ref.ObjectId, squeezed)
                count += 1

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            "Squeeze applied to {0} object(s) with factor {1:.2f}.".format(count, factor)
        )
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error applying squeeze: {0}".format(e))
        return rc.Result.Failure
