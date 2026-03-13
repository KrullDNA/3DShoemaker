"""
podoCAD_panel.py - Main dockable side panel for 3DShoemaker.

PodoCADPanel is the primary UI surface of the plugin.  It lives in
Rhino's side-panel area and provides categorised buttons for every
major command, curve-editing controls, clipping-plane management,
layer visibility toggles, and a status bar.
"""

from typing import Dict, List, Optional

import Rhino
import Rhino.Display
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.UI
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

import Eto.Forms as forms
import Eto.Drawing as drawing

import plugin as plugin_constants


# ---------------------------------------------------------------------------
# Command descriptors: (label, command_method_name, tooltip)
# Grouped by category for the panel layout.
# ---------------------------------------------------------------------------

_CMD_BUILD = [
    ("New Last", "cmd_new_last", "Create a new shoe last from template"),
    ("Import Last", "cmd_import_last", "Import a last from file"),
    ("Build Insole", "cmd_build_insole", "Generate insole from foot data"),
    ("Build Bottom", "cmd_build_bottom", "Generate outsole/midsole geometry"),
    ("Import Foot", "cmd_import_foot", "Import a 2D/3D foot scan"),
]

_CMD_EDIT = [
    ("Edit Last", "cmd_edit_last", "Modify last surface interactively"),
    ("Edit Insole", "cmd_edit_insole", "Modify insole geometry"),
    ("Morph", "cmd_morph", "Morph geometry from source to target"),
    ("Edit Dimensions", "cmd_edit_dimensions", "View/edit measurement dimensions"),
    ("Mirror", "cmd_mirror", "Mirror geometry to opposite foot"),
]

_CMD_COMPONENTS = [
    ("Add Toe Cap", "cmd_add_toe_cap", "Add a toe-cap component"),
    ("Add Heel Counter", "cmd_add_heel_counter", "Add a heel counter"),
    ("Add Arch Support", "cmd_add_arch_support", "Add arch support geometry"),
    ("Add Met Pad", "cmd_add_met_pad", "Add a metatarsal pad"),
    ("Add Posting", "cmd_add_posting", "Add medial/lateral posting"),
]

_CMD_GRADE = [
    ("Grade Footwear", "cmd_grade_footwear", "Grade to a different shoe size"),
    ("Foot Measurements", "cmd_foot_measurements", "Enter foot measurements"),
]

_CMD_EXPORT = [
    ("3D Print Prep", "cmd_print_prep", "Prepare for 3D printing"),
    ("Vacuum Form", "cmd_vacuum_form", "Prepare for vacuum forming"),
    ("Export STL", "cmd_export_stl", "Export as STL mesh"),
    ("Export OBJ", "cmd_export_obj", "Export as OBJ"),
]

_CMD_VIEW = [
    ("Reset View", "cmd_reset_view", "Reset to default viewing angle"),
    ("Toggle Construction", "cmd_toggle_construction", "Show/hide construction lines"),
    ("Toggle Measurements", "cmd_toggle_measurements", "Show/hide measurement display"),
]

_CMD_FOOT = [
    ("Show Foot", "cmd_show_foot", "Show the foot scan/model"),
    ("Hide Foot", "cmd_hide_foot", "Hide the foot scan/model"),
    ("Foot Overlay", "cmd_foot_overlay", "Overlay foot on last"),
]

# Curve types available in the Edit Curve dropdown
_EDIT_CURVE_TYPES = [
    "Toe Profile",
    "Heel Profile",
    "Medial Outline",
    "Lateral Outline",
    "Bottom Profile",
    "Cone Line",
    "Feather Edge",
    "Tread Pattern",
]


class PodoCADPanel(forms.Panel):
    """
    Main dockable side panel for the 3DShoemaker plugin.

    Provides categorised command buttons, curve-editing controls,
    clipping-plane management, layer visibility toggles, and status
    indicators.
    """

    # Class-level reference for singleton access
    _instance: Optional["PodoCADPanel"] = None

    def __init__(self):
        super().__init__()
        PodoCADPanel._instance = self

        self._buttons: Dict[str, forms.Button] = {}
        self._clipping_plane_ids: List[System.Guid] = []
        self._layer_visibility: Dict[str, bool] = {}

        self._build_ui()
        self.Initialized()

    @classmethod
    def instance(cls) -> Optional["PodoCADPanel"]:
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def Initialized(self):
        """
        Post-construction setup.  Called once after the panel is created
        and Rhino has finished loading.
        """
        self._refresh_layer_visibility()
        self.SidePanelButtonEnableStatusChange()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Root scrollable so the panel works at any dock size
        scrollable = forms.Scrollable()
        scrollable.Border = forms.BorderType.None_
        scrollable.ExpandContentWidth = True

        root = forms.DynamicLayout()
        root.DefaultSpacing = drawing.Size(4, 4)
        root.Padding = drawing.Padding(6)

        # Header
        header = forms.Label(
            Text="3DShoemaker",
            Font=drawing.Font(drawing.SystemFont.Bold, 12),
            TextAlignment=forms.TextAlignment.Center,
        )
        root.AddRow(header)
        root.AddRow(self._separator())

        # --- Build section ------------------------------------------------
        root.AddRow(self._create_section("Build", _CMD_BUILD))
        root.AddRow(self._separator())

        # --- Edit section -------------------------------------------------
        root.AddRow(self._create_section("Edit", _CMD_EDIT))

        # Edit curve dropdown
        curve_row = forms.DynamicLayout()
        curve_row.DefaultSpacing = drawing.Size(4, 4)
        curve_row.AddRow(forms.Label(Text="Edit Curve:"))

        self._cmb_edit_curve = forms.DropDown()
        for ct in _EDIT_CURVE_TYPES:
            self._cmb_edit_curve.Items.Add(forms.ListItem(Text=ct))
        self._cmb_edit_curve.SelectedIndex = 0
        self._cmb_edit_curve.SelectedIndexChanged += self.cmbEditCurve_Click
        curve_row.AddRow(self._cmb_edit_curve)
        root.AddRow(curve_row)
        root.AddRow(self._separator())

        # --- Components section -------------------------------------------
        root.AddRow(self._create_section("Components", _CMD_COMPONENTS))
        root.AddRow(self._separator())

        # --- Grade section ------------------------------------------------
        root.AddRow(self._create_section("Grade", _CMD_GRADE))
        root.AddRow(self._separator())

        # --- Export section ------------------------------------------------
        root.AddRow(self._create_section("Export", _CMD_EXPORT))
        root.AddRow(self._separator())

        # --- View section -------------------------------------------------
        root.AddRow(self._create_section("View", _CMD_VIEW))

        # Clipping plane controls
        clip_row = forms.DynamicLayout()
        clip_row.DefaultSpacing = drawing.Size(4, 4)
        btn_clip_add = forms.Button(Text="Add Clipping Plane")
        btn_clip_add.Click += self._on_add_clipping_plane
        btn_clip_remove = forms.Button(Text="Remove Clipping Planes")
        btn_clip_remove.Click += self._on_remove_clipping_planes

        self._num_clip_position = forms.NumericStepper()
        self._num_clip_position.MinValue = -500
        self._num_clip_position.MaxValue = 500
        self._num_clip_position.DecimalPlaces = 1
        self._num_clip_position.Increment = 5.0
        self._num_clip_position.Value = 0
        self._num_clip_position.ValueChanged += self._on_clip_position_changed

        clip_row.AddRow(btn_clip_add, btn_clip_remove)
        clip_row.AddRow(forms.Label(Text="Clip Position:"), self._num_clip_position)
        root.AddRow(clip_row)
        root.AddRow(self._separator())

        # --- Layer visibility section -------------------------------------
        root.AddRow(self._create_layer_toggles())
        root.AddRow(self._separator())

        # --- Foot section -------------------------------------------------
        root.AddRow(self._create_section("Foot", _CMD_FOOT))
        root.AddRow(self._separator())

        # --- Status panel -------------------------------------------------
        status_group = forms.GroupBox(Text="Status")
        status_layout = forms.DynamicLayout()
        status_layout.DefaultSpacing = drawing.Size(4, 2)
        status_layout.Padding = drawing.Padding(6)

        self._lbl_status_edition = forms.Label(Text="Edition: --")
        self._lbl_status_size = forms.Label(Text="Size: --")
        self._lbl_status_foot = forms.Label(Text="Foot: --")
        self._lbl_status_layers = forms.Label(Text="Layers: --")

        status_layout.AddRow(self._lbl_status_edition)
        status_layout.AddRow(self._lbl_status_size)
        status_layout.AddRow(self._lbl_status_foot)
        status_layout.AddRow(self._lbl_status_layers)

        status_group.Content = status_layout
        root.AddRow(status_group)

        # --- Options button at bottom -------------------------------------
        btn_options = forms.Button(Text="Options...")
        btn_options.Click += self._on_options
        root.AddRow(btn_options)

        scrollable.Content = root
        self.Content = scrollable

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _create_section(self, title: str,
                        commands: List[tuple]) -> forms.GroupBox:
        """Create a GroupBox containing buttons for the given commands."""
        group = forms.GroupBox(Text=title)
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(3, 3)
        layout.Padding = drawing.Padding(4)

        for label, method_name, tooltip in commands:
            btn = forms.Button(Text=label, ToolTip=tooltip)
            btn.Tag = method_name
            btn.Click += self._on_command_button
            self._buttons[method_name] = btn
            layout.AddRow(btn)

        group.Content = layout
        return group

    @staticmethod
    def _separator() -> forms.Panel:
        """Create a thin horizontal separator line."""
        sep = forms.Panel()
        sep.Height = 1
        sep.BackgroundColor = drawing.Colors.Gray
        return sep

    def _create_layer_toggles(self) -> forms.GroupBox:
        """Create layer visibility toggle checkboxes."""
        group = forms.GroupBox(Text="Layer Visibility")
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(3, 3)
        layout.Padding = drawing.Padding(4)

        self._layer_checkboxes: Dict[str, forms.CheckBox] = {}
        for layer_name in plugin_constants.DEFAULT_LAYER_COLORS:
            chk = forms.CheckBox(Text=layer_name)
            chk.Checked = True
            chk.Tag = layer_name
            chk.CheckedChanged += self._on_layer_toggle
            self._layer_checkboxes[layer_name] = chk
            layout.AddRow(chk)

        group.Content = layout
        return group

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _on_command_button(self, sender, e):
        """Dispatch a command button click to the appropriate handler."""
        btn = sender
        method_name = btn.Tag if hasattr(btn, "Tag") else None
        if method_name and hasattr(self, method_name):
            getattr(self, method_name)()
        elif method_name:
            # Fall back to running a Rhino command with matching name
            rhino_cmd = method_name.replace("cmd_", "SLM_")
            Rhino.RhinoApp.RunScript(rhino_cmd, False)

    # ------------------------------------------------------------------
    # Build commands
    # ------------------------------------------------------------------

    def cmd_new_last(self):
        Rhino.RhinoApp.RunScript("SLM_NewLast", False)

    def cmd_import_last(self):
        Rhino.RhinoApp.RunScript("SLM_ImportLast", False)

    def cmd_build_insole(self):
        Rhino.RhinoApp.RunScript("SLM_BuildInsole", False)

    def cmd_build_bottom(self):
        Rhino.RhinoApp.RunScript("SLM_BuildBottom", False)

    def cmd_import_foot(self):
        from plugin.forms.import_foot_form import ImportFootForm
        dlg = ImportFootForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    # ------------------------------------------------------------------
    # Edit commands
    # ------------------------------------------------------------------

    def cmd_edit_last(self):
        Rhino.RhinoApp.RunScript("SLM_EditLast", False)

    def cmd_edit_insole(self):
        Rhino.RhinoApp.RunScript("SLM_EditInsole", False)

    def cmd_morph(self):
        from plugin.forms.morph_form import MorphForm
        dlg = MorphForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    def cmd_edit_dimensions(self):
        from plugin.forms.edit_dimension_form import EditDimensionForm
        dlg = EditDimensionForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    def cmd_mirror(self):
        Rhino.RhinoApp.RunScript("SLM_Mirror", False)

    # ------------------------------------------------------------------
    # Component commands
    # ------------------------------------------------------------------

    def cmd_add_toe_cap(self):
        Rhino.RhinoApp.RunScript("SLM_AddToeCap", False)

    def cmd_add_heel_counter(self):
        Rhino.RhinoApp.RunScript("SLM_AddHeelCounter", False)

    def cmd_add_arch_support(self):
        Rhino.RhinoApp.RunScript("SLM_AddArchSupport", False)

    def cmd_add_met_pad(self):
        Rhino.RhinoApp.RunScript("SLM_AddMetPad", False)

    def cmd_add_posting(self):
        Rhino.RhinoApp.RunScript("SLM_AddPosting", False)

    # ------------------------------------------------------------------
    # Grade commands
    # ------------------------------------------------------------------

    def cmd_grade_footwear(self):
        from plugin.forms.grade_footwear_form import GradeFootwearForm
        dlg = GradeFootwearForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    def cmd_foot_measurements(self):
        from plugin.forms.foot_measurement_form import FootMeasurementForm
        dlg = FootMeasurementForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    # ------------------------------------------------------------------
    # Export commands
    # ------------------------------------------------------------------

    def cmd_print_prep(self):
        from plugin.forms.print_prep_form import PrintPrepForm
        dlg = PrintPrepForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    def cmd_vacuum_form(self):
        from plugin.forms.vacuum_form import VacuumForm
        dlg = VacuumForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    def cmd_export_stl(self):
        Rhino.RhinoApp.RunScript("SLM_ExportSTL", False)

    def cmd_export_obj(self):
        Rhino.RhinoApp.RunScript("SLM_ExportOBJ", False)

    # ------------------------------------------------------------------
    # View commands
    # ------------------------------------------------------------------

    def cmd_reset_view(self):
        from plugin.plugin_main import PodoCADPlugIn
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc:
            PodoCADPlugIn.instance().PopulatePerspectiveView(doc)

    def cmd_toggle_construction(self):
        self._toggle_layer_visibility("Construction")

    def cmd_toggle_measurements(self):
        self._toggle_layer_visibility("Measurements")

    # ------------------------------------------------------------------
    # Foot commands
    # ------------------------------------------------------------------

    def cmd_show_foot(self):
        self._set_layer_visible("Foot", True)

    def cmd_hide_foot(self):
        self._set_layer_visible("Foot", False)

    def cmd_foot_overlay(self):
        Rhino.RhinoApp.RunScript("SLM_FootOverlay", False)

    # ------------------------------------------------------------------
    # Edit curve dropdown
    # ------------------------------------------------------------------

    def cmbEditCurve_Click(self, sender, e):
        """
        Handle curve-type selection from the Edit Curve dropdown.

        Activates the corresponding curve editing tool in Rhino.
        """
        idx = self._cmb_edit_curve.SelectedIndex
        if idx < 0 or idx >= len(_EDIT_CURVE_TYPES):
            return

        curve_type = _EDIT_CURVE_TYPES[idx]
        # Map curve types to Rhino command names
        cmd_map = {
            "Toe Profile": "SLM_EditToeProfile",
            "Heel Profile": "SLM_EditHeelProfile",
            "Medial Outline": "SLM_EditMedialOutline",
            "Lateral Outline": "SLM_EditLateralOutline",
            "Bottom Profile": "SLM_EditBottomProfile",
            "Cone Line": "SLM_EditConeLine",
            "Feather Edge": "SLM_EditFeatherEdge",
            "Tread Pattern": "SLM_EditTreadPattern",
        }

        cmd = cmd_map.get(curve_type)
        if cmd:
            Rhino.RhinoApp.RunScript(cmd, False)

    # ------------------------------------------------------------------
    # Clipping planes
    # ------------------------------------------------------------------

    def _on_add_clipping_plane(self, sender, e):
        """Add a clipping plane at the current position."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        try:
            position = self._num_clip_position.Value
            plane = Rhino.Geometry.Plane(
                Rhino.Geometry.Point3d(0, 0, position),
                Rhino.Geometry.Vector3d.ZAxis,
            )

            # Get active viewport IDs for clipping
            view_ids = []
            for view in doc.Views:
                view_ids.append(view.ActiveViewportID)

            clip_id = doc.Objects.AddClippingPlane(
                plane, 300, 300, view_ids
            )
            if clip_id != System.Guid.Empty:
                self._clipping_plane_ids.append(clip_id)
                doc.Views.Redraw()

        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[3DShoemaker] Add clipping plane error: {ex}"
            )

    def _on_remove_clipping_planes(self, sender, e):
        """Remove all clipping planes added by this panel."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        for cp_id in self._clipping_plane_ids:
            doc.Objects.Delete(cp_id, True)

        self._clipping_plane_ids.clear()
        doc.Views.Redraw()

    def _on_clip_position_changed(self, sender, e):
        """Move existing clipping planes to the new position."""
        self.UpdateClippingPlanes()

    def UpdateClippingPlanes(self):
        """
        Reposition all managed clipping planes to match the current
        position slider value.
        """
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        position = self._num_clip_position.Value
        move_vector = Rhino.Geometry.Vector3d(0, 0, 0)

        for cp_id in self._clipping_plane_ids:
            obj = doc.Objects.FindId(cp_id)
            if obj is None:
                continue

            geom = obj.Geometry
            if not isinstance(geom, Rhino.Geometry.ClippingPlaneSurface):
                continue

            current_z = geom.Plane.Origin.Z
            delta = position - current_z
            xform = Rhino.Geometry.Transform.Translation(0, 0, delta)
            doc.Objects.Transform(cp_id, xform, True)

        doc.Views.Redraw()

    # ------------------------------------------------------------------
    # Layer visibility
    # ------------------------------------------------------------------

    def _on_layer_toggle(self, sender, e):
        """Handle a layer visibility checkbox toggle."""
        chk = sender
        layer_name = chk.Tag if hasattr(chk, "Tag") else None
        if layer_name:
            visible = chk.Checked == True
            self._set_layer_visible(layer_name, visible)

    def _toggle_layer_visibility(self, layer_suffix: str):
        """Toggle visibility of a specific SLM layer."""
        currently_visible = self._layer_visibility.get(layer_suffix, True)
        self._set_layer_visible(layer_suffix, not currently_visible)
        # Update checkbox if it exists
        chk = self._layer_checkboxes.get(layer_suffix)
        if chk:
            chk.Checked = not currently_visible

    def _set_layer_visible(self, layer_suffix: str, visible: bool):
        """Set visibility of a specific SLM child layer."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        full_path = f"SLM::{layer_suffix}"
        layer_idx = doc.Layers.FindByFullPath(full_path, -1)
        if layer_idx >= 0:
            layer = doc.Layers[layer_idx]
            layer.IsVisible = visible
            doc.Layers.Modify(layer, layer_idx, True)
            self._layer_visibility[layer_suffix] = visible
            doc.Views.Redraw()

    def UpdateLayerVisibility(self):
        """
        Synchronise all layer visibility checkboxes with the actual
        Rhino layer state.
        """
        self._refresh_layer_visibility()

    def _refresh_layer_visibility(self):
        """Read current layer visibility from the document."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        for layer_name, chk in self._layer_checkboxes.items():
            full_path = f"SLM::{layer_name}"
            layer_idx = doc.Layers.FindByFullPath(full_path, -1)
            if layer_idx >= 0:
                visible = doc.Layers[layer_idx].IsVisible
                chk.Checked = visible
                self._layer_visibility[layer_name] = visible

    # ------------------------------------------------------------------
    # Status panel
    # ------------------------------------------------------------------

    def SidePanelButtonEnableStatusChange(self):
        """
        Update button enabled/disabled states and the status panel
        based on the current plugin and document state.
        """
        from plugin.plugin_main import PodoCADPlugIn
        plug = PodoCADPlugIn.instance()
        doc = Rhino.RhinoDoc.ActiveDoc

        # Update status labels
        self._lbl_status_edition.Text = f"Edition: {plug.edition}"

        if doc is not None:
            ds = plug.GetDocumentSettings(doc)
            self._lbl_status_size.Text = (
                f"Size: {ds.last_size} {ds.last_size_system}"
            )
            self._lbl_status_foot.Text = f"Foot: {ds.foot_side}"

            # Count SLM layers
            slm_count = sum(
                1 for i in range(doc.Layers.Count)
                if not doc.Layers[i].IsDeleted
                and doc.Layers[i].FullPath.startswith("SLM")
            )
            self._lbl_status_layers.Text = f"Layers: {slm_count}"
        else:
            self._lbl_status_size.Text = "Size: --"
            self._lbl_status_foot.Text = "Foot: --"
            self._lbl_status_layers.Text = "Layers: --"

        # Enable/disable commands based on license
        commercial_only = [
            "cmd_grade_footwear", "cmd_vacuum_form",
            "cmd_print_prep", "cmd_export_stl", "cmd_export_obj",
        ]
        has_license = plug.is_licensed

        for method_name, btn in self._buttons.items():
            if method_name in commercial_only:
                btn.Enabled = has_license
            else:
                btn.Enabled = True

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    def _on_options(self, sender, e):
        from plugin.forms.options_form import OptionsForm
        dlg = OptionsForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
        # Refresh status after options may have changed
        self.SidePanelButtonEnableStatusChange()
