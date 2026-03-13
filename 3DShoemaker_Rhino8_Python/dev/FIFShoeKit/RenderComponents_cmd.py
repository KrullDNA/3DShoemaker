# -*- coding: utf-8 -*-
"""Renders footwear components with materials and lighting.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.DocObjects as rdo
import Rhino.Commands as rc
import scriptcontext as sc
import System

__commandname__ = "RenderComponents"


def RunCommand(is_interactive):
    doc = sc.doc

    component_materials = {
        "Last": System.Drawing.Color.FromArgb(200, 180, 160),
        "Insert": System.Drawing.Color.FromArgb(60, 60, 180),
        "Sole": System.Drawing.Color.FromArgb(40, 40, 40),
        "Heel": System.Drawing.Color.FromArgb(50, 50, 50),
        "ShankBoard": System.Drawing.Color.FromArgb(139, 90, 43),
        "TopPiece": System.Drawing.Color.FromArgb(80, 80, 80),
        "MetPad": System.Drawing.Color.FromArgb(100, 150, 200),
    }

    try:
        for layer_idx in range(doc.Layers.Count):
            layer = doc.Layers[layer_idx]
            layer_name = layer.Name
            for comp_name, color in component_materials.items():
                if comp_name.lower() in layer_name.lower():
                    mat_index = doc.Materials.Add()
                    mat = doc.Materials[mat_index]
                    mat.DiffuseColor = color
                    mat.Shine = 0.3 * rdo.Material.MaxShine
                    mat.Transparency = 0.0
                    mat.CommitChanges()

                    objs = doc.Objects.FindByLayer(layer)
                    if objs:
                        for obj in objs:
                            obj.Attributes.MaterialSource = rdo.ObjectMaterialSource.MaterialFromObject
                            obj.Attributes.MaterialIndex = mat_index
                            obj.CommitChanges()
                    break

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("Render materials applied to components.")
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error rendering components: {0}".format(e))
        return rc.Result.Failure
