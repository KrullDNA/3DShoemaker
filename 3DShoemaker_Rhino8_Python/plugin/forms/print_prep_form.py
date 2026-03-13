"""
print_prep_form.py - 3D print preparation dialog for Feet in Focus Shoe Kit.

Provides settings for exporting geometry ready for 3D printing,
including shell thickness, support generation, print-area fitting,
and export format selection.
"""

from typing import Optional

import Rhino
import Rhino.Geometry
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

import Eto.Forms as forms
import Eto.Drawing as drawing


# Supported export formats
_EXPORT_FORMATS = ["STL", "OBJ", "3MF", "PLY", "AMF"]

# Common printer bed sizes (mm) for MaximizePrintableArea
_PRINTER_PRESETS = {
    "Custom": (0, 0, 0),
    "Small (120x120x120)": (120, 120, 120),
    "Medium (220x220x250)": (220, 220, 250),
    "Large (300x300x400)": (300, 300, 400),
    "Extra Large (400x400x500)": (400, 400, 500),
}


class PrintPrepForm(forms.Dialog[bool]):
    """
    Dialog for configuring 3D print preparation settings.

    Controls shell thickness, support generation, print-area optimisation,
    post-processing mode, and export format.
    """

    def __init__(self):
        super().__init__()

        self.Title = "Feet in Focus Shoe Kit - 3D Print Preparation"
        self.ClientSize = drawing.Size(460, 560)
        self.Padding = drawing.Padding(10)
        self.Resizable = True

        # Settings state
        self.maximize_printable_area: bool = False
        self.for_post_processing: bool = False
        self.shell_thickness: float = 2.0
        self.generate_supports: bool = False
        self.support_angle: float = 45.0
        self.support_density: float = 15.0
        self.export_format: str = "STL"
        self.export_path: str = ""
        self.printer_bed_x: float = 220.0
        self.printer_bed_y: float = 220.0
        self.printer_bed_z: float = 250.0
        self.stl_tolerance: float = 0.05
        self.stl_angle_tolerance: float = 5.0

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        # -- Print area group ----------------------------------------------
        area_group = forms.GroupBox(Text="Print Area")
        area_layout = forms.DynamicLayout()
        area_layout.DefaultSpacing = drawing.Size(5, 5)
        area_layout.Padding = drawing.Padding(8)

        self._chk_maximize = forms.CheckBox(Text="Maximize Printable Area")
        self._chk_maximize.Checked = self.maximize_printable_area
        self._chk_maximize.CheckedChanged += self._on_maximize_changed
        area_layout.AddRow(self._chk_maximize)

        area_layout.AddRow(forms.Label(Text="Printer Preset:"))
        self._cmb_preset = forms.DropDown()
        for name in _PRINTER_PRESETS:
            self._cmb_preset.Items.Add(forms.ListItem(Text=name))
        self._cmb_preset.SelectedIndex = 2  # Medium
        self._cmb_preset.SelectedIndexChanged += self._on_preset_changed
        area_layout.AddRow(self._cmb_preset)

        bed_row = forms.DynamicLayout()
        bed_row.DefaultSpacing = drawing.Size(5, 5)

        self._num_bed_x = forms.NumericStepper(
            MinValue=1, MaxValue=2000, DecimalPlaces=0, Value=self.printer_bed_x)
        self._num_bed_y = forms.NumericStepper(
            MinValue=1, MaxValue=2000, DecimalPlaces=0, Value=self.printer_bed_y)
        self._num_bed_z = forms.NumericStepper(
            MinValue=1, MaxValue=2000, DecimalPlaces=0, Value=self.printer_bed_z)

        bed_row.AddRow(
            forms.Label(Text="X:"), self._num_bed_x,
            forms.Label(Text="Y:"), self._num_bed_y,
            forms.Label(Text="Z:"), self._num_bed_z,
        )
        area_layout.AddRow(bed_row)

        area_group.Content = area_layout
        layout.AddRow(area_group)

        layout.AddSpace()

        # -- Shell group ---------------------------------------------------
        shell_group = forms.GroupBox(Text="Shell Settings")
        shell_layout = forms.DynamicLayout()
        shell_layout.DefaultSpacing = drawing.Size(5, 5)
        shell_layout.Padding = drawing.Padding(8)

        shell_layout.AddRow(forms.Label(Text="Shell Thickness (mm):"))
        self._num_shell = forms.NumericStepper()
        self._num_shell.MinValue = 0.1
        self._num_shell.MaxValue = 50.0
        self._num_shell.DecimalPlaces = 1
        self._num_shell.Increment = 0.5
        self._num_shell.Value = self.shell_thickness
        shell_layout.AddRow(self._num_shell)

        self._chk_post_processing = forms.CheckBox(
            Text="For Post-Processing (hollow shell)")
        self._chk_post_processing.Checked = self.for_post_processing
        shell_layout.AddRow(self._chk_post_processing)

        shell_group.Content = shell_layout
        layout.AddRow(shell_group)

        layout.AddSpace()

        # -- Support generation --------------------------------------------
        support_group = forms.GroupBox(Text="Support Generation")
        support_layout = forms.DynamicLayout()
        support_layout.DefaultSpacing = drawing.Size(5, 5)
        support_layout.Padding = drawing.Padding(8)

        self._chk_supports = forms.CheckBox(Text="Generate Supports")
        self._chk_supports.Checked = self.generate_supports
        self._chk_supports.CheckedChanged += self._on_supports_changed
        support_layout.AddRow(self._chk_supports)

        support_layout.AddRow(forms.Label(Text="Overhang Angle (degrees):"))
        self._num_support_angle = forms.NumericStepper()
        self._num_support_angle.MinValue = 0
        self._num_support_angle.MaxValue = 90
        self._num_support_angle.DecimalPlaces = 1
        self._num_support_angle.Value = self.support_angle
        self._num_support_angle.Enabled = self.generate_supports
        support_layout.AddRow(self._num_support_angle)

        support_layout.AddRow(forms.Label(Text="Support Density (%):"))
        self._num_support_density = forms.NumericStepper()
        self._num_support_density.MinValue = 1
        self._num_support_density.MaxValue = 100
        self._num_support_density.DecimalPlaces = 0
        self._num_support_density.Value = self.support_density
        self._num_support_density.Enabled = self.generate_supports
        support_layout.AddRow(self._num_support_density)

        support_group.Content = support_layout
        layout.AddRow(support_group)

        layout.AddSpace()

        # -- Export format -------------------------------------------------
        export_group = forms.GroupBox(Text="Export")
        export_layout = forms.DynamicLayout()
        export_layout.DefaultSpacing = drawing.Size(5, 5)
        export_layout.Padding = drawing.Padding(8)

        export_layout.AddRow(forms.Label(Text="Format:"))
        self._cmb_format = forms.DropDown()
        for fmt in _EXPORT_FORMATS:
            self._cmb_format.Items.Add(forms.ListItem(Text=fmt))
        self._cmb_format.SelectedIndex = 0
        export_layout.AddRow(self._cmb_format)

        export_layout.AddRow(forms.Label(Text="STL Tolerance (mm):"))
        self._num_stl_tol = forms.NumericStepper()
        self._num_stl_tol.MinValue = 0.001
        self._num_stl_tol.MaxValue = 1.0
        self._num_stl_tol.DecimalPlaces = 3
        self._num_stl_tol.Increment = 0.01
        self._num_stl_tol.Value = self.stl_tolerance
        export_layout.AddRow(self._num_stl_tol)

        export_layout.AddRow(forms.Label(Text="Angle Tolerance (degrees):"))
        self._num_stl_angle = forms.NumericStepper()
        self._num_stl_angle.MinValue = 0.1
        self._num_stl_angle.MaxValue = 30.0
        self._num_stl_angle.DecimalPlaces = 1
        self._num_stl_angle.Increment = 1.0
        self._num_stl_angle.Value = self.stl_angle_tolerance
        export_layout.AddRow(self._num_stl_angle)

        # Export path
        path_row = forms.DynamicLayout()
        path_row.DefaultSpacing = drawing.Size(5, 5)
        self._txt_export_path = forms.TextBox(
            ReadOnly=True, PlaceholderText="Select export location...")
        btn_browse = forms.Button(Text="Browse...")
        btn_browse.Click += self._on_browse_export
        path_row.AddRow(self._txt_export_path, btn_browse)
        export_layout.AddRow(path_row)

        export_group.Content = export_layout
        layout.AddRow(export_group)

        layout.AddSpace()

        # -- Buttons -------------------------------------------------------
        btn_ok = forms.Button(Text="OK")
        btn_ok.Click += self._on_ok
        btn_cancel = forms.Button(Text="Cancel")
        btn_cancel.Click += self._on_cancel

        self.DefaultButton = btn_ok
        self.AbortButton = btn_cancel

        btn_layout = forms.DynamicLayout()
        btn_layout.AddRow(None, btn_cancel, btn_ok)
        layout.AddRow(btn_layout)

        self.Content = layout

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_maximize_changed(self, sender, e):
        enabled = self._chk_maximize.Checked == True
        self._cmb_preset.Enabled = enabled
        self._num_bed_x.Enabled = enabled
        self._num_bed_y.Enabled = enabled
        self._num_bed_z.Enabled = enabled

    def _on_preset_changed(self, sender, e):
        idx = self._cmb_preset.SelectedIndex
        if idx >= 0:
            name = list(_PRINTER_PRESETS.keys())[idx]
            x, y, z = _PRINTER_PRESETS[name]
            if x > 0:
                self._num_bed_x.Value = x
                self._num_bed_y.Value = y
                self._num_bed_z.Value = z

    def _on_supports_changed(self, sender, e):
        enabled = self._chk_supports.Checked == True
        self._num_support_angle.Enabled = enabled
        self._num_support_density.Enabled = enabled

    def _on_browse_export(self, sender, e):
        dlg = forms.SaveFileDialog()
        dlg.Title = "Select Export Location"

        fmt_idx = self._cmb_format.SelectedIndex
        fmt = _EXPORT_FORMATS[fmt_idx] if fmt_idx >= 0 else "STL"
        ext = fmt.lower()
        dlg.Filters.Add(forms.FileFilter(f"{fmt} Files", f".{ext}"))
        dlg.Filters.Add(forms.FileFilter("All Files", ".*"))

        result = dlg.ShowDialog(self)
        if result == forms.DialogResult.Ok:
            self.export_path = dlg.FileName
            self._txt_export_path.Text = self.export_path

    # ------------------------------------------------------------------
    # Collect state
    # ------------------------------------------------------------------

    def _collect(self):
        """Read all control values into instance attributes."""
        self.maximize_printable_area = self._chk_maximize.Checked == True
        self.for_post_processing = self._chk_post_processing.Checked == True
        self.shell_thickness = self._num_shell.Value
        self.generate_supports = self._chk_supports.Checked == True
        self.support_angle = self._num_support_angle.Value
        self.support_density = self._num_support_density.Value
        self.printer_bed_x = self._num_bed_x.Value
        self.printer_bed_y = self._num_bed_y.Value
        self.printer_bed_z = self._num_bed_z.Value
        self.stl_tolerance = self._num_stl_tol.Value
        self.stl_angle_tolerance = self._num_stl_angle.Value

        fmt_idx = self._cmb_format.SelectedIndex
        self.export_format = _EXPORT_FORMATS[fmt_idx] if fmt_idx >= 0 else "STL"

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_ok(self, sender, e):
        self._collect()
        self.Close(True)

    def _on_cancel(self, sender, e):
        self.Close(False)
