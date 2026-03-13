"""
grade_footwear_form.py - Size grading dialog for 3DShoemaker.

Provides a UI for grading (scaling) footwear geometry from one shoe
size to another using standard grading systems (EU, US, UK, Mondopoint).
"""

from typing import Any, Dict, List, Optional, Tuple

import Rhino
import Rhino.Geometry
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

import Eto.Forms as forms
import Eto.Drawing as drawing

from plugin.document_settings import DocumentSettings


# ---------------------------------------------------------------------------
# Grading tables -- millimetre increments per full size step
# ---------------------------------------------------------------------------

_GRADING_INCREMENTS: Dict[str, float] = {
    "EU": 6.667,       # 2/3 cm per Paris point
    "US_Men": 8.467,   # 1/3 inch per size
    "US_Women": 8.467,
    "UK": 8.467,
    "Mondopoint": 5.0,  # 5 mm per Mondopoint size
}

_SIZE_SYSTEMS = list(_GRADING_INCREMENTS.keys())

# Ball-girth and instep-girth increments per full size (mm)
_BALL_GIRTH_INCREMENT: Dict[str, float] = {
    "EU": 5.0, "US_Men": 5.0, "US_Women": 5.0,
    "UK": 5.0, "Mondopoint": 5.0,
}
_INSTEP_GIRTH_INCREMENT: Dict[str, float] = {
    "EU": 4.0, "US_Men": 4.0, "US_Women": 4.0,
    "UK": 4.0, "Mondopoint": 4.0,
}


class GradeFootwearForm(forms.Dialog[bool]):
    """
    Dialog for grading footwear geometry from one size to another.

    The user selects the current and target sizes plus the grading
    system.  On confirmation the dialog computes the required scale
    factors and applies them to the document geometry.
    """

    def __init__(self, current_size: float = 42.0,
                 grading_system: str = "EU"):
        super().__init__()

        self.Title = "3DShoemaker - Grade Footwear"
        self.ClientSize = drawing.Size(440, 480)
        self.Padding = drawing.Padding(10)
        self.Resizable = True

        # State
        self.current_size: float = current_size
        self.target_size: float = current_size
        self.grading_system: str = grading_system
        self.current_ball_girth: float = 0.0
        self.current_instep_girth: float = 0.0
        self.target_ball_girth: float = 0.0
        self.target_instep_girth: float = 0.0

        # Result geometry transforms (populated by _compute_grade)
        self.length_scale: float = 1.0
        self.width_scale: float = 1.0
        self.girth_scale: float = 1.0

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        # -- Grading system ------------------------------------------------
        layout.AddRow(forms.Label(Text="Grading System:"))
        self._cmb_system = forms.DropDown()
        for sys_name in _SIZE_SYSTEMS:
            self._cmb_system.Items.Add(forms.ListItem(Text=sys_name))
        idx = _SIZE_SYSTEMS.index(self.grading_system) if self.grading_system in _SIZE_SYSTEMS else 0
        self._cmb_system.SelectedIndex = idx
        self._cmb_system.SelectedIndexChanged += self._on_system_changed
        layout.AddRow(self._cmb_system)

        layout.AddSpace()

        # -- Current size --------------------------------------------------
        size_group = forms.GroupBox(Text="Size")
        size_layout = forms.DynamicLayout()
        size_layout.DefaultSpacing = drawing.Size(5, 5)
        size_layout.Padding = drawing.Padding(8)

        size_layout.AddRow(forms.Label(Text="Current Size:"))
        self._num_current_size = forms.NumericStepper()
        self._num_current_size.MinValue = 1
        self._num_current_size.MaxValue = 80
        self._num_current_size.DecimalPlaces = 1
        self._num_current_size.Increment = 0.5
        self._num_current_size.Value = self.current_size
        self._num_current_size.ValueChanged += self._on_size_changed
        size_layout.AddRow(self._num_current_size)

        size_layout.AddRow(forms.Label(Text="Target Size:"))
        self._num_target_size = forms.NumericStepper()
        self._num_target_size.MinValue = 1
        self._num_target_size.MaxValue = 80
        self._num_target_size.DecimalPlaces = 1
        self._num_target_size.Increment = 0.5
        self._num_target_size.Value = self.target_size
        self._num_target_size.ValueChanged += self._on_size_changed
        size_layout.AddRow(self._num_target_size)

        size_group.Content = size_layout
        layout.AddRow(size_group)

        layout.AddSpace()

        # -- Girth parameters ----------------------------------------------
        girth_group = forms.GroupBox(Text="Girth Parameters")
        girth_layout = forms.DynamicLayout()
        girth_layout.DefaultSpacing = drawing.Size(5, 5)
        girth_layout.Padding = drawing.Padding(8)

        girth_layout.AddRow(forms.Label(Text="Current Ball Girth (mm):"))
        self._num_cbg = forms.NumericStepper()
        self._num_cbg.MinValue = 0
        self._num_cbg.MaxValue = 500
        self._num_cbg.DecimalPlaces = 1
        self._num_cbg.Value = self.current_ball_girth
        self._num_cbg.ValueChanged += self._on_girth_changed
        girth_layout.AddRow(self._num_cbg)

        girth_layout.AddRow(forms.Label(Text="Current Instep Girth (mm):"))
        self._num_cig = forms.NumericStepper()
        self._num_cig.MinValue = 0
        self._num_cig.MaxValue = 500
        self._num_cig.DecimalPlaces = 1
        self._num_cig.Value = self.current_instep_girth
        self._num_cig.ValueChanged += self._on_girth_changed
        girth_layout.AddRow(self._num_cig)

        girth_layout.AddRow(forms.Label(Text="Target Ball Girth (mm):"))
        self._lbl_tbg = forms.Label(Text="--")
        girth_layout.AddRow(self._lbl_tbg)

        girth_layout.AddRow(forms.Label(Text="Target Instep Girth (mm):"))
        self._lbl_tig = forms.Label(Text="--")
        girth_layout.AddRow(self._lbl_tig)

        girth_group.Content = girth_layout
        layout.AddRow(girth_group)

        layout.AddSpace()

        # -- Preview label -------------------------------------------------
        self._lbl_preview = forms.Label(Text="Adjust sizes to preview grading.")
        layout.AddRow(self._lbl_preview)

        layout.AddSpace()

        # -- Buttons -------------------------------------------------------
        btn_grade = forms.Button(Text="Grade")
        btn_grade.Click += self._on_grade
        btn_cancel = forms.Button(Text="Cancel")
        btn_cancel.Click += self._on_cancel

        self.DefaultButton = btn_grade
        self.AbortButton = btn_cancel

        btn_layout = forms.DynamicLayout()
        btn_layout.AddRow(None, btn_cancel, btn_grade)
        layout.AddRow(btn_layout)

        self.Content = layout

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_system_changed(self, sender, e):
        if self._cmb_system.SelectedIndex >= 0:
            self.grading_system = _SIZE_SYSTEMS[self._cmb_system.SelectedIndex]
        self._update_preview()

    def _on_size_changed(self, sender, e):
        self.current_size = self._num_current_size.Value
        self.target_size = self._num_target_size.Value
        self._update_preview()

    def _on_girth_changed(self, sender, e):
        self.current_ball_girth = self._num_cbg.Value
        self.current_instep_girth = self._num_cig.Value
        self.UpdateCBG()
        self.UpdateCIG()
        self._update_preview()

    # ------------------------------------------------------------------
    # Girth updates
    # ------------------------------------------------------------------

    def UpdateCBG(self):
        """Update the target ball girth based on size delta."""
        size_delta = self.target_size - self.current_size
        increment = _BALL_GIRTH_INCREMENT.get(self.grading_system, 5.0)
        self.target_ball_girth = self.current_ball_girth + (size_delta * increment)
        self._lbl_tbg.Text = f"{self.target_ball_girth:.1f}"

    def UpdateCIG(self):
        """Update the target instep girth based on size delta."""
        size_delta = self.target_size - self.current_size
        increment = _INSTEP_GIRTH_INCREMENT.get(self.grading_system, 4.0)
        self.target_instep_girth = self.current_instep_girth + (size_delta * increment)
        self._lbl_tig.Text = f"{self.target_instep_girth:.1f}"

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _update_preview(self):
        """Recompute scale factors and update the preview label."""
        self.UpdateCBG()
        self.UpdateCIG()
        self._compute_grade()
        self._lbl_preview.Text = (
            f"Length scale: {self.length_scale:.4f}  |  "
            f"Width scale: {self.width_scale:.4f}  |  "
            f"Girth scale: {self.girth_scale:.4f}"
        )

    def _compute_grade(self):
        """Compute scale factors from the current and target sizes."""
        increment = _GRADING_INCREMENTS.get(self.grading_system, 6.667)
        size_delta = self.target_size - self.current_size

        # Length scaling
        base_length_mm = self.current_size * increment
        if base_length_mm > 0:
            self.length_scale = (base_length_mm + size_delta * increment) / base_length_mm
        else:
            self.length_scale = 1.0

        # Width scales proportionally at ~60% of length change
        self.width_scale = 1.0 + (self.length_scale - 1.0) * 0.6

        # Girth scale from ball girth if available
        if self.current_ball_girth > 0 and self.target_ball_girth > 0:
            self.girth_scale = self.target_ball_girth / self.current_ball_girth
        else:
            self.girth_scale = self.width_scale

    # ------------------------------------------------------------------
    # Grading operations
    # ------------------------------------------------------------------

    def OrientationAndSettings(self) -> Dict[str, Any]:
        """
        Return a dict of all grading parameters for the current
        configuration, suitable for passing to the grading engine.
        """
        return {
            "grading_system": self.grading_system,
            "current_size": self.current_size,
            "target_size": self.target_size,
            "length_scale": self.length_scale,
            "width_scale": self.width_scale,
            "girth_scale": self.girth_scale,
            "current_ball_girth": self.current_ball_girth,
            "target_ball_girth": self.target_ball_girth,
            "current_instep_girth": self.current_instep_girth,
            "target_instep_girth": self.target_instep_girth,
        }

    def TransformGeomtries(self, doc: Rhino.RhinoDoc) -> bool:
        """
        Apply the computed grading transforms to all SLM geometry in *doc*.

        Returns True on success.
        """
        self._compute_grade()
        settings = self.OrientationAndSettings()

        try:
            # Build a non-uniform scale transform centred at the origin
            origin = Rhino.Geometry.Point3d.Origin
            xform = Rhino.Geometry.Transform.Scale(
                Rhino.Geometry.Plane.WorldXY,
                settings["length_scale"],
                settings["width_scale"],
                settings["girth_scale"],
            )

            # Collect objects on SLM layers
            count = 0
            for layer_idx in range(doc.Layers.Count):
                layer = doc.Layers[layer_idx]
                if layer.IsDeleted:
                    continue
                if not layer.FullPath.startswith("SLM"):
                    continue
                objs = doc.Objects.FindByLayer(layer)
                if objs is None:
                    continue
                for obj in objs:
                    doc.Objects.Transform(obj, xform, True)
                    count += 1

            if count > 0:
                doc.Views.Redraw()
                Rhino.RhinoApp.WriteLine(
                    f"[3DShoemaker] Graded {count} objects "
                    f"({self.current_size} -> {self.target_size} "
                    f"{self.grading_system})."
                )
            return True

        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[3DShoemaker] TransformGeomtries error: {ex}"
            )
            return False

    def GradeInsole(self, doc: Rhino.RhinoDoc) -> bool:
        """
        Grade only the insole/insert layer geometry.

        Uses the same scale factors but restricts transformation to objects
        on the Insert layer.
        """
        self._compute_grade()

        try:
            xform = Rhino.Geometry.Transform.Scale(
                Rhino.Geometry.Plane.WorldXY,
                self.length_scale,
                self.width_scale,
                self.girth_scale,
            )

            insert_layer_path = "SLM::Insert"
            layer_idx = doc.Layers.FindByFullPath(insert_layer_path, -1)
            if layer_idx < 0:
                Rhino.RhinoApp.WriteLine(
                    "[3DShoemaker] Insert layer not found for grading."
                )
                return False

            layer = doc.Layers[layer_idx]
            objs = doc.Objects.FindByLayer(layer)
            if objs is None or len(objs) == 0:
                Rhino.RhinoApp.WriteLine(
                    "[3DShoemaker] No insole geometry found to grade."
                )
                return False

            for obj in objs:
                doc.Objects.Transform(obj, xform, True)

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(
                f"[3DShoemaker] Graded {len(objs)} insole objects."
            )
            return True

        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[3DShoemaker] GradeInsole error: {ex}"
            )
            return False

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_grade(self, sender, e):
        self._compute_grade()
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is not None:
            self.TransformGeomtries(doc)
        self.Close(True)

    def _on_cancel(self, sender, e):
        self.Close(False)
