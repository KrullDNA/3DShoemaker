"""
import_foot_form.py - Foot scan import dialog for 3DShoemaker.

Provides a UI for importing 2D or 3D foot scan data from external
files (STL, OBJ, PLY, etc.) with optional measurement overrides.
"""

from typing import Optional

import Rhino
import Rhino.Geometry
import Rhino.FileIO
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

import Eto.Forms as forms
import Eto.Drawing as drawing


# Supported scan file formats
_SCAN_FILTERS = (
    "All Supported|*.stl;*.obj;*.ply;*.3ds;*.fbx;*.3dm;*.xyz;*.csv|"
    "STL Files (*.stl)|*.stl|"
    "OBJ Files (*.obj)|*.obj|"
    "PLY Files (*.ply)|*.ply|"
    "3DS Files (*.3ds)|*.3ds|"
    "FBX Files (*.fbx)|*.fbx|"
    "Rhino Files (*.3dm)|*.3dm|"
    "Point Cloud (*.xyz, *.csv)|*.xyz;*.csv|"
    "All Files (*.*)|*.*"
)


class ImportFootForm(forms.Dialog[bool]):
    """
    Dialog for importing a foot scan (2D outline or 3D mesh) into
    the active Rhino document on the Foot layer.
    """

    def __init__(self):
        super().__init__()

        self.Title = "3DShoemaker - Import Foot"
        self.ClientSize = drawing.Size(500, 520)
        self.Padding = drawing.Padding(10)
        self.Resizable = True

        # Result state
        self.scan_file_path: str = ""
        self.import_mode: str = "3D"  # "2D" or "3D"
        self.foot_side: str = "Right"

        # Optional measurement overrides (mm)
        self.foot_length: float = 0.0
        self.ball_width: float = 0.0
        self.heel_width: float = 0.0
        self.ball_girth: float = 0.0
        self.instep_girth: float = 0.0
        self.arch_length: float = 0.0

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        # -- Import mode ---------------------------------------------------
        mode_group = forms.GroupBox(Text="Import Mode")
        mode_layout = forms.DynamicLayout()
        mode_layout.DefaultSpacing = drawing.Size(5, 5)
        mode_layout.Padding = drawing.Padding(8)

        self._rb_3d = forms.RadioButton(Text="3D Foot Model")
        self._rb_3d.Checked = True
        self._rb_3d.CheckedChanged += self._on_mode_changed

        self._rb_2d = forms.RadioButton(self._rb_3d, Text="2D Foot Outline")
        self._rb_2d.CheckedChanged += self._on_mode_changed

        mode_layout.AddRow(self._rb_3d)
        mode_layout.AddRow(self._rb_2d)

        mode_group.Content = mode_layout
        layout.AddRow(mode_group)

        layout.AddSpace()

        # -- Foot side -----------------------------------------------------
        layout.AddRow(forms.Label(Text="Foot Side:"))
        self._cmb_side = forms.DropDown()
        self._cmb_side.Items.Add(forms.ListItem(Text="Right"))
        self._cmb_side.Items.Add(forms.ListItem(Text="Left"))
        self._cmb_side.SelectedIndex = 0
        self._cmb_side.SelectedIndexChanged += self._on_side_changed
        layout.AddRow(self._cmb_side)

        layout.AddSpace()

        # -- File selection ------------------------------------------------
        file_group = forms.GroupBox(Text="Scan File")
        file_layout = forms.DynamicLayout()
        file_layout.DefaultSpacing = drawing.Size(5, 5)
        file_layout.Padding = drawing.Padding(8)

        self._txt_file = forms.TextBox(ReadOnly=True,
                                       PlaceholderText="No file selected")
        btn_browse = forms.Button(Text="Browse...")
        btn_browse.Click += self._on_browse

        file_layout.AddRow(self._txt_file, btn_browse)
        file_group.Content = file_layout
        layout.AddRow(file_group)

        layout.AddSpace()

        # -- Measurement overrides -----------------------------------------
        meas_group = forms.GroupBox(Text="Foot Measurements (optional, mm)")
        meas_layout = forms.DynamicLayout()
        meas_layout.DefaultSpacing = drawing.Size(5, 5)
        meas_layout.Padding = drawing.Padding(8)

        self._num_length = self._add_measurement_row(
            meas_layout, "Foot Length:", 0, 500)
        self._num_ball_width = self._add_measurement_row(
            meas_layout, "Ball Width:", 0, 200)
        self._num_heel_width = self._add_measurement_row(
            meas_layout, "Heel Width:", 0, 200)
        self._num_ball_girth = self._add_measurement_row(
            meas_layout, "Ball Girth:", 0, 500)
        self._num_instep_girth = self._add_measurement_row(
            meas_layout, "Instep Girth:", 0, 500)
        self._num_arch_length = self._add_measurement_row(
            meas_layout, "Arch Length:", 0, 400)

        meas_group.Content = meas_layout
        layout.AddRow(meas_group)

        layout.AddSpace()

        # -- Status --------------------------------------------------------
        self._lbl_status = forms.Label(Text="Select a scan file to import.")
        layout.AddRow(self._lbl_status)

        layout.AddSpace()

        # -- Buttons -------------------------------------------------------
        btn_import = forms.Button(Text="Import")
        btn_import.Click += self._on_import
        btn_cancel = forms.Button(Text="Cancel")
        btn_cancel.Click += self._on_cancel

        self.DefaultButton = btn_import
        self.AbortButton = btn_cancel

        btn_layout = forms.DynamicLayout()
        btn_layout.AddRow(None, btn_cancel, btn_import)
        layout.AddRow(btn_layout)

        self.Content = layout

    @staticmethod
    def _add_measurement_row(layout: forms.DynamicLayout,
                             label: str, min_val: float,
                             max_val: float) -> forms.NumericStepper:
        """Add a labelled numeric stepper row and return the stepper."""
        layout.AddRow(forms.Label(Text=label))
        stepper = forms.NumericStepper()
        stepper.MinValue = min_val
        stepper.MaxValue = max_val
        stepper.DecimalPlaces = 1
        stepper.Increment = 0.5
        stepper.Value = 0.0
        layout.AddRow(stepper)
        return stepper

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_mode_changed(self, sender, e):
        self.import_mode = "3D" if self._rb_3d.Checked else "2D"

    def _on_side_changed(self, sender, e):
        idx = self._cmb_side.SelectedIndex
        self.foot_side = "Right" if idx == 0 else "Left"

    def _on_browse(self, sender, e):
        dlg = forms.OpenFileDialog()
        dlg.Title = "Select Foot Scan File"
        dlg.Filters.Add(forms.FileFilter("All Supported",
                                         ".stl", ".obj", ".ply", ".3ds",
                                         ".fbx", ".3dm", ".xyz", ".csv"))
        dlg.Filters.Add(forms.FileFilter("STL Files", ".stl"))
        dlg.Filters.Add(forms.FileFilter("OBJ Files", ".obj"))
        dlg.Filters.Add(forms.FileFilter("PLY Files", ".ply"))
        dlg.Filters.Add(forms.FileFilter("Point Cloud", ".xyz", ".csv"))
        dlg.Filters.Add(forms.FileFilter("All Files", ".*"))

        result = dlg.ShowDialog(self)
        if result == forms.DialogResult.Ok:
            self.scan_file_path = dlg.FileName
            self._txt_file.Text = self.scan_file_path
            self._lbl_status.Text = f"File selected: {self.scan_file_path}"

    # ------------------------------------------------------------------
    # Import logic
    # ------------------------------------------------------------------

    def _collect_measurements(self):
        """Read measurement values from the numeric steppers."""
        self.foot_length = self._num_length.Value
        self.ball_width = self._num_ball_width.Value
        self.heel_width = self._num_heel_width.Value
        self.ball_girth = self._num_ball_girth.Value
        self.instep_girth = self._num_instep_girth.Value
        self.arch_length = self._num_arch_length.Value

    def _validate(self) -> bool:
        """Validate selections before import."""
        if not self.scan_file_path:
            self._lbl_status.Text = "Error: No scan file selected."
            return False

        import os
        if not os.path.isfile(self.scan_file_path):
            self._lbl_status.Text = "Error: Selected file does not exist."
            return False

        return True

    def _do_import(self) -> bool:
        """
        Execute the foot scan import into the active document.

        Geometry is placed on the SLM::Foot layer.
        """
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            self._lbl_status.Text = "Error: No active document."
            return False

        try:
            # Ensure Foot layer exists
            foot_layer_path = "SLM::Foot"
            layer_idx = doc.Layers.FindByFullPath(foot_layer_path, -1)
            if layer_idx < 0:
                Rhino.RhinoApp.WriteLine(
                    "[3DShoemaker] Foot layer not found; creating layers."
                )
                from plugin.plugin_main import PodoCADPlugIn
                PodoCADPlugIn.instance().SetupLayers(doc)
                layer_idx = doc.Layers.FindByFullPath(foot_layer_path, -1)

            if layer_idx < 0:
                self._lbl_status.Text = "Error: Could not find or create Foot layer."
                return False

            # Import the file using Rhino's built-in import
            import_options = f'-Layer="{foot_layer_path}"'
            cmd = f'_-Import "{self.scan_file_path}" _Enter'
            result = Rhino.RhinoApp.RunScript(cmd, False)

            if not result:
                self._lbl_status.Text = "Error: Import command failed."
                return False

            # Move newly imported objects to the Foot layer
            selected = doc.Objects.GetSelectedObjects(False, False)
            attrs = Rhino.DocObjects.ObjectAttributes()
            attrs.LayerIndex = layer_idx

            count = 0
            for obj in selected:
                obj_attrs = obj.Attributes.Duplicate()
                obj_attrs.LayerIndex = layer_idx
                doc.Objects.ModifyAttributes(obj, obj_attrs, True)
                count += 1

            # Mirror for left foot if needed
            if self.foot_side == "Left":
                self._mirror_to_left(doc)

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(
                f"[3DShoemaker] Imported {count} foot scan objects "
                f"({self.import_mode}, {self.foot_side})."
            )
            return True

        except Exception as ex:
            self._lbl_status.Text = f"Error: {ex}"
            Rhino.RhinoApp.WriteLine(
                f"[3DShoemaker] Import error: {ex}"
            )
            return False

    @staticmethod
    def _mirror_to_left(doc: Rhino.RhinoDoc):
        """Mirror selected geometry about the YZ plane for left foot."""
        mirror = Rhino.Geometry.Transform.Mirror(
            Rhino.Geometry.Plane.WorldYZ
        )
        for obj in doc.Objects.GetSelectedObjects(False, False):
            doc.Objects.Transform(obj, mirror, True)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_import(self, sender, e):
        self._collect_measurements()
        if self._validate():
            if self._do_import():
                self.Close(True)

    def _on_cancel(self, sender, e):
        self.Close(False)
