# -*- coding: utf-8 -*-
"""Export last to file.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import os
import Rhino
import Rhino.Commands
import Rhino.FileIO
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import Rhino.UI
import scriptcontext as sc

__commandname__ = "ExportLast"

# ---- Constants ----
_SLM_LAYER_PREFIX = "SLM"
_CLASS_LAST = "Last"
_EXPORT_FILTER = (
    "Rhino Files (*.3dm)|*.3dm|"
    "STEP Files (*.stp)|*.stp|"
    "IGES Files (*.igs)|*.igs|"
    "STL Files (*.stl)|*.stl"
)


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

    last_objs = _find_last_objects(doc)
    if not last_objs:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry to export.")
        return 1

    # Prompt for output file
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Export file path (or press Enter for dialog)")
    gs.AcceptNothing(True)
    gs.Get()

    file_path = ""
    if gs.CommandResult() == Rhino.Commands.Result.Success and gs.StringResult():
        file_path = gs.StringResult().strip().strip('"')

    if not file_path:
        dialog = Rhino.UI.SaveFileDialog()
        dialog.Title = "Export Last"
        dialog.Filter = _EXPORT_FILTER
        dialog.DefaultExt = "stl"
        if not dialog.ShowSaveDialog():
            return 1
        file_path = dialog.FileName

    if not file_path:
        return 1

    ext = os.path.splitext(file_path)[1].lower()

    # Select last objects for export
    doc.Objects.UnselectAll()
    for obj in last_objs:
        doc.Objects.Select(obj.Id, True)

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Exporting last to: {0}".format(file_path)
    )

    if ext == ".3dm":
        file3dm = Rhino.FileIO.File3dm()
        for obj in last_objs:
            geom = obj.Geometry
            attrs = obj.Attributes
            if geom is not None:
                file3dm.Objects.Add(geom, attrs)
        opts = Rhino.FileIO.File3dmWriteOptions()
        file3dm.Write(file_path, opts)
    else:
        # Use Rhino's built-in export for STEP, IGES, STL
        script = '_-Export "{0}" _Enter'.format(file_path)
        Rhino.RhinoApp.RunScript(script, False)

    doc.Objects.UnselectAll()
    doc.Views.Redraw()

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Last exported: {0}".format(os.path.basename(file_path))
    )
    return 0
