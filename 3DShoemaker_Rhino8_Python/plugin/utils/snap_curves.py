"""
snap_curves.py - Curve snapping utility for Feet in Focus Shoe Kit.

Provides the ``SnapCurves`` class that snaps (pulls / projects) curves
onto surfaces and meshes.  Used during interactive editing operations
such as drawing insole outlines on a last surface or positioning seam
lines on a foot scan mesh.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence

import Rhino
import Rhino.Geometry as rg


# ---------------------------------------------------------------------------
# SnapCurves
# ---------------------------------------------------------------------------

class SnapCurves:
    """Snaps curves to surfaces and meshes.

    The class maintains a reference geometry (surface or mesh) and provides
    methods to snap individual curves or collections of curves onto that
    target.

    Parameters
    ----------
    target_brep : Brep or None
        A Brep surface to snap onto.
    target_mesh : Mesh or None
        A mesh to snap onto (used when *target_brep* is None or when a
        mesh is faster/more appropriate).
    tolerance : float
        Snapping tolerance.  0 uses the active document tolerance.
    """

    def __init__(
        self,
        target_brep: Optional[rg.Brep] = None,
        target_mesh: Optional[rg.Mesh] = None,
        tolerance: float = 0.0,
    ) -> None:
        self.target_brep = target_brep
        self.target_mesh = target_mesh
        self.tolerance = (
            tolerance
            or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        )

    # ======================================================================
    # Single-curve operations
    # ======================================================================

    def snap_curve_to_brep(
        self,
        curve: rg.Curve,
        brep: Optional[rg.Brep] = None,
    ) -> Optional[List[rg.Curve]]:
        """Pull *curve* onto a Brep surface (closest-point projection).

        Parameters
        ----------
        curve : Curve
            The curve to snap.
        brep : Brep or None
            Override the instance target.

        Returns
        -------
        list[Curve] or None
        """
        target = brep or self.target_brep
        if curve is None or target is None:
            return None

        results: List[rg.Curve] = []
        for i in range(target.Faces.Count):
            face = target.Faces[i]
            pulled = rg.Curve.PullToBrepFace(curve, face, self.tolerance)
            if pulled:
                results.extend(pulled)

        return results if results else None

    def snap_curve_to_mesh(
        self,
        curve: rg.Curve,
        mesh: Optional[rg.Mesh] = None,
        direction: Optional[rg.Vector3d] = None,
    ) -> Optional[List[rg.Curve]]:
        """Project *curve* onto a mesh.

        Parameters
        ----------
        curve : Curve
            The curve to snap.
        mesh : Mesh or None
            Override the instance target mesh.
        direction : Vector3d or None
            Projection direction.  Defaults to -Z (downward).

        Returns
        -------
        list[Curve] or None
        """
        target = mesh or self.target_mesh
        if curve is None or target is None:
            return None

        proj_dir = direction or rg.Vector3d(0, 0, -1)

        result = rg.Curve.ProjectToMesh(
            [curve], [target], proj_dir, self.tolerance,
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    def snap_curve_to_surface(
        self,
        curve: rg.Curve,
        surface: rg.Surface,
    ) -> Optional[List[rg.Curve]]:
        """Pull *curve* onto a Surface (not Brep).

        Parameters
        ----------
        curve : Curve
        surface : Surface

        Returns
        -------
        list[Curve] or None
        """
        if curve is None or surface is None:
            return None

        result = rg.Curve.PullToSurface(curve, surface, self.tolerance)
        if result is None or len(result) == 0:
            return None
        return list(result)

    # ======================================================================
    # Multi-curve operations
    # ======================================================================

    def snap_curves_to_brep(
        self,
        curves: Sequence[rg.Curve],
        brep: Optional[rg.Brep] = None,
    ) -> List[List[rg.Curve]]:
        """Snap multiple curves to a Brep.

        Returns a list of results (one per input curve).  Each result
        is a list of projected curve segments, or an empty list on failure.
        """
        results: List[List[rg.Curve]] = []
        for c in curves:
            snapped = self.snap_curve_to_brep(c, brep)
            results.append(snapped or [])
        return results

    def snap_curves_to_mesh(
        self,
        curves: Sequence[rg.Curve],
        mesh: Optional[rg.Mesh] = None,
        direction: Optional[rg.Vector3d] = None,
    ) -> List[List[rg.Curve]]:
        """Snap multiple curves to a mesh.

        Returns a list of results (one per input curve).
        """
        results: List[List[rg.Curve]] = []
        for c in curves:
            snapped = self.snap_curve_to_mesh(c, mesh, direction)
            results.append(snapped or [])
        return results

    # ======================================================================
    # Point snapping
    # ======================================================================

    def snap_point_to_brep(
        self,
        point: rg.Point3d,
        brep: Optional[rg.Brep] = None,
    ) -> Optional[rg.Point3d]:
        """Find the closest point on a Brep to *point*.

        Returns the closest point, or None on failure.
        """
        target = brep or self.target_brep
        if target is None:
            return None
        result = target.ClosestPoint(point)
        if result != rg.Point3d.Unset:
            return result
        return None

    def snap_point_to_mesh(
        self,
        point: rg.Point3d,
        mesh: Optional[rg.Mesh] = None,
    ) -> Optional[rg.Point3d]:
        """Find the closest point on a mesh to *point*.

        Returns the closest point, or None on failure.
        """
        target = mesh or self.target_mesh
        if target is None:
            return None
        result = target.ClosestPoint(point)
        if result != rg.Point3d.Unset:
            return result
        return None

    def snap_points_to_brep(
        self,
        points: Sequence[rg.Point3d],
        brep: Optional[rg.Brep] = None,
    ) -> List[rg.Point3d]:
        """Snap multiple points to a Brep.

        Points that fail to snap are returned unchanged.
        """
        result: List[rg.Point3d] = []
        for pt in points:
            snapped = self.snap_point_to_brep(pt, brep)
            result.append(snapped if snapped is not None else pt)
        return result

    def snap_points_to_mesh(
        self,
        points: Sequence[rg.Point3d],
        mesh: Optional[rg.Mesh] = None,
    ) -> List[rg.Point3d]:
        """Snap multiple points to a mesh.

        Points that fail to snap are returned unchanged.
        """
        result: List[rg.Point3d] = []
        for pt in points:
            snapped = self.snap_point_to_mesh(pt, mesh)
            result.append(snapped if snapped is not None else pt)
        return result

    # ======================================================================
    # Offset snap (snap then offset normal to surface)
    # ======================================================================

    def snap_curve_offset_normal(
        self,
        curve: rg.Curve,
        surface: rg.Surface,
        height: float,
    ) -> Optional[List[rg.Curve]]:
        """Snap a curve to a surface and then offset it along the surface
        normal by *height*.

        This is commonly used to create curves that float above a surface
        at a constant material-thickness distance.

        Parameters
        ----------
        curve : Curve
        surface : Surface
        height : float
            Offset distance along the surface normal.

        Returns
        -------
        list[Curve] or None
        """
        if curve is None or surface is None:
            return None

        # First pull to the surface
        pulled = rg.Curve.PullToSurface(curve, surface, self.tolerance)
        if not pulled:
            return None

        # Then offset each pulled segment along the surface normal
        result: List[rg.Curve] = []
        for pc in pulled:
            offset = rg.Curve.OffsetNormalToSurface(surface, pc, height)
            if offset is not None:
                result.append(offset)
            else:
                result.append(pc)  # fallback: return un-offset curve

        return result if result else None

    # ======================================================================
    # Rebuild after snap
    # ======================================================================

    @staticmethod
    def rebuild_curve(
        curve: rg.Curve,
        point_count: int = 20,
        degree: int = 3,
    ) -> Optional[rg.NurbsCurve]:
        """Rebuild a curve to a given point count and degree.

        Useful after snapping when the projected curve may have more
        control points than desired.

        Returns
        -------
        NurbsCurve or None
        """
        if curve is None:
            return None
        nurbs = curve.Rebuild(point_count, degree, True)
        return nurbs if nurbs is not None and nurbs.IsValid else None

    # ======================================================================
    # Repr
    # ======================================================================

    def __repr__(self) -> str:
        parts = []
        if self.target_brep is not None:
            parts.append("brep")
        if self.target_mesh is not None:
            parts.append("mesh")
        target = "+".join(parts) if parts else "none"
        return f"<SnapCurves target={target}, tol={self.tolerance:.4f}>"
