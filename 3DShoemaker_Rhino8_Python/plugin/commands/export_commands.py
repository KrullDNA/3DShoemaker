"""
Export, options, and utility commands for Feet in Focus Shoe Kit Rhino 8 plugin.
Handles parameter export, folder watching, measurement, and rebuild.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input as ri
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import rhinoscriptsyntax as rs
import System
import json
import os


class ExportInsertParameters(Rhino.Commands.Command):
    """Exports insert parameters to a JSON file."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "ExportInsertParameters"

    def RunCommand(self, doc, mode):
        try:
            from ..plugin_main import PodoCADPlugIn
            plugin = PodoCADPlugIn.Instance
            if plugin is None or plugin.insert is None:
                Rhino.RhinoApp.WriteLine("No active insert found.")
                return rc.Result.Failure

            save_dialog = Rhino.UI.SaveFileDialog()
            save_dialog.Title = "Export Insert Parameters"
            save_dialog.Filter = "JSON Files (*.json)|*.json|All Files (*.*)|*.*"
            save_dialog.DefaultExt = "json"

            if not save_dialog.ShowSaveDialog():
                return rc.Result.Cancel

            filepath = save_dialog.FileName
            insert = plugin.insert

            params = {}
            for key, value in insert.parameters.items():
                if isinstance(value, (int, float, str, bool, type(None))):
                    params[key] = value
                elif isinstance(value, System.Guid):
                    params[key] = str(value)

            with open(filepath, 'w') as f:
                json.dump(params, f, indent=2)

            Rhino.RhinoApp.WriteLine(f"Insert parameters exported to: {filepath}")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error exporting insert parameters: {e}")
            return rc.Result.Failure


class ExportSupportParameters(Rhino.Commands.Command):
    """Exports support/bottom parameters to a JSON file."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "ExportSupportParameters"

    def RunCommand(self, doc, mode):
        try:
            from ..plugin_main import PodoCADPlugIn
            plugin = PodoCADPlugIn.Instance
            if plugin is None or plugin.bottom is None:
                Rhino.RhinoApp.WriteLine("No active bottom/support found.")
                return rc.Result.Failure

            save_dialog = Rhino.UI.SaveFileDialog()
            save_dialog.Title = "Export Support Parameters"
            save_dialog.Filter = "JSON Files (*.json)|*.json|All Files (*.*)|*.*"
            save_dialog.DefaultExt = "json"

            if not save_dialog.ShowSaveDialog():
                return rc.Result.Cancel

            filepath = save_dialog.FileName
            bottom = plugin.bottom

            params = {}
            for key, value in bottom.parameters.items():
                if isinstance(value, (int, float, str, bool, type(None))):
                    params[key] = value
                elif isinstance(value, System.Guid):
                    params[key] = str(value)

            with open(filepath, 'w') as f:
                json.dump(params, f, indent=2)

            Rhino.RhinoApp.WriteLine(f"Support parameters exported to: {filepath}")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error exporting support parameters: {e}")
            return rc.Result.Failure


class OpenFIFShoeKitOptions(Rhino.Commands.Command):
    """Opens the Feet in Focus Shoe Kit options/settings dialog."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "OpenFIFShoeKitOptions"

    def RunCommand(self, doc, mode):
        try:
            from ..forms.options_form import OptionsForm
            form = OptionsForm()
            result = form.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

            if result is not None and form.accepted:
                Rhino.RhinoApp.WriteLine("Options saved.")
                return rc.Result.Success
            else:
                return rc.Result.Cancel

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error opening options: {e}")
            return rc.Result.Failure


class OpenFolderWatcher(Rhino.Commands.Command):
    """Opens folder watcher for automatic scan file import."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "OpenFolderWatcher"

    def RunCommand(self, doc, mode):
        try:
            from ..forms.folder_watcher import FolderWatcher
            form = FolderWatcher()
            form.Show()
            Rhino.RhinoApp.WriteLine("Folder watcher opened.")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error opening folder watcher: {e}")
            return rc.Result.Failure


class RebuildFootwear(Rhino.Commands.Command):
    """Rebuilds all footwear geometry from stored parameters."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "RebuildFootwear"

    def RunCommand(self, doc, mode):
        try:
            from ..plugin_main import PodoCADPlugIn
            plugin = PodoCADPlugIn.Instance
            if plugin is None:
                Rhino.RhinoApp.WriteLine("Plugin not initialized.")
                return rc.Result.Failure

            Rhino.RhinoApp.WriteLine("Rebuilding footwear from stored parameters...")

            if plugin.last is not None:
                Rhino.RhinoApp.WriteLine("Rebuilding last...")
                plugin.last.Create()

            if plugin.insert is not None:
                Rhino.RhinoApp.WriteLine("Rebuilding insert...")
                plugin.insert.DesignCurves()
                plugin.insert.DesignSurfaces()
                plugin.insert.DesignBody()

            if plugin.bottom is not None:
                Rhino.RhinoApp.WriteLine("Rebuilding bottom...")
                plugin.bottom.DesignCurves()
                plugin.bottom.DesignBody()

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Footwear rebuild complete.")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error rebuilding footwear: {e}")
            return rc.Result.Failure


class VacuumFormCommand(Rhino.Commands.Command):
    """Opens the vacuum forming preparation dialog."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "VacuumForm"

    def RunCommand(self, doc, mode):
        try:
            from ..forms.vacuum_form import VacuumForm
            form = VacuumForm()
            result = form.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

            if result is None or not form.accepted:
                return rc.Result.Cancel

            go = ric.GetObject()
            go.SetCommandPrompt("Select object for vacuum forming")
            go.GeometryFilter = rdo.ObjectType.Brep | rdo.ObjectType.Mesh | rdo.ObjectType.SubD
            go.Get()
            if go.CommandResult() != rc.Result.Success:
                return go.CommandResult()

            geom = go.Object(0).Geometry()
            if geom is None:
                return rc.Result.Failure

            brep = None
            if isinstance(geom, rg.Brep):
                brep = geom
            elif isinstance(geom, rg.SubD):
                brep = geom.ToBrep(rg.SubDToBrepOptions())
            elif isinstance(geom, rg.Mesh):
                brep = rg.Brep.CreateFromMesh(geom, True)

            if brep is None:
                Rhino.RhinoApp.WriteLine("Could not process geometry.")
                return rc.Result.Failure

            thickness = form.material_thickness
            draft_angle = form.draft_angle

            offset_brep = rg.Brep.CreateOffsetBrep(
                brep, thickness, True, True, 0.01, out_blends=None, out_walls=None
            )

            if offset_brep and len(offset_brep) > 0:
                attrs = rdo.ObjectAttributes()
                attrs.Name = "VacuumFormed"
                layer_idx = doc.Layers.FindByFullPath("Feet in Focus Shoe Kit::VacuumForm", -1)
                if layer_idx >= 0:
                    attrs.LayerIndex = layer_idx

                for b in offset_brep:
                    doc.Objects.AddBrep(b, attrs)

                doc.Views.Redraw()
                Rhino.RhinoApp.WriteLine("Vacuum form shell created.")
                return rc.Result.Success
            else:
                Rhino.RhinoApp.WriteLine("Could not create offset shell.")
                return rc.Result.Failure

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error in vacuum form: {e}")
            return rc.Result.Failure


class MeasureLast(Rhino.Commands.Command):
    """Measures last dimensions including girths at cross sections."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "MeasureLast"

    def RunCommand(self, doc, mode):
        try:
            from ..plugin_main import PodoCADPlugIn
            plugin = PodoCADPlugIn.Instance
            if plugin is None or plugin.last is None:
                Rhino.RhinoApp.WriteLine("No active last found.")
                return rc.Result.Failure

            last = plugin.last

            measurements = {
                "Length": last.parameters.get("Length", 0),
                "Ball Width": last.parameters.get("BallWidth", 0),
                "Ball Width Perp": last.parameters.get("BallWidthPerp", 0),
                "Heel Width": last.parameters.get("HeelWidth", 0),
                "Ball Girth": last.parameters.get("BallGirth", 0),
                "Instep Girth": last.parameters.get("InstepGirth", 0),
                "Waist Girth": last.parameters.get("WaistGirth", 0),
                "Waist2 Girth": last.parameters.get("Waist2Girth", 0),
                "Arch Girth": last.parameters.get("ArchGirth", 0),
                "Heel Girth": last.parameters.get("HeelGirth", 0),
                "Ankle Girth": last.parameters.get("AnkleGirth", 0),
                "Heel Height": last.parameters.get("HeelHeight", 0),
                "Toe Spring": last.parameters.get("ToeSpring", 0),
                "Ball Break Angle": last.parameters.get("BallBreakPointAngle", 0),
                "Ball Roll Bulge": last.parameters.get("BallRollBulge", 0),
                "Ball Line Ratio": last.parameters.get("BallLineRatio", 0),
                "Arch Length": last.parameters.get("ArchLength", 0),
            }

            Rhino.RhinoApp.WriteLine("\n=== Last Measurements ===")
            for name, value in measurements.items():
                if value is not None and value != 0:
                    Rhino.RhinoApp.WriteLine(f"  {name}: {value:.2f}")

            self._measure_girths(doc, plugin)

            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error measuring last: {e}")
            return rc.Result.Failure

    def _measure_girths(self, doc, plugin):
        """Measure actual girth curves in the document."""
        last = plugin.last
        girth_curves = {
            "Ball Girth": last.geometry_ids.get("CBG"),
            "Instep Girth": last.geometry_ids.get("CIG"),
            "Waist Girth": last.geometry_ids.get("CWG"),
            "Waist2 Girth": last.geometry_ids.get("CW2G"),
        }

        Rhino.RhinoApp.WriteLine("\n=== Measured Girths ===")
        for name, guid in girth_curves.items():
            if guid and guid != System.Guid.Empty:
                obj = doc.Objects.FindId(guid)
                if obj and obj.Geometry:
                    curve = obj.Geometry
                    if isinstance(curve, rg.Curve):
                        length = curve.GetLength()
                        Rhino.RhinoApp.WriteLine(f"  {name}: {length:.2f}")


class ChangeClippingPlane(Rhino.Commands.Command):
    """Modifies clipping plane position and orientation."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "ChangeClippingPlane"

    def RunCommand(self, doc, mode):
        try:
            go = ric.GetObject()
            go.SetCommandPrompt("Select clipping plane to modify")
            go.GeometryFilter = rdo.ObjectType.ClipPlane
            go.Get()
            if go.CommandResult() != rc.Result.Success:
                return go.CommandResult()

            obj_ref = go.Object(0)
            clip_obj = obj_ref.Object()

            if clip_obj is None:
                return rc.Result.Failure

            gp = ric.GetPoint()
            gp.SetCommandPrompt("New clipping plane origin")
            gp.Get()
            if gp.CommandResult() != rc.Result.Success:
                return gp.CommandResult()

            new_origin = gp.Point()
            old_bbox = clip_obj.Geometry.GetBoundingBox(True)
            old_center = old_bbox.Center

            move_vec = new_origin - old_center
            xform = rg.Transform.Translation(move_vec)

            doc.Objects.Transform(obj_ref.ObjectId, xform, True)
            doc.Views.Redraw()

            Rhino.RhinoApp.WriteLine("Clipping plane moved.")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error changing clipping plane: {e}")
            return rc.Result.Failure


class SnapCurvesCommand(Rhino.Commands.Command):
    """Snaps curves to mesh or surface geometry."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "SnapCurves"

    def RunCommand(self, doc, mode):
        try:
            from ..utils.snap_curves import SnapCurvesToSurface

            go_curve = ric.GetObject()
            go_curve.SetCommandPrompt("Select curves to snap")
            go_curve.GeometryFilter = rdo.ObjectType.Curve
            go_curve.GetMultiple(1, 0)
            if go_curve.CommandResult() != rc.Result.Success:
                return go_curve.CommandResult()

            go_target = ric.GetObject()
            go_target.SetCommandPrompt("Select target mesh or surface")
            go_target.GeometryFilter = rdo.ObjectType.Mesh | rdo.ObjectType.Brep | rdo.ObjectType.Surface
            go_target.Get()
            if go_target.CommandResult() != rc.Result.Success:
                return go_target.CommandResult()

            target_geom = go_target.Object(0).Geometry()
            curves = []
            for i in range(go_curve.ObjectCount):
                curve = go_curve.Object(i).Curve()
                if curve:
                    curves.append(curve)

            if not curves:
                return rc.Result.Failure

            snapper = SnapCurvesToSurface()
            snapped = snapper.snap(curves, target_geom)

            for curve in snapped:
                doc.Objects.AddCurve(curve)

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(f"Snapped {len(snapped)} curve(s) to target.")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error snapping curves: {e}")
            return rc.Result.Failure


class SqueezeCommand(Rhino.Commands.Command):
    """Applies squeeze deformation to geometry."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "Squeeze"

    def RunCommand(self, doc, mode):
        try:
            from ..utils.squeeze import SqueezeDeformation

            go = ric.GetObject()
            go.SetCommandPrompt("Select objects to squeeze")
            go.GeometryFilter = (rdo.ObjectType.Mesh | rdo.ObjectType.Brep |
                                rdo.ObjectType.Surface | rdo.ObjectType.SubD)
            go.GetMultiple(1, 0)
            if go.CommandResult() != rc.Result.Success:
                return go.CommandResult()

            gn = ric.GetNumber()
            gn.SetCommandPrompt("Squeeze factor (0.5 = half, 2.0 = double)")
            gn.SetDefaultNumber(1.0)
            gn.SetLowerLimit(0.01, False)
            gn.SetUpperLimit(10.0, False)
            gn.Get()
            if gn.CommandResult() != rc.Result.Success:
                return gn.CommandResult()

            factor = gn.Number()

            squeeze = SqueezeDeformation()
            count = 0
            for i in range(go.ObjectCount):
                obj_ref = go.Object(i)
                geom = obj_ref.Geometry()
                if geom is None:
                    continue

                squeezed = squeeze.apply(geom, factor)
                if squeezed is not None:
                    doc.Objects.Replace(obj_ref.ObjectId, squeezed)
                    count += 1

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(f"Squeeze applied to {count} object(s) with factor {factor:.2f}.")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error applying squeeze: {e}")
            return rc.Result.Failure


class TestingCommand(Rhino.Commands.Command):
    """Debug and testing utilities for plugin development."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "Testing"

    def RunCommand(self, doc, mode):
        try:
            from ..plugin_main import PodoCADPlugIn
            plugin = PodoCADPlugIn.Instance

            Rhino.RhinoApp.WriteLine("\n=== Feet in Focus Shoe Kit Debug Info ===")
            Rhino.RhinoApp.WriteLine(f"  Plugin loaded: {plugin is not None}")
            if plugin:
                Rhino.RhinoApp.WriteLine(f"  Last: {plugin.last is not None}")
                Rhino.RhinoApp.WriteLine(f"  Insert: {plugin.insert is not None}")
                Rhino.RhinoApp.WriteLine(f"  Bottom: {plugin.bottom is not None}")
                Rhino.RhinoApp.WriteLine(f"  Foot: {plugin.foot is not None}")

            Rhino.RhinoApp.WriteLine(f"  Document: {doc.Name}")
            Rhino.RhinoApp.WriteLine(f"  Objects: {doc.Objects.Count}")
            Rhino.RhinoApp.WriteLine(f"  Layers: {doc.Layers.Count}")

            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error in testing: {e}")
            return rc.Result.Failure
