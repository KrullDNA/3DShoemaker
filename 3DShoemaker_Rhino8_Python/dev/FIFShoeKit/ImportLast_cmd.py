# -*- coding: utf-8 -*-
"""Import a last from file (3dm, STEP, IGES, STL).

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

__commandname__ = "ImportLast"

# ---- Constants ----
_SLM_LAYER_PREFIX = "SLM"
_CLASS_LAST = "Last"
_IMPORT_FILTER = (
    "All Supported Files (*.3dm;*.stp;*.step;*.igs;*.iges;*.stl)|"
    "*.3dm;*.stp;*.step;*.igs;*.iges;*.stl|"
    "Rhino Files (*.3dm)|*.3dm|"
    "STEP Files (*.stp;*.step)|*.stp;*.step|"
    "IGES Files (*.igs;*.iges)|*.igs;*.iges|"
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


# ---- Command ----

def RunCommand(is_interactive):
    doc = sc.doc

    # Prompt for file path
    fd = Rhino.Input.Custom.GetString()
    fd.SetCommandPrompt("Path to last file (3dm, STEP, IGES, STL)")
    fd.Get()
    if fd.CommandResult() != Rhino.Commands.Result.Success:
        return 1

    file_path = fd.StringResult().strip().strip('"')
    if not file_path or not os.path.isfile(file_path):
        # Try the Rhino open file dialog
        dialog = Rhino.UI.OpenFileDialog()
        dialog.Title = "Import Last"
        dialog.Filter = _IMPORT_FILTER
        if not dialog.ShowOpenDialog():
            return 1
        file_path = dialog.FileName

    if not os.path.isfile(file_path):
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] File not found: {0}".format(file_path)
        )
        return 1

    ext = os.path.splitext(file_path)[1].lower()
    layer_idx = _get_last_layer_index(doc)

    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Importing last from: {0}".format(file_path)
    )

    imported_count = 0
    if ext == ".3dm":
        # Read 3dm file and import geometry
        file3dm = Rhino.FileIO.File3dm.Read(file_path)
        if file3dm is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to read 3dm file.")
            return 1
        for obj in file3dm.Objects:
            geom = obj.Geometry
            if geom is not None:
                attrs = Rhino.DocObjects.ObjectAttributes()
                attrs.Name = obj.Attributes.Name or "SLM_ImportedLast"
                if layer_idx >= 0:
                    attrs.LayerIndex = layer_idx
                doc.Objects.Add(geom, attrs)
                imported_count += 1
    elif ext in (".stp", ".step", ".igs", ".iges", ".stl"):
        # Use Rhino's built-in import command
        script = '_-Import "{0}" _Enter'.format(file_path)
        Rhino.RhinoApp.RunScript(script, False)
        # Move imported objects to the Last layer
        if layer_idx >= 0:
            selected = doc.Objects.GetSelectedObjects(False, False)
            if selected:
                for obj in selected:
                    attrs = obj.Attributes.Duplicate()
                    attrs.LayerIndex = layer_idx
                    attrs.Name = attrs.Name or "SLM_ImportedLast"
                    doc.Objects.ModifyAttributes(obj, attrs, True)
                    imported_count += 1
    else:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Unsupported file format: {0}".format(ext)
        )
        return 1

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Imported {0} object(s) from {1}.".format(
            imported_count, os.path.basename(file_path)
        )
    )
    return 0
