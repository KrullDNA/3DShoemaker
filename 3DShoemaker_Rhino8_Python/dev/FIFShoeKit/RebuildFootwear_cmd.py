# -*- coding: utf-8 -*-
"""Rebuilds all footwear geometry from stored parameters.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.DocObjects as rdo
import Rhino.Geometry as rg
import scriptcontext as sc

__commandname__ = "RebuildFootwear"


def _find_objects_on_layer(doc, layer_path):
    """Find all objects on a given layer path."""
    layer_idx = doc.Layers.FindByFullPath(layer_path, -1)
    if layer_idx < 0:
        return []
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        return list(objs)
    return []


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        Rhino.RhinoApp.WriteLine("Rebuilding footwear from stored parameters...")

        # Check for existing footwear layers and objects
        layer_prefixes = [
            "Feet in Focus Shoe Kit::Last",
            "Feet in Focus Shoe Kit::Insert",
            "Feet in Focus Shoe Kit::Bottom",
            "SLM::Last",
            "SLM::Insert",
            "SLM::Bottom",
        ]

        has_last = False
        has_insert = False
        has_bottom = False

        for prefix in layer_prefixes:
            objs = _find_objects_on_layer(doc, prefix)
            if objs:
                if "Last" in prefix:
                    has_last = True
                elif "Insert" in prefix:
                    has_insert = True
                elif "Bottom" in prefix:
                    has_bottom = True

        if has_last:
            Rhino.RhinoApp.WriteLine("  Rebuilding last...")
            # Trigger last rebuild via Rhino command
            Rhino.RhinoApp.RunScript("_-UpdateLast", False)

        if has_insert:
            Rhino.RhinoApp.WriteLine("  Rebuilding insert...")
            # Re-run insert design curves and surfaces
            Rhino.RhinoApp.RunScript("_-CreateInsole", False)

        if has_bottom:
            Rhino.RhinoApp.WriteLine("  Rebuilding bottom...")
            # Re-run bottom design
            Rhino.RhinoApp.RunScript("_-CreateSole", False)

        if not (has_last or has_insert or has_bottom):
            Rhino.RhinoApp.WriteLine("  No existing footwear components found to rebuild.")
            Rhino.RhinoApp.WriteLine("  Use NewBuild to create a new footwear design.")
            return rc.Result.Nothing

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Footwear rebuild complete.")
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error rebuilding footwear: {0}".format(e))
        return rc.Result.Failure
