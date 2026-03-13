"""
Feet in Focus Shoe Kit Rhino 8 Plugin - Parameter adjustment commands.

Commands:
    ChangeParameter                         - Generic parameter change command.
    ChangeComponentParameterization         - Changes component parameters.
    ChangeInsertParameterization            - Changes insert parameters.
    AdjustBottomComponentParameterization   - Adjusts bottom component parameters.
    AdjustMaterial                          - Adjusts material properties.
    AdjustMaterialThicknesses               - Adjusts material thickness values.
    AdjustFitCustomization                  - Adjusts fit customization parameters.
    AdjustFootbedDepth                      - Adjusts footbed depth.
    AdjustLastDepthForFootbeds              - Adjusts last depth for footbed integration.
    AdjustCSPlanePositions                  - Adjusts cross-section plane positions.
    ChangeStatus                            - Changes object status/state.
"""

from __future__ import annotations

import json
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
from plugin.document_settings import DocumentSettings
from plugin.material_thicknesses import MaterialThicknesses


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _find_named_object(
    doc: Rhino.RhinoDoc, name: str
) -> Optional[Rhino.DocObjects.RhinoObject]:
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.NameFilter = name
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        return obj
    return None


def _find_objects_by_prefix(
    doc: Rhino.RhinoDoc, prefix: str
) -> List[Rhino.DocObjects.RhinoObject]:
    results: List[Rhino.DocObjects.RhinoObject] = []
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.DeletedObjects = False
    settings.HiddenObjects = True
    for obj in doc.Objects.GetObjectList(settings):
        name = obj.Attributes.Name or ""
        if name.startswith(prefix):
            results.append(obj)
    return results


def _rebuild_footwear_from_settings(doc: Rhino.RhinoDoc) -> bool:
    """Trigger a rebuild of footwear from stored parameters (placeholder).

    In a full implementation this would call into the build pipeline.
    """
    Rhino.RhinoApp.WriteLine("  Rebuild triggered (parameter change applied).")
    doc.Views.Redraw()
    return True


# ---------------------------------------------------------------------------
#  ChangeParameter
# ---------------------------------------------------------------------------

class ChangeParameter(Rhino.Commands.Command):
    """Generic parameter change command.

    Allows changing any named parameter in the DocumentSettings by key.
    """

    _instance: ChangeParameter | None = None

    def __init__(self):
        super().__init__()
        ChangeParameter._instance = self

    @classmethod
    @property
    def Instance(cls) -> ChangeParameter | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ChangeParameter"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)

        # Prompt for parameter name
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Enter parameter name")
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return gs.CommandResult()

        param_name = gs.StringResult().strip()
        if not param_name:
            Rhino.RhinoApp.WriteLine("No parameter name entered.")
            return Rhino.Commands.Result.Cancel

        current_val = ds.get(param_name)
        Rhino.RhinoApp.WriteLine(f"Current value of '{param_name}': {current_val}")

        # Prompt for new value
        gs2 = Rhino.Input.Custom.GetString()
        gs2.SetCommandPrompt(f"Enter new value for '{param_name}'")
        gs2.Get()
        if gs2.CommandResult() != Rhino.Commands.Result.Success:
            return gs2.CommandResult()

        raw_value = gs2.StringResult().strip()

        # Attempt type-appropriate conversion
        new_value: Any
        try:
            new_value = float(raw_value)
        except ValueError:
            if raw_value.lower() in ("true", "yes"):
                new_value = True
            elif raw_value.lower() in ("false", "no"):
                new_value = False
            else:
                new_value = raw_value

        ds.set(param_name, new_value)
        plug.SetDocumentSettings(doc, ds)

        Rhino.RhinoApp.WriteLine(
            f"Parameter '{param_name}' set to: {new_value}"
        )
        _rebuild_footwear_from_settings(doc)
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  ChangeComponentParameterization
# ---------------------------------------------------------------------------

class ChangeComponentParameterization(Rhino.Commands.Command):
    """Change component parameters (sole, heel, shank, etc.).

    Presents the component's adjustable parameters and applies changes.
    """

    _instance: ChangeComponentParameterization | None = None

    def __init__(self):
        super().__init__()
        ChangeComponentParameterization._instance = self

    @classmethod
    @property
    def Instance(cls) -> ChangeComponentParameterization | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ChangeComponentParameterization"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)
        mt = plug.GetMaterialThicknesses(doc)

        components = [
            "Sole", "Heel", "ShankBoard", "TopPiece",
            "InsoleBoard", "Welt", "Midsole",
        ]

        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Select component to parameterize")
        go.AddOptionList("Component", components, 0)

        component_idx = 0
        while True:
            res = go.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                component_idx = go.Option().CurrentListOptionIndex
                continue
            break

        component = components[component_idx] if component_idx < len(components) else components[0]
        Rhino.RhinoApp.WriteLine(f"Adjusting {component} parameters ...")

        # Component-specific parameters
        go2 = Rhino.Input.Custom.GetOption()
        go2.SetCommandPrompt(f"{component} parameters")

        if component == "Sole":
            opt_thick = Rhino.Input.Custom.OptionDouble(mt.bottom_outsole, 0.0, 30.0)
            opt_profile = Rhino.Input.Custom.OptionInteger(0)
            go2.AddOptionDouble("Thickness", opt_thick)
            go2.AddOptionList("Profile", ["Flat", "Rocker", "Wedge"], 0)
        elif component == "Heel":
            opt_height = Rhino.Input.Custom.OptionDouble(
                ds.get("last_heel_height_mm", 0.0), 0.0, 120.0
            )
            go2.AddOptionDouble("HeelHeight", opt_height)
        elif component == "ShankBoard":
            opt_thick = Rhino.Input.Custom.OptionDouble(mt.bottom_shank, 0.0, 10.0)
            go2.AddOptionDouble("Thickness", opt_thick)
        elif component == "Midsole":
            opt_thick = Rhino.Input.Custom.OptionDouble(mt.bottom_midsole, 0.0, 30.0)
            go2.AddOptionDouble("Thickness", opt_thick)
        else:
            opt_generic = Rhino.Input.Custom.OptionDouble(0.0)
            go2.AddOptionDouble("Value", opt_generic)

        while True:
            res = go2.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        # Apply parameter changes
        if component == "Sole":
            mt.bottom_outsole = opt_thick.CurrentValue
            plug.SetMaterialThicknesses(doc, mt)
        elif component == "Heel":
            ds.set("last_heel_height_mm", opt_height.CurrentValue)
            plug.SetDocumentSettings(doc, ds)
        elif component == "ShankBoard":
            mt.bottom_shank = opt_thick.CurrentValue
            plug.SetMaterialThicknesses(doc, mt)
        elif component == "Midsole":
            mt.bottom_midsole = opt_thick.CurrentValue
            plug.SetMaterialThicknesses(doc, mt)

        plug.MarkDocumentDirty()
        _rebuild_footwear_from_settings(doc)
        Rhino.RhinoApp.WriteLine(f"{component} parameters updated.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  ChangeInsertParameterization
# ---------------------------------------------------------------------------

class ChangeInsertParameterization(Rhino.Commands.Command):
    """Change insert/insole parameters."""

    _instance: ChangeInsertParameterization | None = None

    def __init__(self):
        super().__init__()
        ChangeInsertParameterization._instance = self

    @classmethod
    @property
    def Instance(cls) -> ChangeInsertParameterization | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ChangeInsertParameterization"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)
        mt = plug.GetMaterialThicknesses(doc)

        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Adjust insert parameters")

        opt_thick = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_thickness_mm", mt.insole_base), 0.5, 20.0
        )
        opt_top = Rhino.Input.Custom.OptionDouble(mt.insole_top_cover, 0.0, 5.0)
        opt_bottom = Rhino.Input.Custom.OptionDouble(mt.insole_bottom_cover, 0.0, 5.0)
        opt_arch = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_arch_height_mm", 0.0), 0.0, 30.0
        )
        opt_heel_cup = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_heel_cup_depth_mm", 0.0), 0.0, 25.0
        )
        opt_med_post = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_posting_medial_mm", mt.insole_posting_medial), 0.0, 15.0
        )
        opt_lat_post = Rhino.Input.Custom.OptionDouble(
            ds.get("insert_posting_lateral_mm", mt.insole_posting_lateral), 0.0, 15.0
        )
        materials_list = ["EVA", "Cork", "Leather", "Polypropylene", "Carbon", "Nylon"]
        current_mat = ds.get("insert_material", "EVA")
        mat_idx = materials_list.index(current_mat) if current_mat in materials_list else 0

        go.AddOptionDouble("Thickness", opt_thick)
        go.AddOptionDouble("TopCover", opt_top)
        go.AddOptionDouble("BottomCover", opt_bottom)
        go.AddOptionDouble("ArchHeight", opt_arch)
        go.AddOptionDouble("HeelCupDepth", opt_heel_cup)
        go.AddOptionDouble("MedialPosting", opt_med_post)
        go.AddOptionDouble("LateralPosting", opt_lat_post)
        go.AddOptionList("Material", materials_list, mat_idx)

        while True:
            res = go.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        # Store changes
        ds.set("insert_thickness_mm", opt_thick.CurrentValue)
        ds.set("insert_top_cover_mm", opt_top.CurrentValue)
        ds.set("insert_bottom_cover_mm", opt_bottom.CurrentValue)
        ds.set("insert_arch_height_mm", opt_arch.CurrentValue)
        ds.set("insert_heel_cup_depth_mm", opt_heel_cup.CurrentValue)
        ds.set("insert_posting_medial_mm", opt_med_post.CurrentValue)
        ds.set("insert_posting_lateral_mm", opt_lat_post.CurrentValue)

        mt.insole_base = opt_thick.CurrentValue
        mt.insole_top_cover = opt_top.CurrentValue
        mt.insole_bottom_cover = opt_bottom.CurrentValue
        mt.insole_posting_medial = opt_med_post.CurrentValue
        mt.insole_posting_lateral = opt_lat_post.CurrentValue

        plug.SetDocumentSettings(doc, ds)
        plug.SetMaterialThicknesses(doc, mt)

        _rebuild_footwear_from_settings(doc)
        Rhino.RhinoApp.WriteLine("Insert parameters updated.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustBottomComponentParameterization
# ---------------------------------------------------------------------------

class AdjustBottomComponentParameterization(Rhino.Commands.Command):
    """Adjust bottom component (outsole, midsole, insole board) parameters."""

    _instance: AdjustBottomComponentParameterization | None = None

    def __init__(self):
        super().__init__()
        AdjustBottomComponentParameterization._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustBottomComponentParameterization | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustBottomComponentParameterization"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        mt = plug.GetMaterialThicknesses(doc)
        ds = plug.GetDocumentSettings(doc)

        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Adjust bottom component parameters")

        opt_outsole = Rhino.Input.Custom.OptionDouble(mt.bottom_outsole, 0.0, 30.0)
        opt_midsole = Rhino.Input.Custom.OptionDouble(mt.bottom_midsole, 0.0, 30.0)
        opt_board = Rhino.Input.Custom.OptionDouble(mt.bottom_insole_board, 0.0, 10.0)
        opt_shank = Rhino.Input.Custom.OptionDouble(mt.bottom_shank, 0.0, 10.0)
        opt_welt = Rhino.Input.Custom.OptionDouble(mt.bottom_welt, 0.0, 10.0)
        opt_profile = Rhino.Input.Custom.OptionInteger(0)

        go.AddOptionDouble("OutsoleThickness", opt_outsole)
        go.AddOptionDouble("MidsoleThickness", opt_midsole)
        go.AddOptionDouble("InsoleBoardThickness", opt_board)
        go.AddOptionDouble("ShankThickness", opt_shank)
        go.AddOptionDouble("WeltThickness", opt_welt)
        go.AddOptionList("Profile", ["Flat", "Rocker", "Negative"], 0)

        while True:
            res = go.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        mt.bottom_outsole = opt_outsole.CurrentValue
        mt.bottom_midsole = opt_midsole.CurrentValue
        mt.bottom_insole_board = opt_board.CurrentValue
        mt.bottom_shank = opt_shank.CurrentValue
        mt.bottom_welt = opt_welt.CurrentValue
        plug.SetMaterialThicknesses(doc, mt)

        Rhino.RhinoApp.WriteLine(
            f"Bottom component total: {mt.total_bottom_thickness():.2f} mm"
        )
        _rebuild_footwear_from_settings(doc)
        Rhino.RhinoApp.WriteLine("Bottom component parameters updated.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustMaterial
# ---------------------------------------------------------------------------

class AdjustMaterial(Rhino.Commands.Command):
    """Adjust material properties for a component."""

    _instance: AdjustMaterial | None = None

    def __init__(self):
        super().__init__()
        AdjustMaterial._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustMaterial | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustMaterial"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)

        components = ["Insert", "Bottom", "Last"]
        materials = [
            "EVA", "Cork", "Leather", "Rubber", "Polypropylene",
            "Carbon", "Nylon", "TPU", "Silicone", "Polyester",
        ]

        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Adjust material")
        go.AddOptionList("Component", components, 0)
        go.AddOptionList("Material", materials, 0)
        opt_density = Rhino.Input.Custom.OptionDouble(1.0, 0.01, 20.0)
        opt_hardness = Rhino.Input.Custom.OptionDouble(40.0, 0.0, 100.0)
        go.AddOptionDouble("Density", opt_density)
        go.AddOptionDouble("ShoreA_Hardness", opt_hardness)

        comp_idx = 0
        mat_idx = 0
        while True:
            res = go.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                option = go.Option()
                if option.EnglishName == "Component":
                    comp_idx = option.CurrentListOptionIndex
                elif option.EnglishName == "Material":
                    mat_idx = option.CurrentListOptionIndex
                continue
            break

        component = components[comp_idx] if comp_idx < len(components) else "Insert"
        material = materials[mat_idx] if mat_idx < len(materials) else "EVA"

        # Store in settings
        key_prefix = component.lower()
        ds.set(f"{key_prefix}_material", material)
        ds.set(f"{key_prefix}_material_density", opt_density.CurrentValue)
        ds.set(f"{key_prefix}_material_hardness", opt_hardness.CurrentValue)
        plug.SetDocumentSettings(doc, ds)

        Rhino.RhinoApp.WriteLine(
            f"{component} material set to {material} "
            f"(density={opt_density.CurrentValue:.2f}, "
            f"hardness={opt_hardness.CurrentValue:.0f} Shore A)."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustMaterialThicknesses
# ---------------------------------------------------------------------------

class AdjustMaterialThicknesses(Rhino.Commands.Command):
    """Adjust material thickness values for all layers."""

    _instance: AdjustMaterialThicknesses | None = None

    def __init__(self):
        super().__init__()
        AdjustMaterialThicknesses._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustMaterialThicknesses | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustMaterialThicknesses"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        mt = plug.GetMaterialThicknesses(doc)

        # Display current values
        Rhino.RhinoApp.WriteLine("Current material thicknesses:")
        data = mt.to_dict()
        for key, val in sorted(data.items()):
            Rhino.RhinoApp.WriteLine(f"  {key}: {val:.2f} mm")

        # Prompt for key to change
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt(
            "Enter thickness name to change (or 'all' for full editor, Enter to exit)"
        )
        gs.AcceptNothing(True)
        gs.Get()
        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return gs.CommandResult()

        raw = (gs.StringResult() or "").strip()
        if not raw:
            return Rhino.Commands.Result.Nothing

        if raw.lower() == "all":
            # Interactive editor for common thicknesses
            go = Rhino.Input.Custom.GetOption()
            go.SetCommandPrompt("Adjust thicknesses (Enter when done)")
            go.AcceptNothing(True)

            opts = {}
            for key in sorted(data.keys()):
                opt = Rhino.Input.Custom.OptionDouble(data[key], 0.0, 50.0)
                label = key.replace("_", "").title()[:20]  # Rhino option name limit
                go.AddOptionDouble(label, opt)
                opts[key] = (label, opt)

            while True:
                res = go.Get()
                if res == Rhino.Input.Custom.GetResult.Option:
                    continue
                break

            for key, (label, opt) in opts.items():
                mt.set(key, opt.CurrentValue)

        elif raw in data:
            gd = Rhino.Input.Custom.GetNumber()
            gd.SetCommandPrompt(f"New value for '{raw}' (current={data[raw]:.2f})")
            gd.SetLowerLimit(0.0, True)
            gd.Get()
            if gd.CommandResult() != Rhino.Commands.Result.Success:
                return gd.CommandResult()
            mt.set(raw, gd.Number())
        else:
            Rhino.RhinoApp.WriteLine(f"Unknown thickness key: '{raw}'")
            return Rhino.Commands.Result.Failure

        plug.SetMaterialThicknesses(doc, mt)

        Rhino.RhinoApp.WriteLine("Material thicknesses updated.")
        Rhino.RhinoApp.WriteLine(
            f"  Total insole: {mt.total_insole_thickness():.2f} mm"
        )
        Rhino.RhinoApp.WriteLine(
            f"  Total bottom: {mt.total_bottom_thickness():.2f} mm"
        )
        Rhino.RhinoApp.WriteLine(
            f"  Total build height: {mt.total_build_height():.2f} mm"
        )
        _rebuild_footwear_from_settings(doc)
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustFitCustomization
# ---------------------------------------------------------------------------

class AdjustFitCustomization(Rhino.Commands.Command):
    """Adjust fit customization parameters.

    Modifies ease allowances, toe room, heel fit, and girth adjustments
    that control how tightly the footwear conforms to the foot.
    """

    _instance: AdjustFitCustomization | None = None

    def __init__(self):
        super().__init__()
        AdjustFitCustomization._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustFitCustomization | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustFitCustomization"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)

        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Adjust fit customization")

        opt_toe_room = Rhino.Input.Custom.OptionDouble(
            ds.get("fit_toe_room_mm", 12.0), 0.0, 30.0
        )
        opt_ball_ease = Rhino.Input.Custom.OptionDouble(
            ds.get("fit_ball_ease_mm", 0.0), -5.0, 10.0
        )
        opt_instep_ease = Rhino.Input.Custom.OptionDouble(
            ds.get("fit_instep_ease_mm", 0.0), -5.0, 10.0
        )
        opt_heel_ease = Rhino.Input.Custom.OptionDouble(
            ds.get("fit_heel_ease_mm", 0.0), -3.0, 5.0
        )
        opt_width_ease = Rhino.Input.Custom.OptionDouble(
            ds.get("fit_width_ease_mm", 0.0), -5.0, 10.0
        )
        opt_girth_adj = Rhino.Input.Custom.OptionDouble(
            ds.get("fit_girth_adjustment_mm", 0.0), -10.0, 10.0
        )

        go.AddOptionDouble("ToeRoom", opt_toe_room)
        go.AddOptionDouble("BallEase", opt_ball_ease)
        go.AddOptionDouble("InstepEase", opt_instep_ease)
        go.AddOptionDouble("HeelEase", opt_heel_ease)
        go.AddOptionDouble("WidthEase", opt_width_ease)
        go.AddOptionDouble("GirthAdjustment", opt_girth_adj)

        while True:
            res = go.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        ds.set("fit_toe_room_mm", opt_toe_room.CurrentValue)
        ds.set("fit_ball_ease_mm", opt_ball_ease.CurrentValue)
        ds.set("fit_instep_ease_mm", opt_instep_ease.CurrentValue)
        ds.set("fit_heel_ease_mm", opt_heel_ease.CurrentValue)
        ds.set("fit_width_ease_mm", opt_width_ease.CurrentValue)
        ds.set("fit_girth_adjustment_mm", opt_girth_adj.CurrentValue)

        plug.SetDocumentSettings(doc, ds)
        _rebuild_footwear_from_settings(doc)
        Rhino.RhinoApp.WriteLine("Fit customization updated.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustFootbedDepth
# ---------------------------------------------------------------------------

class AdjustFootbedDepth(Rhino.Commands.Command):
    """Adjust footbed depth parameter.

    Controls how deeply the foot sits into the footbed cavity.
    """

    _instance: AdjustFootbedDepth | None = None

    def __init__(self):
        super().__init__()
        AdjustFootbedDepth._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustFootbedDepth | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustFootbedDepth"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)
        current_depth = ds.get("footbed_depth_mm", 5.0)

        gn = Rhino.Input.Custom.GetNumber()
        gn.SetCommandPrompt(f"Footbed depth in mm (current={current_depth:.2f})")
        gn.SetDefaultNumber(current_depth)
        gn.SetLowerLimit(0.0, True)
        gn.SetUpperLimit(30.0, True)
        gn.Get()
        if gn.CommandResult() != Rhino.Commands.Result.Success:
            return gn.CommandResult()

        new_depth = gn.Number()
        ds.set("footbed_depth_mm", new_depth)
        plug.SetDocumentSettings(doc, ds)

        Rhino.RhinoApp.WriteLine(f"Footbed depth set to {new_depth:.2f} mm.")
        _rebuild_footwear_from_settings(doc)
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustLastDepthForFootbeds
# ---------------------------------------------------------------------------

class AdjustLastDepthForFootbeds(Rhino.Commands.Command):
    """Adjust last depth to accommodate a footbed.

    Increases or decreases the volume inside the last to account for
    the footbed thickness and contour.
    """

    _instance: AdjustLastDepthForFootbeds | None = None

    def __init__(self):
        super().__init__()
        AdjustLastDepthForFootbeds._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustLastDepthForFootbeds | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustLastDepthForFootbeds"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)
        mt = plug.GetMaterialThicknesses(doc)

        current_adj = ds.get("last_footbed_depth_adjustment_mm", 0.0)
        footbed_thick = mt.total_insole_thickness()

        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Adjust last depth for footbed")

        opt_adj = Rhino.Input.Custom.OptionDouble(current_adj, -20.0, 20.0)
        opt_auto = Rhino.Input.Custom.OptionToggle(False, "Manual", "Auto")

        go.AddOptionDouble("DepthAdjustment", opt_adj)
        go.AddOptionToggle("Mode", opt_auto)

        while True:
            res = go.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                continue
            break

        if opt_auto.CurrentValue:
            # Auto-calculate from footbed thickness
            adjustment = footbed_thick
            Rhino.RhinoApp.WriteLine(
                f"  Auto-calculated depth adjustment from footbed thickness: {adjustment:.2f} mm"
            )
        else:
            adjustment = opt_adj.CurrentValue

        ds.set("last_footbed_depth_adjustment_mm", adjustment)
        plug.SetDocumentSettings(doc, ds)

        # Apply to last geometry if present
        last_obj = _find_named_object(doc, "Last")
        if last_obj is not None:
            last_geom = last_obj.Geometry
            if isinstance(last_geom, Rhino.Geometry.Brep):
                # Offset the bottom surface of the last downward
                offset_results = Rhino.Geometry.Brep.CreateOffsetBrep(
                    last_geom, -adjustment, solid=False, extend=False, tolerance=0.01
                )
                if offset_results and len(offset_results) > 0:
                    new_brep = None
                    if hasattr(offset_results[0], "__iter__"):
                        for b in offset_results[0]:
                            if isinstance(b, Rhino.Geometry.Brep) and b.IsValid:
                                new_brep = b
                                break
                    elif isinstance(offset_results[0], Rhino.Geometry.Brep):
                        new_brep = offset_results[0]
                    if new_brep is not None:
                        doc.Objects.Replace(last_obj.Id, new_brep)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Last depth adjusted by {adjustment:.2f} mm for footbed."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  AdjustCSPlanePositions
# ---------------------------------------------------------------------------

class AdjustCSPlanePositions(Rhino.Commands.Command):
    """Adjust cross-section plane positions along the last.

    Repositions the measurement/construction planes used to define
    cross-sectional profiles (ball, waist, instep, heel, etc.).
    """

    _instance: AdjustCSPlanePositions | None = None

    def __init__(self):
        super().__init__()
        AdjustCSPlanePositions._instance = self

    @classmethod
    @property
    def Instance(cls) -> AdjustCSPlanePositions | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "AdjustCSPlanePositions"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        ds = plug.GetDocumentSettings(doc)

        # Standard cross-section names and their default position ratios
        # (proportion of total last length from the heel)
        cs_sections = {
            "Heel":    ("cs_heel_ratio", 0.00),
            "Seat":    ("cs_seat_ratio", 0.10),
            "Instep":  ("cs_instep_ratio", 0.40),
            "Waist":   ("cs_waist_ratio", 0.50),
            "Ball":    ("cs_ball_ratio", 0.68),
            "Toe":     ("cs_toe_ratio", 0.90),
            "TipToe":  ("cs_tiptoe_ratio", 1.00),
        }

        # Display current positions
        Rhino.RhinoApp.WriteLine("Cross-section plane positions (ratio of last length):")
        for name, (key, default) in cs_sections.items():
            current = ds.get(key, default)
            Rhino.RhinoApp.WriteLine(f"  {name}: {current:.2%}")

        # Select section to adjust
        section_names = list(cs_sections.keys())
        go = Rhino.Input.Custom.GetOption()
        go.SetCommandPrompt("Select cross-section to adjust")
        go.AddOptionList("Section", section_names, 0)

        section_idx = 0
        while True:
            res = go.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                section_idx = go.Option().CurrentListOptionIndex
                continue
            break

        section_name = section_names[section_idx]
        key, default = cs_sections[section_name]
        current_val = ds.get(key, default)

        gn = Rhino.Input.Custom.GetNumber()
        gn.SetCommandPrompt(
            f"New position ratio for {section_name} (0.0=heel, 1.0=toe, current={current_val:.3f})"
        )
        gn.SetDefaultNumber(current_val)
        gn.SetLowerLimit(0.0, True)
        gn.SetUpperLimit(1.0, True)
        gn.Get()
        if gn.CommandResult() != Rhino.Commands.Result.Success:
            return gn.CommandResult()

        new_val = gn.Number()
        ds.set(key, new_val)
        plug.SetDocumentSettings(doc, ds)

        # Update clipping plane if it exists
        plane_obj = _find_named_object(doc, f"CSPlane_{section_name}")
        if plane_obj is not None:
            # Move the plane to the new position
            last_obj = _find_named_object(doc, "Last")
            if last_obj is not None:
                last_bbox = last_obj.Geometry.GetBoundingBox(True)
                if last_bbox.IsValid:
                    total_length = last_bbox.Max.Y - last_bbox.Min.Y
                    new_y = last_bbox.Min.Y + total_length * new_val
                    old_bbox = plane_obj.Geometry.GetBoundingBox(True)
                    if old_bbox.IsValid:
                        old_y = (old_bbox.Min.Y + old_bbox.Max.Y) / 2.0
                        delta_y = new_y - old_y
                        xform = Rhino.Geometry.Transform.Translation(
                            Rhino.Geometry.Vector3d(0, delta_y, 0)
                        )
                        doc.Objects.Transform(plane_obj, xform, True)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"{section_name} cross-section position set to {new_val:.3f}."
        )
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  ChangeStatus
# ---------------------------------------------------------------------------

class ChangeStatus(Rhino.Commands.Command):
    """Change object status/state.

    Toggles the design status of selected objects (e.g., Draft, Review,
    Approved, Locked) and stores it in user text.
    """

    _instance: ChangeStatus | None = None

    def __init__(self):
        super().__init__()
        ChangeStatus._instance = self

    @classmethod
    @property
    def Instance(cls) -> ChangeStatus | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "ChangeStatus"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        plug = PodoCADPlugIn.instance()
        if not plug.is_licensed:
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit: A valid license is required.")
            return Rhino.Commands.Result.Failure

        # Select objects
        go = Rhino.Input.Custom.GetObject()
        go.SetCommandPrompt("Select objects to change status")
        go.EnablePreSelect(True, True)
        go.GetMultiple(1, 0)
        if go.CommandResult() != Rhino.Commands.Result.Success:
            return go.CommandResult()

        count = go.ObjectCount
        if count == 0:
            return Rhino.Commands.Result.Cancel

        statuses = ["Draft", "Review", "Approved", "Locked", "Archived"]

        go_stat = Rhino.Input.Custom.GetOption()
        go_stat.SetCommandPrompt("Select new status")
        go_stat.AddOptionList("Status", statuses, 0)

        status_idx = 0
        while True:
            res = go_stat.Get()
            if res == Rhino.Input.Custom.GetResult.Option:
                status_idx = go_stat.Option().CurrentListOptionIndex
                continue
            break

        new_status = statuses[status_idx] if status_idx < len(statuses) else "Draft"

        # Apply status to selected objects
        changed = 0
        for i in range(count):
            obj = go.Object(i).Object()
            if obj is None:
                continue

            attrs = obj.Attributes.Duplicate()
            # Store status in user text
            attrs.SetUserString("FIFShoeKit_Status", new_status)

            # Visual feedback: lock objects with "Locked" status
            if new_status == "Locked":
                attrs.Mode = Rhino.DocObjects.ObjectMode.Locked
            elif new_status == "Archived":
                attrs.Visible = False
            else:
                attrs.Mode = Rhino.DocObjects.ObjectMode.Normal
                attrs.Visible = True

            doc.Objects.ModifyAttributes(obj, attrs, True)
            changed += 1

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine(
            f"Status changed to '{new_status}' for {changed} object(s)."
        )
        return Rhino.Commands.Result.Success
