"""
preview_module.py - Custom display conduit for Feet in Focus Shoe Kit preview rendering.

Provides real-time shaded/wireframe preview of Brep and SubD geometry
through Rhino's DisplayConduit pipeline, used during interactive
editing operations (e.g. last shaping, insole profiling).
"""

import traceback
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import Rhino
import Rhino.Display
import Rhino.DocObjects
import Rhino.Geometry
import System
import System.Drawing


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PreviewStyle(Enum):
    """How a preview object should be drawn."""
    SHADED = auto()
    WIREFRAME = auto()
    SHADED_AND_WIREFRAME = auto()
    GHOSTED = auto()


# ---------------------------------------------------------------------------
# PreviewObject
# ---------------------------------------------------------------------------

class PreviewObject:
    """
    Lightweight wrapper around a piece of geometry that should be shown
    in the preview conduit.

    Attributes
    ----------
    geometry : Rhino.Geometry.GeometryBase
        The Brep, SubD, Mesh, or Curve to display.
    color : System.Drawing.Color
        Fill / wire colour.
    style : PreviewStyle
        Rendering mode for this object.
    thickness : int
        Wire thickness in pixels (used for wireframe/curve drawing).
    transparency : float
        0.0 = fully opaque, 1.0 = fully transparent.
    material : Rhino.Display.DisplayMaterial | None
        Optional custom material; when None a material is built from
        *color* and *transparency*.
    tag : str
        Arbitrary label for identification / filtering.
    visible : bool
        Set to False to temporarily hide without removing.
    """

    def __init__(
        self,
        geometry: Rhino.Geometry.GeometryBase,
        color: System.Drawing.Color = None,
        style: PreviewStyle = PreviewStyle.SHADED_AND_WIREFRAME,
        thickness: int = 1,
        transparency: float = 0.0,
        material: Optional[Rhino.Display.DisplayMaterial] = None,
        tag: str = "",
        visible: bool = True,
    ) -> None:
        self.geometry = geometry
        self.color = color or System.Drawing.Color.FromArgb(180, 180, 220)
        self.style = style
        self.thickness = max(1, thickness)
        self.transparency = max(0.0, min(1.0, transparency))
        self.material = material
        self.tag = tag
        self.visible = visible

        # Build a default display material when none is supplied
        if self.material is None:
            self.material = self._build_material()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_material(self) -> Rhino.Display.DisplayMaterial:
        """Create a DisplayMaterial matching the object's colour/transparency."""
        mat = Rhino.Display.DisplayMaterial()
        mat.Diffuse = self.color
        mat.Specular = System.Drawing.Color.White
        mat.Shine = 0.6
        mat.Transparency = self.transparency

        # Compute a slightly darker emission to simulate ambient
        r = max(0, self.color.R - 40)
        g = max(0, self.color.G - 40)
        b = max(0, self.color.B - 40)
        mat.Emission = System.Drawing.Color.FromArgb(r, g, b)

        # Back-face colour: slightly lighter variant
        br = min(255, self.color.R + 30)
        bg = min(255, self.color.G + 30)
        bb = min(255, self.color.B + 30)
        mat.BackDiffuse = System.Drawing.Color.FromArgb(br, bg, bb)
        mat.BackTransparency = self.transparency

        return mat

    def update_color(self, color: System.Drawing.Color) -> None:
        """Change colour and rebuild the material."""
        self.color = color
        self.material = self._build_material()

    def update_transparency(self, value: float) -> None:
        """Change transparency and rebuild the material."""
        self.transparency = max(0.0, min(1.0, value))
        self.material = self._build_material()


# ---------------------------------------------------------------------------
# PreviewConduitClass
# ---------------------------------------------------------------------------

class PreviewConduitClass(Rhino.Display.DisplayConduit):
    """
    Custom DisplayConduit that draws a collection of PreviewObjects.

    Usage::

        conduit = PreviewConduitClass()
        conduit.AddPreviewObject(PreviewObject(brep, color=...))
        conduit.Enabled = True     # begin drawing
        Rhino.RhinoDoc.ActiveDoc.Views.Redraw()

        # ... when done ...
        conduit.ClearPreview()
        conduit.Enabled = False
        Rhino.RhinoDoc.ActiveDoc.Views.Redraw()
    """

    def __init__(self) -> None:
        super().__init__()
        self._objects: List[PreviewObject] = []
        self._bbox: Optional[Rhino.Geometry.BoundingBox] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def AddPreviewObject(self, preview_obj: PreviewObject) -> None:
        """Add a PreviewObject to the conduit's draw list."""
        if preview_obj is None or preview_obj.geometry is None:
            return
        self._objects.append(preview_obj)
        self._update_bounding_box()

    def AddPreviewObjects(self, objs: List[PreviewObject]) -> None:
        """Bulk-add multiple PreviewObjects."""
        for obj in objs:
            if obj is not None and obj.geometry is not None:
                self._objects.append(obj)
        self._update_bounding_box()

    def RemoveByTag(self, tag: str) -> int:
        """Remove all objects matching *tag*.  Returns count removed."""
        before = len(self._objects)
        self._objects = [o for o in self._objects if o.tag != tag]
        self._update_bounding_box()
        return before - len(self._objects)

    def ClearPreview(self) -> None:
        """Remove every preview object."""
        self._objects.clear()
        self._bbox = None

    @property
    def object_count(self) -> int:
        return len(self._objects)

    # ------------------------------------------------------------------
    # Bounding-box calculation
    # ------------------------------------------------------------------

    def _update_bounding_box(self) -> None:
        """Recompute the union bounding box of all preview objects."""
        if not self._objects:
            self._bbox = None
            return
        bbox = Rhino.Geometry.BoundingBox.Empty
        for obj in self._objects:
            if obj.visible and obj.geometry is not None:
                obj_box = obj.geometry.GetBoundingBox(False)
                if obj_box.IsValid:
                    bbox.Union(obj_box)
        self._bbox = bbox if bbox.IsValid else None

    # ------------------------------------------------------------------
    # DisplayConduit overrides
    # ------------------------------------------------------------------

    def CalculateBoundingBox(self, e) -> None:
        """Include our preview geometry in the viewport bounding box."""
        try:
            if self._bbox is not None and self._bbox.IsValid:
                e.IncludeBoundingBox(self._bbox)
        except Exception:
            pass

    def CalculateBoundingBoxZoomExtents(self, e) -> None:
        """Include preview geometry in zoom-extents computation."""
        try:
            if self._bbox is not None and self._bbox.IsValid:
                e.IncludeBoundingBox(self._bbox)
        except Exception:
            pass

    def PreDrawObjects(self, e) -> None:
        """
        Main drawing callback.  Called once per frame before Rhino draws
        its own document objects.

        Iterates the preview list and delegates to the appropriate
        draw method based on geometry type and preview style.
        """
        try:
            for obj in self._objects:
                if not obj.visible or obj.geometry is None:
                    continue
                self._draw_object(e, obj)
        except Exception as ex:
            # Fail silently in the render pipeline to avoid crashes
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] PreviewConduit draw error: {ex}"
            )

    def PostDrawObjects(self, e) -> None:
        """
        Secondary drawing pass executed after document objects are drawn.

        Used for transparent / ghosted objects so they composite over
        the opaque scene.
        """
        try:
            for obj in self._objects:
                if not obj.visible or obj.geometry is None:
                    continue
                if obj.style == PreviewStyle.GHOSTED:
                    self._draw_object(e, obj)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Drawing dispatch
    # ------------------------------------------------------------------

    def _draw_object(
        self,
        e: Rhino.Display.DrawEventArgs,
        obj: PreviewObject,
    ) -> None:
        """Route *obj* to the correct draw method."""
        geom = obj.geometry
        pipeline = e.Display

        if isinstance(geom, Rhino.Geometry.Brep):
            if obj.style in (
                PreviewStyle.SHADED, PreviewStyle.SHADED_AND_WIREFRAME,
                PreviewStyle.GHOSTED,
            ):
                self.DrawBrepShaded(pipeline, geom, obj.material)
            if obj.style in (
                PreviewStyle.WIREFRAME, PreviewStyle.SHADED_AND_WIREFRAME,
            ):
                self.DrawBrepWires(
                    pipeline, geom, obj.color, obj.thickness
                )

        elif isinstance(geom, Rhino.Geometry.SubD):
            if obj.style in (
                PreviewStyle.SHADED, PreviewStyle.SHADED_AND_WIREFRAME,
                PreviewStyle.GHOSTED,
            ):
                self.DrawSubDShaded(pipeline, geom, obj.material)
            if obj.style in (
                PreviewStyle.WIREFRAME, PreviewStyle.SHADED_AND_WIREFRAME,
            ):
                self.DrawSubDWires(
                    pipeline, geom, obj.color, obj.thickness
                )

        elif isinstance(geom, Rhino.Geometry.Mesh):
            if obj.style in (
                PreviewStyle.SHADED, PreviewStyle.SHADED_AND_WIREFRAME,
                PreviewStyle.GHOSTED,
            ):
                self._draw_mesh_shaded(pipeline, geom, obj.material)
            if obj.style in (
                PreviewStyle.WIREFRAME, PreviewStyle.SHADED_AND_WIREFRAME,
            ):
                self._draw_mesh_wires(
                    pipeline, geom, obj.color, obj.thickness
                )

        elif isinstance(geom, Rhino.Geometry.Curve):
            self._draw_curve(pipeline, geom, obj.color, obj.thickness)

        elif isinstance(geom, Rhino.Geometry.Point3d):
            self._draw_point(pipeline, geom, obj.color, obj.thickness)

        elif isinstance(geom, Rhino.Geometry.PointCloud):
            self._draw_point_cloud(pipeline, geom, obj.color, obj.thickness)

    # ------------------------------------------------------------------
    # Brep drawing
    # ------------------------------------------------------------------

    @staticmethod
    def DrawBrepShaded(
        pipeline: Rhino.Display.DisplayPipeline,
        brep: Rhino.Geometry.Brep,
        material: Rhino.Display.DisplayMaterial,
    ) -> None:
        """
        Draw a Brep with shaded faces using *material*.

        The Brep is tessellated into render meshes which are then drawn
        through the pipeline's shaded-mesh routine.
        """
        try:
            meshes = Rhino.Geometry.Mesh.CreateFromBrep(
                brep,
                Rhino.Geometry.MeshingParameters.Default,
            )
            if meshes:
                for mesh in meshes:
                    if mesh and mesh.IsValid:
                        pipeline.DrawMeshShaded(mesh, material)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] DrawBrepShaded error: {ex}"
            )

    @staticmethod
    def DrawBrepWires(
        pipeline: Rhino.Display.DisplayPipeline,
        brep: Rhino.Geometry.Brep,
        color: System.Drawing.Color,
        thickness: int = 1,
    ) -> None:
        """Draw the wireframe edges of a Brep."""
        try:
            pipeline.DrawBrepWires(brep, color, thickness)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] DrawBrepWires error: {ex}"
            )

    # ------------------------------------------------------------------
    # SubD drawing
    # ------------------------------------------------------------------

    @staticmethod
    def DrawSubDShaded(
        pipeline: Rhino.Display.DisplayPipeline,
        subd: Rhino.Geometry.SubD,
        material: Rhino.Display.DisplayMaterial,
    ) -> None:
        """
        Draw a SubD surface with shading.

        SubD is converted to its limit surface mesh for display.
        """
        try:
            mesh = Rhino.Geometry.Mesh.CreateFromSubD(subd, 0)
            if mesh and mesh.IsValid:
                pipeline.DrawMeshShaded(mesh, material)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] DrawSubDShaded error: {ex}"
            )

    @staticmethod
    def DrawSubDWires(
        pipeline: Rhino.Display.DisplayPipeline,
        subd: Rhino.Geometry.SubD,
        color: System.Drawing.Color,
        thickness: int = 1,
    ) -> None:
        """Draw the wireframe edges of a SubD."""
        try:
            pipeline.DrawSubDWires(subd, color, thickness)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] DrawSubDWires error: {ex}"
            )

    # ------------------------------------------------------------------
    # Mesh drawing
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_mesh_shaded(
        pipeline: Rhino.Display.DisplayPipeline,
        mesh: Rhino.Geometry.Mesh,
        material: Rhino.Display.DisplayMaterial,
    ) -> None:
        try:
            pipeline.DrawMeshShaded(mesh, material)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] _draw_mesh_shaded error: {ex}"
            )

    @staticmethod
    def _draw_mesh_wires(
        pipeline: Rhino.Display.DisplayPipeline,
        mesh: Rhino.Geometry.Mesh,
        color: System.Drawing.Color,
        thickness: int = 1,
    ) -> None:
        try:
            pipeline.DrawMeshWires(mesh, color, thickness)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] _draw_mesh_wires error: {ex}"
            )

    # ------------------------------------------------------------------
    # Curve / Point drawing
    # ------------------------------------------------------------------

    @staticmethod
    def _draw_curve(
        pipeline: Rhino.Display.DisplayPipeline,
        curve: Rhino.Geometry.Curve,
        color: System.Drawing.Color,
        thickness: int = 1,
    ) -> None:
        try:
            pipeline.DrawCurve(curve, color, thickness)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] _draw_curve error: {ex}"
            )

    @staticmethod
    def _draw_point(
        pipeline: Rhino.Display.DisplayPipeline,
        point: Rhino.Geometry.Point3d,
        color: System.Drawing.Color,
        size: int = 5,
    ) -> None:
        try:
            style = Rhino.Display.PointStyle.Simple
            pipeline.DrawPoint(point, style, size, color)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] _draw_point error: {ex}"
            )

    @staticmethod
    def _draw_point_cloud(
        pipeline: Rhino.Display.DisplayPipeline,
        cloud: Rhino.Geometry.PointCloud,
        color: System.Drawing.Color,
        size: int = 3,
    ) -> None:
        try:
            pipeline.DrawPointCloud(cloud, size, color)
        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[Feet in Focus Shoe Kit] _draw_point_cloud error: {ex}"
            )

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        enabled = "enabled" if self.Enabled else "disabled"
        return (
            f"<PreviewConduitClass {enabled}, "
            f"{len(self._objects)} object(s)>"
        )
