"""
Feet in Focus Shoe Kit Rhino 8 Plugin - Grading (size scaling) commands.

Commands:
    GradeFootwear - Grades complete footwear to a different size using
                    GradeFootwearForm for interactive UI.
    BatchGrade    - Batch grades footwear to multiple sizes at once.
"""

from __future__ import annotations

import json
import math
import traceback
from typing import Any, Dict, List, Optional, Tuple

import Rhino  # type: ignore
import Rhino.Commands  # type: ignore
import Rhino.DocObjects  # type: ignore
import Rhino.Geometry  # type: ignore
import Rhino.Input  # type: ignore
import Rhino.Input.Custom  # type: ignore
import Rhino.RhinoApp  # type: ignore
import Rhino.RhinoDoc  # type: ignore
import scriptcontext as sc  # type: ignore
import System  # type: ignore

import plugin as plugin_constants
from plugin.plugin_main import PodoCADPlugIn


# ---------------------------------------------------------------------------
#  Grading helpers
# ---------------------------------------------------------------------------

# Standard EU size grading increment (mm) per full size step.
_EU_GRADE_INCREMENT_LENGTH = 6.667
_EU_GRADE_INCREMENT_WIDTH = 1.5
_EU_GRADE_INCREMENT_GIRTH = 5.0

# Size-system conversion tables (base size -> mm stick length).
_SIZE_SYSTEMS: Dict[str, Dict[str, float]] = {
    "EU": {"base_size": 40.0, "base_stick_length": 260.0,
           "increment": _EU_GRADE_INCREMENT_LENGTH},
    "US": {"base_size": 8.0, "base_stick_length": 260.0,
           "increment": 8.467},
    "UK": {"base_size": 7.0, "base_stick_length": 260.0,
           "increment": 8.467},
    "Mondopoint": {"base_size": 260.0, "base_stick_length": 260.0,
                   "increment": 5.0},
}


def _compute_scale_factor(
    from_size: float,
    to_size: float,
    size_system: str,
) -> float:
    """Return the uniform length scale factor for grading between two sizes."""
    info = _SIZE_SYSTEMS.get(size_system, _SIZE_SYSTEMS["EU"])
    from_length = info["base_stick_length"] + (from_size - info["base_size"]) * info["increment"]
    to_length = info["base_stick_length"] + (to_size - info["base_size"]) * info["increment"]
    if abs(from_length) < 1e-9:
        return 1.0
    return to_length / from_length


def _compute_girth_delta(
    from_size: float,
    to_size: float,
) -> float:
    """Return the girth adjustment (mm) when grading between sizes."""
    return (to_size - from_size) * _EU_GRADE_INCREMENT_GIRTH


def _build_grade_transform(
    scale_factor: float,
    origin: Rhino.Geometry.Point3d,
) -> Rhino.Geometry.Transform:
    """Build a uniform scale transform about *origin*."""
    xform = Rhino.Geometry.Transform.Scale(origin, scale_factor)
    return xform


def _find_objects_by_name_prefix(
    doc: Rhino.RhinoDoc,
    prefix: str,
) -> List[Rhino.DocObjects.RhinoObject]:
    """Return all doc objects whose name starts with *prefix*."""
    results: List[Rhino.DocObjects.RhinoObject] = []
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.DeletedObjects = False
    settings.HiddenObjects = True
    settings.LockedObjects = True
    for obj in doc.Objects.GetObjectList(settings):
        name = obj.Attributes.Name or ""
        if name.startswith(prefix):
            results.append(obj)
    return results


def _find_objects_on_layer(
    doc: Rhino.RhinoDoc,
    layer_name: str,
) -> List[Rhino.DocObjects.RhinoObject]:
    """Return all doc objects residing on *layer_name*."""
    layer_index = doc.Layers.FindByFullPath(layer_name, -1)
    if layer_index < 0:
        # Try without prefix
        for i in range(doc.Layers.Count):
            lyr = doc.Layers[i]
            if not lyr.IsDeleted and lyr.Name == layer_name:
                layer_index = i
                break
    if layer_index < 0:
        return []
    layer = doc.Layers[layer_index]
    objs = doc.Objects.FindByLayer(layer)
    return list(objs) if objs else []


# ---------------------------------------------------------------------------
#  GradeFootwear
# ---------------------------------------------------------------------------

class GradeFootwear(Rhino.Commands.Command):
    """Grade complete footwear to a different size.

    Uses GradeFootwearForm for interactive UI.  Supports grading of insole,
    outline, third-party insole, and general geometries.  Updates CBG (ball
    girth) and CIG (instep girth) measurements during the grading process.
    """

    _instance: GradeFootwear | None = None

    def __init__(self):
        super().__init__()
        GradeFootwear._instance = self

    @classmethod
    @property
    def Instance(cls) -> GradeFootwear | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "GradeFootwear"

    # -- Core grading methods -----------------------------------------------

    def OrientationAndSettings(
        self, doc: Rhino.RhinoDoc
    ) -> Tuple[Rhino.Geometry.Point3d, str, float, float]:
        """Retrieve the current orientation origin, size system, and sizes
        from the document settings.

        Returns (origin, size_system, current_size, target_size).
        """
        plug = PodoCADPlugIn.instance()
        ds = plug.GetDocumentSettings(doc)

        origin = Rhino.Geometry.Point3d.Origin
        # Try to locate the heel-centre point stored on the document
        heel_id = plug.GetIDFromDocObjectName(doc, "HeelCentre")
        if heel_id is not None:
            obj = doc.Objects.FindId(heel_id)
            if obj is not None:
                pt_geom = obj.Geometry
                if isinstance(pt_geom, Rhino.Geometry.Point):
                    origin = pt_geom.Location
                elif hasattr(pt_geom, "PointAtStart"):
                    origin = pt_geom.PointAtStart

        size_system = ds.get("last_size_system", "EU")
        current_size = ds.get("last_size", 40.0)
        return origin, size_system, current_size, current_size

    def GradeInsole(
        self,
        doc: Rhino.RhinoDoc,
        scale_factor: float,
        origin: Rhino.Geometry.Point3d,
    ) -> bool:
        """Scale all insole geometry by *scale_factor* about *origin*."""
        xform = _build_grade_transform(scale_factor, origin)
        objs = _find_objects_by_name_prefix(doc, "Insole")
        if not objs:
            Rhino.RhinoApp.WriteLine("  No insole objects found to grade.")
            return False
        for obj in objs:
            doc.Objects.Transform(obj, xform, True)
        Rhino.RhinoApp.WriteLine(f"  Graded {len(objs)} insole object(s).")
        return True

    def GradeOutline(
        self,
        doc: Rhino.RhinoDoc,
        scale_factor: float,
        origin: Rhino.Geometry.Point3d,
    ) -> bool:
        """Scale all outline/last-outline curves by *scale_factor*."""
        xform = _build_grade_transform(scale_factor, origin)
        objs = _find_objects_by_name_prefix(doc, "Outline")
        objs += _find_objects_by_name_prefix(doc, "LastOutline")
        if not objs:
            Rhino.RhinoApp.WriteLine("  No outline objects found to grade.")
            return False
        for obj in objs:
            doc.Objects.Transform(obj, xform, True)
        Rhino.RhinoApp.WriteLine(f"  Graded {len(objs)} outline object(s).")
        return True

    def GradeOtherPartyInsole(
        self,
        doc: Rhino.RhinoDoc,
        scale_factor: float,
        origin: Rhino.Geometry.Point3d,
    ) -> bool:
        """Scale third-party insole geometry if present."""
        xform = _build_grade_transform(scale_factor, origin)
        objs = _find_objects_by_name_prefix(doc, "OtherPartyInsole")
        objs += _find_objects_by_name_prefix(doc, "ThirdPartyInsole")
        if not objs:
            return False
        for obj in objs:
            doc.Objects.Transform(obj, xform, True)
        Rhino.RhinoApp.WriteLine(
            f"  Graded {len(objs)} third-party insole object(s)."
        )
        return True

    def GradeGeomtries(
        self,
        doc: Rhino.RhinoDoc,
        scale_factor: float,
        origin: Rhino.Geometry.Point3d,
    ) -> bool:
        """Scale all remaining SLM-layer geometry by *scale_factor*."""
        xform = _build_grade_transform(scale_factor, origin)
        layer_name = f"{plugin_constants.SLM_LAYER_PREFIX}"
        graded_count = 0

        for cls in plugin_constants.ALL_CLASSES:
            full_path = f"{layer_name}::{cls}"
            objs = _find_objects_on_layer(doc, full_path)
            for obj in objs:
                doc.Objects.Transform(obj, xform, True)
                graded_count += 1

        if graded_count:
            Rhino.RhinoApp.WriteLine(
                f"  Graded {graded_count} general geometry object(s)."
            )
        return graded_count > 0

    def TransformGeomtries(
        self,
        doc: Rhino.RhinoDoc,
        xform: Rhino.Geometry.Transform,
        object_ids: List[System.Guid],
    ) -> int:
        """Apply an arbitrary transform to a list of objects by ID.

        Returns the number of objects successfully transformed.
        """
        count = 0
        for oid in object_ids:
            obj = doc.Objects.FindId(oid)
            if obj is not None:
                if doc.Objects.Transform(obj, xform, True):
                    count += 1
        return count

    def _update_girth_measurements(
        self,
        doc: Rhino.RhinoDoc,
        from_size: float,
        to_size: float,
    ) -> None:
        """Update CBG (ball girth) and CIG (instep girth) values stored
        in the document settings after grading."""
        plug = PodoCADPlugIn.instance()
        ds = plug.GetDocumentSettings(doc)
        delta = _compute_girth_delta(from_size, to_size)

        cbg = ds.get("cbg_ball_girth", 0.0)
        cig = ds.get("cig_instep_girth", 0.0)

        if cbg:
            ds.set("cbg_ball_girth", cbg + delta)
        if cig:
            ds.set("cig_instep_girth", cig + delta)

        plug.SetDocumentSettings(doc, ds)
        Rhino.RhinoApp.WriteLine(
            f"  Updated girth measurements: CBG delta={delta:+.2f} mm, "
            f"CIG delta={delta:+.2f} mm"
        )

    # -- RunCommand ---------------------------------------------------------

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)
        current_size = ds.get("last_size", 0.0)
        size_system = ds.get("last_size_system", "EU")

        if current_size <= 0:
            Rhino.RhinoApp.WriteLine(
                "No current size is set.  Please run NewBuild or UpdateLast first."
            )
            return Rhino.Commands.Result.Failure

        # --- Interactive prompt for target size ---
        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Grade footwear to new size")

        opt_target = Rhino.Input.Custom.OptionDouble(current_size)
        opt_system_idx = Rhino.Input.Custom.OptionInteger(0)

        systems_list = list(_SIZE_SYSTEMS.keys())
        current_sys_idx = systems_list.index(size_system) if size_system in systems_list else 0

        go.AddOptionDouble("TargetSize", opt_target)
        go.AddOptionList("SizeSystem", systems_list, current_sys_idx)

        while True:
            res = go.Get()
            if res == Rhino.Input.GetResult.Option:
                continue
            if res == Rhino.Input.GetResult.Nothing:
                break
            return Rhino.Commands.Result.Cancel

        target_size = opt_target.CurrentValue
        chosen_sys_idx = go.Option().CurrentListOptionIndex if go.OptionIndex() == 1 else current_sys_idx
        size_system = systems_list[chosen_sys_idx] if chosen_sys_idx < len(systems_list) else size_system

        if abs(target_size - current_size) < 1e-6:
            Rhino.RhinoApp.WriteLine("Target size is the same as current size. Nothing to do.")
            return Rhino.Commands.Result.Nothing

        Rhino.RhinoApp.WriteLine(
            f"Grading from {size_system} {current_size} to {size_system} {target_size} ..."
        )

        origin, _, _, _ = self.OrientationAndSettings(doc)
        scale_factor = _compute_scale_factor(current_size, target_size, size_system)

        Rhino.RhinoApp.WriteLine(f"  Scale factor: {scale_factor:.6f}")

        # Perform grading
        try:
            self.GradeInsole(doc, scale_factor, origin)
            self.GradeOutline(doc, scale_factor, origin)
            self.GradeOtherPartyInsole(doc, scale_factor, origin)
            self.GradeGeomtries(doc, scale_factor, origin)
            self._update_girth_measurements(doc, current_size, target_size)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(f"Grading error: {ex}\n{traceback.format_exc()}")
            return Rhino.Commands.Result.Failure

        # Update document settings
        ds.set("last_size", target_size)
        ds.set("last_size_system", size_system)
        plug.SetDocumentSettings(doc, ds)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Grading complete: {size_system} {target_size}"
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  BatchGrade
# ---------------------------------------------------------------------------

class BatchGrade(Rhino.Commands.Command):
    """Batch-grade footwear to multiple target sizes in one operation.

    Creates a copy of all SLM-layer geometry for each target size and
    grades each copy independently.
    """

    _instance: BatchGrade | None = None

    def __init__(self):
        super().__init__()
        BatchGrade._instance = self

    @classmethod
    @property
    def Instance(cls) -> BatchGrade | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "BatchGrade"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)
        current_size = ds.get("last_size", 0.0)
        size_system = ds.get("last_size_system", "EU")

        if current_size <= 0:
            Rhino.RhinoApp.WriteLine(
                "No current size is set.  Please run NewBuild first."
            )
            return Rhino.Commands.Result.Failure

        # Prompt for a comma-separated list of target sizes
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt(
            f"Enter target sizes (comma-separated, {size_system} system, "
            f"current={current_size})"
        )
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return Rhino.Commands.Result.Cancel

        raw = gs.StringResult().strip()
        if not raw:
            Rhino.RhinoApp.WriteLine("No sizes entered.")
            return Rhino.Commands.Result.Cancel

        # Parse sizes
        target_sizes: List[float] = []
        for token in raw.replace(";", ",").split(","):
            token = token.strip()
            if not token:
                continue
            try:
                val = float(token)
                if val > 0:
                    target_sizes.append(val)
            except ValueError:
                Rhino.RhinoApp.WriteLine(f"  Skipping invalid size: '{token}'")

        if not target_sizes:
            Rhino.RhinoApp.WriteLine("No valid sizes provided.")
            return Rhino.Commands.Result.Cancel

        Rhino.RhinoApp.WriteLine(
            f"Batch grading from {size_system} {current_size} to "
            f"{len(target_sizes)} size(s): {target_sizes}"
        )

        # Gather all objects on SLM layers
        original_ids: List[System.Guid] = []
        for cls in plugin_constants.ALL_CLASSES:
            full_path = f"{plugin_constants.SLM_LAYER_PREFIX}::{cls}"
            objs = _find_objects_on_layer(doc, full_path)
            for obj in objs:
                original_ids.append(obj.Id)

        if not original_ids:
            Rhino.RhinoApp.WriteLine("No SLM objects found to grade.")
            return Rhino.Commands.Result.Failure

        origin_pt = Rhino.Geometry.Point3d.Origin
        # Try to get origin from grading command
        grader = GradeFootwear.Instance
        if grader is not None:
            origin_pt, _, _, _ = grader.OrientationAndSettings(doc)

        success_count = 0
        spacing_x = 0.0

        for target_size in target_sizes:
            if abs(target_size - current_size) < 1e-6:
                Rhino.RhinoApp.WriteLine(
                    f"  Skipping size {target_size} (same as current)."
                )
                continue

            scale_factor = _compute_scale_factor(
                current_size, target_size, size_system
            )

            # Duplicate objects
            dup_ids: List[System.Guid] = []
            for oid in original_ids:
                src_obj = doc.Objects.FindId(oid)
                if src_obj is None:
                    continue
                geom = src_obj.Geometry.Duplicate()
                attrs = src_obj.Attributes.Duplicate()
                name = attrs.Name or ""
                attrs.Name = f"{name}_Size{target_size}"
                new_id = doc.Objects.Add(geom, attrs)
                if new_id != System.Guid.Empty:
                    dup_ids.append(new_id)

            if not dup_ids:
                Rhino.RhinoApp.WriteLine(
                    f"  Failed to duplicate objects for size {target_size}."
                )
                continue

            # Scale the duplicates
            xform_scale = _build_grade_transform(scale_factor, origin_pt)

            # Offset laterally so graded sizes don't overlap
            spacing_x += 350.0
            xform_move = Rhino.Geometry.Transform.Translation(
                Rhino.Geometry.Vector3d(spacing_x, 0, 0)
            )
            xform_combined = xform_move * xform_scale

            transformed = 0
            for oid in dup_ids:
                obj = doc.Objects.FindId(oid)
                if obj is not None:
                    if doc.Objects.Transform(obj, xform_combined, True):
                        transformed += 1

            Rhino.RhinoApp.WriteLine(
                f"  Size {target_size}: duplicated and graded {transformed} object(s) "
                f"(scale={scale_factor:.4f})."
            )
            success_count += 1

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Batch grading complete: {success_count} size(s) created."
        )
        return Rhino.Commands.Result.Success
