# -*- coding: utf-8 -*-
"""Feet in Focus Shoe Kit - ShowFIFShoeKitPanel Command

Opens the Feet in Focus Shoe Kit panel as a modeless form.
The panel provides categorised buttons for every major command,
layer visibility toggles, clipping-plane controls, and a status bar.

This file is self-contained (no imports from plugin/) so it works
in both IronPython 2 and CPython 3 runtimes within Rhino 8.
"""

import Rhino
import Rhino.RhinoDoc
import Eto.Forms as ef
import Eto.Drawing as ed


__commandname__ = "ShowFIFShoeKitPanel"

# Module-level reference to keep the form alive
_panel_form = None


# ---------------------------------------------------------------------------
# Command groups: (button_label, rhino_command_name, tooltip)
# ---------------------------------------------------------------------------

_CMD_BUILD = [
    ("New Build", "NewBuild", "Create a new shoe last build"),
    ("Import Last", "ImportLast", "Import a last from file"),
    ("Create Insole", "CreateInsole", "Generate insole from last"),
    ("Create Sole", "CreateSole", "Generate outsole geometry"),
    ("Import Foot", "ImportFoot", "Import a 2D/3D foot scan"),
]

_CMD_EDIT = [
    ("Edit Curve", "EditCurve", "Enter curve editing mode"),
    ("End Edit", "EndEdit", "Exit editing mode"),
    ("Morph", "NewMorph", "Morph geometry from source to target"),
    ("Sculpt", "Sculpt", "Sculpt surfaces interactively"),
    ("Blend Surfaces", "BlendSurfaceToSurface", "Blend between two surfaces"),
]

_CMD_COMPONENTS = [
    ("Create Heel", "CreateHeel", "Create the heel"),
    ("Create Top Piece", "CreateTopPiece", "Create the top piece"),
    ("Create Shank Board", "CreateShankBoard", "Create the shank board"),
    ("Create Met Pad", "CreateMetPad", "Add a metatarsal pad"),
    ("Create Upper Bodies", "CreateUpperBodies", "Generate upper pattern bodies"),
    ("Create Mockup", "CreateMockup", "Create a full footwear mockup"),
]

_CMD_GRADE = [
    ("Grade Footwear", "GradeFootwear", "Grade to a different shoe size"),
    ("Batch Grade", "BatchGrade", "Grade to multiple sizes at once"),
]

_CMD_EXPORT = [
    ("3D Print Prep", "PrintPrep", "Prepare for 3D printing"),
    ("Export Last", "ExportLast", "Export the last to file"),
    ("Render Components", "RenderComponents", "Render component views"),
]

_CMD_VIEW = [
    ("Gaze At Last", "GazeAtLast", "Set viewport to look at the last"),
    ("Clipping Planes", "DrawClippingPlanes", "Draw clipping planes"),
]

_CMD_FOOT = [
    ("Import Foot", "ImportFoot", "Import a foot scan or model"),
    ("Analyze Plantar", "AnalyzePlantarFootScan", "Analyze plantar foot scan"),
]

_CMD_ORTHOTIC = [
    ("Make Orthotic", "MakeOrthotic", "Create orthotic from foot/last data"),
    ("Adjust To Blank", "AdjustOrthoticToBlank", "Fit orthotic to a blank"),
    ("Print Prep Orthotic", "PrintPrepOrthotic", "Prepare orthotic for 3D printing"),
]

_CMD_SANDAL = [
    ("Build Sandal", "BuildSandal", "Create a sandal from a last"),
    ("Build Insert", "BuildInsert", "Create a removable insert"),
]

_CMD_OPTIONS = [
    ("Options", "OpenFIFShoeKitOptions", "Open the plugin options dialog"),
    ("Rebuild Footwear", "RebuildFootwear", "Rebuild all footwear components"),
]

_ALL_SECTIONS = [
    ("Build", _CMD_BUILD),
    ("Edit", _CMD_EDIT),
    ("Components", _CMD_COMPONENTS),
    ("Grade", _CMD_GRADE),
    ("Export", _CMD_EXPORT),
    ("View", _CMD_VIEW),
    ("Foot", _CMD_FOOT),
    ("Orthotic", _CMD_ORTHOTIC),
    ("Sandal", _CMD_SANDAL),
    ("Utility", _CMD_OPTIONS),
]


# ---------------------------------------------------------------------------
# Panel builder
# ---------------------------------------------------------------------------

def _make_cmd_handler(cmd_name):
    """Create a click handler that runs a Rhino command."""
    def handler(sender, e):
        Rhino.RhinoApp.RunScript(cmd_name, False)
    return handler


def _separator():
    """Create a thin horizontal separator line."""
    sep = ef.Panel()
    sep.Height = 1
    sep.BackgroundColor = ed.Colors.Gray
    return sep


def _build_section(title, commands):
    """Create a GroupBox with buttons for the given command list."""
    group = ef.GroupBox()
    group.Text = title
    layout = ef.DynamicLayout()
    layout.DefaultSpacing = ed.Size(3, 3)
    layout.Padding = ed.Padding(4)

    for label, cmd_name, tooltip in commands:
        btn = ef.Button()
        btn.Text = label
        btn.ToolTip = tooltip
        btn.Click += _make_cmd_handler(cmd_name)
        layout.AddRow(btn)

    group.Content = layout
    return group


def _build_panel():
    """Build and return the complete panel form."""
    form = ef.Form()
    form.Title = "Feet in Focus Shoe Kit"
    form.ClientSize = ed.Size(280, 720)
    form.Minimizable = True
    form.Resizable = True

    scrollable = ef.Scrollable()
    scrollable.Border = ef.BorderType.None_
    scrollable.ExpandContentWidth = True

    root = ef.DynamicLayout()
    root.DefaultSpacing = ed.Size(4, 4)
    root.Padding = ed.Padding(6)

    # Header
    header = ef.Label()
    header.Text = "Feet in Focus Shoe Kit"
    header.Font = ed.Font(ed.SystemFont.Bold, 12)
    header.TextAlignment = ef.TextAlignment.Center
    root.AddRow(header)
    root.AddRow(_separator())

    # Command sections
    for title, commands in _ALL_SECTIONS:
        root.AddRow(_build_section(title, commands))
        root.AddRow(_separator())

    scrollable.Content = root
    form.Content = scrollable
    return form


# ---------------------------------------------------------------------------
# RunCommand
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    global _panel_form

    # If form already exists and is visible, just bring it to front
    if _panel_form is not None:
        try:
            if _panel_form.Visible:
                _panel_form.BringToFront()
                return 0
        except Exception:
            _panel_form = None

    try:
        _panel_form = _build_panel()
        _panel_form.Show()
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Panel opened."
        )
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Failed to open panel - {}".format(ex)
        )
        return 1

    return 0
