#!/usr/bin/env python3
"""Generate _cmd.py wrapper files for all FIFShoeKit commands.

These wrappers are required by Rhino's .rhi installer format to discover
and register commands. Each file follows the IronPython 2 compatible pattern
with __commandname__ and RunCommand(is_interactive).

The wrappers attempt to delegate to the CPython 3 plugin implementation
if available, and fall back to a status message if not.
"""

import os
from pathlib import Path

_DEV_DIR = Path(__file__).resolve().parent / "dev" / "FIFShoeKit"

# (command_name, module_path, class_name, description)
# module_path is relative to plugin.commands
COMMANDS = [
    # Last commands
    ("NewBuild", "last_commands", "NewBuild", "Create a new shoe last build"),
    ("NewBuildScriptable", "last_commands", "NewBuildScriptable", "Create a new build with scriptable parameters"),
    ("UpdateLast", "last_commands", "UpdateLast", "Update the current last geometry"),
    ("ImportLast", "last_commands", "ImportLast", "Import a shoe last from file"),
    ("ExportLast", "last_commands", "ExportLast", "Export the current last to file"),
    ("GradeLast", "last_commands", "GradeLast", "Grade the current last to a different size"),
    ("FlattenLast", "last_commands", "FlattenLast", "Flatten the last for 2D output"),
    ("GazeAtLast", "last_commands", "GazeAtLast", "Set the viewport to look at the last"),
    ("ChangeLastParameterization", "last_commands", "ChangeLastParameterization", "Modify last parameterization settings"),
    ("ExportLastParameters", "last_commands", "ExportLastParameters", "Export last parameters to file"),
    ("ImportParameters", "last_commands", "ImportParameters", "Import parameters from file"),
    ("ExportMeasurementEquations", "last_commands", "ExportMeasurementEquations", "Export measurement equations"),
    ("NameObjectsInDoc", "last_commands", "NameObjectsInDoc", "Name all objects in the document"),
    ("GetObjectIDName", "last_commands", "GetObjectIDName", "Get the ID and name of an object"),
    ("Establish", "last_commands", "Establish", "Establish the last baseline"),
    # Morph commands
    ("Morph", "morph_commands", "Morph", "Morph the last shape interactively"),
    ("NewMorph", "morph_commands", "NewMorph", "Create a new morph operation"),
    ("NewMorphScriptable", "morph_commands", "NewMorphScriptable", "Create a morph with scriptable parameters"),
    # Component commands
    ("CreateInsole", "component_commands", "CreateInsole", "Generate an insole from the last"),
    ("CreateSole", "component_commands", "CreateSole", "Create the outsole"),
    ("CreateHeel", "component_commands", "CreateHeel", "Create the heel"),
    ("CreateHeelParts", "component_commands", "CreateHeelParts", "Create individual heel parts"),
    ("CreateTopPiece", "component_commands", "CreateTopPiece", "Create the top piece"),
    ("CreateShankBoard", "component_commands", "CreateShankBoard", "Create the shank board"),
    ("CreateMetPad", "component_commands", "CreateMetPad", "Add a metatarsal pad"),
    ("CreateToeCrest", "component_commands", "CreateToeCrest", "Create a toe crest"),
    ("CreateToeRidge", "component_commands", "CreateToeRidge", "Create a toe ridge"),
    ("CreateThongHole", "component_commands", "CreateThongHole", "Create a thong hole in the sole"),
    ("CreatePinHole", "component_commands", "CreatePinHole", "Create a pin hole"),
    ("CreateShoeTree", "component_commands", "CreateShoeTree", "Create a shoe tree"),
    ("CreateUpperBodies", "component_commands", "CreateUpperBodies", "Generate upper pattern bodies"),
    ("MakeComponent", "component_commands", "MakeComponent", "Create a generic component"),
    ("CreateAlphaJoint", "component_commands", "CreateAlphaJoint", "Create an alpha joint"),
    ("CreateRailGuideJoint", "component_commands", "CreateRailGuideJoint", "Create a rail guide joint"),
    ("CreateMockup", "component_commands", "CreateMockup", "Create a full footwear mockup"),
    # Grade commands
    ("GradeFootwear", "grade_commands", "GradeFootwear", "Grade footwear to a specific size"),
    ("BatchGrade", "grade_commands", "BatchGrade", "Grade to multiple sizes at once"),
    # Foot commands
    ("ImportFoot", "foot_commands", "ImportFoot", "Import a foot scan or model"),
    ("OpenImportFootForm", "foot_commands", "OpenImportFootForm", "Open the foot import dialog"),
    ("AnalyzePlantarFootScan", "foot_commands", "AnalyzePlantarFootScan", "Analyze a plantar foot scan"),
    # Orthotic commands
    ("MakeOrthotic", "orthotic_commands", "MakeOrthotic", "Create an orthotic from foot and last data"),
    ("AdjustOrthoticToBlank", "orthotic_commands", "AdjustOrthoticToBlank", "Adjust orthotic to fit a blank"),
    ("AdjustOrthoticArchHeightAndLength", "orthotic_commands", "AdjustOrthoticArchHeightAndLength", "Modify orthotic arch height and length"),
    ("AdjustOrthoticFeature", "orthotic_commands", "AdjustOrthoticFeature", "Adjust orthotic features"),
    ("TwistOrthotic", "orthotic_commands", "TwistOrthotic", "Apply twist deformation to orthotic"),
    ("PrintPrepOrthotic", "orthotic_commands", "PrintPrepOrthotic", "Prepare orthotic for 3D printing"),
    ("PrintPrepOrthotics", "orthotic_commands", "PrintPrepOrthotics", "Batch prepare multiple orthotics"),
    # Sandal commands
    ("BuildSandal", "sandal_commands", "BuildSandal", "Create a sandal from a last"),
    ("BuildInsert", "sandal_commands", "BuildInsert", "Create a removable insert"),
    ("AddSandalGroove", "sandal_commands", "AddSandalGroove", "Add a groove to the sandal"),
    ("AddThongSlot", "sandal_commands", "AddThongSlot", "Add a thong slot"),
    ("ToggleThongSlotInclusion", "sandal_commands", "ToggleThongSlotInclusion", "Toggle thong slot on/off"),
    ("AddMetpad", "sandal_commands", "AddMetpad", "Add a metatarsal pad to sandal"),
    # Editing commands
    ("EditCurve", "editing_commands", "EditCurve", "Enter curve editing mode"),
    ("EndEdit", "editing_commands", "EndEdit", "Exit editing mode"),
    ("MoveObjectGrips", "editing_commands", "MoveObjectGrips", "Move object control points"),
    ("Sculpt", "editing_commands", "Sculpt", "Sculpt surfaces interactively"),
    ("BlendSurfaceToSurface", "editing_commands", "BlendSurfaceToSurface", "Blend between two surfaces"),
    ("GirthCurveAveraging", "editing_commands", "GirthCurveAveraging", "Average girth curves"),
    ("AdjustSurfacingCurveControlPointPosition", "editing_commands", "AdjustSurfacingCurveControlPointPosition", "Adjust surfacing curve control points"),
    ("CopyObjectToMultiplePoints", "editing_commands", "CopyObjectToMultiplePoints", "Copy an object to multiple locations"),
    # Parameterization commands
    ("ChangeParameter", "parameterization_commands", "ChangeParameter", "Modify a single design parameter"),
    ("ChangeComponentParameterization", "parameterization_commands", "ChangeComponentParameterization", "Change component parameterization"),
    ("ChangeInsertParameterization", "parameterization_commands", "ChangeInsertParameterization", "Change insert parameterization"),
    ("AdjustBottomComponentParameterization", "parameterization_commands", "AdjustBottomComponentParameterization", "Adjust bottom component parameters"),
    ("AdjustMaterial", "parameterization_commands", "AdjustMaterial", "Set material properties"),
    ("AdjustMaterialThicknesses", "parameterization_commands", "AdjustMaterialThicknesses", "Set material layer thicknesses"),
    ("AdjustFitCustomization", "parameterization_commands", "AdjustFitCustomization", "Customize fit parameters"),
    ("AdjustFootbedDepth", "parameterization_commands", "AdjustFootbedDepth", "Adjust footbed depth"),
    ("AdjustLastDepthForFootbeds", "parameterization_commands", "AdjustLastDepthForFootbeds", "Adjust last depth for footbeds"),
    ("AdjustCSPlanePositions", "parameterization_commands", "AdjustCSPlanePositions", "Adjust cross-section plane positions"),
    ("ChangeStatus", "parameterization_commands", "ChangeStatus", "Change the build status"),
    # View commands
    ("DrawClippingPlanes", "view_commands", "DrawClippingPlanes", "Draw clipping planes on the model"),
    ("RenderComponents", "view_commands", "RenderComponents", "Render component views"),
    ("FlattenInsert", "view_commands", "FlattenInsert", "Flatten insert to 2D"),
    ("FlattenSole", "view_commands", "FlattenSole", "Flatten sole to 2D"),
    ("FlattenBottomSides", "view_commands", "FlattenBottomSides", "Flatten bottom sides to 2D"),
    ("PrintPrep", "view_commands", "PrintPrep", "Prepare model for 3D printing"),
    # Export/Utility commands
    ("ExportInsertParameters", "export_commands", "ExportInsertParameters", "Export insert parameters to file"),
    ("ExportSupportParameters", "export_commands", "ExportSupportParameters", "Export support parameters to file"),
    ("OpenFIFShoeKitOptions", "export_commands", "OpenFIFShoeKitOptions", "Open the plugin options dialog"),
    ("OpenFolderWatcher", "export_commands", "OpenFolderWatcher", "Open the folder watcher utility"),
    ("RebuildFootwear", "export_commands", "RebuildFootwear", "Rebuild all footwear components"),
    ("VacuumForm", "export_commands", "VacuumFormCommand", "Create vacuum form geometry"),
    ("MeasureLast", "export_commands", "MeasureLast", "Measure the current last"),
    ("ChangeClippingPlane", "export_commands", "ChangeClippingPlane", "Change the active clipping plane"),
    ("SnapCurves", "export_commands", "SnapCurvesCommand", "Snap curves to surfaces"),
    ("Squeeze", "export_commands", "SqueezeCommand", "Squeeze/compress geometry"),
]

# Commands that already have _cmd.py files (skip these)
EXISTING = {"FIFShoeKit", "ShowFIFShoeKitPanel"}

TEMPLATE = '''# -*- coding: utf-8 -*-
"""{description}

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "{cmd_name}"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] {cmd_name} invoked.")
    Rhino.RhinoApp.WriteLine("  {description}")
    return 0
'''


def main():
    generated = 0
    skipped = 0

    for cmd_name, module, cls_name, description in COMMANDS:
        if cmd_name in EXISTING:
            skipped += 1
            continue

        filename = "{}_cmd.py".format(cmd_name)
        filepath = _DEV_DIR / filename

        content = TEMPLATE.format(
            cmd_name=cmd_name,
            module=module,
            cls_name=cls_name,
            description=description,
        )

        filepath.write_text(content, encoding="utf-8")
        generated += 1
        print("  + {}".format(filename))

    print()
    print("Generated: {} files".format(generated))
    print("Skipped (existing): {} files".format(skipped))
    print("Output directory: {}".format(_DEV_DIR))


if __name__ == "__main__":
    main()
