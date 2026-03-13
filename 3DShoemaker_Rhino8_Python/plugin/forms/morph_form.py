"""
morph_form.py - Morph operation dialog for 3DShoemaker.

Allows the user to select source and target meshes/curves for
morphing operations (e.g. transferring a last shape onto a new
foot outline).
"""

from typing import List, Optional, Tuple

import Rhino
import Rhino.Geometry
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System

import Eto.Forms as forms
import Eto.Drawing as drawing


class MorphForm(forms.Dialog[bool]):
    """
    Dialog for configuring a mesh/curve morph operation.

    The user selects source and target meshes plus optional guide
    curves.  On OK the dialog validates the selection and prepares
    point lists for the morph engine.
    """

    def __init__(self):
        super().__init__()

        self.Title = "3DShoemaker - Morph"
        self.ClientSize = drawing.Size(480, 420)
        self.Padding = drawing.Padding(10)
        self.Resizable = True

        # Selection state
        self.source_mesh_id: Optional[System.Guid] = None
        self.target_mesh_id: Optional[System.Guid] = None
        self.source_curve_id: Optional[System.Guid] = None
        self.target_curve_id: Optional[System.Guid] = None

        # Compiled point lists (populated by PrepareToMorph)
        self.source_points: List[Rhino.Geometry.Point3d] = []
        self.target_points: List[Rhino.Geometry.Point3d] = []

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        # -- Source group ---------------------------------------------------
        source_group = forms.GroupBox(Text="Source")
        source_layout = forms.DynamicLayout()
        source_layout.DefaultSpacing = drawing.Size(5, 5)
        source_layout.Padding = drawing.Padding(8)

        self._txt_source_mesh = forms.TextBox(ReadOnly=True,
                                              PlaceholderText="No mesh selected")
        btn_pick_source_mesh = forms.Button(Text="Pick Source Mesh")
        btn_pick_source_mesh.Click += self._on_pick_source_mesh

        source_layout.AddRow(forms.Label(Text="Source Mesh:"))
        source_layout.AddRow(self._txt_source_mesh, btn_pick_source_mesh)

        self._txt_source_curve = forms.TextBox(ReadOnly=True,
                                               PlaceholderText="No curve selected")
        btn_pick_source_curve = forms.Button(Text="Pick Source Curve")
        btn_pick_source_curve.Click += self._on_pick_source_curve

        source_layout.AddRow(forms.Label(Text="Source Curve:"))
        source_layout.AddRow(self._txt_source_curve, btn_pick_source_curve)

        source_group.Content = source_layout
        layout.AddRow(source_group)

        # -- Target group ---------------------------------------------------
        target_group = forms.GroupBox(Text="Target")
        target_layout = forms.DynamicLayout()
        target_layout.DefaultSpacing = drawing.Size(5, 5)
        target_layout.Padding = drawing.Padding(8)

        self._txt_target_mesh = forms.TextBox(ReadOnly=True,
                                              PlaceholderText="No mesh selected")
        btn_pick_target_mesh = forms.Button(Text="Pick Target Mesh")
        btn_pick_target_mesh.Click += self._on_pick_target_mesh

        target_layout.AddRow(forms.Label(Text="Target Mesh:"))
        target_layout.AddRow(self._txt_target_mesh, btn_pick_target_mesh)

        self._txt_target_curve = forms.TextBox(ReadOnly=True,
                                               PlaceholderText="No curve selected")
        btn_pick_target_curve = forms.Button(Text="Pick Target Curve")
        btn_pick_target_curve.Click += self._on_pick_target_curve

        target_layout.AddRow(forms.Label(Text="Target Curve:"))
        target_layout.AddRow(self._txt_target_curve, btn_pick_target_curve)

        target_group.Content = target_layout
        layout.AddRow(target_group)

        # -- Status ---------------------------------------------------------
        self._lbl_status = forms.Label(Text="Select source and target geometry.")
        layout.AddRow(self._lbl_status)

        layout.AddSpace()

        # -- Buttons --------------------------------------------------------
        btn_ok = forms.Button(Text="OK")
        btn_ok.Click += self._on_ok
        btn_cancel = forms.Button(Text="Cancel")
        btn_cancel.Click += self._on_cancel

        self.DefaultButton = btn_ok
        self.AbortButton = btn_cancel

        button_layout = forms.DynamicLayout()
        button_layout.AddRow(None, btn_cancel, btn_ok)
        layout.AddRow(button_layout)

        self.Content = layout

    # ------------------------------------------------------------------
    # Object picking
    # ------------------------------------------------------------------

    def _pick_object(self, prompt: str,
                     filter_type: Rhino.DocObjects.ObjectType
                     ) -> Optional[System.Guid]:
        """Hide the dialog, let the user pick an object, then re-show."""
        self.Visible = False
        try:
            obj_ref = rs.GetObject(prompt, filter=int(filter_type))
            if obj_ref:
                return rs.coerceguid(obj_ref)
        finally:
            self.Visible = True
        return None

    def _on_pick_source_mesh(self, sender, e):
        guid = self._pick_object(
            "Select source mesh",
            Rhino.DocObjects.ObjectType.Mesh,
        )
        if guid:
            self.source_mesh_id = guid
            self._txt_source_mesh.Text = str(guid)

    def _on_pick_target_mesh(self, sender, e):
        guid = self._pick_object(
            "Select target mesh",
            Rhino.DocObjects.ObjectType.Mesh,
        )
        if guid:
            self.target_mesh_id = guid
            self._txt_target_mesh.Text = str(guid)

    def _on_pick_source_curve(self, sender, e):
        guid = self._pick_object(
            "Select source curve",
            Rhino.DocObjects.ObjectType.Curve,
        )
        if guid:
            self.source_curve_id = guid
            self._txt_source_curve.Text = str(guid)

    def _on_pick_target_curve(self, sender, e):
        guid = self._pick_object(
            "Select target curve",
            Rhino.DocObjects.ObjectType.Curve,
        )
        if guid:
            self.target_curve_id = guid
            self._txt_target_curve.Text = str(guid)

    # ------------------------------------------------------------------
    # Validation and morph preparation
    # ------------------------------------------------------------------

    def PrepareToMorph(self) -> bool:
        """
        Validate the current selections, compile source and target
        point lists, and return True when the morph is ready to execute.
        """
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            self._lbl_status.Text = "Error: No active document."
            return False

        # Validate meshes
        if self.source_mesh_id is None or self.target_mesh_id is None:
            self._lbl_status.Text = "Both source and target meshes are required."
            return False

        source_obj = doc.Objects.FindId(self.source_mesh_id)
        target_obj = doc.Objects.FindId(self.target_mesh_id)
        if source_obj is None or target_obj is None:
            self._lbl_status.Text = "One or both mesh objects no longer exist."
            return False

        source_mesh = source_obj.Geometry
        target_mesh = target_obj.Geometry

        if not isinstance(source_mesh, Rhino.Geometry.Mesh):
            self._lbl_status.Text = "Source object is not a mesh."
            return False
        if not isinstance(target_mesh, Rhino.Geometry.Mesh):
            self._lbl_status.Text = "Target object is not a mesh."
            return False

        # Compile source points
        self.source_points = self._compile_points(
            source_mesh, self.source_curve_id, doc
        )
        self.target_points = self._compile_points(
            target_mesh, self.target_curve_id, doc
        )

        if len(self.source_points) == 0:
            self._lbl_status.Text = "Could not extract source points."
            return False
        if len(self.target_points) == 0:
            self._lbl_status.Text = "Could not extract target points."
            return False

        if len(self.source_points) != len(self.target_points):
            self._lbl_status.Text = (
                f"Point count mismatch: source={len(self.source_points)}, "
                f"target={len(self.target_points)}. Counts must match."
            )
            return False

        self._lbl_status.Text = (
            f"Ready: {len(self.source_points)} point pairs compiled."
        )
        return True

    @staticmethod
    def _compile_points(
        mesh: Rhino.Geometry.Mesh,
        curve_id: Optional[System.Guid],
        doc: Rhino.RhinoDoc,
    ) -> List[Rhino.Geometry.Point3d]:
        """
        Build an ordered point list from a mesh.

        If a guide curve is supplied, points are sampled along the curve
        and projected onto the mesh.  Otherwise, mesh vertices are used
        directly.
        """
        points: List[Rhino.Geometry.Point3d] = []

        if curve_id is not None:
            curve_obj = doc.Objects.FindId(curve_id)
            if curve_obj is not None:
                curve = curve_obj.Geometry
                if isinstance(curve, Rhino.Geometry.Curve):
                    # Sample curve at uniform parameter intervals
                    domain = curve.Domain
                    sample_count = min(mesh.Vertices.Count, 200)
                    for i in range(sample_count):
                        t = domain.ParameterAt(i / max(1, sample_count - 1))
                        pt = curve.PointAt(t)
                        # Project onto mesh
                        closest = mesh.ClosestPoint(pt)
                        if closest is not None and closest != Rhino.Geometry.Point3d.Unset:
                            points.append(closest)
                        else:
                            points.append(pt)
                    return points

        # Fallback: use mesh vertices directly
        for i in range(mesh.Vertices.Count):
            points.append(Rhino.Geometry.Point3d(mesh.Vertices[i]))

        return points

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_ok(self, sender, e):
        if self.PrepareToMorph():
            self.Close(True)
        # else: status label already shows the error

    def _on_cancel(self, sender, e):
        self.Close(False)
