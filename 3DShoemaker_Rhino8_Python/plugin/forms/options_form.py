"""
options_form.py - Plugin settings / preferences dialog for Feet in Focus Shoe Kit.

Displays plugin information, default parameter settings, unit
preferences, and auto-save configuration.
"""

import os

import Rhino
import System

import Eto.Forms as forms
import Eto.Drawing as drawing

import plugin as plugin_constants
from plugin.document_settings import DocumentSettings


# Available unit systems
_UNIT_SYSTEMS = ["Millimeters", "Centimeters", "Inches"]

# Auto-save interval options (minutes)
_AUTOSAVE_INTERVALS = [0, 1, 2, 5, 10, 15, 30]


class OptionsForm(forms.Dialog[bool]):
    """
    Plugin settings and preferences dialog.

    Sections:
    - Plugin info (read-only display)
    - Default parameters for new documents
    - Units selection
    - Auto-save settings
    """

    def __init__(self):
        super().__init__()

        self.Title = "Feet in Focus Shoe Kit - Options"
        self.ClientSize = drawing.Size(480, 580)
        self.Padding = drawing.Padding(10)
        self.Resizable = True

        # Load current settings from the plugin singleton
        self._load_current_settings()

        self._build_ui()

    # ------------------------------------------------------------------
    # Load settings
    # ------------------------------------------------------------------

    def _load_current_settings(self):
        """Populate initial values from the plugin and active document."""
        from plugin.plugin_main import PodoCADPlugIn
        plug = PodoCADPlugIn.instance()

        # Defaults
        self.units: str = "Millimeters"
        self.absolute_tolerance: float = 0.01
        self.relative_tolerance: float = 0.01
        self.angle_tolerance: float = 1.0
        self.default_export_format: str = "STL"
        self.default_size_system: str = "EU"
        self.autosave_interval: int = 5  # minutes, 0 = disabled

        # Override from active document if available
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is not None:
            ds = plug.GetDocumentSettings(doc)
            self.units = ds.units
            self.absolute_tolerance = ds.absolute_tolerance
            self.relative_tolerance = ds.relative_tolerance
            self.angle_tolerance = ds.angle_tolerance_degrees
            self.default_export_format = ds.export_format
            self.default_size_system = ds.last_size_system

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        # -- Plugin info ---------------------------------------------------
        info_group = forms.GroupBox(Text="Plugin Information")
        info_layout = forms.DynamicLayout()
        info_layout.DefaultSpacing = drawing.Size(5, 3)
        info_layout.Padding = drawing.Padding(8)
        info_layout.AddRow(
            forms.Label(Text="Plugin:"),
            forms.Label(Text="Feet in Focus Shoe Kit"),
        )
        info_layout.AddRow(
            forms.Label(Text="Version:"),
            forms.Label(Text=plugin_constants.__version__),
        )
        info_layout.AddRow(
            forms.Label(Text="License:"),
            forms.Label(Text="Free"),
        )
        info_group.Content = info_layout
        layout.AddRow(info_group)

        layout.AddSpace()

        # -- Units ---------------------------------------------------------
        units_group = forms.GroupBox(Text="Units & Tolerances")
        units_layout = forms.DynamicLayout()
        units_layout.DefaultSpacing = drawing.Size(5, 5)
        units_layout.Padding = drawing.Padding(8)

        units_layout.AddRow(forms.Label(Text="Unit System:"))
        self._cmb_units = forms.DropDown()
        for u in _UNIT_SYSTEMS:
            self._cmb_units.Items.Add(forms.ListItem(Text=u))
        try:
            self._cmb_units.SelectedIndex = _UNIT_SYSTEMS.index(self.units)
        except ValueError:
            self._cmb_units.SelectedIndex = 0
        units_layout.AddRow(self._cmb_units)

        units_layout.AddRow(forms.Label(Text="Absolute Tolerance:"))
        self._num_abs_tol = forms.NumericStepper()
        self._num_abs_tol.MinValue = 0.0001
        self._num_abs_tol.MaxValue = 10.0
        self._num_abs_tol.DecimalPlaces = 4
        self._num_abs_tol.Increment = 0.001
        self._num_abs_tol.Value = self.absolute_tolerance
        units_layout.AddRow(self._num_abs_tol)

        units_layout.AddRow(forms.Label(Text="Relative Tolerance:"))
        self._num_rel_tol = forms.NumericStepper()
        self._num_rel_tol.MinValue = 0.0001
        self._num_rel_tol.MaxValue = 10.0
        self._num_rel_tol.DecimalPlaces = 4
        self._num_rel_tol.Increment = 0.001
        self._num_rel_tol.Value = self.relative_tolerance
        units_layout.AddRow(self._num_rel_tol)

        units_layout.AddRow(forms.Label(Text="Angle Tolerance (degrees):"))
        self._num_angle_tol = forms.NumericStepper()
        self._num_angle_tol.MinValue = 0.01
        self._num_angle_tol.MaxValue = 90.0
        self._num_angle_tol.DecimalPlaces = 2
        self._num_angle_tol.Increment = 0.5
        self._num_angle_tol.Value = self.angle_tolerance
        units_layout.AddRow(self._num_angle_tol)

        units_group.Content = units_layout
        layout.AddRow(units_group)

        layout.AddSpace()

        # -- Default parameters --------------------------------------------
        defaults_group = forms.GroupBox(Text="Default Parameters")
        defaults_layout = forms.DynamicLayout()
        defaults_layout.DefaultSpacing = drawing.Size(5, 5)
        defaults_layout.Padding = drawing.Padding(8)

        defaults_layout.AddRow(forms.Label(Text="Default Export Format:"))
        self._cmb_export_fmt = forms.DropDown()
        for fmt in ["STL", "OBJ", "3MF", "PLY", "AMF"]:
            self._cmb_export_fmt.Items.Add(forms.ListItem(Text=fmt))
        try:
            self._cmb_export_fmt.SelectedIndex = ["STL", "OBJ", "3MF", "PLY", "AMF"].index(
                self.default_export_format)
        except ValueError:
            self._cmb_export_fmt.SelectedIndex = 0
        defaults_layout.AddRow(self._cmb_export_fmt)

        defaults_layout.AddRow(forms.Label(Text="Default Size System:"))
        self._cmb_size_sys = forms.DropDown()
        for sys_name in ["EU", "US_Men", "US_Women", "UK", "Mondopoint"]:
            self._cmb_size_sys.Items.Add(forms.ListItem(Text=sys_name))
        try:
            self._cmb_size_sys.SelectedIndex = ["EU", "US_Men", "US_Women", "UK", "Mondopoint"].index(
                self.default_size_system)
        except ValueError:
            self._cmb_size_sys.SelectedIndex = 0
        defaults_layout.AddRow(self._cmb_size_sys)

        defaults_group.Content = defaults_layout
        layout.AddRow(defaults_group)

        layout.AddSpace()

        # -- Auto-save -----------------------------------------------------
        save_group = forms.GroupBox(Text="Auto-Save")
        save_layout = forms.DynamicLayout()
        save_layout.DefaultSpacing = drawing.Size(5, 5)
        save_layout.Padding = drawing.Padding(8)

        save_layout.AddRow(forms.Label(Text="Auto-save interval (minutes, 0 = disabled):"))
        self._cmb_autosave = forms.DropDown()
        for mins in _AUTOSAVE_INTERVALS:
            label = "Disabled" if mins == 0 else f"{mins} min"
            self._cmb_autosave.Items.Add(forms.ListItem(Text=label))
        try:
            self._cmb_autosave.SelectedIndex = _AUTOSAVE_INTERVALS.index(
                self.autosave_interval)
        except ValueError:
            self._cmb_autosave.SelectedIndex = 0
        save_layout.AddRow(self._cmb_autosave)

        save_group.Content = save_layout
        layout.AddRow(save_group)

        layout.AddSpace()

        # -- Status --------------------------------------------------------
        self._lbl_status = forms.Label(Text="")
        layout.AddRow(self._lbl_status)

        layout.AddSpace()

        # -- Buttons -------------------------------------------------------
        btn_ok = forms.Button(Text="OK")
        btn_ok.Click += self._on_ok

        btn_apply = forms.Button(Text="Apply")
        btn_apply.Click += self._on_apply

        btn_cancel = forms.Button(Text="Cancel")
        btn_cancel.Click += self._on_cancel

        self.DefaultButton = btn_ok
        self.AbortButton = btn_cancel

        btn_layout = forms.DynamicLayout()
        btn_layout.AddRow(None, btn_cancel, btn_apply, btn_ok)
        layout.AddRow(btn_layout)

        self.Content = layout

    # ------------------------------------------------------------------
    # Collect / apply
    # ------------------------------------------------------------------

    def _collect(self):
        """Read all control values into instance attributes."""
        idx = self._cmb_units.SelectedIndex
        self.units = _UNIT_SYSTEMS[idx] if idx >= 0 else "Millimeters"

        self.absolute_tolerance = self._num_abs_tol.Value
        self.relative_tolerance = self._num_rel_tol.Value
        self.angle_tolerance = self._num_angle_tol.Value

        fmt_idx = self._cmb_export_fmt.SelectedIndex
        fmts = ["STL", "OBJ", "3MF", "PLY", "AMF"]
        self.default_export_format = fmts[fmt_idx] if fmt_idx >= 0 else "STL"

        sys_idx = self._cmb_size_sys.SelectedIndex
        systems = ["EU", "US_Men", "US_Women", "UK", "Mondopoint"]
        self.default_size_system = systems[sys_idx] if sys_idx >= 0 else "EU"

        auto_idx = self._cmb_autosave.SelectedIndex
        self.autosave_interval = (
            _AUTOSAVE_INTERVALS[auto_idx] if auto_idx >= 0 else 0
        )

    def _apply_settings(self) -> bool:
        """Write collected settings back to the plugin / active doc."""
        self._collect()

        try:
            from plugin.plugin_main import PodoCADPlugIn
            plug = PodoCADPlugIn.instance()
            doc = Rhino.RhinoDoc.ActiveDoc

            if doc is not None:
                ds = plug.GetDocumentSettings(doc)
                ds.units = self.units
                ds.absolute_tolerance = self.absolute_tolerance
                ds.relative_tolerance = self.relative_tolerance
                ds.angle_tolerance_degrees = self.angle_tolerance
                ds.export_format = self.default_export_format
                ds.last_size_system = self.default_size_system
                plug.SetDocumentSettings(doc, ds)

                # Also update Rhino's own tolerance settings
                doc.ModelAbsoluteTolerance = self.absolute_tolerance
                doc.ModelRelativeTolerance = self.relative_tolerance
                doc.ModelAngleToleranceDegrees = self.angle_tolerance

            self._lbl_status.Text = "Settings applied."
            return True

        except Exception as ex:
            self._lbl_status.Text = f"Error applying settings: {ex}"
            return False

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_ok(self, sender, e):
        self._apply_settings()
        self.Close(True)

    def _on_apply(self, sender, e):
        self._apply_settings()

    def _on_cancel(self, sender, e):
        self.Close(False)
