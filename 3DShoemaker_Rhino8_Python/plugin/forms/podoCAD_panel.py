"""
podoCAD_panel.py - Main dockable side panel for Feet in Focus Shoe Kit.

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
    ("New Build", "cmd_new_build", "Create a new shoe last build"),
    ("Import Last", "cmd_import_last", "Import a last from file"),
    ("Create Insole", "cmd_create_insole", "Generate insole from last"),
    ("Create Sole", "cmd_create_sole", "Generate outsole geometry"),
    ("Import Foot", "cmd_import_foot", "Import a 2D/3D foot scan"),
]

_CMD_EDIT = [
    ("Edit Curve", "cmd_edit_curve_mode", "Enter curve editing mode"),
    ("End Edit", "cmd_end_edit", "Exit editing mode"),
    ("Morph", "cmd_morph", "Morph geometry from source to target"),
    ("Sculpt", "cmd_sculpt", "Sculpt surfaces interactively"),
    ("Blend Surfaces", "cmd_blend_surfaces", "Blend between two surfaces"),
]

_CMD_COMPONENTS = [
    ("Create Heel", "cmd_create_heel", "Create the heel"),
    ("Create Top Piece", "cmd_create_top_piece", "Create the top piece"),
    ("Create Shank Board", "cmd_create_shank_board", "Create the shank board"),
    ("Create Met Pad", "cmd_create_met_pad", "Add a metatarsal pad"),
    ("Create Upper Bodies", "cmd_create_upper_bodies", "Generate upper pattern bodies"),
    ("Create Mockup", "cmd_create_mockup", "Create a full footwear mockup"),
]

_CMD_GRADE = [
    ("Grade Footwear", "cmd_grade_footwear", "Grade to a different shoe size"),
    ("Batch Grade", "cmd_batch_grade", "Grade to multiple sizes at once"),
    ("Foot Measurements", "cmd_foot_measurements", "Enter foot measurements"),
]

_CMD_EXPORT = [
    ("3D Print Prep", "cmd_print_prep", "Prepare for 3D printing"),
    ("Vacuum Form", "cmd_vacuum_form", "Prepare for vacuum forming"),
    ("Export Last", "cmd_export_last", "Export the last to file"),
    ("Render Components", "cmd_render_components", "Render component views"),
]

_CMD_VIEW = [
    ("Gaze At Last", "cmd_gaze_at_last", "Set viewport to look at the last"),
    ("Toggle Construction", "cmd_toggle_construction", "Show/hide construction lines"),
    ("Toggle Measurements", "cmd_toggle_measurements", "Show/hide measurement display"),
    ("Clipping Planes", "cmd_draw_clipping_planes", "Draw clipping planes"),
]

_CMD_FOOT = [
    ("Show Foot", "cmd_show_foot", "Show the foot scan/model"),
    ("Hide Foot", "cmd_hide_foot", "Hide the foot scan/model"),
    ("Analyze Plantar", "cmd_analyze_plantar", "Analyze plantar foot scan"),
]

_CMD_ORTHOTIC = [
    ("Make Orthotic", "cmd_make_orthotic", "Create orthotic from foot/last data"),
    ("Adjust To Blank", "cmd_adjust_to_blank", "Fit orthotic to a blank"),
    ("Print Prep Orthotic", "cmd_print_prep_orthotic", "Prepare orthotic for 3D printing"),
]

_CMD_SANDAL = [
    ("Build Sandal", "cmd_build_sandal", "Create a sandal from a last"),
    ("Build Insert", "cmd_build_insert", "Create a removable insert"),
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
    Main dockable side panel for the Feet in Focus Shoe Kit plugin.

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
            Text="Feet in Focus Shoe Kit",
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

        # --- Orthotic section ---------------------------------------------
        root.AddRow(self._create_section("Orthotic", _CMD_ORTHOTIC))
        root.AddRow(self._separator())

        # --- Sandal section -----------------------------------------------
        root.AddRow(self._create_section("Sandal", _CMD_SANDAL))
        root.AddRow(self._separator())

        # --- Status panel -------------------------------------------------
        status_group = forms.GroupBox(Text="Status")
        status_layout = forms.DynamicLayout()
        status_layout.DefaultSpacing = drawing.Size(4, 2)
        status_layout.Padding = drawing.Padding(6)

        self._lbl_status_size = forms.Label(Text="Size: --")
        self._lbl_status_foot = forms.Label(Text="Foot: --")
        self._lbl_status_layers = forms.Label(Text="Layers: --")

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

    # ------------------------------------------------------------------
    # Build commands
    # ------------------------------------------------------------------

    def cmd_new_build(self):
        Rhino.RhinoApp.RunScript("NewBuild", False)

    def cmd_import_last(self):
        Rhino.RhinoApp.RunScript("ImportLast", False)

    def cmd_create_insole(self):
        Rhino.RhinoApp.RunScript("CreateInsole", False)

    def cmd_create_sole(self):
        Rhino.RhinoApp.RunScript("CreateSole", False)

    def cmd_import_foot(self):
        Rhino.RhinoApp.RunScript("ImportFoot", False)

    # ------------------------------------------------------------------
    # Edit commands
    # ------------------------------------------------------------------

    def cmd_edit_curve_mode(self):
        Rhino.RhinoApp.RunScript("EditCurve", False)

    def cmd_end_edit(self):
        Rhino.RhinoApp.RunScript("EndEdit", False)

    def cmd_morph(self):
        Rhino.RhinoApp.RunScript("NewMorph", False)

    def cmd_sculpt(self):
        Rhino.RhinoApp.RunScript("Sculpt", False)

    def cmd_blend_surfaces(self):
        Rhino.RhinoApp.RunScript("BlendSurfaceToSurface", False)

    # ------------------------------------------------------------------
    # Component commands
    # ------------------------------------------------------------------

    def cmd_create_heel(self):
        Rhino.RhinoApp.RunScript("CreateHeel", False)

    def cmd_create_top_piece(self):
        Rhino.RhinoApp.RunScript("CreateTopPiece", False)

    def cmd_create_shank_board(self):
        Rhino.RhinoApp.RunScript("CreateShankBoard", False)

    def cmd_create_met_pad(self):
        Rhino.RhinoApp.RunScript("CreateMetPad", False)

    def cmd_create_upper_bodies(self):
        Rhino.RhinoApp.RunScript("CreateUpperBodies", False)

    def cmd_create_mockup(self):
        Rhino.RhinoApp.RunScript("CreateMockup", False)

    # ------------------------------------------------------------------
    # Grade commands
    # ------------------------------------------------------------------

    def cmd_grade_footwear(self):
        Rhino.RhinoApp.RunScript("GradeFootwear", False)

    def cmd_batch_grade(self):
        Rhino.RhinoApp.RunScript("BatchGrade", False)

    def cmd_foot_measurements(self):
        from plugin.forms.foot_measurement_form import FootMeasurementForm
        dlg = FootMeasurementForm()
        dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    # ------------------------------------------------------------------
    # Export commands
    # ------------------------------------------------------------------

    def cmd_print_prep(self):
        Rhino.RhinoApp.RunScript("PrintPrep", False)

    def cmd_vacuum_form(self):
        Rhino.RhinoApp.RunScript("VacuumFormCommand", False)

    def cmd_export_last(self):
        Rhino.RhinoApp.RunScript("ExportLast", False)

    def cmd_render_components(self):
        Rhino.RhinoApp.RunScript("RenderComponents", False)

    # ------------------------------------------------------------------
    # View commands
    # ------------------------------------------------------------------

    def cmd_gaze_at_last(self):
        Rhino.RhinoApp.RunScript("GazeAtLast", False)

    def cmd_toggle_construction(self):
        self._toggle_layer_visibility("Construction")

    def cmd_toggle_measurements(self):
        self._toggle_layer_visibility("Measurements")

    def cmd_draw_clipping_planes(self):
        Rhino.RhinoApp.RunScript("DrawClippingPlanes", False)

    # ------------------------------------------------------------------
    # Foot commands
    # ------------------------------------------------------------------

    def cmd_show_foot(self):
        self._set_layer_visible("Foot", True)

    def cmd_hide_foot(self):
        self._set_layer_visible("Foot", False)

    def cmd_analyze_plantar(self):
        Rhino.RhinoApp.RunScript("AnalyzePlantarFootScan", False)

    # ------------------------------------------------------------------
    # Orthotic commands
    # ------------------------------------------------------------------

    def cmd_make_orthotic(self):
        Rhino.RhinoApp.RunScript("MakeOrthotic", False)

    def cmd_adjust_to_blank(self):
        Rhino.RhinoApp.RunScript("AdjustOrthoticToBlank", False)

    def cmd_print_prep_orthotic(self):
        Rhino.RhinoApp.RunScript("PrintPrepOrthotic", False)

    # ------------------------------------------------------------------
    # Sandal commands
    # ------------------------------------------------------------------

    def cmd_build_sandal(self):
        Rhino.RhinoApp.RunScript("BuildSandal", False)

    def cmd_build_insert(self):
        Rhino.RhinoApp.RunScript("BuildInsert", False)

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
        # Run EditCurve command -- the curve type is selected via the
        # Rhino command options when EditCurve is active.
        Rhino.RhinoApp.RunScript("EditCurve", False)

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
                f"[Feet in Focus Shoe Kit] Add clipping plane error: {ex}"
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

        # Enable all commands (free plugin)
        for method_name, btn in self._buttons.items():
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
