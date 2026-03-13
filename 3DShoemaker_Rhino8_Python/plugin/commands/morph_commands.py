"""
3DShoemaker Rhino 8 Plugin - Morphing / shape transformation commands.

Commands:
    Morph              - Main morph command with FFD and point-to-point morphing.
    NewMorph           - Open interactive morph form.
    NewMorphScriptable - Scriptable (non-interactive) morph.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import Rhino  # type: ignore
import Rhino.Commands  # type: ignore
import Rhino.Display  # type: ignore
import Rhino.DocObjects  # type: ignore
import Rhino.Geometry  # type: ignore
import Rhino.Geometry.Morphs  # type: ignore
import Rhino.Input  # type: ignore
import Rhino.Input.Custom  # type: ignore
import Rhino.RhinoApp  # type: ignore
import Rhino.RhinoDoc  # type: ignore
import rhinoscriptsyntax as rs  # type: ignore
import scriptcontext as sc  # type: ignore
import System  # type: ignore

import plugin as plugin_constants
from plugin.plugin_main import PodoCADPlugIn


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_plugin() -> PodoCADPlugIn:
    return PodoCADPlugIn.instance()


def _require_license() -> bool:
    plug = _get_plugin()
    if not plug.is_licensed:
        Rhino.RhinoApp.WriteLine(
            "[3DShoemaker] This command requires a valid license. "
            "Run Activate3DShoemaker first."
        )
        return False
    return True


def _pick_points(prompt: str, min_count: int = 1) -> Optional[List[Rhino.Geometry.Point3d]]:
    """Prompt the user to pick one or more points. Returns None on cancel."""
    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt(prompt)
    gp.AcceptNothing(True)

    points: List[Rhino.Geometry.Point3d] = []
    while True:
        if points:
            gp.SetCommandPrompt(f"{prompt} ({len(points)} picked, Enter to finish)")
            gp.DynamicDraw += lambda sender, e: _draw_point_markers(e, points)
        result = gp.Get()
        if result == Rhino.Input.GetResult.Point:
            points.append(gp.Point())
        elif result == Rhino.Input.GetResult.Nothing:
            break
        else:
            if len(points) < min_count:
                return None
            break
    return points if len(points) >= min_count else None


def _draw_point_markers(
    e: Rhino.Input.Custom.GetPointDrawEventArgs,
    points: List[Rhino.Geometry.Point3d],
) -> None:
    """Draw small crosses at picked points during dynamic draw."""
    for pt in points:
        e.Display.DrawPoint(pt, Rhino.Display.PointStyle.X, 5,
                            System.Drawing.Color.Red)


def _pick_objects(
    prompt: str,
    filter_type: Rhino.DocObjects.ObjectType = Rhino.DocObjects.ObjectType.AnyObject,
    allow_multiple: bool = True,
) -> Optional[List[Rhino.DocObjects.ObjRef]]:
    """Prompt the user to select one or more objects."""
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(prompt)
    go.GeometryFilter = filter_type
    if allow_multiple:
        go.GetMultiple(1, 0)
    else:
        go.Get()
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return None
    return [go.Object(i) for i in range(go.ObjectCount)]


def _pick_mesh(prompt: str) -> Optional[Rhino.DocObjects.ObjRef]:
    """Prompt the user to select a single mesh."""
    refs = _pick_objects(prompt, Rhino.DocObjects.ObjectType.Mesh, allow_multiple=False)
    return refs[0] if refs else None


def _pick_curve(prompt: str) -> Optional[Rhino.DocObjects.ObjRef]:
    """Prompt the user to select a single curve."""
    refs = _pick_objects(prompt, Rhino.DocObjects.ObjectType.Curve, allow_multiple=False)
    return refs[0] if refs else None


# ---------------------------------------------------------------------------
#  Morph
# ---------------------------------------------------------------------------

class Morph(Rhino.Commands.Command):
    """
    Main morph command providing FFD and point-to-point morphing operations.

    Supports mesh-to-mesh, point-to-point, mesh-to-point, NURBS surface
    morphing, and forefoot/rearfoot twist morphs.
    """

    _instance: Morph | None = None

    # Shared state for source/target points
    SourcePoints: List[Rhino.Geometry.Point3d] = []
    TargetPoints: List[Rhino.Geometry.Point3d] = []

    # IDs for source/target meshes and curves
    _source_mesh_id: Optional[System.Guid] = None
    _target_mesh_id: Optional[System.Guid] = None
    _source_curve_id: Optional[System.Guid] = None
    _target_curve_id: Optional[System.Guid] = None

    def __init__(self):
        super().__init__()
        Morph._instance = self

    @classmethod
    @property
    def Instance(cls) -> Morph | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "Morph"

    # ------------------------------------------------------------------
    # Point compilation
    # ------------------------------------------------------------------

    @staticmethod
    def CompilePoints(
        mesh: Rhino.Geometry.Mesh,
        sample_count: int = 0,
    ) -> List[Rhino.Geometry.Point3d]:
        """
        Extract control points from a mesh.

        If *sample_count* > 0 the mesh vertices are sub-sampled uniformly;
        otherwise every vertex is returned.
        """
        vertices = [
            Rhino.Geometry.Point3d(v.X, v.Y, v.Z)
            for v in mesh.Vertices
        ]
        if sample_count > 0 and sample_count < len(vertices):
            step = max(1, len(vertices) // sample_count)
            vertices = vertices[::step]
        return vertices

    @staticmethod
    def GetSourcesAndTargets(
        source_mesh: Rhino.Geometry.Mesh,
        target_mesh: Rhino.Geometry.Mesh,
    ) -> Tuple[List[Rhino.Geometry.Point3d], List[Rhino.Geometry.Point3d]]:
        """
        Build paired source/target point lists by closest-point mapping
        between two meshes.
        """
        sources: List[Rhino.Geometry.Point3d] = []
        targets: List[Rhino.Geometry.Point3d] = []

        for v in source_mesh.Vertices:
            src_pt = Rhino.Geometry.Point3d(v.X, v.Y, v.Z)
            closest = target_mesh.ClosestPoint(src_pt)
            if closest is not None:
                sources.append(src_pt)
                targets.append(closest)
        return sources, targets

    # ------------------------------------------------------------------
    # FFD (Free-Form Deformation)
    # ------------------------------------------------------------------

    @staticmethod
    def FFD(
        geometry: Rhino.Geometry.GeometryBase,
        source_points: List[Rhino.Geometry.Point3d],
        target_points: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ) -> Optional[Rhino.Geometry.GeometryBase]:
        """
        Apply Free-Form Deformation by displacing control lattice points.

        Uses SpaceMorph sub-class to move *source_points* to *target_points*.
        """
        if len(source_points) != len(target_points):
            Rhino.RhinoApp.WriteLine(
                "[3DShoemaker] FFD: source and target point counts must match."
            )
            return None

        if len(source_points) == 0:
            return geometry.Duplicate()

        morph = _PointToPointMorph(source_points, target_points, tolerance)
        result = geometry.Duplicate()
        if morph.Morph(result):
            return result
        return None

    @staticmethod
    def FFDMesh(
        mesh: Rhino.Geometry.Mesh,
        source_points: List[Rhino.Geometry.Point3d],
        target_points: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ) -> Optional[Rhino.Geometry.Mesh]:
        """FFD overload specifically for meshes."""
        result = Morph.FFD(mesh, source_points, target_points, tolerance)
        if isinstance(result, Rhino.Geometry.Mesh):
            return result
        return None

    @staticmethod
    def FFDBrep(
        brep: Rhino.Geometry.Brep,
        source_points: List[Rhino.Geometry.Point3d],
        target_points: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ) -> Optional[Rhino.Geometry.Brep]:
        """FFD overload specifically for breps."""
        result = Morph.FFD(brep, source_points, target_points, tolerance)
        if isinstance(result, Rhino.Geometry.Brep):
            return result
        return None

    # ------------------------------------------------------------------
    # Point-to-Point morphing
    # ------------------------------------------------------------------

    @staticmethod
    def MorphMeshP2P(
        mesh: Rhino.Geometry.Mesh,
        source_pts: List[Rhino.Geometry.Point3d],
        target_pts: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ) -> Optional[Rhino.Geometry.Mesh]:
        """Morph a mesh using explicit point-to-point correspondences."""
        if len(source_pts) != len(target_pts) or len(source_pts) == 0:
            return None

        result_mesh = mesh.Duplicate()
        vertices = result_mesh.Vertices

        for vi in range(vertices.Count):
            v = Rhino.Geometry.Point3d(vertices[vi].X, vertices[vi].Y, vertices[vi].Z)
            displacement = Rhino.Geometry.Vector3d.Zero

            total_weight = 0.0
            for si in range(len(source_pts)):
                dist = v.DistanceTo(source_pts[si])
                weight = 1.0 / (dist + tolerance) ** 2
                total_weight += weight
                delta = target_pts[si] - source_pts[si]
                displacement += delta * weight

            if total_weight > 0:
                displacement /= total_weight
                new_pt = v + displacement
                vertices.SetVertex(vi, new_pt.X, new_pt.Y, new_pt.Z)

        result_mesh.Normals.ComputeNormals()
        return result_mesh

    @staticmethod
    def MorphMeshM2P(
        mesh: Rhino.Geometry.Mesh,
        source_mesh: Rhino.Geometry.Mesh,
        target_pts: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ) -> Optional[Rhino.Geometry.Mesh]:
        """Morph mesh using source mesh vertices mapped to target points."""
        source_pts = Morph.CompilePoints(source_mesh, len(target_pts))
        n = min(len(source_pts), len(target_pts))
        return Morph.MorphMeshP2P(mesh, source_pts[:n], target_pts[:n], tolerance)

    @staticmethod
    def MorphMeshM2M(
        mesh: Rhino.Geometry.Mesh,
        source_mesh: Rhino.Geometry.Mesh,
        target_mesh: Rhino.Geometry.Mesh,
        tolerance: float = 0.1,
    ) -> Optional[Rhino.Geometry.Mesh]:
        """Morph mesh using source-mesh-to-target-mesh correspondences."""
        sources, targets = Morph.GetSourcesAndTargets(source_mesh, target_mesh)
        if not sources:
            return None
        return Morph.MorphMeshP2P(mesh, sources, targets, tolerance)

    @staticmethod
    def MorphMeshesAndPointsP2P(
        meshes: List[Rhino.Geometry.Mesh],
        extra_points: List[Rhino.Geometry.Point3d],
        source_pts: List[Rhino.Geometry.Point3d],
        target_pts: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ) -> Tuple[List[Rhino.Geometry.Mesh], List[Rhino.Geometry.Point3d]]:
        """Morph multiple meshes and loose points using P2P correspondences."""
        morphed_meshes: List[Rhino.Geometry.Mesh] = []
        for m in meshes:
            result = Morph.MorphMeshP2P(m, source_pts, target_pts, tolerance)
            morphed_meshes.append(result if result else m.Duplicate())

        morphed_points: List[Rhino.Geometry.Point3d] = []
        for pt in extra_points:
            displacement = Rhino.Geometry.Vector3d.Zero
            total_weight = 0.0
            for si in range(len(source_pts)):
                dist = pt.DistanceTo(source_pts[si])
                weight = 1.0 / (dist + tolerance) ** 2
                total_weight += weight
                delta = target_pts[si] - source_pts[si]
                displacement += delta * weight
            if total_weight > 0:
                displacement /= total_weight
            morphed_points.append(pt + displacement)
        return morphed_meshes, morphed_points

    @staticmethod
    def MorphMeshesAndPointsM2M(
        meshes: List[Rhino.Geometry.Mesh],
        extra_points: List[Rhino.Geometry.Point3d],
        source_mesh: Rhino.Geometry.Mesh,
        target_mesh: Rhino.Geometry.Mesh,
        tolerance: float = 0.1,
    ) -> Tuple[List[Rhino.Geometry.Mesh], List[Rhino.Geometry.Point3d]]:
        """Morph multiple meshes and loose points using M2M correspondences."""
        sources, targets = Morph.GetSourcesAndTargets(source_mesh, target_mesh)
        if not sources:
            return [m.Duplicate() for m in meshes], list(extra_points)
        return Morph.MorphMeshesAndPointsP2P(
            meshes, extra_points, sources, targets, tolerance
        )

    @staticmethod
    def MorphMeshesAndPointsAndNodesP2P(
        meshes: List[Rhino.Geometry.Mesh],
        extra_points: List[Rhino.Geometry.Point3d],
        node_points: List[Rhino.Geometry.Point3d],
        source_pts: List[Rhino.Geometry.Point3d],
        target_pts: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ) -> Tuple[
        List[Rhino.Geometry.Mesh],
        List[Rhino.Geometry.Point3d],
        List[Rhino.Geometry.Point3d],
    ]:
        """Morph meshes, extra points, and node points using P2P."""
        morphed_meshes, morphed_points = Morph.MorphMeshesAndPointsP2P(
            meshes, extra_points, source_pts, target_pts, tolerance
        )
        _, morphed_nodes = Morph.MorphMeshesAndPointsP2P(
            [], node_points, source_pts, target_pts, tolerance
        )
        return morphed_meshes, morphed_points, morphed_nodes

    @staticmethod
    def MorphMeshesAndPointsAndNodesM2M(
        meshes: List[Rhino.Geometry.Mesh],
        extra_points: List[Rhino.Geometry.Point3d],
        node_points: List[Rhino.Geometry.Point3d],
        source_mesh: Rhino.Geometry.Mesh,
        target_mesh: Rhino.Geometry.Mesh,
        tolerance: float = 0.1,
    ) -> Tuple[
        List[Rhino.Geometry.Mesh],
        List[Rhino.Geometry.Point3d],
        List[Rhino.Geometry.Point3d],
    ]:
        """Morph meshes, extra points, and node points using M2M."""
        sources, targets = Morph.GetSourcesAndTargets(source_mesh, target_mesh)
        if not sources:
            return (
                [m.Duplicate() for m in meshes],
                list(extra_points),
                list(node_points),
            )
        return Morph.MorphMeshesAndPointsAndNodesP2P(
            meshes, extra_points, node_points, sources, targets, tolerance
        )

    @staticmethod
    def MorphNurbsSurfacesAndPointsP2P(
        surfaces: List[Rhino.Geometry.NurbsSurface],
        extra_points: List[Rhino.Geometry.Point3d],
        source_pts: List[Rhino.Geometry.Point3d],
        target_pts: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ) -> Tuple[List[Rhino.Geometry.NurbsSurface], List[Rhino.Geometry.Point3d]]:
        """Morph NURBS surfaces and points using P2P correspondences."""
        morph = _PointToPointMorph(source_pts, target_pts, tolerance)

        morphed_surfaces: List[Rhino.Geometry.NurbsSurface] = []
        for srf in surfaces:
            dup = srf.Duplicate()
            if morph.Morph(dup):
                morphed_surfaces.append(dup)
            else:
                morphed_surfaces.append(srf.Duplicate())

        morphed_points: List[Rhino.Geometry.Point3d] = []
        for pt in extra_points:
            morphed_points.append(morph.MorphPoint(pt))

        return morphed_surfaces, morphed_points

    # ------------------------------------------------------------------
    # Twist morphs
    # ------------------------------------------------------------------

    @staticmethod
    def ForeFootTwistMorph(
        geometry: Rhino.Geometry.GeometryBase,
        axis_origin: Rhino.Geometry.Point3d,
        axis_direction: Rhino.Geometry.Vector3d,
        angle_radians: float,
        start_distance: float = 0.0,
        end_distance: float = 100.0,
    ) -> Optional[Rhino.Geometry.GeometryBase]:
        """
        Apply a twist deformation to the forefoot region using TwistSpaceMorph.

        The twist is applied around *axis_direction* at *axis_origin*,
        ramping from zero twist at *start_distance* to full *angle_radians*
        at *end_distance*.
        """
        axis_line = Rhino.Geometry.Line(
            axis_origin,
            axis_origin + axis_direction * end_distance,
        )
        twist = Rhino.Geometry.Morphs.TwistSpaceMorph()
        twist.TwistAxis = axis_line
        twist.TwistAngleRadians = angle_radians

        result = geometry.Duplicate()
        if twist.Morph(result):
            return result
        return None

    @staticmethod
    def RearFootTwistMorph(
        geometry: Rhino.Geometry.GeometryBase,
        axis_origin: Rhino.Geometry.Point3d,
        axis_direction: Rhino.Geometry.Vector3d,
        angle_radians: float,
        start_distance: float = 0.0,
        end_distance: float = 100.0,
    ) -> Optional[Rhino.Geometry.GeometryBase]:
        """
        Apply a twist deformation to the rearfoot region using TwistSpaceMorph.

        Identical mechanism to ForeFootTwistMorph but intended for the
        heel-to-midfoot section with a negative Y direction.
        """
        axis_line = Rhino.Geometry.Line(
            axis_origin,
            axis_origin - axis_direction * end_distance,
        )
        twist = Rhino.Geometry.Morphs.TwistSpaceMorph()
        twist.TwistAxis = axis_line
        twist.TwistAngleRadians = angle_radians

        result = geometry.Duplicate()
        if twist.Morph(result):
            return result
        return None

    # ------------------------------------------------------------------
    # RunCommand
    # ------------------------------------------------------------------

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("[3DShoemaker] Morph Command")

        # Present morph operation options
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Morph operation")
        gs.AcceptNothing(False)

        opt_ffd = gs.AddOption("FFD")
        opt_p2p = gs.AddOption("PointToPoint")
        opt_m2m = gs.AddOption("MeshToMesh")
        opt_m2p = gs.AddOption("MeshToPoint")
        opt_twist_fore = gs.AddOption("ForeFootTwist")
        opt_twist_rear = gs.AddOption("RearFootTwist")
        opt_nurbs = gs.AddOption("NurbsSurface")

        result = gs.Get()
        if result != Rhino.Input.GetResult.Option:
            return Rhino.Commands.Result.Cancel

        option_idx = gs.OptionIndex()

        tol = doc.ModelAbsoluteTolerance

        # -- FFD -----------------------------------------------------------
        if option_idx == opt_ffd:
            return self._run_ffd(doc, tol)

        # -- Point-to-Point -----------------------------------------------
        if option_idx == opt_p2p:
            return self._run_p2p(doc, tol)

        # -- Mesh-to-Mesh -------------------------------------------------
        if option_idx == opt_m2m:
            return self._run_m2m(doc, tol)

        # -- Mesh-to-Point ------------------------------------------------
        if option_idx == opt_m2p:
            return self._run_m2p(doc, tol)

        # -- ForeFootTwist ------------------------------------------------
        if option_idx == opt_twist_fore:
            return self._run_twist(doc, forefoot=True)

        # -- RearFootTwist ------------------------------------------------
        if option_idx == opt_twist_rear:
            return self._run_twist(doc, forefoot=False)

        # -- NurbsSurface -------------------------------------------------
        if option_idx == opt_nurbs:
            return self._run_nurbs_p2p(doc, tol)

        return Rhino.Commands.Result.Nothing

    # ------------------------------------------------------------------
    # Sub-operations
    # ------------------------------------------------------------------

    def _run_ffd(self, doc, tol) -> Rhino.Commands.Result:
        """FFD morph: pick object, pick source points, pick target points."""
        obj_refs = _pick_objects("Select object(s) to deform")
        if not obj_refs:
            return Rhino.Commands.Result.Cancel

        Rhino.RhinoApp.WriteLine("Pick source control points:")
        source = _pick_points("Source points", 1)
        if not source:
            return Rhino.Commands.Result.Cancel

        Rhino.RhinoApp.WriteLine(f"Pick {len(source)} target control points:")
        target = _pick_points("Target points", len(source))
        if not target or len(target) != len(source):
            Rhino.RhinoApp.WriteLine("[3DShoemaker] Source/target point count mismatch.")
            return Rhino.Commands.Result.Failure

        Morph.SourcePoints = source
        Morph.TargetPoints = target

        for ref in obj_refs:
            geom = ref.Geometry()
            if geom is None:
                continue
            morphed = self.FFD(geom, source, target, tol)
            if morphed is not None:
                doc.Objects.Replace(ref.ObjectId, morphed)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("[3DShoemaker] FFD morph applied.")
        return Rhino.Commands.Result.Success

    def _run_p2p(self, doc, tol) -> Rhino.Commands.Result:
        """Point-to-point morph on meshes."""
        mesh_ref = _pick_mesh("Select mesh to morph")
        if not mesh_ref:
            return Rhino.Commands.Result.Cancel
        mesh = mesh_ref.Mesh()
        if mesh is None:
            return Rhino.Commands.Result.Failure

        source = _pick_points("Source points", 1)
        if not source:
            return Rhino.Commands.Result.Cancel

        target = _pick_points(f"Target points ({len(source)} needed)", len(source))
        if not target or len(target) != len(source):
            return Rhino.Commands.Result.Failure

        Morph.SourcePoints = source
        Morph.TargetPoints = target

        morphed = self.MorphMeshP2P(mesh, source, target, tol)
        if morphed is not None:
            doc.Objects.Replace(mesh_ref.ObjectId, morphed)
            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("[3DShoemaker] P2P morph applied.")
            return Rhino.Commands.Result.Success

        return Rhino.Commands.Result.Failure

    def _run_m2m(self, doc, tol) -> Rhino.Commands.Result:
        """Mesh-to-mesh morph."""
        mesh_ref = _pick_mesh("Select mesh to morph")
        if not mesh_ref:
            return Rhino.Commands.Result.Cancel
        mesh = mesh_ref.Mesh()

        src_ref = _pick_mesh("Select SOURCE reference mesh")
        if not src_ref:
            return Rhino.Commands.Result.Cancel
        src_mesh = src_ref.Mesh()

        tgt_ref = _pick_mesh("Select TARGET reference mesh")
        if not tgt_ref:
            return Rhino.Commands.Result.Cancel
        tgt_mesh = tgt_ref.Mesh()

        Morph._source_mesh_id = src_ref.ObjectId
        Morph._target_mesh_id = tgt_ref.ObjectId

        morphed = self.MorphMeshM2M(mesh, src_mesh, tgt_mesh, tol)
        if morphed is not None:
            doc.Objects.Replace(mesh_ref.ObjectId, morphed)
            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("[3DShoemaker] M2M morph applied.")
            return Rhino.Commands.Result.Success

        return Rhino.Commands.Result.Failure

    def _run_m2p(self, doc, tol) -> Rhino.Commands.Result:
        """Mesh-to-point morph."""
        mesh_ref = _pick_mesh("Select mesh to morph")
        if not mesh_ref:
            return Rhino.Commands.Result.Cancel
        mesh = mesh_ref.Mesh()

        src_ref = _pick_mesh("Select SOURCE reference mesh")
        if not src_ref:
            return Rhino.Commands.Result.Cancel
        src_mesh = src_ref.Mesh()

        Morph._source_mesh_id = src_ref.ObjectId

        target = _pick_points("Target points", 1)
        if not target:
            return Rhino.Commands.Result.Cancel

        Morph.TargetPoints = target

        morphed = self.MorphMeshM2P(mesh, src_mesh, target, tol)
        if morphed is not None:
            doc.Objects.Replace(mesh_ref.ObjectId, morphed)
            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("[3DShoemaker] M2P morph applied.")
            return Rhino.Commands.Result.Success

        return Rhino.Commands.Result.Failure

    def _run_twist(self, doc, forefoot: bool) -> Rhino.Commands.Result:
        """Twist morph (forefoot or rearfoot)."""
        obj_refs = _pick_objects("Select object(s) to twist")
        if not obj_refs:
            return Rhino.Commands.Result.Cancel

        # Get twist axis origin
        gp = Rhino.Input.Custom.GetPoint()
        gp.SetCommandPrompt("Twist axis origin")
        if gp.Get() != Rhino.Input.GetResult.Point:
            return Rhino.Commands.Result.Cancel
        axis_origin = gp.Point()

        # Get twist angle
        gn = Rhino.Input.Custom.GetNumber()
        gn.SetCommandPrompt("Twist angle (degrees)")
        gn.SetDefaultNumber(5.0)
        if gn.Get() != Rhino.Input.GetResult.Number:
            return Rhino.Commands.Result.Cancel
        angle_deg = gn.Number()
        angle_rad = math.radians(angle_deg)

        # Get distance range
        gn2 = Rhino.Input.Custom.GetNumber()
        gn2.SetCommandPrompt("Twist end distance (mm)")
        gn2.SetDefaultNumber(100.0)
        if gn2.Get() != Rhino.Input.GetResult.Number:
            return Rhino.Commands.Result.Cancel
        end_dist = gn2.Number()

        axis_dir = Rhino.Geometry.Vector3d.YAxis  # along foot length
        morph_fn = self.ForeFootTwistMorph if forefoot else self.RearFootTwistMorph

        for ref in obj_refs:
            geom = ref.Geometry()
            if geom is None:
                continue
            morphed = morph_fn(geom, axis_origin, axis_dir, angle_rad, 0.0, end_dist)
            if morphed is not None:
                doc.Objects.Replace(ref.ObjectId, morphed)

        doc.Views.Redraw()
        label = "ForeFootTwist" if forefoot else "RearFootTwist"
        Rhino.RhinoApp.WriteLine(f"[3DShoemaker] {label} morph applied ({angle_deg} deg).")
        return Rhino.Commands.Result.Success

    def _run_nurbs_p2p(self, doc, tol) -> Rhino.Commands.Result:
        """NURBS surface point-to-point morph."""
        obj_refs = _pick_objects(
            "Select NURBS surface(s) to morph",
            Rhino.DocObjects.ObjectType.Surface,
        )
        if not obj_refs:
            return Rhino.Commands.Result.Cancel

        source = _pick_points("Source points", 1)
        if not source:
            return Rhino.Commands.Result.Cancel
        target = _pick_points(f"Target points ({len(source)} needed)", len(source))
        if not target or len(target) != len(source):
            return Rhino.Commands.Result.Failure

        Morph.SourcePoints = source
        Morph.TargetPoints = target

        surfaces: List[Rhino.Geometry.NurbsSurface] = []
        obj_ids: List[System.Guid] = []
        for ref in obj_refs:
            srf = ref.Surface()
            if srf is not None:
                nurbs = srf.ToNurbsSurface()
                if nurbs is not None:
                    surfaces.append(nurbs)
                    obj_ids.append(ref.ObjectId)

        morphed_surfaces, _ = self.MorphNurbsSurfacesAndPointsP2P(
            surfaces, [], source, target, tol
        )

        for oid, morphed_srf in zip(obj_ids, morphed_surfaces):
            brep = morphed_srf.ToBrep()
            if brep is not None:
                doc.Objects.Replace(oid, brep)

        doc.Views.Redraw()
        Rhino.RhinoApp.WriteLine("[3DShoemaker] NURBS P2P morph applied.")
        return Rhino.Commands.Result.Success


# ---------------------------------------------------------------------------
#  Internal SpaceMorph implementation
# ---------------------------------------------------------------------------

class _PointToPointMorph(Rhino.Geometry.SpaceMorph):
    """
    SpaceMorph that displaces points based on weighted inverse-distance
    interpolation from source to target control points.
    """

    def __init__(
        self,
        source_pts: List[Rhino.Geometry.Point3d],
        target_pts: List[Rhino.Geometry.Point3d],
        tolerance: float = 0.1,
    ):
        super().__init__()
        self._sources = list(source_pts)
        self._targets = list(target_pts)
        self._tol = tolerance
        self.Tolerance = tolerance

    def MorphPoint(self, point: Rhino.Geometry.Point3d) -> Rhino.Geometry.Point3d:
        """Compute the morphed location of *point*."""
        displacement = Rhino.Geometry.Vector3d.Zero
        total_weight = 0.0

        for i in range(len(self._sources)):
            dist = point.DistanceTo(self._sources[i])
            weight = 1.0 / (dist + self._tol) ** 2
            total_weight += weight
            delta = self._targets[i] - self._sources[i]
            displacement += delta * weight

        if total_weight > 0:
            displacement /= total_weight

        return point + displacement


# ---------------------------------------------------------------------------
#  NewMorph
# ---------------------------------------------------------------------------

class NewMorph(Rhino.Commands.Command):
    """
    Open interactive morph form for visual morphing.

    Presents an Eto dialog where the user can pick source/target
    references and adjust morph parameters before applying.
    """

    _instance: NewMorph | None = None

    def __init__(self):
        super().__init__()
        NewMorph._instance = self

    @classmethod
    @property
    def Instance(cls) -> NewMorph | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "NewMorph"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        Rhino.RhinoApp.WriteLine("[3DShoemaker] Interactive Morph")

        # Try to show Eto-based morph form
        try:
            import Eto.Forms as ef
            import Eto.Drawing as ed

            dlg = ef.Dialog()
            dlg.Title = "3DShoemaker - Morph"
            dlg.ClientSize = ed.Size(450, 380)
            dlg.Padding = ef.Padding(10)

            layout = ef.DynamicLayout()
            layout.DefaultSpacing = ed.Size(5, 5)

            layout.AddRow(ef.Label(Text="Morph Operation:"))

            op_dropdown = ef.DropDown()
            op_dropdown.Items.Add(ef.ListItem(Text="Point-to-Point", Key="P2P"))
            op_dropdown.Items.Add(ef.ListItem(Text="Mesh-to-Mesh", Key="M2M"))
            op_dropdown.Items.Add(ef.ListItem(Text="Free-Form Deformation", Key="FFD"))
            op_dropdown.Items.Add(ef.ListItem(Text="ForeFootTwist", Key="FT"))
            op_dropdown.Items.Add(ef.ListItem(Text="RearFootTwist", Key="RT"))
            op_dropdown.SelectedIndex = 0
            layout.AddRow(op_dropdown)

            layout.AddRow(ef.Label(Text="Tolerance:"))
            tol_input = ef.NumericStepper()
            tol_input.Value = doc.ModelAbsoluteTolerance
            tol_input.MinValue = 0.001
            tol_input.MaxValue = 10.0
            tol_input.DecimalPlaces = 4
            tol_input.Increment = 0.01
            layout.AddRow(tol_input)

            layout.AddRow(ef.Label(Text="Twist Angle (degrees, for twist ops):"))
            angle_input = ef.NumericStepper()
            angle_input.Value = 5.0
            angle_input.MinValue = -90.0
            angle_input.MaxValue = 90.0
            angle_input.DecimalPlaces = 1
            angle_input.Increment = 1.0
            layout.AddRow(angle_input)

            layout.AddSpace()

            morph_result = [Rhino.Commands.Result.Cancel]
            selected_op = ["P2P"]

            def on_apply(sender, e):
                idx = op_dropdown.SelectedIndex
                if idx >= 0:
                    selected_op[0] = op_dropdown.Items[idx].Key
                morph_result[0] = Rhino.Commands.Result.Success
                dlg.Close()

            def on_cancel(sender, e):
                dlg.Close()

            btn_apply = ef.Button(Text="Apply Morph")
            btn_cancel = ef.Button(Text="Cancel")
            btn_apply.Click += on_apply
            btn_cancel.Click += on_cancel

            btn_row = ef.DynamicLayout()
            btn_row.AddRow(None, btn_cancel, btn_apply)
            layout.AddRow(btn_row)

            dlg.Content = layout
            dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

            if morph_result[0] != Rhino.Commands.Result.Success:
                return Rhino.Commands.Result.Cancel

            # Delegate to the Morph command based on selection
            morph_cmd = Morph.Instance
            if morph_cmd is None:
                morph_cmd = Morph()

            op = selected_op[0]
            tol = tol_input.Value

            if op == "P2P":
                return morph_cmd._run_p2p(doc, tol)
            elif op == "M2M":
                return morph_cmd._run_m2m(doc, tol)
            elif op == "FFD":
                return morph_cmd._run_ffd(doc, tol)
            elif op == "FT":
                return morph_cmd._run_twist(doc, forefoot=True)
            elif op == "RT":
                return morph_cmd._run_twist(doc, forefoot=False)

            return Rhino.Commands.Result.Nothing

        except Exception as ex:
            Rhino.RhinoApp.WriteLine(
                f"[3DShoemaker] Morph form error: {ex}. "
                "Falling back to command-line interface."
            )
            # Fall back to the main Morph command
            morph_cmd = Morph.Instance
            if morph_cmd is None:
                morph_cmd = Morph()
            return morph_cmd.RunCommand(doc, mode)


# ---------------------------------------------------------------------------
#  NewMorphScriptable
# ---------------------------------------------------------------------------

class NewMorphScriptable(Rhino.Commands.Command):
    """
    Scriptable (non-interactive) morph command.

    Accepts morph type, source/target object IDs or point arrays via
    command-line options.
    """

    _instance: NewMorphScriptable | None = None

    def __init__(self):
        super().__init__()
        NewMorphScriptable._instance = self

    @classmethod
    @property
    def Instance(cls) -> NewMorphScriptable | None:
        return cls._instance

    @property
    def EnglishName(self) -> str:
        return "NewMorphScriptable"

    def RunCommand(self, doc, mode) -> Rhino.Commands.Result:
        if not _require_license():
            return Rhino.Commands.Result.Failure

        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Morph type (P2P/M2M/FFD/ForeFootTwist/RearFootTwist)")
        gs.SetDefaultString("P2P")
        gs.AcceptNothing(True)

        opt_tol = Rhino.Input.Custom.OptionDouble(doc.ModelAbsoluteTolerance)
        gs.AddOptionDouble("Tolerance", opt_tol)

        while True:
            result = gs.Get()
            if result == Rhino.Input.GetResult.Option:
                continue
            break

        if gs.CommandResult() != Rhino.Commands.Result.Success:
            return gs.CommandResult()

        morph_type = (gs.StringResult() or "P2P").strip().upper()
        tol = opt_tol.CurrentValue

        morph_cmd = Morph.Instance
        if morph_cmd is None:
            morph_cmd = Morph()

        if morph_type == "P2P":
            return morph_cmd._run_p2p(doc, tol)
        elif morph_type == "M2M":
            return morph_cmd._run_m2m(doc, tol)
        elif morph_type == "M2P":
            return morph_cmd._run_m2p(doc, tol)
        elif morph_type == "FFD":
            return morph_cmd._run_ffd(doc, tol)
        elif morph_type in ("FOREFOOTTWIST", "FT"):
            return morph_cmd._run_twist(doc, forefoot=True)
        elif morph_type in ("REARFOOTTWIST", "RT"):
            return morph_cmd._run_twist(doc, forefoot=False)
        elif morph_type == "NURBS":
            return morph_cmd._run_nurbs_p2p(doc, tol)
        else:
            Rhino.RhinoApp.WriteLine(
                f"[3DShoemaker] Unknown morph type: {morph_type}"
            )
            return Rhino.Commands.Result.Failure
