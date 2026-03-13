"""
edit_dimension_form.py - Dimension editing dialog for 3DShoemaker.

Displays the current measurement dimensions of a selected object and
allows the user to modify them.  Changes can be applied immediately
(Apply) or accepted on close (OK).
"""

from typing import Dict, List, Optional, Tuple

import Rhino
import Rhino.Geometry
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

import Eto.Forms as forms
import Eto.Drawing as drawing


class EditDimensionForm(forms.Dialog[bool]):
    """
    Dialog for viewing and editing dimension values of the current
    design element.

    Dimensions are presented as labelled numeric fields. The user can
    modify values and either apply them live or accept on OK.
    """

    def __init__(self, dimensions: Optional[Dict[str, float]] = None,
                 title_suffix: str = ""):
        super().__init__()

        suffix = f" - {title_suffix}" if title_suffix else ""
        self.Title = f"3DShoemaker - Edit Dimensions{suffix}"
        self.ClientSize = drawing.Size(400, 500)
        self.Padding = drawing.Padding(10)
        self.Resizable = True

        # Dimension values: key -> (label, value, unit)
        self._dimensions: Dict[str, Tuple[str, float, str]] = {}
        if dimensions:
            for key, value in dimensions.items():
                label = key.replace("_", " ").title()
                self._dimensions[key] = (label, value, "mm")

        # Editable stepper references
        self._steppers: Dict[str, forms.NumericStepper] = {}

        # Output values
        self.result_dimensions: Dict[str, float] = {}
        self.applied: bool = False

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        layout.AddRow(forms.Label(
            Text="Current dimensions (editable):",
            Font=drawing.Font(drawing.SystemFont.Bold, 10),
        ))
        layout.AddSpace()

        # Scrollable for potentially many dimensions
        scrollable = forms.Scrollable()
        scrollable.Border = forms.BorderType.Bezel
        scrollable.ExpandContentHeight = False

        inner = forms.DynamicLayout()
        inner.DefaultSpacing = drawing.Size(5, 3)
        inner.Padding = drawing.Padding(8)

        if self._dimensions:
            for key, (label, value, unit) in self._dimensions.items():
                lbl = forms.Label(Text=f"{label} ({unit}):")
                stepper = forms.NumericStepper()
                stepper.MinValue = -1000
                stepper.MaxValue = 1000
                stepper.DecimalPlaces = 2
                stepper.Increment = 0.1
                stepper.Value = value
                self._steppers[key] = stepper
                inner.AddRow(lbl, stepper)
        else:
            inner.AddRow(forms.Label(
                Text="No dimensions to display.\n"
                     "Select an object with measurable dimensions first."
            ))

        scrollable.Content = inner
        layout.AddRow(scrollable)

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
    # Data collection
    # ------------------------------------------------------------------

    def _collect(self) -> Dict[str, float]:
        """Read current stepper values."""
        values: Dict[str, float] = {}
        for key, stepper in self._steppers.items():
            values[key] = stepper.Value
        return values

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def _apply_dimensions(self) -> bool:
        """
        Apply the edited dimensions to the active document geometry.

        This writes dimension user-text on selected objects and
        triggers a view redraw.
        """
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            self._lbl_status.Text = "Error: No active document."
            return False

        self.result_dimensions = self._collect()

        try:
            # Store updated dimensions as user text on selected objects
            selected = list(doc.Objects.GetSelectedObjects(False, False))
            if not selected:
                self._lbl_status.Text = "No objects selected to update."
                return False

            for obj in selected:
                for key, value in self.result_dimensions.items():
                    obj.Attributes.SetUserString(
                        f"SLM_Dim_{key}", f"{value:.4f}"
                    )
                obj.CommitChanges()

            doc.Views.Redraw()
            self._lbl_status.Text = (
                f"Applied {len(self.result_dimensions)} dimensions "
                f"to {len(selected)} object(s)."
            )
            self.applied = True
            return True

        except Exception as ex:
            self._lbl_status.Text = f"Error: {ex}"
            return False

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_ok(self, sender, e):
        self.result_dimensions = self._collect()
        if not self.applied:
            self._apply_dimensions()
        self.Close(True)

    def _on_apply(self, sender, e):
        self._apply_dimensions()

    def _on_cancel(self, sender, e):
        self.Close(False)
