"""
geometry_utils.py - Geometry utility functions for Feet in Focus Shoe Kit.

Wraps Rhino.Geometry operations for boolean operations, surface creation,
curve manipulation, meshing, and offset/projection tasks used throughout
the footwear-design workflow.

All public helpers are collected under the ``GeometryUtils`` class as
static methods so they can be called without instantiation.
"""

from typing import List, Optional, Sequence, Tuple

import Rhino
import Rhino.Geometry as rg


# ---------------------------------------------------------------------------
# GeometryUtils
# ---------------------------------------------------------------------------

class GeometryUtils:
    """Static helper methods that wrap Rhino.Geometry operations."""

    # ======================================================================
    # Boolean operations
    # ======================================================================

    @staticmethod
    def CreateBooleanDifference(
        brep_a: rg.Brep,
        brep_b: rg.Brep,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Compute the boolean difference *A - B*.

        Parameters
        ----------
        brep_a : Brep
            The Brep to subtract from.
        brep_b : Brep
            The Brep to subtract.
        tolerance : float
            Intersection tolerance. 0 uses the document tolerance.

        Returns
        -------
        list[Brep] or None
            Resulting Breps, or None on failure.
        """
        if brep_a is None or brep_b is None:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Brep.CreateBooleanDifference(brep_a, brep_b, tol)
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CreateBooleanUnion(
        breps: Sequence[rg.Brep],
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Compute the boolean union of multiple Breps.

        Parameters
        ----------
        breps : sequence of Brep
            Two or more Breps to union.
        tolerance : float
            Intersection tolerance. 0 uses the document tolerance.

        Returns
        -------
        list[Brep] or None
        """
        if breps is None or len(breps) < 2:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Brep.CreateBooleanUnion(breps, tol)
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CreateBooleanIntersection(
        brep_a: rg.Brep,
        brep_b: rg.Brep,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Compute the boolean intersection of two Breps.

        Returns
        -------
        list[Brep] or None
        """
        if brep_a is None or brep_b is None:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Brep.CreateBooleanIntersection(brep_a, brep_b, tol)
        if result is None or len(result) == 0:
            return None
        return list(result)

    # ======================================================================
    # Surface / Brep creation
    # ======================================================================

    @staticmethod
    def CreateFromSubD(subd: rg.SubD) -> Optional[rg.Brep]:
        """Convert a SubD to a Brep via its NURBS representation.

        Returns
        -------
        Brep or None
        """
        if subd is None:
            return None
        brep = subd.ToBrep(rg.SubDToBrepOptions())
        return brep if brep is not None and brep.IsValid else None

    @staticmethod
    def CreateFromOffsetFace(
        face: rg.BrepFace,
        offset_distance: float,
        tolerance: float = 0.0,
        both_sides: bool = False,
        create_solid: bool = True,
    ) -> Optional[rg.Brep]:
        """Offset a Brep face to create a solid or shell.

        Parameters
        ----------
        face : BrepFace
            The face to offset.
        offset_distance : float
            Distance to offset (positive = outward along normal).
        tolerance : float
            Tolerance for the operation.
        both_sides : bool
            Offset in both directions.
        create_solid : bool
            Whether to cap the result into a closed solid.

        Returns
        -------
        Brep or None
        """
        if face is None:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        brep = rg.Brep.CreateFromOffsetFace(
            face, offset_distance, tol, both_sides, create_solid,
        )
        return brep if brep is not None and brep.IsValid else None

    @staticmethod
    def CreateFromTaperedExtrude(
        curve: rg.Curve,
        distance: float,
        direction: rg.Vector3d,
        base_point: rg.Point3d,
        draft_angle_radians: float,
        corner_type: rg.ExtrudeCornerType = rg.ExtrudeCornerType.None_,
        tolerance: float = 0.0,
        angle_tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Create a tapered extrusion from a curve.

        Parameters
        ----------
        curve : Curve
            Profile curve.
        distance : float
            Extrusion distance.
        direction : Vector3d
            Extrusion direction.
        base_point : Point3d
            Base point for the draft angle.
        draft_angle_radians : float
            Draft / taper angle in radians.
        corner_type : ExtrudeCornerType
            How corners are handled.
        tolerance, angle_tolerance : float
            Document tolerances when 0.

        Returns
        -------
        list[Brep] or None
        """
        if curve is None:
            return None
        doc = Rhino.RhinoDoc.ActiveDoc
        tol = tolerance or doc.ModelAbsoluteTolerance
        atol = angle_tolerance or doc.ModelAngleToleranceRadians
        result = rg.Brep.CreateFromTaperedExtrude(
            curve, distance, direction, base_point,
            draft_angle_radians, corner_type, tol, atol,
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CreateFromLoft(
        curves: Sequence[rg.Curve],
        loft_type: rg.LoftType = rg.LoftType.Normal,
        closed: bool = False,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Loft through a sequence of section curves.

        Parameters
        ----------
        curves : sequence of Curve
            Section curves in order.
        loft_type : LoftType
            Lofting algorithm.
        closed : bool
            True to create a closed (periodic) loft.
        tolerance : float
            Fitting tolerance. 0 uses the document tolerance.

        Returns
        -------
        list[Brep] or None
        """
        if curves is None or len(curves) < 2:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        start = rg.Point3d.Unset
        end = rg.Point3d.Unset
        result = rg.Brep.CreateFromLoft(
            curves, start, end, loft_type, closed,
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CreateEdgeSurface(
        curves: Sequence[rg.Curve],
    ) -> Optional[rg.Brep]:
        """Create an edge surface (2, 3, or 4 boundary curves).

        Returns
        -------
        Brep or None
        """
        if curves is None or len(curves) < 2 or len(curves) > 4:
            return None
        result = rg.Brep.CreateEdgeSurface(curves)
        return result if result is not None and result.IsValid else None

    @staticmethod
    def CreateNetworkSurface(
        u_curves: Sequence[rg.Curve],
        u_continuity: int,
        v_curves: Sequence[rg.Curve],
        v_continuity: int,
        edge_tolerance: float = 0.0,
        interior_tolerance: float = 0.0,
        angle_tolerance_radians: float = 0.0,
    ) -> Optional[rg.Brep]:
        """Create a network surface from two sets of crossing curves.

        Parameters
        ----------
        u_curves, v_curves : sequence of Curve
            Curves in the U and V directions.
        u_continuity, v_continuity : int
            Continuity order (0=position, 1=tangency, 2=curvature).
        edge_tolerance, interior_tolerance : float
            Fitting tolerances. 0 uses the document default.
        angle_tolerance_radians : float
            Angle tolerance in radians. 0 uses the document default.

        Returns
        -------
        Brep or None
        """
        if not u_curves or not v_curves:
            return None
        doc = Rhino.RhinoDoc.ActiveDoc
        e_tol = edge_tolerance or doc.ModelAbsoluteTolerance
        i_tol = interior_tolerance or doc.ModelAbsoluteTolerance
        a_tol = angle_tolerance_radians or doc.ModelAngleToleranceRadians

        error_code = 0
        result = rg.NurbsSurface.CreateNetworkSurface(
            u_curves, u_continuity,
            v_curves, v_continuity,
            e_tol, i_tol, a_tol,
        )
        if result is None:
            return None
        # CreateNetworkSurface returns (NurbsSurface, int) tuple
        if isinstance(result, tuple):
            srf, error_code = result
            if srf is None:
                return None
            return srf.ToBrep()
        return result.ToBrep() if hasattr(result, "ToBrep") else None

    @staticmethod
    def CreatePatch(
        geometry: Sequence[rg.GeometryBase],
        u_spans: int = 10,
        v_spans: int = 10,
        tolerance: float = 0.0,
    ) -> Optional[rg.Brep]:
        """Create a patch surface through geometry (points and curves).

        Parameters
        ----------
        geometry : sequence of GeometryBase
            Input curves, points, point clouds.
        u_spans, v_spans : int
            Span counts in U and V.
        tolerance : float
            Fitting tolerance.

        Returns
        -------
        Brep or None
        """
        if geometry is None or len(geometry) == 0:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Brep.CreatePatch(
            geometry, u_spans, v_spans, tol,
        )
        return result if result is not None and result.IsValid else None

    @staticmethod
    def CreatePipe(
        rail: rg.Curve,
        radius: float,
        local_blending: bool = False,
        cap: rg.PipeCapMode = rg.PipeCapMode.Round,
        fit_rail: bool = False,
        tolerance: float = 0.0,
        angle_tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Create a pipe surface along a rail curve.

        Parameters
        ----------
        rail : Curve
            Centre-line curve.
        radius : float
            Pipe radius.
        local_blending : bool
            Use local blending for better results on kinked rails.
        cap : PipeCapMode
            How ends are capped (None_, Flat, Round).
        fit_rail : bool
            Fit pipe more closely to the rail.
        tolerance, angle_tolerance : float
            0 uses the document defaults.

        Returns
        -------
        list[Brep] or None
        """
        if rail is None or radius <= 0.0:
            return None
        doc = Rhino.RhinoDoc.ActiveDoc
        tol = tolerance or doc.ModelAbsoluteTolerance
        atol = angle_tolerance or doc.ModelAngleToleranceRadians
        result = rg.Brep.CreatePipe(
            rail, radius, local_blending, cap, fit_rail, tol, atol,
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CreateFillet(
        face_a: rg.BrepFace,
        uv_a: rg.Point2d,
        face_b: rg.BrepFace,
        uv_b: rg.Point2d,
        radius: float,
        extend: bool = True,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Create a fillet surface between two Brep faces.

        Parameters
        ----------
        face_a, face_b : BrepFace
            The two faces to fillet between.
        uv_a, uv_b : Point2d
            Parameter-space seed points on each face.
        radius : float
            Fillet radius.
        extend : bool
            Extend surfaces if needed.
        tolerance : float
            0 uses the document tolerance.

        Returns
        -------
        list[Brep] or None
        """
        if face_a is None or face_b is None or radius <= 0.0:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Brep.CreateFilletSurface(
            face_a, uv_a, face_b, uv_b, radius, extend, tol,
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CreateFilletEdges(
        brep: rg.Brep,
        edge_indices: Sequence[int],
        radii_start: Sequence[float],
        radii_end: Sequence[float],
        blend_type: rg.BlendType = rg.BlendType.Fillet,
        rail_type: rg.RailType = rg.RailType.RollingBall,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Fillet edges of a Brep.

        Parameters
        ----------
        brep : Brep
            The Brep whose edges should be filleted.
        edge_indices : sequence of int
            Indices of edges to fillet.
        radii_start, radii_end : sequence of float
            Start and end radii for each edge.
        blend_type : BlendType
            Fillet, Chamfer, or Blend.
        rail_type : RailType
            RollingBall, DistanceFromEdge, etc.
        tolerance : float
            0 uses the document tolerance.

        Returns
        -------
        list[Brep] or None
        """
        if brep is None or not edge_indices:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Brep.CreateFilletEdges(
            brep, list(edge_indices),
            list(radii_start), list(radii_end),
            blend_type, rail_type, tol,
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CreateOffsetBrep(
        brep: rg.Brep,
        distance: float,
        solid: bool = True,
        extend: bool = True,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Offset all faces of a Brep.

        Parameters
        ----------
        brep : Brep
            Input Brep.
        distance : float
            Offset distance (positive = outward).
        solid : bool
            Create a closed solid offset.
        extend : bool
            Extend offset surfaces through kinks.
        tolerance : float
            0 uses the document tolerance.

        Returns
        -------
        list[Brep] or None
        """
        if brep is None:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        outbreaks = rg.Brep.CreateOffsetBrep(
            brep, distance, solid, extend, tol,
        )
        # CreateOffsetBrep returns (Brep[], BrepFace[]) or similar tuple
        if outbreaks is None:
            return None
        if isinstance(outbreaks, tuple):
            result_breps = outbreaks[0]
        else:
            result_breps = outbreaks
        if result_breps is None or len(result_breps) == 0:
            return None
        return list(result_breps)

    # ======================================================================
    # Quad remeshing
    # ======================================================================

    @staticmethod
    def QuadRemeshBrep(
        brep: rg.Brep,
        target_quad_count: int = 2000,
        adaptive_quad_count: bool = True,
        adaptive_size: float = 50.0,
        detect_hard_edges: bool = True,
        preserve_symmetry: bool = False,
        symmetry_plane: Optional[rg.Plane] = None,
    ) -> Optional[rg.Mesh]:
        """Perform quad-dominant remeshing of a Brep.

        Parameters
        ----------
        brep : Brep
            Input Brep.
        target_quad_count : int
            Target number of quad faces.
        adaptive_quad_count : bool
            Allow the mesher to vary quad count for quality.
        adaptive_size : float
            0-100 slider for adaptive sizing.
        detect_hard_edges : bool
            Detect and preserve hard edges.
        preserve_symmetry : bool
            Try to produce a symmetric mesh.
        symmetry_plane : Plane or None
            Plane of symmetry if preserve_symmetry is True.

        Returns
        -------
        Mesh or None
        """
        if brep is None:
            return None
        params = rg.QuadRemeshParameters()
        params.TargetQuadCount = target_quad_count
        params.AdaptiveQuadCount = adaptive_quad_count
        params.AdaptiveSize = adaptive_size
        params.DetectHardEdges = detect_hard_edges
        if preserve_symmetry and symmetry_plane is not None:
            params.PreserveSymmetry = True
            params.SymmetryPlane = symmetry_plane
        mesh = rg.Mesh.QuadRemeshBrep(brep, params)
        return mesh if mesh is not None and mesh.IsValid else None

    @staticmethod
    def QuadRemeshBrepWithParameters(
        brep: rg.Brep,
        parameters: rg.QuadRemeshParameters,
    ) -> Optional[rg.Mesh]:
        """Quad-remesh a Brep using a pre-configured parameters object.

        Returns
        -------
        Mesh or None
        """
        if brep is None or parameters is None:
            return None
        mesh = rg.Mesh.QuadRemeshBrep(brep, parameters)
        return mesh if mesh is not None and mesh.IsValid else None

    # ======================================================================
    # ShrinkWrap meshing
    # ======================================================================

    @staticmethod
    def CreateShrinkWrapParameters(
        resolution: int = 256,
        offset: float = 0.0,
        smooth_steps: int = 5,
        feature_angle_degrees: float = 20.0,
    ) -> "rg.ShrinkWrapParameters":
        """Create a ShrinkWrapParameters object for mesh wrapping.

        Parameters
        ----------
        resolution : int
            Voxel resolution for the wrapping grid.
        offset : float
            Offset distance from the original geometry.
        smooth_steps : int
            Number of smoothing iterations.
        feature_angle_degrees : float
            Angle threshold for detecting features.

        Returns
        -------
        ShrinkWrapParameters
        """
        params = rg.ShrinkWrapParameters()
        params.Resolution = resolution
        params.Offset = offset
        params.SmoothSteps = smooth_steps
        params.FeatureAngle = feature_angle_degrees
        return params

    @staticmethod
    def ShrinkWrap(
        meshes: Sequence[rg.Mesh],
        parameters: "rg.ShrinkWrapParameters",
    ) -> Optional[rg.Mesh]:
        """Apply shrink-wrap meshing to a collection of meshes.

        Parameters
        ----------
        meshes : sequence of Mesh
            Input meshes to wrap.
        parameters : ShrinkWrapParameters
            Wrapping configuration.

        Returns
        -------
        Mesh or None
        """
        if not meshes or parameters is None:
            return None
        result = rg.Mesh.CreateShrinkWrapMesh(list(meshes), parameters)
        return result if result is not None and result.IsValid else None

    # ======================================================================
    # Curve creation and manipulation
    # ======================================================================

    @staticmethod
    def CreateTweenCurves(
        curve_a: rg.Curve,
        curve_b: rg.Curve,
        num_curves: int = 1,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Curve]]:
        """Create tween (intermediate) curves between two curves.

        Parameters
        ----------
        curve_a, curve_b : Curve
            Start and end curves.
        num_curves : int
            Number of intermediate curves.
        tolerance : float
            0 uses the document tolerance.

        Returns
        -------
        list[Curve] or None
        """
        if curve_a is None or curve_b is None or num_curves < 1:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Curve.CreateTweenCurves(curve_a, curve_b, num_curves, tol)
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CreateInterpolatedCurve(
        points: Sequence[rg.Point3d],
        degree: int = 3,
        knot_style: rg.CurveKnotStyle = rg.CurveKnotStyle.Chord,
        start_tangent: Optional[rg.Vector3d] = None,
        end_tangent: Optional[rg.Vector3d] = None,
    ) -> Optional[rg.Curve]:
        """Create an interpolated curve through points.

        Parameters
        ----------
        points : sequence of Point3d
            Points the curve must pass through.
        degree : int
            Curve degree (typically 3).
        knot_style : CurveKnotStyle
            Parameterization style.
        start_tangent, end_tangent : Vector3d or None
            Optional tangent vectors at the ends.

        Returns
        -------
        Curve or None
        """
        if points is None or len(points) < 2:
            return None
        st = start_tangent if start_tangent is not None else rg.Vector3d.Unset
        et = end_tangent if end_tangent is not None else rg.Vector3d.Unset
        result = rg.Curve.CreateInterpolatedCurve(
            list(points), degree, knot_style, st, et,
        )
        return result if result is not None and result.IsValid else None

    @staticmethod
    def CreateControlPointCurve(
        points: Sequence[rg.Point3d],
        degree: int = 3,
    ) -> Optional[rg.NurbsCurve]:
        """Create a NURBS curve from control points.

        Parameters
        ----------
        points : sequence of Point3d
            Control points.
        degree : int
            Curve degree.

        Returns
        -------
        NurbsCurve or None
        """
        if points is None or len(points) < 2:
            return None
        result = rg.Curve.CreateControlPointCurve(list(points), degree)
        return result if result is not None and result.IsValid else None

    @staticmethod
    def CreateSoftEditCurve(
        curve: rg.Curve,
        t: float,
        delta: rg.Vector3d,
        length: float,
        fixed_ends: bool = True,
    ) -> Optional[rg.Curve]:
        """Soft-edit a curve by moving a region around a parameter.

        Parameters
        ----------
        curve : Curve
            Input curve.
        t : float
            Curve parameter at the edit centre.
        delta : Vector3d
            Displacement vector.
        length : float
            Influence length along the curve (both sides of t).
        fixed_ends : bool
            Pin curve endpoints.

        Returns
        -------
        Curve or None
        """
        if curve is None:
            return None
        result = rg.Curve.CreateSoftEditCurve(
            curve, t, delta, length, fixed_ends,
        )
        return result if result is not None and result.IsValid else None

    # ======================================================================
    # Planar operations
    # ======================================================================

    @staticmethod
    def CreatePlanarBreps(
        curves: Sequence[rg.Curve],
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Brep]]:
        """Create planar Brep faces from closed planar curves.

        Returns
        -------
        list[Brep] or None
        """
        if curves is None or len(curves) == 0:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Brep.CreatePlanarBreps(curves, tol)
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def CapPlanarHoles(
        brep: rg.Brep,
        tolerance: float = 0.0,
    ) -> Optional[rg.Brep]:
        """Cap all planar holes in a Brep.

        Returns
        -------
        Brep or None
        """
        if brep is None:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = brep.CapPlanarHoles(tol)
        return result if result is not None and result.IsValid else None

    # ======================================================================
    # Offset operations
    # ======================================================================

    @staticmethod
    def OffsetOnSurface(
        curve: rg.Curve,
        face: rg.BrepFace,
        distance: float,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Curve]]:
        """Offset a curve lying on a surface.

        Parameters
        ----------
        curve : Curve
            Curve to offset (must lie on *face*).
        face : BrepFace
            The surface on which to offset.
        distance : float
            Offset distance.
        tolerance : float
            0 uses the document tolerance.

        Returns
        -------
        list[Curve] or None
        """
        if curve is None or face is None:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Curve.OffsetOnSurface(curve, face, distance, tol)
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def OffsetNormalToSurface(
        surface: rg.Surface,
        curves: Sequence[rg.Curve],
        height: float,
    ) -> Optional[List[rg.Curve]]:
        """Offset curves normal to a surface.

        Parameters
        ----------
        surface : Surface
            Reference surface.
        curves : sequence of Curve
            Curves on the surface.
        height : float
            Offset distance along the surface normal.

        Returns
        -------
        list[Curve] or None
        """
        if surface is None or not curves:
            return None
        result = rg.Curve.OffsetNormalToSurface(surface, list(curves), height)
        if result is None or len(result) == 0:
            return None
        return list(result)

    # ======================================================================
    # Pull / project operations
    # ======================================================================

    @staticmethod
    def PullCurve(
        surface: rg.BrepFace,
        curve: rg.Curve,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Curve]]:
        """Pull (closest-point project) a curve onto a surface.

        Returns
        -------
        list[Curve] or None
        """
        if surface is None or curve is None:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Curve.PullToBrepFace(curve, surface, tol)
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def PullPointsToMesh(
        mesh: rg.Mesh,
        points: Sequence[rg.Point3d],
    ) -> Optional[List[rg.Point3d]]:
        """Pull points to the closest location on a mesh.

        Returns
        -------
        list[Point3d] or None
        """
        if mesh is None or not points:
            return None
        result = []
        for pt in points:
            closest = mesh.ClosestPoint(pt)
            if closest != rg.Point3d.Unset:
                result.append(closest)
            else:
                result.append(pt)
        return result if result else None

    @staticmethod
    def ProjectToMesh(
        curves: Sequence[rg.Curve],
        meshes: Sequence[rg.Mesh],
        direction: rg.Vector3d,
        tolerance: float = 0.0,
    ) -> Optional[List[rg.Curve]]:
        """Project curves onto meshes along a direction.

        Returns
        -------
        list[Curve] or None
        """
        if not curves or not meshes:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        result = rg.Curve.ProjectToMesh(
            list(curves), list(meshes), direction, tol,
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    # ======================================================================
    # Mesh boolean operations
    # ======================================================================

    @staticmethod
    def MeshBooleanDifference(
        mesh_a: Sequence[rg.Mesh],
        mesh_b: Sequence[rg.Mesh],
    ) -> Optional[List[rg.Mesh]]:
        """Mesh boolean difference (A - B).

        Returns
        -------
        list[Mesh] or None
        """
        if not mesh_a or not mesh_b:
            return None
        result = rg.Mesh.CreateBooleanDifference(
            list(mesh_a), list(mesh_b),
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def MeshBooleanUnion(
        meshes: Sequence[rg.Mesh],
    ) -> Optional[List[rg.Mesh]]:
        """Mesh boolean union.

        Returns
        -------
        list[Mesh] or None
        """
        if not meshes or len(meshes) < 2:
            return None
        result = rg.Mesh.CreateBooleanUnion(list(meshes))
        if result is None or len(result) == 0:
            return None
        return list(result)

    @staticmethod
    def MeshBooleanIntersection(
        mesh_a: Sequence[rg.Mesh],
        mesh_b: Sequence[rg.Mesh],
    ) -> Optional[List[rg.Mesh]]:
        """Mesh boolean intersection.

        Returns
        -------
        list[Mesh] or None
        """
        if not mesh_a or not mesh_b:
            return None
        result = rg.Mesh.CreateBooleanIntersection(
            list(mesh_a), list(mesh_b),
        )
        if result is None or len(result) == 0:
            return None
        return list(result)

    # ======================================================================
    # Splitting / trimming
    # ======================================================================

    @staticmethod
    def SplitAtLastWallCurve(
        brep: rg.Brep,
        wall_curve: rg.Curve,
        tolerance: float = 0.0,
    ) -> Optional[Tuple[List[rg.Brep], List[rg.Brep]]]:
        """Split a Brep at a wall curve, returning inner and outer parts.

        The wall curve is projected onto the Brep surface and used as a
        splitting boundary.  The returned tuple holds (inner_breps, outer_breps)
        where *inner* is the portion on the same side as the curve normal
        direction and *outer* is the remainder.

        Parameters
        ----------
        brep : Brep
            The Brep to split.
        wall_curve : Curve
            The splitting curve (should lie on or near the Brep surface).
        tolerance : float
            0 uses the document tolerance.

        Returns
        -------
        (list[Brep], list[Brep]) or None
            (inner_parts, outer_parts), or None on failure.
        """
        if brep is None or wall_curve is None:
            return None
        tol = tolerance or Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance

        # Project the curve onto the Brep
        projected = rg.Curve.ProjectToBrep(
            wall_curve, brep, rg.Vector3d.ZAxis, tol,
        )
        if projected is None or len(projected) == 0:
            return None

        split_curve = projected[0]

        # Split the Brep
        split_results = brep.Split.Overloads[
            rg.Curve, float
        ](split_curve, tol) if hasattr(brep.Split, "Overloads") else None

        # Fallback: use Brep.Split(IEnumerable<Curve>, tolerance)
        if split_results is None or len(split_results) == 0:
            split_results = brep.Split(
                [split_curve], tol,
            )

        if split_results is None or len(split_results) == 0:
            return None

        # Classify into inner / outer based on centroid position relative
        # to the wall curve midpoint normal.
        mid_t = split_curve.Domain.Mid
        mid_pt = split_curve.PointAt(mid_t)
        tangent = split_curve.TangentAt(mid_t)
        normal = rg.Vector3d.CrossProduct(tangent, rg.Vector3d.ZAxis)
        if normal.Length < 1e-12:
            normal = rg.Vector3d.XAxis
        normal.Unitize()

        inner = []
        outer = []
        for piece in split_results:
            centroid = rg.AreaMassProperties.Compute(piece)
            if centroid is not None:
                to_centroid = centroid.Centroid - mid_pt
                if rg.Vector3d.Multiply(to_centroid, normal) >= 0:
                    inner.append(piece)
                else:
                    outer.append(piece)
            else:
                outer.append(piece)

        return (inner, outer)
