"""
Feet in Focus Shoe Kit Rhino 8 Plugin - Shoe last commands.

Commands:
    NewBuild                    - Create a new shoe last build from parameters.
    NewBuildScriptable          - Scriptable (non-interactive) NewBuild.
    UpdateLast                  - Update existing last geometry after param changes.
    ImportLast                  - Import a last from file (3dm, STEP, IGES, STL).
    ExportLast                  - Export last to file.
    GradeLast                   - Grade (size) the last to a different size.
    FlattenLast                 - Flatten last bottom to a 2D pattern.
    GazeAtLast                  - Set viewport to standard last-viewing angles.
    ChangeLastParameterization  - Open dialog to modify last parameters.
    ExportLastParameters        - Export parameters to JSON.
    ImportParameters            - Import parameters from JSON.
    ExportMeasurementEquations  - Export measurement equations.
    NameObjectsInDoc            - Name all objects with standardized names.
    GetObjectIDName             - Get the name/ID of a selected object.
    Establish                   - Initialize a new shoe last project.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional

import Rhino  # type: ignore
import Rhino.Commands  # type: ignore
import Rhino.Display  # type: ignore
import Rhino.DocObjects  # type: ignore
import Rhino.FileIO  # type: ignore
import Rhino.Geometry  # type: ignore
import Rhino.Input  # type: ignore
import Rhino.Input.Custom  # type: ignore
import Rhino.RhinoApp  # type: ignore
import Rhino.RhinoDoc  # type: ignore
import rhinoscriptsyntax as rs  # type: ignore
import scriptcontext as sc  # type: ignore
import System  # type: ignore

import plugin as plugin_constants
from plugin.plugin_main import PodoCADPlugIn
from plugin.document_settings import DocumentSettings


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

_SIZE_SYSTEMS = ("EU", "US", "UK", "Mondopoint")
_TOE_SHAPES = ("Round", "Pointed", "Square", "Almond", "Oblique")
_LAST_STYLES = ("Standard", "Sport", "Dress", "Casual", "Orthopedic")
_IMPORT_FILTER = (
    "All Supported Files (*.3dm;*.stp;*.step;*.igs;*.iges;*.stl)|"
    "*.3dm;*.stp;*.step;*.igs;*.iges;*.stl|"
    "Rhino Files (*.3dm)|*.3dm|"
    "STEP Files (*.stp;*.step)|*.stp;*.step|"
    "IGES Files (*.igs;*.iges)|*.igs;*.iges|"
    "STL Files (*.stl)|*.stl"
)
_EXPORT_FILTER = (
    "Rhino Files (*.3dm)|*.3dm|"
    "STEP Files (*.stp)|*.stp|"
    "IGES Files (*.igs)|*.igs|"
    "STL Files (*.stl)|*.stl"
)

_VIEW_ANGLES = {
    "Top":    (Rhino.Geometry.Point3d(0, 0, 500), Rhino.Geometry.Point3d(0, 0, 0)),
    "Bottom": (Rhino.Geometry.Point3d(0, 0, -500), Rhino.Geometry.Point3d(0, 0, 0)),
    "Medial": (Rhino.Geometry.Point3d(500, 0, 30), Rhino.Geometry.Point3d(0, 0, 30)),
    "Lateral": (Rhino.Geometry.Point3d(-500, 0, 30), Rhino.Geometry.Point3d(0, 0, 30)),
    "Front":  (Rhino.Geometry.Point3d(0, -500, 30), Rhino.Geometry.Point3d(0, 0, 30)),
    "Back":   (Rhino.Geometry.Point3d(0, 500, 30), Rhino.Geometry.Point3d(0, 0, 30)),
    "Perspective": (Rhino.Geometry.Point3d(250, -300, 150), Rhino.Geometry.Point3d(0, 0, 30)),
}


def _get_plugin() -> PodoCADPlugIn:
    """Return the plugin singleton."""
    return PodoCADPlugIn.instance()


def _require_license() -> bool:
    """Return True if the plugin is licensed, otherwise warn the user."""
    plug = _get_plugin()
    if not plug.is_licensed:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] This command requires a valid license. "
            "Run ActivateFIFShoeKit first."
        )
        return False
    return True


def _get_last_layer_index(doc: Rhino.RhinoDoc) -> int:
    """Return the index of the SLM::Last layer, creating it if needed."""
    full_path = f"{plugin_constants.SLM_LAYER_PREFIX}::{plugin_constants.CLASS_LAST}"
    idx = doc.Layers.FindByFullPath(full_path, -1)
    if idx < 0:
        _get_plugin().SetupLayers(doc)
        idx = doc.Layers.FindByFullPath(full_path, -1)
    return idx


def _find_last_objects(doc: Rhino.RhinoDoc) -> List[Rhino.DocObjects.RhinoObject]:
    """Return all objects on the SLM::Last layer."""
    layer_idx = _get_last_layer_index(doc)
    if layer_idx < 0:
        return []
    layer = doc.Layers[layer_idx]
    objs = doc.Objects.FindByLayer(layer)
    return list(objs) if objs else []


def _prompt_size_system() -> Optional[str]:
    """Prompt user to choose a size system."""
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Size system")
    for s in _SIZE_SYSTEMS:
        gs.AddOption(Rhino.Input.Custom.OptionToggle(False, "No", "Yes"), s)
    gs.SetDefaultString("EU")
    gs.AcceptNothing(True)
    if gs.Get() == Rhino.Input.GetResult.String:
        val = gs.StringResult().strip()
        if val in _SIZE_SYSTEMS:
            return val
    return "EU"


def _prompt_float(prompt: str, default: float) -> Optional[float]:
    """Prompt the user for a floating point number."""
    gn = Rhino.Input.Custom.GetNumber()
    gn.SetCommandPrompt(prompt)
    gn.SetDefaultNumber(default)
    gn.AcceptNothing(True)
    if gn.Get() == Rhino.Input.GetResult.Number:
        return gn.Number()
    if gn.CommandResult() == Rhino.Commands.Result.Success:
        return default
    return None


def _prompt_string(prompt: str, default: str = "") -> Optional[str]:
    """Prompt the user for a string value."""
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt(prompt)
    if default:
        gs.SetDefaultString(default)
    gs.AcceptNothing(True)
    result = gs.Get()
    if result == Rhino.Input.GetResult.String:
        return gs.StringResult().strip()
    if gs.CommandResult() == Rhino.Commands.Result.Success:
        return default
    return None


def _build_last_from_settings(
    doc: Rhino.RhinoDoc, settings: DocumentSettings
) -> Optional[Rhino.Geometry.Brep]:
    """
    Build a parametric shoe last Brep from the given settings.

    This creates a simplified last shape by lofting cross-section curves
    derived from the last parameters (size, heel height, toe shape, etc.).
    The geometry is placed on the SLM::Last layer.
    """
    size_mm = settings.last_size
    heel_height = settings.last_heel_height_mm
    toe_shape = settings.last_toe_shape
    style = settings.last_style

    # Derive approximate last length from size (EU sizing: length_mm ~ size * 6.67)
    size_system = settings.last_size_system
    if size_system == "EU":
        length = size_mm * 6.67
    elif size_system == "US":
        length = (size_mm + 23.5) * 6.67
    elif size_system == "UK":
        length = (size_mm + 24.0) * 6.67
    else:  # Mondopoint
        length = size_mm

    if length <= 0:
        length = 260.0  # fallback

    # Derive width ~ 38% of length (typical proportion)
    width = length * 0.38
    height = length * 0.24

    # Build cross-section curves at intervals along the Y axis (heel to toe)
    sections: List[Rhino.Geometry.Curve] = []
    num_sections = 8
    for i in range(num_sections):
        t = i / (num_sections - 1)  # 0 = heel, 1 = toe
        y = t * length

        # Width varies along length
        if t < 0.15:
            # Heel region -- narrowing from back
            w = width * (0.55 + t * 2.0)
        elif t < 0.55:
            # Ball region -- widest
            w = width * (0.85 + 0.15 * math.sin((t - 0.15) / 0.4 * math.pi))
        else:
            # Toe region -- narrowing
            toe_factor = (1.0 - t) / 0.45
            if toe_shape == "Pointed":
                w = width * toe_factor ** 1.8
            elif toe_shape == "Square":
                w = width * max(toe_factor, 0.25)
            elif toe_shape == "Almond":
                w = width * toe_factor ** 1.3
            elif toe_shape == "Oblique":
                w = width * toe_factor ** 1.1
            else:  # Round
                w = width * toe_factor ** 1.4

        w = max(w, 2.0)

        # Height varies and includes heel lift
        heel_lift = heel_height * (1.0 - t) ** 2 if t < 0.6 else 0.0
        h = height * (0.6 + 0.4 * math.sin(t * math.pi)) + heel_lift
        h = max(h, 2.0)

        # Create an ellipse cross-section at this station
        plane = Rhino.Geometry.Plane(
            Rhino.Geometry.Point3d(0, y, heel_lift + h * 0.5),
            Rhino.Geometry.Vector3d.XAxis,
            Rhino.Geometry.Vector3d.ZAxis,
        )
        ellipse = Rhino.Geometry.Ellipse(plane, w * 0.5, h * 0.5)
        curve = ellipse.ToNurbsCurve()
        if curve is not None:
            sections.append(curve)

    if len(sections) < 2:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to generate last sections.")
        return None

    # Loft the sections
    breps = Rhino.Geometry.Brep.CreateFromLoft(
        sections,
        Rhino.Geometry.Point3d.Unset,
        Rhino.Geometry.Point3d.Unset,
        Rhino.Geometry.LoftType.Normal,
        False,
    )
    if not breps or len(breps) == 0:
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Loft operation failed.")
        return None

    # Cap the ends
    last_brep = breps[0].CapPlanarHoles(doc.ModelAbsoluteTolerance)
    if last_brep is None:
        last_brep = breps[0]

    return last_brep


def _add_last_to_doc(
    doc: Rhino.RhinoDoc,
    brep: Rhino.Geometry.Brep,
    name: str = "SLM_Last",
) -> System.Guid:
    """Add a last brep to the document on the correct layer."""
    layer_idx = _get_last_layer_index(doc)
    attrs = Rhino.DocObjects.ObjectAttributes()
    if layer_idx >= 0:
        attrs.LayerIndex = layer_idx
    attrs.Name = name
    guid = doc.Objects.AddBrep(brep, attrs)
    doc.Views.Redraw()
    return guid


# ---------------------------------------------------------------------------
#  NewBuild
# ---------------------------------------------------------------------------

class NewBuild(Rhino.Commands.Command):
    """Create a new shoe last build from interactively prompted parameters."""

    _instance: NewBuild | None = None

    def __init__(self):
        super().__init__()
        NewBuild._instance = self

    @classmethod
    @property
    def Instance(cls) -> NewBuild | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "NewBuild"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc).copy()

        # Prompt for key measurements
        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] New Last Build")
        Rhino.RhinoApp.WriteLine("Enter last measurements (press Enter for defaults):")

        # Size system
        sys_str = _prompt_string(
            f"Size system ({'/'.join(_SIZE_SYSTEMS)})",
            settings.last_size_system,
        )
        if sys_str is None:
            return Rhino.Commands.Result.Cancel
        if sys_str in _SIZE_SYSTEMS:
            settings.last_size_system = sys_str

        # Size
        size = _prompt_float(
            f"Last size ({settings.last_size_system})",
            settings.last_size if settings.last_size > 0 else 42.0,
        )
        if size is None:
            return Rhino.Commands.Result.Cancel
        settings.last_size = size

        # Heel height
        heel = _prompt_float("Heel height (mm)", settings.last_heel_height_mm)
        if heel is None:
            return Rhino.Commands.Result.Cancel
        settings.last_heel_height_mm = heel

        # Toe shape
        toe = _prompt_string(
            f"Toe shape ({'/'.join(_TOE_SHAPES)})",
            settings.last_toe_shape,
        )
        if toe is None:
            return Rhino.Commands.Result.Cancel
        if toe in _TOE_SHAPES:
            settings.last_toe_shape = toe

        # Style
        style = _prompt_string(
            f"Last style ({'/'.join(_LAST_STYLES)})",
            settings.last_style,
        )
        if style is None:
            return Rhino.Commands.Result.Cancel
        if style in _LAST_STYLES:
            settings.last_style = style

        # Width
        width = _prompt_string("Width designation (e.g. D, E, EE)", settings.last_width or "D")
        if width is None:
            return Rhino.Commands.Result.Cancel
        settings.last_width = width

        # Symmetry
        sym = _prompt_string("Symmetry (Right/Left/Symmetric)", settings.last_symmetry)
        if sym is None:
            return Rhino.Commands.Result.Cancel
        if sym in ("Right", "Left", "Symmetric"):
            settings.last_symmetry = sym

        # Build the last
        Rhino.RhinoApp.WriteLine("Building last geometry...")
        brep = _build_last_from_settings(doc, settings)
        if brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to build last.")
            return Rhino.Commands.Result.Failure

        # Mirror for left foot if needed
        if settings.last_symmetry == "Left":
            mirror_plane = Rhino.Geometry.Plane(
                Rhino.Geometry.Point3d.Origin,
                Rhino.Geometry.Vector3d.YAxis,
                Rhino.Geometry.Vector3d.ZAxis,
            )
            xform = Rhino.Geometry.Transform.Mirror(mirror_plane)
            brep.Transform(xform)

        guid = _add_last_to_doc(doc, brep)
        if guid == System.Guid.Empty:
            return Rhino.Commands.Result.Failure

        # Store settings
        plug.SetDocumentSettings(doc, settings)
        plug.StoreGeometry(doc, "LastBrep", brep)
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Last built: size {settings.last_size} "
            f"{settings.last_size_system}, heel {settings.last_heel_height_mm}mm, "
            f"{settings.last_toe_shape} toe, {settings.last_style} style."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  NewBuildScriptable
# ---------------------------------------------------------------------------

class NewBuildScriptable(Rhino.Commands.Command):
    """
    Scriptable (non-interactive) version of NewBuild.

    Accepts parameters via command-line options so it can be called from
    scripts and macros without user prompts.
    """

    _instance: NewBuildScriptable | None = None

    def __init__(self):
        super().__init__()
        NewBuildScriptable._instance = self

    @classmethod
    @property
    def Instance(cls) -> NewBuildScriptable | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "NewBuildScriptable"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc).copy()

        # Use GetString with options to collect all parameters in one go
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("NewBuildScriptable")
        gs.AcceptNothing(True)

        opt_size = Rhino.Input.Custom.OptionDouble(settings.last_size if settings.last_size > 0 else 42.0)
        opt_heel = Rhino.Input.Custom.OptionDouble(settings.last_heel_height_mm)
        opt_system = Rhino.Input.Custom.OptionToggle(
            settings.last_size_system == "US", "EU", "US"
        )

        gs.AddOptionDouble("Size", opt_size)
        gs.AddOptionDouble("HeelHeight", opt_heel)
        gs.AddOptionToggle("SizeSystem", opt_system)

        while True:
            result = gs.Get()
            if result == Rhino.Input.GetResult.Option:
                continue
            break

        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return gs.CommandResult()

        settings.last_size = opt_size.CurrentValue
        settings.last_heel_height_mm = opt_heel.CurrentValue
        settings.last_size_system = "US" if opt_system.CurrentValue else "EU"

        brep = _build_last_from_settings(doc, settings)
        if brep is None:
            return Rhino.Commands.Result.Failure

        guid = _add_last_to_doc(doc, brep)
        if guid == System.Guid.Empty:
            return Rhino.Commands.Result.Failure

        plug.SetDocumentSettings(doc, settings)
        plug.StoreGeometry(doc, "LastBrep", brep)
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Scriptable build complete: size {settings.last_size} "
            f"{settings.last_size_system}."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  UpdateLast
# ---------------------------------------------------------------------------

class UpdateLast(Rhino.Commands.Command):
    """Update existing last geometry after parameter changes."""

    _instance: UpdateLast | None = None

    def __init__(self):
        super().__init__()
        UpdateLast._instance = self

    @classmethod
    @property
    def Instance(cls) -> UpdateLast | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "UpdateLast"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)

        # Find and remove old last objects
        old_objs = _find_last_objects(doc)
        if not old_objs:
            Rhino.RhinoApp.WriteLine(
                "[Feet in Focus Shoe Kit] No existing last found. Use NewBuild first."
            )
            return Rhino.Commands.Result.Failure

        for obj in old_objs:
            doc.Objects.Delete(obj, True)

        # Rebuild with current settings
        brep = _build_last_from_settings(doc, settings)
        if brep is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to rebuild last.")
            return Rhino.Commands.Result.Failure

        if settings.last_symmetry == "Left":
            mirror_plane = Rhino.Geometry.Plane(
                Rhino.Geometry.Point3d.Origin,
                Rhino.Geometry.Vector3d.YAxis,
                Rhino.Geometry.Vector3d.ZAxis,
            )
            xform = Rhino.Geometry.Transform.Mirror(mirror_plane)
            brep.Transform(xform)

        guid = _add_last_to_doc(doc, brep)
        if guid == System.Guid.Empty:
            return Rhino.Commands.Result.Failure

        plug.StoreGeometry(doc, "LastBrep", brep)
        plug.MarkDocumentDirty()

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Last geometry updated.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  ImportLast
# ---------------------------------------------------------------------------

class ImportLast(Rhino.Commands.Command):
    """Import a last from file (3dm, STEP, IGES, STL)."""

    _instance: ImportLast | None = None

    def __init__(self):
        super().__init__()
        ImportLast._instance = self

    @classmethod
    @property
    def Instance(cls) -> ImportLast | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ImportLast"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        # Prompt for file path
        fd = Rhino.Input.Custom.GetString()
        fd.SetCommandPrompt("Path to last file (3dm, STEP, IGES, STL)")
        fd.Get()
        if fd.CommandResult() != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        file_path = fd.StringResult().strip().strip('"')
        if not file_path or not os.path.isfile(file_path):
            # Try the Rhino open file dialog
            dialog = Rhino.UI.OpenFileDialog()
            dialog.Title = "Import Last"
            dialog.Filter = _IMPORT_FILTER
            if not dialog.ShowOpenDialog():
                return Rhino.Commands.Result.Cancel
            file_path = dialog.FileName

        if not os.path.isfile(file_path):
            Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] File not found: {file_path}")
            return Rhino.Commands.Result.Failure

        ext = os.path.splitext(file_path)[1].lower()
        layer_idx = _get_last_layer_index(doc)

        Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Importing last from: {file_path}")

        imported_count = 0
        if ext == ".3dm":
            # Read 3dm file and import geometry
            file3dm = Rhino.FileIO.File3dm.Read(file_path)
            if file3dm is None:
                Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Failed to read 3dm file.")
                return Rhino.Commands.Result.Failure
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
            script = f'_-Import "{file_path}" _Enter'
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
                f"[Feet in Focus Shoe Kit] Unsupported file format: {ext}"
            )
            return Rhino.Commands.Result.Failure

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Imported {imported_count} object(s) from {os.path.basename(file_path)}."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  ExportLast
# ---------------------------------------------------------------------------

class ExportLast(Rhino.Commands.Command):
    """Export last to file."""

    _instance: ExportLast | None = None

    def __init__(self):
        super().__init__()
        ExportLast._instance = self

    @classmethod
    @property
    def Instance(cls) -> ExportLast | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ExportLast"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        last_objs = _find_last_objects(doc)
        if not last_objs:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry to export.")
            return Rhino.Commands.Result.Failure

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
                return Rhino.Commands.Result.Cancel
            file_path = dialog.FileName

        if not file_path:
            return Rhino.Commands.Result.Cancel

        ext = os.path.splitext(file_path)[1].lower()

        # Select last objects for export
        doc.Objects.UnselectAll()
        for obj in last_objs:
            doc.Objects.Select(obj.Id, True)

        Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Exporting last to: {file_path}")

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
            script = f'_-Export "{file_path}" _Enter'
            Rhino.RhinoApp.RunScript(script, False)

        doc.Objects.UnselectAll()
        doc.Views.Redraw()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Last exported: {os.path.basename(file_path)}"
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  GradeLast
# ---------------------------------------------------------------------------

class GradeLast(Rhino.Commands.Command):
    """Grade (size) the last to a different size."""

    _instance: GradeLast | None = None

    def __init__(self):
        super().__init__()
        GradeLast._instance = self

    @classmethod
    @property
    def Instance(cls) -> GradeLast | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "GradeLast"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)

        current_size = settings.last_size
        if current_size <= 0:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No current last size set. Build a last first.")
            return Rhino.Commands.Result.Failure

        # Prompt for target size
        target = _prompt_float(
            f"Target size ({settings.last_size_system}, current={current_size})",
            current_size,
        )
        if target is None or target <= 0:
            return Rhino.Commands.Result.Cancel

        if abs(target - current_size) < 0.001:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Target size is the same as current. No change.")
            return Rhino.Commands.Result.Nothing

        # Calculate scale factor
        scale_factor = target / current_size

        # Length scales linearly with size; width/height scale at ~85% of length
        scale_x = 1.0 + (scale_factor - 1.0) * 0.85  # width
        scale_y = scale_factor                          # length
        scale_z = 1.0 + (scale_factor - 1.0) * 0.85   # height

        xform = Rhino.Geometry.Transform.Scale(
            Rhino.Geometry.Plane.WorldXY,
            scale_x,
            scale_y,
            scale_z,
        )

        last_objs = _find_last_objects(doc)
        if not last_objs:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last objects found to grade.")
            return Rhino.Commands.Result.Failure

        for obj in last_objs:
            doc.Objects.Transform(obj, xform, True)

        # Update settings
        settings.last_size = target
        plug.SetDocumentSettings(doc, settings)
        plug.MarkDocumentDirty()

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Last graded from size {current_size} to {target} "
            f"({settings.last_size_system}). Scale factor: {scale_factor:.4f}"
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  FlattenLast
# ---------------------------------------------------------------------------

class FlattenLast(Rhino.Commands.Command):
    """Flatten last bottom to a 2D pattern."""

    _instance: FlattenLast | None = None

    def __init__(self):
        super().__init__()
        FlattenLast._instance = self

    @classmethod
    @property
    def Instance(cls) -> FlattenLast | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "FlattenLast"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        last_objs = _find_last_objects(doc)
        if not last_objs:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No last geometry found.")
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Flattening last bottom...")

        # Find brep objects among the last objects
        breps: List[Rhino.Geometry.Brep] = []
        for obj in last_objs:
            geom = obj.Geometry
            if isinstance(geom, Rhino.Geometry.Brep):
                breps.append(geom)
            elif isinstance(geom, Rhino.Geometry.Mesh):
                b = Rhino.Geometry.Brep.CreateFromMesh(geom, True)
                if b is not None:
                    breps.append(b)

        if not breps:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No suitable geometry to flatten.")
            return Rhino.Commands.Result.Failure

        # Create a cutting plane at Z=0
        cut_plane = Rhino.Geometry.Plane.WorldXY
        tol = doc.ModelAbsoluteTolerance

        pattern_curves: List[Rhino.Geometry.Curve] = []
        for brep in breps:
            # Intersect the brep with the XY plane
            intersections = Rhino.Geometry.Brep.CreateContourCurves(
                brep,
                cut_plane.Origin,
                cut_plane.Origin + Rhino.Geometry.Vector3d.ZAxis,
                tol,
            )
            if intersections:
                for curve in intersections:
                    # Project to Z=0
                    projected = Rhino.Geometry.Curve.ProjectToPlane(
                        curve, Rhino.Geometry.Plane.WorldXY
                    )
                    if projected is not None:
                        pattern_curves.append(projected)

        if not pattern_curves:
            # Fallback: project the bottom outline
            for brep in breps:
                bbox = brep.GetBoundingBox(True)
                z_min = bbox.Min.Z
                section_plane = Rhino.Geometry.Plane(
                    Rhino.Geometry.Point3d(0, 0, z_min + tol),
                    Rhino.Geometry.Vector3d.ZAxis,
                )
                sections = Rhino.Geometry.Brep.CreateContourCurves(
                    brep,
                    section_plane.Origin,
                    section_plane.Origin + Rhino.Geometry.Vector3d.ZAxis,
                    tol,
                )
                if sections:
                    for curve in sections:
                        projected = Rhino.Geometry.Curve.ProjectToPlane(
                            curve, Rhino.Geometry.Plane.WorldXY
                        )
                        if projected is not None:
                            pattern_curves.append(projected)

        if not pattern_curves:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Could not generate flatten pattern.")
            return Rhino.Commands.Result.Failure

        # Add pattern curves to the Construction layer
        construction_path = f"{plugin_constants.SLM_LAYER_PREFIX}::Construction"
        layer_idx = doc.Layers.FindByFullPath(construction_path, -1)
        attrs = Rhino.DocObjects.ObjectAttributes()
        if layer_idx >= 0:
            attrs.LayerIndex = layer_idx
        attrs.Name = "SLM_FlattenPattern"

        for curve in pattern_curves:
            doc.Objects.AddCurve(curve, attrs)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Flatten complete. {len(pattern_curves)} pattern curve(s) added."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  GazeAtLast
# ---------------------------------------------------------------------------

class GazeAtLast(Rhino.Commands.Command):
    """Set viewport to look at last from standard angles."""

    _instance: GazeAtLast | None = None

    def __init__(self):
        super().__init__()
        GazeAtLast._instance = self

    @classmethod
    @property
    def Instance(cls) -> GazeAtLast | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "GazeAtLast"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        # Select view angle
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("View angle")
        for name in _VIEW_ANGLES:
            gs.AddOption(Rhino.Input.Custom.OptionToggle(False, "No", "Yes"), name)
        gs.SetDefaultString("Perspective")
        gs.AcceptNothing(True)

        result = gs.Get()
        view_name = "Perspective"
        if result == Rhino.Input.GetResult.String:
            user_val = gs.StringResult().strip()
            if user_val in _VIEW_ANGLES:
                view_name = user_val
        elif result == Rhino.Input.GetResult.Option:
            view_name = gs.Option().EnglishName

        if gs.CommandResult() != Rhino.Commands.Result.Success:
            if result != Rhino.Input.GetResult.Option:
                return Rhino.Commands.Result.Cancel

        camera, target = _VIEW_ANGLES[view_name]

        # Adjust target to center of last bounding box if a last exists
        last_objs = _find_last_objects(doc)
        if last_objs:
            bbox = Rhino.Geometry.BoundingBox.Empty
            for obj in last_objs:
                obj_bbox = obj.Geometry.GetBoundingBox(True)
                bbox.Union(obj_bbox)
            if bbox.IsValid:
                center = bbox.Center
                offset = center - target
                target = center
                camera = camera + offset

        # Apply to the active viewport
        view = doc.Views.ActiveView
        if view is None:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No active view.")
            return Rhino.Commands.Result.Failure

        vp = view.ActiveViewport
        vp.SetCameraTarget(target, True)
        vp.SetCameraLocation(camera, True)
        vp.Camera35mmLensLength = 50.0
        view.Redraw()

        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] View set to '{view_name}'."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  ChangeLastParameterization
# ---------------------------------------------------------------------------

class ChangeLastParameterization(Rhino.Commands.Command):
    """Open dialog to modify last parameters."""

    _instance: ChangeLastParameterization | None = None

    def __init__(self):
        super().__init__()
        ChangeLastParameterization._instance = self

    @classmethod
    @property
    def Instance(cls) -> ChangeLastParameterization | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ChangeLastParameterization"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Current Last Parameters:")
        Rhino.RhinoApp.WriteLine(f"  Size: {settings.last_size} {settings.last_size_system}")
        Rhino.RhinoApp.WriteLine(f"  Width: {settings.last_width}")
        Rhino.RhinoApp.WriteLine(f"  Heel Height: {settings.last_heel_height_mm} mm")
        Rhino.RhinoApp.WriteLine(f"  Toe Shape: {settings.last_toe_shape}")
        Rhino.RhinoApp.WriteLine(f"  Style: {settings.last_style}")
        Rhino.RhinoApp.WriteLine(f"  Symmetry: {settings.last_symmetry}")

        # Interactive parameter modification via GetString with options
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Select parameter to modify (or Enter to finish)")
        gs.AcceptNothing(True)

        opt_size = Rhino.Input.Custom.OptionDouble(settings.last_size)
        opt_heel = Rhino.Input.Custom.OptionDouble(settings.last_heel_height_mm)

        gs.AddOptionDouble("Size", opt_size)
        gs.AddOptionDouble("HeelHeight", opt_heel)

        changed = False
        while True:
            result = gs.Get()
            if result == Rhino.Input.GetResult.Option:
                changed = True
                continue
            elif result == Rhino.Input.GetResult.String:
                val = gs.StringResult().strip()
                if val:
                    # Allow setting toe shape or style by typing it
                    if val in _TOE_SHAPES:
                        settings.last_toe_shape = val
                        changed = True
                        Rhino.RhinoApp.WriteLine(f"  Toe shape set to: {val}")
                        continue
                    if val in _LAST_STYLES:
                        settings.last_style = val
                        changed = True
                        Rhino.RhinoApp.WriteLine(f"  Style set to: {val}")
                        continue
                break
            else:
                break

        if changed:
            settings.last_size = opt_size.CurrentValue
            settings.last_heel_height_mm = opt_heel.CurrentValue
            plug.SetDocumentSettings(doc, settings)
            plug.MarkDocumentDirty()
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Parameters updated. Run UpdateLast to rebuild.")
        else:
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] No changes made.")

        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  ExportLastParameters
# ---------------------------------------------------------------------------

class ExportLastParameters(Rhino.Commands.Command):
    """Export parameters to JSON."""

    _instance: ExportLastParameters | None = None

    def __init__(self):
        super().__init__()
        ExportLastParameters._instance = self

    @classmethod
    @property
    def Instance(cls) -> ExportLastParameters | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ExportLastParameters"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)

        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Export JSON file path")
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        file_path = gs.StringResult().strip().strip('"')
        if not file_path:
            return Rhino.Commands.Result.Cancel

        if not file_path.lower().endswith(".json"):
            file_path += ".json"

        try:
            data = settings.to_dict()
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2, sort_keys=True)
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] Parameters exported to: {file_path}"
            )
            return Rhino.Commands.Result.Success
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Export error: {ex}")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  ImportParameters
# ---------------------------------------------------------------------------

class ImportParameters(Rhino.Commands.Command):
    """Import parameters from JSON."""

    _instance: ImportParameters | None = None

    def __init__(self):
        super().__init__()
        ImportParameters._instance = self

    @classmethod
    @property
    def Instance(cls) -> ImportParameters | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ImportParameters"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("JSON file path to import")
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        file_path = gs.StringResult().strip().strip('"')
        if not file_path or not os.path.isfile(file_path):
            Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] File not found: {file_path}")
            return Rhino.Commands.Result.Failure

        try:
            with open(file_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            imported_settings = DocumentSettings.from_dict(data)

            plug = _get_plugin()
            current = plug.GetDocumentSettings(doc)
            current.merge(imported_settings)
            plug.SetDocumentSettings(doc, current)
            plug.MarkDocumentDirty()

            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] Parameters imported from: {file_path}"
            )
            Rhino.RhinoApp.WriteLine("  Run UpdateLast to apply changes to geometry.")
            return Rhino.Commands.Result.Success
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Import error: {ex}")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  ExportMeasurementEquations
# ---------------------------------------------------------------------------

class ExportMeasurementEquations(Rhino.Commands.Command):
    """Export measurement equations."""

    _instance: ExportMeasurementEquations | None = None

    def __init__(self):
        super().__init__()
        ExportMeasurementEquations._instance = self

    @classmethod
    @property
    def Instance(cls) -> ExportMeasurementEquations | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ExportMeasurementEquations"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()
        settings = plug.GetDocumentSettings(doc)

        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Export equations file path (JSON)")
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        file_path = gs.StringResult().strip().strip('"')
        if not file_path:
            return Rhino.Commands.Result.Cancel

        if not file_path.lower().endswith(".json"):
            file_path += ".json"

        # Compute measurement equations from current settings
        size = settings.last_size
        size_system = settings.last_size_system

        if size_system == "EU":
            foot_length = size * 6.67
        elif size_system == "US":
            foot_length = (size + 23.5) * 6.67
        elif size_system == "UK":
            foot_length = (size + 24.0) * 6.67
        else:
            foot_length = size

        equations = {
            "size": size,
            "size_system": size_system,
            "foot_length_mm": round(foot_length, 2),
            "ball_width_mm": round(foot_length * 0.38, 2),
            "ball_girth_mm": round(foot_length * 0.38 * math.pi, 2),
            "waist_girth_mm": round(foot_length * 0.30 * math.pi, 2),
            "instep_girth_mm": round(foot_length * 0.34 * math.pi, 2),
            "heel_girth_mm": round(foot_length * 0.32 * math.pi + settings.last_heel_height_mm * 0.5, 2),
            "toe_spring_mm": round(foot_length * 0.04, 2),
            "heel_height_mm": settings.last_heel_height_mm,
            "cone_angle_deg": settings.last_cone_angle_degrees,
            "stick_length_mm": round(foot_length * 1.02, 2),
            "last_length_mm": round(foot_length * 1.03, 2),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(equations, fp, indent=2)
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] Measurement equations exported to: {file_path}"
            )
            return Rhino.Commands.Result.Success
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Export error: {ex}")
            return Rhino.Commands.Result.Failure


# ---------------------------------------------------------------------------
#  NameObjectsInDoc
# ---------------------------------------------------------------------------

class NameObjectsInDoc(Rhino.Commands.Command):
    """Name all objects in document with standardized names."""

    _instance: NameObjectsInDoc | None = None

    def __init__(self):
        super().__init__()
        NameObjectsInDoc._instance = self

    @classmethod
    @property
    def Instance(cls) -> NameObjectsInDoc | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "NameObjectsInDoc"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        prefix = plugin_constants.SLM_LAYER_PREFIX
        named_count = 0

        # Iterate all objects and assign standardized names based on layer
        enum_settings = Rhino.DocObjects.ObjectEnumeratorSettings()
        enum_settings.DeletedObjects = False
        enum_settings.HiddenObjects = True
        enum_settings.LockedObjects = True

        for obj in doc.Objects.GetObjectList(enum_settings):
            layer = doc.Layers[obj.Attributes.LayerIndex]
            full_path = layer.FullPath

            if not full_path.startswith(prefix):
                continue

            # Derive category from layer path
            parts = full_path.split("::")
            category = parts[-1] if len(parts) > 1 else prefix

            # Build a standardized name: SLM_{Category}_{TypeAbbrev}_{Index}
            geom = obj.Geometry
            if isinstance(geom, Rhino.Geometry.Brep):
                type_abbrev = "Brep"
            elif isinstance(geom, Rhino.Geometry.Mesh):
                type_abbrev = "Mesh"
            elif isinstance(geom, Rhino.Geometry.Curve):
                type_abbrev = "Crv"
            elif isinstance(geom, Rhino.Geometry.Surface):
                type_abbrev = "Srf"
            elif isinstance(geom, Rhino.Geometry.Point):
                type_abbrev = "Pt"
            else:
                type_abbrev = "Obj"

            new_name = f"SLM_{category}_{type_abbrev}_{named_count:04d}"
            attrs = obj.Attributes.Duplicate()
            attrs.Name = new_name
            doc.Objects.ModifyAttributes(obj, attrs, True)
            named_count += 1

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"[Feet in Focus Shoe Kit] Named {named_count} object(s) with standardized names."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  GetObjectIDName
# ---------------------------------------------------------------------------

class GetObjectIDName(Rhino.Commands.Command):
    """Get the name/ID of a selected object."""

    _instance: GetObjectIDName | None = None

    def __init__(self):
        super().__init__()
        GetObjectIDName._instance = self

    @classmethod
    @property
    def Instance(cls) -> GetObjectIDName | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "GetObjectIDName"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        # Prompt user to select an object
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select object to identify")
        go.GeometryFilter = Rhino.DocObjects.ObjectType.AnyObject
        go.Get()
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        obj_ref = go.Object(0)
        obj = obj_ref.Object()
        if obj is None:
            return Rhino.Commands.Result.Failure

        obj_id = obj.Id
        obj_name = obj.Attributes.Name or "(unnamed)"
        layer = doc.Layers[obj.Attributes.LayerIndex]
        layer_name = layer.FullPath

        geom = obj.Geometry
        geom_type = type(geom).__name__ if geom else "Unknown"

        Rhino.RhinoApp.WriteLine(f"[Feet in Focus Shoe Kit] Object Info:")
        Rhino.RhinoApp.WriteLine(f"  ID:    {obj_id}")
        Rhino.RhinoApp.WriteLine(f"  Name:  {obj_name}")
        Rhino.RhinoApp.WriteLine(f"  Layer: {layer_name}")
        Rhino.RhinoApp.WriteLine(f"  Type:  {geom_type}")

        if isinstance(geom, Rhino.Geometry.Brep):
            Rhino.RhinoApp.WriteLine(
                f"  Faces: {geom.Faces.Count}, Edges: {geom.Edges.Count}"
            )
        elif isinstance(geom, Rhino.Geometry.Mesh):
            Rhino.RhinoApp.WriteLine(
                f"  Vertices: {geom.Vertices.Count}, Faces: {geom.Faces.Count}"
            )

        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  Establish
# ---------------------------------------------------------------------------

class Establish(Rhino.Commands.Command):
    """Establish/initialize a new shoe last project."""

    _instance: Establish | None = None

    def __init__(self):
        super().__init__()
        Establish._instance = self

    @classmethod
    @property
    def Instance(cls) -> Establish | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "Establish"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        plug = _get_plugin()

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Establishing new shoe last project...")

        # Prompt for project name
        project_name = _prompt_string("Project name", "")
        if project_name is None:
            return Rhino.Commands.Result.Cancel

        # Prompt for customer name
        customer_name = _prompt_string("Customer name", "")
        if customer_name is None:
            return Rhino.Commands.Result.Cancel

        # Prompt for foot side
        side = _prompt_string("Foot side (Right/Left)", "Right")
        if side is None:
            return Rhino.Commands.Result.Cancel
        if side not in ("Right", "Left"):
            side = "Right"

        # Set up layers
        plug.SetupLayers(doc)
        plug.SetRendering(doc)
        plug.PopulatePerspectiveView(doc)
        plug.PopulateClasses(doc)

        # Initialize document settings
        settings = DocumentSettings.Create(
            project_name=project_name or "",
            customer_name=customer_name or "",
            foot_side=side,
            last_symmetry=side,
            saved_with_version=plug.plugin_version,
        )
        plug.SetDocumentSettings(doc, settings)
        plug.MarkDocumentDirty()

        # Set document units to millimeters
        doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
        doc.ModelAbsoluteTolerance = 0.01
        doc.ModelRelativeTolerance = 0.01
        doc.ModelAngleToleranceDegrees = 1.0

        doc.Views.Redraw()

        Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Project established:")
        Rhino.RhinoApp.WriteLine(f"  Project: {project_name or '(unnamed)'}")
        Rhino.RhinoApp.WriteLine(f"  Customer: {customer_name or '(none)'}")
        Rhino.RhinoApp.WriteLine(f"  Side: {side}")
        Rhino.RhinoApp.WriteLine("  Layers, rendering, and views configured.")
        Rhino.RhinoApp.WriteLine("  Use NewBuild to create a shoe last.")
        return Rhino.Commands.Result.Success
