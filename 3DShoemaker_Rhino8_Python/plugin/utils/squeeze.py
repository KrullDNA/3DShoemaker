"""
squeeze.py - Squeeze deformation utility for 3DShoemaker.

Provides the ``Squeeze`` class that applies a squeeze (compression /
expansion) deformation to geometry.  This is used in the shoe-last
workflow to modify the girth, width, or height of a last by compressing
or expanding geometry in one or more axes while keeping reference
planes fixed.

The squeeze operation works by defining:
  - A base plane and a height plane that bound the deformation zone.
  - An axis along which to squeeze.
  - A squeeze factor (< 1 = compress, > 1 = expand, 1 = no change).

Points between the two planes are moved along the squeeze axis
proportionally to their distance from the base plane, scaled by the
squeeze factor.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import Rhino
import Rhino.Geometry as rg


# ---------------------------------------------------------------------------
# Squeeze
# ---------------------------------------------------------------------------

class Squeeze:
    """Applies squeeze (compression / expansion) deformation.

    Parameters
    ----------
    base_plane : Plane
        The fixed reference plane (bottom of the deformation zone).
    height_plane : Plane
        The upper bound of the deformation zone.  Geometry beyond this
        plane is rigidly translated by the full squeeze amount.
    axis : Vector3d
        The direction along which squeezing is applied.  Typically the
        normal of the base plane.
    factor : float
        Squeeze factor.  Values < 1 compress, > 1 expand, 1 = identity.
    """

    def __init__(
        self,
        base_plane: rg.Plane,
        height_plane: rg.Plane,
        axis: Optional[rg.Vector3d] = None,
        factor: float = 1.0,
    ) -> None:
        self.base_plane = base_plane
        self.height_plane = height_plane
        self.axis = axis or base_plane.ZAxis
        self.factor = factor

        # Pre-compute the distance between the two planes along the axis
        self._zone_height = abs(
            self.base_plane.DistanceTo(self.height_plane.Origin)
        )
        if self._zone_height < 1e-12:
            self._zone_height = 1.0  # prevent division by zero

        # Unitize axis
        if self.axis.Length > 1e-12:
            self.axis.Unitize()
        else:
            self.axis = rg.Vector3d.ZAxis

    # ======================================================================
    # Core point transformation
    # ======================================================================

    def squeeze_point(self, point: rg.Point3d) -> rg.Point3d:
        """Apply the squeeze deformation to a single point.

        Parameters
        ----------
        point : Point3d

        Returns
        -------
        Point3d
            The deformed point.
        """
        # Signed distance from the base plane along the squeeze axis
        vec = point - self.base_plane.Origin
        dist = rg.Vector3d.Multiply(vec, self.axis)

        if dist < 0:
            # Below the base plane -- no deformation
            return point

        if dist > self._zone_height:
            # Above the height plane -- rigid translation by the full
            # squeeze delta so the top stays continuous
            delta = (self.factor - 1.0) * self._zone_height
            return point + self.axis * delta

        # Within the deformation zone -- proportional squeeze
        t = dist / self._zone_height  # 0 at base, 1 at height
        delta = (self.factor - 1.0) * dist
        return point + self.axis * delta

    # ======================================================================
    # Batch point transformation
    # ======================================================================

    def squeeze_points(
        self, points: Sequence[rg.Point3d],
    ) -> List[rg.Point3d]:
        """Apply squeeze to a sequence of points.

        Returns
        -------
        list[Point3d]
        """
        return [self.squeeze_point(pt) for pt in points]

    # ======================================================================
    # Curve deformation
    # ======================================================================

    def squeeze_curve(
        self,
        curve: rg.Curve,
        rebuild_point_count: int = 0,
    ) -> Optional[rg.Curve]:
        """Apply squeeze deformation to a curve.

        The curve is converted to a NurbsCurve and each control point is
        deformed.  Optionally the result can be rebuilt to a specific
        point count.

        Parameters
        ----------
        curve : Curve
        rebuild_point_count : int
            If > 0, rebuild the result to this many control points.

        Returns
        -------
        Curve or None
        """
        if curve is None:
            return None

        nurbs = curve.ToNurbsCurve()
        if nurbs is None:
            return None

        points = nurbs.Points
        for i in range(points.Count):
            cp = points[i]
            pt = rg.Point3d(cp.Location)
            new_pt = self.squeeze_point(pt)
            points.SetPoint(i, new_pt, cp.Weight)

        if rebuild_point_count > 0:
            rebuilt = nurbs.Rebuild(
                rebuild_point_count, nurbs.Degree, True,
            )
            if rebuilt is not None and rebuilt.IsValid:
                return rebuilt

        return nurbs if nurbs.IsValid else None

    def squeeze_curves(
        self, curves: Sequence[rg.Curve],
    ) -> List[rg.Curve]:
        """Apply squeeze to multiple curves.

        Curves that fail to deform are omitted from the result.
        """
        result: List[rg.Curve] = []
        for c in curves:
            deformed = self.squeeze_curve(c)
            if deformed is not None:
                result.append(deformed)
        return result

    # ======================================================================
    # Surface / Brep deformation
    # ======================================================================

    def squeeze_brep(
        self,
        brep: rg.Brep,
    ) -> Optional[rg.Brep]:
        """Apply squeeze deformation to a Brep.

        Deforms each face's underlying NURBS surface by moving its
        control points.

        Parameters
        ----------
        brep : Brep

        Returns
        -------
        Brep or None
        """
        if brep is None:
            return None

        dup = brep.DuplicateBrep()
        if dup is None:
            return None

        for face_idx in range(dup.Faces.Count):
            srf = dup.Faces[face_idx].UnderlyingSurface()
            if srf is None:
                continue
            nurbs_srf = srf.ToNurbsSurface()
            if nurbs_srf is None:
                continue

            points = nurbs_srf.Points
            for u in range(points.CountU):
                for v in range(points.CountV):
                    cp = points.GetControlPoint(u, v)
                    pt = rg.Point3d(cp.Location)
                    new_pt = self.squeeze_point(pt)
                    points.SetControlPoint(u, v,
                                           rg.ControlPoint(new_pt, cp.Weight))

            dup.Faces[face_idx].RebuildEdges(
                Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance,
                True, True,
            )

        if dup.IsValid:
            return dup

        # Attempt repair
        dup.Repair(Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance)
        return dup if dup.IsValid else None

    # ======================================================================
    # Mesh deformation
    # ======================================================================

    def squeeze_mesh(
        self,
        mesh: rg.Mesh,
    ) -> Optional[rg.Mesh]:
        """Apply squeeze deformation to a mesh.

        Each vertex is moved independently.

        Parameters
        ----------
        mesh : Mesh

        Returns
        -------
        Mesh or None
        """
        if mesh is None:
            return None

        dup = mesh.DuplicateMesh()
        if dup is None:
            return None

        vertices = dup.Vertices
        for i in range(vertices.Count):
            pt = rg.Point3d(vertices[i])
            new_pt = self.squeeze_point(pt)
            vertices.SetVertex(i, new_pt)

        dup.Normals.ComputeNormals()
        dup.Compact()
        return dup if dup.IsValid else None

    # ======================================================================
    # Convenience: two-axis squeeze
    # ======================================================================

    @staticmethod
    def create_width_squeeze(
        base_plane: rg.Plane,
        zone_height: float,
        factor: float,
    ) -> "Squeeze":
        """Create a squeeze along the X-axis of *base_plane* (width).

        Parameters
        ----------
        base_plane : Plane
            Reference plane.
        zone_height : float
            Height of the deformation zone.
        factor : float
            Squeeze factor.

        Returns
        -------
        Squeeze
        """
        height_origin = (
            base_plane.Origin + base_plane.ZAxis * zone_height
        )
        height_plane = rg.Plane(
            height_origin, base_plane.XAxis, base_plane.YAxis,
        )
        return Squeeze(base_plane, height_plane, base_plane.XAxis, factor)

    @staticmethod
    def create_girth_squeeze(
        base_plane: rg.Plane,
        zone_height: float,
        factor: float,
    ) -> "Squeeze":
        """Create a squeeze along the Y-axis of *base_plane* (girth).

        Returns
        -------
        Squeeze
        """
        height_origin = (
            base_plane.Origin + base_plane.ZAxis * zone_height
        )
        height_plane = rg.Plane(
            height_origin, base_plane.XAxis, base_plane.YAxis,
        )
        return Squeeze(base_plane, height_plane, base_plane.YAxis, factor)

    @staticmethod
    def create_height_squeeze(
        base_plane: rg.Plane,
        zone_height: float,
        factor: float,
    ) -> "Squeeze":
        """Create a squeeze along the Z-axis of *base_plane* (height).

        Returns
        -------
        Squeeze
        """
        height_origin = (
            base_plane.Origin + base_plane.ZAxis * zone_height
        )
        height_plane = rg.Plane(
            height_origin, base_plane.XAxis, base_plane.YAxis,
        )
        return Squeeze(base_plane, height_plane, base_plane.ZAxis, factor)

    # ======================================================================
    # Repr
    # ======================================================================

    def __repr__(self) -> str:
        return (
            f"<Squeeze factor={self.factor:.3f}, "
            f"zone_height={self._zone_height:.2f}, "
            f"axis=({self.axis.X:.2f}, {self.axis.Y:.2f}, {self.axis.Z:.2f})>"
        )
