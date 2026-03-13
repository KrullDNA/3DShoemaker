"""
vacuum_form.py - Vacuum forming preparation dialog for Feet in Focus Shoe Kit.

Provides settings for preparing geometry for vacuum forming / thermoforming
manufacture, including material selection, sheet thickness, and draft angles.
"""

from typing import Optional

import Rhino
import Rhino.Geometry
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

import Eto.Forms as forms
import Eto.Drawing as drawing


# Common thermoforming materials
_MATERIALS = [
    "EVA (Ethylene Vinyl Acetate)",
    "Polypropylene (PP)",
    "Polyethylene (PE)",
    "PETG",
    "ABS",
    "Polycarbonate (PC)",
    "PVC",
    "Acrylic (PMMA)",
    "Kydex",
    "Custom",
]

# Standard sheet thicknesses (mm)
_STANDARD_THICKNESSES = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0]


class VacuumForm(forms.Dialog[bool]):
    """
    Dialog for configuring vacuum forming preparation settings.

    Configures material type, sheet thickness, draft angles, undercut
    handling, and trim-line generation for vacuum-formed shoe components.
    """

    def __init__(self):
        super().__init__()

        self.Title = "Feet in Focus Shoe Kit - Vacuum Forming Preparation"
        self.ClientSize = drawing.Size(440, 500)
        self.Padding = drawing.Padding(10)
        self.Resizable = True

        # Settings state
        self.material: str = _MATERIALS[0]
        self.sheet_thickness: float = 3.0
        self.draft_angle_inner: float = 3.0   # degrees
        self.draft_angle_outer: float = 5.0   # degrees
        self.add_draft_angles: bool = True
        self.generate_trim_line: bool = True
        self.trim_offset: float = 5.0         # mm beyond edge
        self.check_undercuts: bool = True
        self.pull_direction: str = "Z-Up"     # vacuum pull direction

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        # -- Material group ------------------------------------------------
        mat_group = forms.GroupBox(Text="Material")
        mat_layout = forms.DynamicLayout()
        mat_layout.DefaultSpacing = drawing.Size(5, 5)
        mat_layout.Padding = drawing.Padding(8)

        mat_layout.AddRow(forms.Label(Text="Material:"))
        self._cmb_material = forms.DropDown()
        for mat in _MATERIALS:
            self._cmb_material.Items.Add(forms.ListItem(Text=mat))
        self._cmb_material.SelectedIndex = 0
        mat_layout.AddRow(self._cmb_material)

        mat_layout.AddRow(forms.Label(Text="Sheet Thickness (mm):"))
        self._cmb_thickness = forms.DropDown()
        for t in _STANDARD_THICKNESSES:
            self._cmb_thickness.Items.Add(forms.ListItem(Text=f"{t:.1f}"))
        self._cmb_thickness.SelectedIndex = 4  # 3.0 mm default

        self._num_thickness = forms.NumericStepper()
        self._num_thickness.MinValue = 0.1
        self._num_thickness.MaxValue = 20.0
        self._num_thickness.DecimalPlaces = 1
        self._num_thickness.Increment = 0.5
        self._num_thickness.Value = self.sheet_thickness
        self._cmb_thickness.SelectedIndexChanged += self._on_thickness_preset

        thickness_row = forms.DynamicLayout()
        thickness_row.DefaultSpacing = drawing.Size(5, 5)
        thickness_row.AddRow(
            forms.Label(Text="Preset:"), self._cmb_thickness,
            forms.Label(Text="Custom:"), self._num_thickness,
        )
        mat_layout.AddRow(thickness_row)

        mat_group.Content = mat_layout
        layout.AddRow(mat_group)

        layout.AddSpace()

        # -- Draft angles --------------------------------------------------
        draft_group = forms.GroupBox(Text="Draft Angles")
        draft_layout = forms.DynamicLayout()
        draft_layout.DefaultSpacing = drawing.Size(5, 5)
        draft_layout.Padding = drawing.Padding(8)

        self._chk_draft = forms.CheckBox(Text="Add Draft Angles")
        self._chk_draft.Checked = self.add_draft_angles
        self._chk_draft.CheckedChanged += self._on_draft_changed
        draft_layout.AddRow(self._chk_draft)

        draft_layout.AddRow(forms.Label(Text="Inner Draft Angle (degrees):"))
        self._num_draft_inner = forms.NumericStepper()
        self._num_draft_inner.MinValue = 0
        self._num_draft_inner.MaxValue = 30
        self._num_draft_inner.DecimalPlaces = 1
        self._num_draft_inner.Increment = 0.5
        self._num_draft_inner.Value = self.draft_angle_inner
        draft_layout.AddRow(self._num_draft_inner)

        draft_layout.AddRow(forms.Label(Text="Outer Draft Angle (degrees):"))
        self._num_draft_outer = forms.NumericStepper()
        self._num_draft_outer.MinValue = 0
        self._num_draft_outer.MaxValue = 30
        self._num_draft_outer.DecimalPlaces = 1
        self._num_draft_outer.Increment = 0.5
        self._num_draft_outer.Value = self.draft_angle_outer
        draft_layout.AddRow(self._num_draft_outer)

        draft_group.Content = draft_layout
        layout.AddRow(draft_group)

        layout.AddSpace()

        # -- Trim & undercut -----------------------------------------------
        trim_group = forms.GroupBox(Text="Trim & Undercut")
        trim_layout = forms.DynamicLayout()
        trim_layout.DefaultSpacing = drawing.Size(5, 5)
        trim_layout.Padding = drawing.Padding(8)

        self._chk_trim = forms.CheckBox(Text="Generate Trim Line")
        self._chk_trim.Checked = self.generate_trim_line
        self._chk_trim.CheckedChanged += self._on_trim_changed
        trim_layout.AddRow(self._chk_trim)

        trim_layout.AddRow(forms.Label(Text="Trim Offset (mm):"))
        self._num_trim_offset = forms.NumericStepper()
        self._num_trim_offset.MinValue = 0
        self._num_trim_offset.MaxValue = 50
        self._num_trim_offset.DecimalPlaces = 1
        self._num_trim_offset.Increment = 1.0
        self._num_trim_offset.Value = self.trim_offset
        trim_layout.AddRow(self._num_trim_offset)

        self._chk_undercuts = forms.CheckBox(Text="Check for Undercuts")
        self._chk_undercuts.Checked = self.check_undercuts
        trim_layout.AddRow(self._chk_undercuts)

        trim_layout.AddRow(forms.Label(Text="Pull Direction:"))
        self._cmb_pull = forms.DropDown()
        for direction in ["Z-Up", "Z-Down", "Y-Forward", "Y-Back", "X-Right", "X-Left"]:
            self._cmb_pull.Items.Add(forms.ListItem(Text=direction))
        self._cmb_pull.SelectedIndex = 0
        trim_layout.AddRow(self._cmb_pull)

        trim_group.Content = trim_layout
        layout.AddRow(trim_group)

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

    def _on_thickness_preset(self, sender, e):
        idx = self._cmb_thickness.SelectedIndex
        if 0 <= idx < len(_STANDARD_THICKNESSES):
            self._num_thickness.Value = _STANDARD_THICKNESSES[idx]

    def _on_draft_changed(self, sender, e):
        enabled = self._chk_draft.Checked == True
        self._num_draft_inner.Enabled = enabled
        self._num_draft_outer.Enabled = enabled

    def _on_trim_changed(self, sender, e):
        enabled = self._chk_trim.Checked == True
        self._num_trim_offset.Enabled = enabled

    # ------------------------------------------------------------------
    # Collect
    # ------------------------------------------------------------------

    def _collect(self):
        """Read all control values into instance attributes."""
        mat_idx = self._cmb_material.SelectedIndex
        self.material = _MATERIALS[mat_idx] if mat_idx >= 0 else _MATERIALS[0]

        self.sheet_thickness = self._num_thickness.Value
        self.add_draft_angles = self._chk_draft.Checked == True
        self.draft_angle_inner = self._num_draft_inner.Value
        self.draft_angle_outer = self._num_draft_outer.Value
        self.generate_trim_line = self._chk_trim.Checked == True
        self.trim_offset = self._num_trim_offset.Value
        self.check_undercuts = self._chk_undercuts.Checked == True

        pull_idx = self._cmb_pull.SelectedIndex
        directions = ["Z-Up", "Z-Down", "Y-Forward", "Y-Back", "X-Right", "X-Left"]
        self.pull_direction = directions[pull_idx] if pull_idx >= 0 else "Z-Up"

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_ok(self, sender, e):
        self._collect()
        self.Close(True)

    def _on_cancel(self, sender, e):
        self.Close(False)
