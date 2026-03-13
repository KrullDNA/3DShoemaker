"""
3DShoemaker Rhino 8 Plugin - Command modules.

All Rhino commands for the 3DShoemaker footwear-design plugin are
registered from the sub-modules in this package.
"""

from plugin.commands.activation_commands import (
    Activate3DShoemaker,
    Deactivate3DShoemaker,
)
from plugin.commands.last_commands import (
    NewBuild,
    NewBuildScriptable,
    UpdateLast,
    ImportLast,
    ExportLast,
    GradeLast,
    FlattenLast,
    GazeAtLast,
    ChangeLastParameterization,
    ExportLastParameters,
    ImportParameters,
    ExportMeasurementEquations,
    NameObjectsInDoc,
    GetObjectIDName,
    Establish,
)
from plugin.commands.morph_commands import (
    Morph,
    NewMorph,
    NewMorphScriptable,
)
from plugin.commands.component_commands import (
    CreateInsole,
    CreateSole,
    CreateHeel,
    CreateHeelParts,
    CreateTopPiece,
    CreateShankBoard,
    CreateMetPad,
    CreateToeCrest,
    CreateToeRidge,
    CreateThongHole,
    CreatePinHole,
    CreateShoeTree,
    CreateUpperBodies,
    MakeComponent,
    CreateAlphaJoint,
    CreateRailGuideJoint,
    CreateMockup,
)
from plugin.commands.grade_commands import (
    GradeFootwear,
    BatchGrade,
)
from plugin.commands.foot_commands import (
    ImportFoot,
    OpenImportFootForm,
    AnalyzePlantarFootScan,
)
from plugin.commands.orthotic_commands import (
    MakeOrthotic,
    AdjustOrthoticToBlank,
    AdjustOrthoticArchHeightAndLength,
    AdjustOrthoticFeature,
    TwistOrthotic,
    PrintPrepOrthotic,
    PrintPrepOrthotics,
)
from plugin.commands.sandal_commands import (
    BuildSandal,
    BuildInsert,
    AddSandalGroove,
    AddThongSlot,
    ToggleThongSlotInclusion,
    AddMetpad,
)
from plugin.commands.editing_commands import (
    EditCurve,
    EndEdit,
    MoveObjectGrips,
    Sculpt,
    BlendSurfaceToSurface,
    GirthCurveAveraging,
    AdjustSurfacingCurveControlPointPosition,
    CopyObjectToMultiplePoints,
)
from plugin.commands.parameterization_commands import (
    ChangeParameter,
    ChangeComponentParameterization,
    ChangeInsertParameterization,
    AdjustBottomComponentParameterization,
    AdjustMaterial,
    AdjustMaterialThicknesses,
    AdjustFitCustomization,
    AdjustFootbedDepth,
    AdjustLastDepthForFootbeds,
    AdjustCSPlanePositions,
    ChangeStatus,
)
from plugin.commands.view_commands import (
    DrawClippingPlanes,
    RenderComponents,
    FlattenInsert,
    FlattenSole,
    FlattenBottomSides,
    PrintPrep,
)
from plugin.commands.export_commands import (
    ExportInsertParameters,
    ExportSupportParameters,
    Open3DShoemakerOptions,
    OpenFolderWatcher,
    RebuildFootwear,
    VacuumFormCommand,
    MeasureLast,
    ChangeClippingPlane,
    SnapCurvesCommand,
    SqueezeCommand,
    TestingCommand,
)

__all__ = [
    # Activation
    "Activate3DShoemaker", "Deactivate3DShoemaker",
    # Last
    "NewBuild", "NewBuildScriptable", "UpdateLast", "ImportLast", "ExportLast",
    "GradeLast", "FlattenLast", "GazeAtLast", "ChangeLastParameterization",
    "ExportLastParameters", "ImportParameters", "ExportMeasurementEquations",
    "NameObjectsInDoc", "GetObjectIDName", "Establish",
    # Morph
    "Morph", "NewMorph", "NewMorphScriptable",
    # Components
    "CreateInsole", "CreateSole", "CreateHeel", "CreateHeelParts",
    "CreateTopPiece", "CreateShankBoard", "CreateMetPad", "CreateToeCrest",
    "CreateToeRidge", "CreateThongHole", "CreatePinHole", "CreateShoeTree",
    "CreateUpperBodies", "MakeComponent", "CreateAlphaJoint",
    "CreateRailGuideJoint", "CreateMockup",
    # Grade
    "GradeFootwear", "BatchGrade",
    # Foot
    "ImportFoot", "OpenImportFootForm", "AnalyzePlantarFootScan",
    # Orthotic
    "MakeOrthotic", "AdjustOrthoticToBlank", "AdjustOrthoticArchHeightAndLength",
    "AdjustOrthoticFeature", "TwistOrthotic", "PrintPrepOrthotic", "PrintPrepOrthotics",
    # Sandal
    "BuildSandal", "BuildInsert", "AddSandalGroove", "AddThongSlot",
    "ToggleThongSlotInclusion", "AddMetpad",
    # Editing
    "EditCurve", "EndEdit", "MoveObjectGrips", "Sculpt",
    "BlendSurfaceToSurface", "GirthCurveAveraging",
    "AdjustSurfacingCurveControlPointPosition", "CopyObjectToMultiplePoints",
    # Parameterization
    "ChangeParameter", "ChangeComponentParameterization",
    "ChangeInsertParameterization", "AdjustBottomComponentParameterization",
    "AdjustMaterial", "AdjustMaterialThicknesses", "AdjustFitCustomization",
    "AdjustFootbedDepth", "AdjustLastDepthForFootbeds", "AdjustCSPlanePositions",
    "ChangeStatus",
    # View
    "DrawClippingPlanes", "RenderComponents", "FlattenInsert", "FlattenSole",
    "FlattenBottomSides", "PrintPrep",
    # Export/Utility
    "ExportInsertParameters", "ExportSupportParameters",
    "Open3DShoemakerOptions", "OpenFolderWatcher", "RebuildFootwear",
    "VacuumFormCommand", "MeasureLast", "ChangeClippingPlane",
    "SnapCurvesCommand", "SqueezeCommand", "TestingCommand",
]
