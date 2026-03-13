"""
foot_measurement_form.py - Manual foot measurement input for 3DShoemaker.

Provides a dialog for entering all standard foot measurements used
in last design and insole fabrication.
"""

from typing import Dict, Optional

import Rhino
import System

import Eto.Forms as forms
import Eto.Drawing as drawing


# Ordered list of measurement fields: (key, label, unit, min, max, default)
_MEASUREMENT_FIELDS = [
    ("foot_length", "Foot Length", "mm", 100, 400, 0.0),
    ("ball_width", "Ball Width", "mm", 50, 150, 0.0),
    ("heel_width", "Heel Width", "mm", 30, 120, 0.0),
    ("arch_length", "Arch Length", "mm", 50, 250, 0.0),
    ("ball_girth", "Ball Girth", "mm", 150, 350, 0.0),
    ("instep_girth", "Instep Girth", "mm", 150, 380, 0.0),
    ("long_heel_girth", "Long Heel Girth", "mm", 200, 450, 0.0),
    ("short_heel_girth", "Short Heel Girth", "mm", 200, 420, 0.0),
    ("ankle_girth", "Ankle Girth", "mm", 150, 350, 0.0),
    ("waist_girth", "Waist Girth", "mm", 130, 320, 0.0),
    ("toe_height", "Toe Height", "mm", 10, 60, 0.0),
    ("instep_height", "Instep Height", "mm", 30, 100, 0.0),
    ("heel_height", "Heel Height", "mm", 20, 80, 0.0),
    ("medial_arch_height", "Medial Arch Height", "mm", 5, 60, 0.0),
    ("lateral_arch_height", "Lateral Arch Height", "mm", 5, 40, 0.0),
    ("first_toe_length", "First Toe Length", "mm", 20, 80, 0.0),
    ("fifth_toe_length", "Fifth Toe Length", "mm", 10, 60, 0.0),
    ("ball_to_heel_length", "Ball-to-Heel Length", "mm", 80, 300, 0.0),
]


class FootMeasurementForm(forms.Dialog[bool]):
    """
    Dialog for entering foot measurements manually.

    All values are stored in millimetres.  The caller retrieves values
    via the ``measurements`` dict after the dialog closes with OK.
    """

    def __init__(self, initial_values: Optional[Dict[str, float]] = None):
        super().__init__()

        self.Title = "3DShoemaker - Foot Measurements"
        self.ClientSize = drawing.Size(420, 620)
        self.Padding = drawing.Padding(10)
        self.Resizable = True

        # Measurement values keyed by field name
        self.measurements: Dict[str, float] = {}
        self._initial = initial_values or {}
        self._steppers: Dict[str, forms.NumericStepper] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 4)
        layout.Padding = drawing.Padding(10)

        layout.AddRow(forms.Label(
            Text="Enter foot measurements (all values in mm):",
            Font=drawing.Font(drawing.SystemFont.Bold, 10),
        ))
        layout.AddSpace()

        # Scrollable area for all measurement fields
        scrollable = forms.Scrollable()
        scrollable.Border = forms.BorderType.Bezel
        scrollable.ExpandContentHeight = False

        inner_layout = forms.DynamicLayout()
        inner_layout.DefaultSpacing = drawing.Size(5, 3)
        inner_layout.Padding = drawing.Padding(8)

        for key, label, unit, min_val, max_val, default in _MEASUREMENT_FIELDS:
            initial = self._initial.get(key, default)
            row_label = forms.Label(Text=f"{label} ({unit}):")
            stepper = forms.NumericStepper()
            stepper.MinValue = min_val
            stepper.MaxValue = max_val
            stepper.DecimalPlaces = 1
            stepper.Increment = 0.5
            stepper.Value = initial
            self._steppers[key] = stepper
            inner_layout.AddRow(row_label, stepper)

        scrollable.Content = inner_layout
        layout.AddRow(scrollable)

        layout.AddSpace()

        # -- Foot side selector -------------------------------------------
        side_layout = forms.DynamicLayout()
        side_layout.AddRow(
            forms.Label(Text="Foot Side:"),
            None,
        )
        self._cmb_side = forms.DropDown()
        self._cmb_side.Items.Add(forms.ListItem(Text="Right"))
        self._cmb_side.Items.Add(forms.ListItem(Text="Left"))
        self._cmb_side.SelectedIndex = 0
        side_layout.AddRow(self._cmb_side)
        layout.AddRow(side_layout)

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
    # Data collection
    # ------------------------------------------------------------------

    def _collect(self):
        """Read all stepper values into the measurements dict."""
        for key, stepper in self._steppers.items():
            self.measurements[key] = stepper.Value

        side_idx = self._cmb_side.SelectedIndex
        self.measurements["foot_side"] = "Right" if side_idx == 0 else "Left"

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_ok(self, sender, e):
        self._collect()
        self.Close(True)

    def _on_cancel(self, sender, e):
        self.Close(False)
