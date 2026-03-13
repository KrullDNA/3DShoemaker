"""
plugin_main.py - Main plugin class for Feet in Focus Shoe Kit (PodoCAD equivalent).

Handles plugin lifecycle, document serialization, layer management,
rendering setup, and view population for Rhino 8.
"""

import json
import os
import sys
import traceback
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import Rhino
import Rhino.Commands
import Rhino.Display
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Render
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System
import System.Drawing

import plugin as plugin_constants
from plugin.document_settings import DocumentSettings
from plugin.material_thicknesses import MaterialThicknesses


# ---------------------------------------------------------------------------
# PodoCADPlugIn
# ---------------------------------------------------------------------------

class PodoCADPlugIn:
    """
    Main plugin singleton -- Python 3 equivalent of the .NET PodoCADPlugIn class.

    In the .NET version this derives from Rhino.PlugIns.PlugIn.  In CPython /
    RhinoCode scripts we cannot truly sub-class the native PlugIn type, so
    instead we keep a singleton that is wired into Rhino's event system
    manually via ``Initialize()``.
    """

    # Singleton reference
    _instance: Optional["PodoCADPlugIn"] = None

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        # Plugin metadata
        self.plugin_name: str = plugin_constants.__plugin_name__
        self.plugin_version: str = plugin_constants.__version__
        self.plugin_url: str = plugin_constants.__plugin_url__

        # Runtime flags
        self._initialized: bool = False
        self._should_write_document: bool = False
        self._terms_accepted: bool = False

        # Per-document caches (keyed by doc serial number)
        self._doc_settings: Dict[int, DocumentSettings] = {}
        self._doc_geometries: Dict[int, Dict[str, str]] = {}
        self._doc_material_thicknesses: Dict[int, MaterialThicknesses] = {}

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> "PodoCADPlugIn":
        """Return (and lazily create) the plugin singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialize -- wire into Rhino events
    # ------------------------------------------------------------------

    def Initialize(self) -> bool:
        """
        Main entry point.  Call once at plugin load time.

        Returns True if the plugin initialised successfully.
        """
        if self._initialized:
            return True

        try:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] Initializing v{self.plugin_version} ..."
            )

            # 1. Hook into document events
            Rhino.RhinoDoc.BeginSaveDocument += self._on_begin_save_document
            Rhino.RhinoDoc.EndSaveDocument += self._on_end_save_document
            Rhino.RhinoDoc.BeginOpenDocument += self._on_begin_open_document
            Rhino.RhinoDoc.EndOpenDocument += self._on_end_open_document
            Rhino.RhinoDoc.CloseDocument += self._on_close_document
            Rhino.RhinoDoc.NewDocument += self._on_new_document

            # 2. Setup layers in the active document (if one is open)
            doc = Rhino.RhinoDoc.ActiveDoc
            if doc is not None:
                self.SetupLayers(doc)
                self.SetRendering(doc)
                self.PopulatePerspectiveView(doc)
                self.PopulateClasses(doc)

            self._initialized = True
            Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Initialization complete.")
            return True

        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] Initialization error: {ex}\n"
                f"{traceback.format_exc()}"
            )
            return False

    # ------------------------------------------------------------------
    # Terms & Conditions dialog
    # ------------------------------------------------------------------

    def ShowTermsDialog(self) -> bool:
        """
        Display the Terms and Conditions to the user and ask for acceptance.

        Returns True if accepted.
        """
        if self._terms_accepted:
            return True

        terms_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Terms.txt",
        )
        terms_text = ""
        if os.path.isfile(terms_path):
            with open(terms_path, "r", encoding="utf-8") as fh:
                terms_text = fh.read()
        else:
            terms_text = (
                "Feet in Focus Shoe Kit Terms and Conditions\n"
                "Please visit https://ShoeLastMaker.com for full terms."
            )

        # Use Rhino's ListBox dialog as a simple viewer + accept/decline
        try:
            import Eto.Forms as ef
            import Eto.Drawing as ed

            dlg = ef.Dialog()
            dlg.Title = "Feet in Focus Shoe Kit - Terms and Conditions"
            dlg.ClientSize = ed.Size(620, 480)
            dlg.Padding = ef.Padding(10)

            layout = ef.DynamicLayout()
            layout.DefaultSpacing = ed.Size(5, 5)

            text_area = ef.TextArea()
            text_area.ReadOnly = True
            text_area.Text = terms_text
            text_area.Wrap = True
            layout.AddRow(text_area)
            layout.AddSpace()

            accepted = [False]

            btn_accept = ef.Button(Text="I Accept")
            btn_decline = ef.Button(Text="Decline")

            def on_accept(sender, e):
                accepted[0] = True
                dlg.Close()

            def on_decline(sender, e):
                dlg.Close()

            btn_accept.Click += on_accept
            btn_decline.Click += on_decline

            btn_row = ef.DynamicLayout()
            btn_row.AddRow(None, btn_decline, btn_accept)
            layout.AddRow(btn_row)

            dlg.Content = layout
            dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

            self._terms_accepted = accepted[0]
            return self._terms_accepted

        except Exception as ex:
            # Fallback to command-line acceptance
            Rhino.RhinoApp.WriteLine("=" * 60)
            Rhino.RhinoApp.WriteLine("Feet in Focus Shoe Kit - Terms and Conditions")
            Rhino.RhinoApp.WriteLine("=" * 60)
            for line in terms_text.split("\n")[:20]:
                Rhino.RhinoApp.WriteLine(line)
            Rhino.RhinoApp.WriteLine("...")
            Rhino.RhinoApp.WriteLine(
                "Full terms at https://ShoeLastMaker.com"
            )

            getter = Rhino.Input.Custom.GetString()
            getter.SetCommandPrompt(
                "Type 'accept' to agree to the Terms and Conditions"
            )
            result = getter.Get()
            if result == Rhino.Input.GetResult.String:
                if getter.StringResult().strip().lower() == "accept":
                    self._terms_accepted = True

            return self._terms_accepted

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def SetupLayers(self, doc: Rhino.RhinoDoc) -> None:
        """
        Ensure all required SLM layers exist in *doc*.

        Creates a parent ``SLM`` layer and child layers for each object
        class and utility category with appropriate colours.
        """
        prefix = plugin_constants.SLM_LAYER_PREFIX

        # Ensure the parent layer exists
        parent_index = doc.Layers.FindByFullPath(prefix, -1)
        if parent_index < 0:
            parent_layer = Rhino.DocObjects.Layer()
            parent_layer.Name = prefix
            parent_layer.Color = System.Drawing.Color.FromArgb(100, 100, 100)
            parent_index = doc.Layers.Add(parent_layer)

        parent_id = doc.Layers[parent_index].Id

        # Child layers
        for suffix, (r, g, b) in plugin_constants.DEFAULT_LAYER_COLORS.items():
            full_path = f"{prefix}::{suffix}"
            idx = doc.Layers.FindByFullPath(full_path, -1)
            if idx < 0:
                child = Rhino.DocObjects.Layer()
                child.Name = suffix
                child.ParentLayerId = parent_id
                child.Color = System.Drawing.Color.FromArgb(r, g, b)
                doc.Layers.Add(child)

        doc.Views.Redraw()

    def DeleteAllSLMLayers(self, doc: Rhino.RhinoDoc) -> int:
        """
        Delete every SLM layer and its contents from *doc*.

        Returns the number of layers removed.
        """
        prefix = plugin_constants.SLM_LAYER_PREFIX
        removed = 0
        layer_table = doc.Layers

        # Collect indices of layers whose full path starts with the prefix
        indices_to_delete: List[int] = []
        for i in range(layer_table.Count):
            layer = layer_table[i]
            if layer.IsDeleted:
                continue
            full_path = layer.FullPath
            if full_path == prefix or full_path.startswith(f"{prefix}::"):
                indices_to_delete.append(i)

        # Delete objects on those layers first
        for idx in indices_to_delete:
            layer = layer_table[idx]
            objs = doc.Objects.FindByLayer(layer)
            if objs:
                for obj in objs:
                    doc.Objects.Delete(obj, True)

        # Delete layers in reverse order (children before parents)
        for idx in sorted(indices_to_delete, reverse=True):
            if layer_table.Delete(idx, True):
                removed += 1

        if removed:
            doc.Views.Redraw()
        return removed

    # ------------------------------------------------------------------
    # Rendering setup
    # ------------------------------------------------------------------

    def SetRendering(self, doc: Rhino.RhinoDoc) -> None:
        """
        Configure default rendering settings for shoe-last visualization.

        Sets a neutral studio-like environment with a white background
        and two-point lighting suitable for inspecting curved surfaces.
        """
        try:
            # Background colour
            settings = doc.RenderSettings
            settings.BackgroundStyle = (
                Rhino.Render.BackgroundStyle.SolidColor
            )

            app_settings = Rhino.ApplicationSettings.AppearanceSettings
            app_settings.ViewportBackgroundColor = (
                System.Drawing.Color.White
            )

            # Default render material -- light grey matte
            mat = Rhino.Render.RenderMaterial.CreateBasicMaterial(
                Rhino.DocObjects.Material(), doc
            )
            mat.Name = "SLM_DefaultMaterial"
            mat.BeginChange(
                Rhino.Render.RenderContent.ChangeContexts.Program
            )
            mat.SetParameter("color",
                             System.Drawing.Color.FromArgb(210, 210, 215))
            mat.SetParameter("reflectivity", 0.15)
            mat.EndChange()

            # Only add the material if it doesn't already exist
            existing = doc.RenderMaterials.Where(
                lambda m: m.Name == "SLM_DefaultMaterial"
            )
            if not any(existing):
                doc.RenderMaterials.Add(mat)

        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] SetRendering warning: {ex}"
            )

    # ------------------------------------------------------------------
    # View population
    # ------------------------------------------------------------------

    def PopulatePerspectiveView(self, doc: Rhino.RhinoDoc) -> None:
        """
        Adjust the Perspective viewport to a standard shoe-last viewing angle.

        Camera target at origin, camera position at an elevated front-right
        angle, with a 35-mm lens equivalent.
        """
        try:
            for view in doc.Views:
                vp = view.ActiveViewport
                if vp.Name == "Perspective":
                    target = Rhino.Geometry.Point3d(0, 0, 30)
                    camera = Rhino.Geometry.Point3d(250, -300, 150)
                    vp.SetCameraTarget(target, True)
                    vp.SetCameraLocation(camera, True)
                    vp.Camera35mmLensLength = 50.0
                    vp.DisplayMode = (
                        Rhino.Display.DisplayModeDescription
                        .FindByName("Shaded")
                    )
                    view.Redraw()
                    break
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] PopulatePerspectiveView warning: {ex}"
            )

    # ------------------------------------------------------------------
    # Class population (object classification layers)
    # ------------------------------------------------------------------

    def PopulateClasses(self, doc: Rhino.RhinoDoc) -> None:
        """
        Ensure object-class layers for Last, Insert, Bottom, Foot exist
        as children of the SLM parent layer.  Each class layer holds the
        geometry for its respective category.
        """
        prefix = plugin_constants.SLM_LAYER_PREFIX
        parent_index = doc.Layers.FindByFullPath(prefix, -1)
        if parent_index < 0:
            # SetupLayers should have been called first
            self.SetupLayers(doc)
            parent_index = doc.Layers.FindByFullPath(prefix, -1)

        if parent_index < 0:
            return

        parent_id = doc.Layers[parent_index].Id

        for cls_name in plugin_constants.ALL_CLASSES:
            full_path = f"{prefix}::{cls_name}"
            idx = doc.Layers.FindByFullPath(full_path, -1)
            if idx < 0:
                lyr = Rhino.DocObjects.Layer()
                lyr.Name = cls_name
                lyr.ParentLayerId = parent_id
                color_tuple = plugin_constants.DEFAULT_LAYER_COLORS.get(
                    cls_name, (180, 180, 180)
                )
                lyr.Color = System.Drawing.Color.FromArgb(*color_tuple)
                doc.Layers.Add(lyr)

    # ------------------------------------------------------------------
    # Document read / write helpers
    # ------------------------------------------------------------------

    def ShouldCallWriteDocument(self) -> bool:
        """Return True when document data has changed and needs saving."""
        return self._should_write_document

    def MarkDocumentDirty(self) -> None:
        """Mark that plugin data needs to be written on next save."""
        self._should_write_document = True

    # -- Write ------------------------------------------------------------

    def WriteDocument(self, doc: Rhino.RhinoDoc) -> bool:
        """
        Persist all plugin data into *doc*'s user text so it is saved
        inside the .3dm file.

        Returns True on success.
        """
        try:
            serial = doc.RuntimeSerialNumber

            # Geometries
            geom_dict = self._doc_geometries.get(serial, {})
            geom_json = self.WriteSimplePropertiesSorted(geom_dict)
            doc.Strings.SetString(
                plugin_constants.DOC_KEY_GEOMETRIES, geom_json
            )

            # Settings
            settings = self._doc_settings.get(serial)
            if settings is not None:
                settings_json = json.dumps(
                    settings.to_dict(), indent=2, sort_keys=True
                )
                doc.Strings.SetString(
                    plugin_constants.DOC_KEY_SETTINGS, settings_json
                )

            # Material thicknesses
            mt = self._doc_material_thicknesses.get(serial)
            if mt is not None:
                mt_json = json.dumps(
                    mt.to_dict(), indent=2, sort_keys=True
                )
                doc.Strings.SetString(
                    plugin_constants.DOC_KEY_MATERIAL_THICKNESSES, mt_json
                )

            # Plugin version
            doc.Strings.SetString(
                plugin_constants.DOC_KEY_VERSION, self.plugin_version
            )

            self._should_write_document = False
            return True

        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] WriteDocument error: {ex}\n"
                f"{traceback.format_exc()}"
            )
            return False

    @staticmethod
    def WriteSimplePropertiesSorted(data: Dict[str, Any]) -> str:
        """
        Serialise *data* to a JSON string with keys sorted alphabetically.

        This mirrors the .NET ``WriteSimplePropertiesSorted`` method that
        was used to guarantee deterministic output for diffing.
        """
        ordered = OrderedDict(sorted(data.items()))
        return json.dumps(ordered, indent=2)

    # -- Read -------------------------------------------------------------

    def ReadDocument(self, doc: Rhino.RhinoDoc) -> bool:
        """
        Restore plugin data from *doc*'s user text.

        Supports both the current JSON approach and the legacy format
        used in older versions.

        Returns True on success.
        """
        try:
            serial = doc.RuntimeSerialNumber

            # Version stamp
            version_str = doc.Strings.GetValue(
                plugin_constants.DOC_KEY_VERSION
            )

            # Geometries
            geom_raw = doc.Strings.GetValue(
                plugin_constants.DOC_KEY_GEOMETRIES
            )
            if geom_raw:
                geom_dict = self.ReadJsonApproach(geom_raw)
                if geom_dict is None:
                    geom_dict = self.ReadOldApproachHelper(geom_raw)
                self._doc_geometries[serial] = geom_dict or {}
            else:
                self._doc_geometries[serial] = {}

            # Settings
            settings_raw = doc.Strings.GetValue(
                plugin_constants.DOC_KEY_SETTINGS
            )
            if settings_raw:
                try:
                    settings_data = json.loads(settings_raw)
                    self._doc_settings[serial] = DocumentSettings.from_dict(
                        settings_data
                    )
                except Exception:
                    self._doc_settings[serial] = DocumentSettings.Create()
            else:
                self._doc_settings[serial] = DocumentSettings.Create()

            # Material thicknesses
            mt_raw = doc.Strings.GetValue(
                plugin_constants.DOC_KEY_MATERIAL_THICKNESSES
            )
            if mt_raw:
                try:
                    mt_data = json.loads(mt_raw)
                    self._doc_settings[serial]  # (already set above)
                    self._doc_material_thicknesses[serial] = (
                        MaterialThicknesses.from_dict(mt_data)
                    )
                except Exception:
                    self._doc_material_thicknesses[serial] = (
                        MaterialThicknesses()
                    )
            else:
                self._doc_material_thicknesses[serial] = MaterialThicknesses()

            return True

        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] ReadDocument error: {ex}\n"
                f"{traceback.format_exc()}"
            )
            return False

    @staticmethod
    def ReadJsonApproach(raw: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse *raw* as JSON and return the resulting dict.

        Returns None when *raw* is not valid JSON so the caller can fall
        back to the legacy parser.
        """
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return None

    @staticmethod
    def ReadOldApproachHelper(raw: str) -> Optional[Dict[str, str]]:
        """
        Parse the legacy pipe-delimited format used in older .NET
        plugin versions::

            key1|value1||key2|value2||...

        Returns a dict or None.
        """
        if not raw or "||" not in raw:
            return None
        try:
            result: Dict[str, str] = {}
            pairs = raw.split("||")
            for pair in pairs:
                if "|" not in pair:
                    continue
                key, _, value = pair.partition("|")
                key = key.strip()
                if key:
                    result[key] = value
            return result if result else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Geometry store/retrieve
    # ------------------------------------------------------------------

    def StoreGeometry(self, doc: Rhino.RhinoDoc, key: str,
                      geometry: Rhino.Geometry.GeometryBase) -> None:
        """
        Serialise *geometry* and store it under *key* for *doc*.

        The geometry is round-tripped through Rhino's own 3dm
        serialisation so that any GeometryBase subclass is handled.
        """
        serial = doc.RuntimeSerialNumber
        if serial not in self._doc_geometries:
            self._doc_geometries[serial] = {}

        try:
            # Serialize geometry to a base-64 encoded 3dm chunk
            import System.IO
            opts = Rhino.FileIO.SerializationOptions()
            bytes_array = Rhino.Runtime.CommonObject.ToByteArray(
                geometry, opts
            )
            b64 = System.Convert.ToBase64String(bytes_array)
            self._doc_geometries[serial][key] = b64
            self._should_write_document = True
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] StoreGeometry error for '{key}': {ex}"
            )

    def GetGeometryFromStoredString(
        self, doc: Rhino.RhinoDoc, key: str
    ) -> Optional[Rhino.Geometry.GeometryBase]:
        """
        Retrieve and deserialise geometry previously stored under *key*.

        Returns None when the key is missing or deserialization fails.
        """
        serial = doc.RuntimeSerialNumber
        geom_dict = self._doc_geometries.get(serial, {})
        b64 = geom_dict.get(key)
        if not b64:
            return None

        try:
            bytes_array = System.Convert.FromBase64String(b64)
            geom = Rhino.Runtime.CommonObject.FromByteArray(bytes_array)
            if isinstance(geom, Rhino.Geometry.GeometryBase):
                return geom
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] GetGeometryFromStoredString error "
                f"for '{key}': {ex}"
            )
        return None

    # ------------------------------------------------------------------
    # Object helpers
    # ------------------------------------------------------------------

    @staticmethod
    def GetIDFromDocObjectName(
        doc: Rhino.RhinoDoc, name: str
    ) -> Optional[System.Guid]:
        """
        Find the first object in *doc* whose Name attribute matches *name*.

        Returns the Guid of the object, or None.
        """
        settings = Rhino.DocObjects.ObjectEnumeratorSettings()
        settings.NameFilter = name
        settings.DeletedObjects = False
        for obj in doc.Objects.GetObjectList(settings):
            return obj.Id
        return None

    # ------------------------------------------------------------------
    # Document-settings convenience accessors
    # ------------------------------------------------------------------

    def GetDocumentSettings(
        self, doc: Rhino.RhinoDoc
    ) -> "DocumentSettings":
        """Return (or create) the DocumentSettings for *doc*."""
        serial = doc.RuntimeSerialNumber
        if serial not in self._doc_settings:
            self._doc_settings[serial] = DocumentSettings.Create()
        return self._doc_settings[serial]

    def SetDocumentSettings(
        self, doc: Rhino.RhinoDoc, settings: "DocumentSettings"
    ) -> None:
        """Assign *settings* to *doc* and mark dirty."""
        self._doc_settings[doc.RuntimeSerialNumber] = settings
        self._should_write_document = True

    def GetMaterialThicknesses(
        self, doc: Rhino.RhinoDoc
    ) -> "MaterialThicknesses":
        """Return (or create) MaterialThicknesses for *doc*."""
        serial = doc.RuntimeSerialNumber
        if serial not in self._doc_material_thicknesses:
            self._doc_material_thicknesses[serial] = MaterialThicknesses()
        return self._doc_material_thicknesses[serial]

    def SetMaterialThicknesses(
        self, doc: Rhino.RhinoDoc, mt: "MaterialThicknesses"
    ) -> None:
        self._doc_material_thicknesses[doc.RuntimeSerialNumber] = mt
        self._should_write_document = True

    # ------------------------------------------------------------------
    # Rhino document event handlers
    # ------------------------------------------------------------------

    def _on_begin_save_document(self, sender, e) -> None:
        """Called just before Rhino saves the .3dm file."""
        try:
            doc = e.Document
            if doc is not None and self.ShouldCallWriteDocument():
                self.WriteDocument(doc)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] _on_begin_save_document error: {ex}"
            )

    def _on_end_save_document(self, sender, e) -> None:
        """Called after Rhino finishes saving."""
        pass  # No action needed after save completes

    def _on_begin_open_document(self, sender, e) -> None:
        """Called just before Rhino opens a .3dm file."""
        pass  # Preparation if needed

    def _on_end_open_document(self, sender, e) -> None:
        """Called after a document is opened -- read our data."""
        try:
            doc = e.Document
            if doc is not None:
                self.ReadDocument(doc)
                self.SetupLayers(doc)
                self.PopulateClasses(doc)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] _on_end_open_document error: {ex}"
            )

    def _on_close_document(self, sender, e) -> None:
        """Called when a document is being closed -- clean up caches."""
        try:
            doc = e.Document
            if doc is not None:
                serial = doc.RuntimeSerialNumber
                self._doc_settings.pop(serial, None)
                self._doc_geometries.pop(serial, None)
                self._doc_material_thicknesses.pop(serial, None)
        except Exception:
            pass

    def _on_new_document(self, sender, e) -> None:
        """Called when a brand-new document is created."""
        try:
            doc = e.Document
            if doc is not None:
                self.SetupLayers(doc)
                self.SetRendering(doc)
                self.PopulatePerspectiveView(doc)
                self.PopulateClasses(doc)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] _on_new_document error: {ex}"
            )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<PodoCADPlugIn v{self.plugin_version}>"
