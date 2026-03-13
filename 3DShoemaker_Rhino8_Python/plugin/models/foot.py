"""
Foot data model for 3DShoemaker Rhino 8 Python plugin.

The Foot class represents a human foot with measurement data, landmark points,
2D and 3D scan geometry, and methods for importing, positioning, measuring,
and adjusting foot scans for shoe last design.

Port of PodoCAD .NET Foot class to Python 3.
"""

import json
import copy
import math
import System
from System import Guid
import Rhino
from Rhino.Geometry import (
    Point3d, Vector3d, Plane, Curve, NurbsCurve, Brep, Mesh, SubD, Surface,
    BoundingBox, Transform, Line, Arc, Circle, Interval
)


class Foot:
    """Represents a human foot with measurements, landmarks, curves, and meshes."""

    # -------------------------------------------------------------------------
    # Foot type enumerations
    # -------------------------------------------------------------------------
    FOOT_SIDE_RIGHT = "Right"
    FOOT_SIDE_LEFT = "Left"

    FOOT_TYPE_2D = "2D"
    FOOT_TYPE_3D = "3D"
    FOOT_TYPE_GENERIC = "Generic"

    POSTURE_NEUTRAL = "Neutral"
    POSTURE_PRONATED = "Pronated"
    POSTURE_SUPINATED = "Supinated"
    POSTURE_CUSTOM = "Custom"

    # Landmark names (anatomical reference points)
    LANDMARK_HEEL_CENTER = "HeelCenter"
    LANDMARK_HEEL_LATERAL = "HeelLateral"
    LANDMARK_HEEL_MEDIAL = "HeelMedial"
    LANDMARK_BALL_LATERAL = "BallLateral"
    LANDMARK_BALL_MEDIAL = "BallMedial"
    LANDMARK_TOE_TIP = "ToeTip"
    LANDMARK_TOE_1 = "Toe1"
    LANDMARK_TOE_2 = "Toe2"
    LANDMARK_TOE_3 = "Toe3"
    LANDMARK_TOE_4 = "Toe4"
    LANDMARK_TOE_5 = "Toe5"
    LANDMARK_ARCH_HIGHEST = "ArchHighest"
    LANDMARK_NAVICULAR = "Navicular"
    LANDMARK_LATERAL_MALLEOLUS = "LateralMalleolus"
    LANDMARK_MEDIAL_MALLEOLUS = "MedialMalleolus"
    LANDMARK_INSTEP = "Instep"
    LANDMARK_ACHILLES = "Achilles"
    LANDMARK_METATARSAL_1 = "Metatarsal1"
    LANDMARK_METATARSAL_5 = "Metatarsal5"
    LANDMARK_STYLOID = "Styloid"
    LANDMARK_SUSTENTACULUM = "Sustentaculum"
    LANDMARK_CUBOID = "Cuboid"
    LANDMARK_CUNEIFORMS = "Cuneiforms"

    # Generic foot landmark list (standard set)
    GENERIC_FOOT_LANDMARKS = [
        LANDMARK_HEEL_CENTER, LANDMARK_HEEL_LATERAL, LANDMARK_HEEL_MEDIAL,
        LANDMARK_BALL_LATERAL, LANDMARK_BALL_MEDIAL,
        LANDMARK_TOE_TIP, LANDMARK_TOE_1, LANDMARK_TOE_2,
        LANDMARK_TOE_3, LANDMARK_TOE_4, LANDMARK_TOE_5,
        LANDMARK_ARCH_HIGHEST, LANDMARK_NAVICULAR,
        LANDMARK_LATERAL_MALLEOLUS, LANDMARK_MEDIAL_MALLEOLUS,
        LANDMARK_INSTEP, LANDMARK_ACHILLES,
        LANDMARK_METATARSAL_1, LANDMARK_METATARSAL_5,
        LANDMARK_STYLOID, LANDMARK_SUSTENTACULUM,
        LANDMARK_CUBOID, LANDMARK_CUNEIFORMS,
    ]

    def __init__(self):
        """Initialize a Foot with default parameter values."""
        # --- Identification ---
        self._name = ""
        self._side = Foot.FOOT_SIDE_RIGHT
        self._foot_type = Foot.FOOT_TYPE_GENERIC
        self._posture = Foot.POSTURE_NEUTRAL
        self._notes = ""

        # --- Patient Info ---
        self._patient_id = ""
        self._patient_name = ""
        self._date_scanned = ""

        # --- Length Measurements ---
        self._foot_length = 260.0
        self._ball_line_length = 182.0
        self._arch_length = 143.0
        self._heel_to_toe1_length = 255.0
        self._heel_to_toe2_length = 260.0
        self._heel_to_toe3_length = 252.0
        self._heel_to_toe4_length = 240.0
        self._heel_to_toe5_length = 225.0
        self._heel_to_ball_lateral_length = 175.0
        self._heel_to_ball_medial_length = 185.0
        self._heel_to_navicular_length = 155.0
        self._heel_to_instep_length = 100.0
        self._forefoot_length = 0.0
        self._midfoot_length = 0.0
        self._rearfoot_length = 0.0

        # --- Width Measurements ---
        self._ball_width = 92.0
        self._ball_width_lateral = 44.0
        self._ball_width_medial = 48.0
        self._heel_width = 60.0
        self._heel_width_lateral = 30.0
        self._heel_width_medial = 30.0
        self._midfoot_width = 70.0
        self._forefoot_width = 85.0
        self._toe_width = 60.0

        # --- Girth Measurements ---
        self._ball_girth = 232.0
        self._instep_girth = 225.0
        self._waist_girth = 215.0
        self._heel_girth = 300.0
        self._ankle_girth = 235.0
        self._short_heel_girth = 280.0
        self._long_heel_girth = 320.0

        # --- Height Measurements ---
        self._ball_height_lateral = 18.0
        self._ball_height_medial = 22.0
        self._instep_height = 55.0
        self._navicular_height = 35.0
        self._arch_height = 20.0
        self._average_malleolus_height = 70.0
        self._lateral_malleolus_height = 65.0
        self._medial_malleolus_height = 75.0
        self._ankle_height = 80.0
        self._dorsum_height = 50.0
        self._heel_height = 0.0
        self._toe1_height = 0.0
        self._toe5_height = 0.0

        # --- Angle Measurements ---
        self._ball_line_angle = 7.0
        self._hallux_valgus_angle = 0.0
        self._rearfoot_angle = 0.0
        self._forefoot_angle = 0.0
        self._tibial_torsion_angle = 0.0
        self._arch_angle = 0.0
        self._toe_out_angle = 0.0

        # --- Posture Adjustments ---
        self._pronation_angle = 0.0
        self._supination_angle = 0.0
        self._forefoot_varus = 0.0
        self._forefoot_valgus = 0.0
        self._rearfoot_varus = 0.0
        self._rearfoot_valgus = 0.0
        self._plantarflexion_1st_ray = 0.0
        self._dorsiflexion_1st_ray = 0.0
        self._ankle_dorsiflexion = 0.0
        self._ankle_plantarflexion = 0.0

        # --- Landmark Points (dictionary: name -> Point3d) ---
        self._landmarks = {}
        for name in Foot.GENERIC_FOOT_LANDMARKS:
            self._landmarks[name] = Point3d.Origin

        # --- 2D Foot Geometry IDs ---
        self._outline_2d = Guid.Empty
        self._outline_2d_lateral = Guid.Empty
        self._outline_2d_medial = Guid.Empty
        self._center_line_2d = Guid.Empty
        self._ball_line_2d = Guid.Empty
        self._heel_line_2d = Guid.Empty
        self._arch_line_2d = Guid.Empty
        self._toe_lines_2d = []  # List of GUIDs for individual toe lines
        self._landmark_points_2d = Guid.Empty  # Point cloud or group

        # --- 3D Foot Geometry IDs ---
        self._mesh_3d = Guid.Empty
        self._mesh_3d_top = Guid.Empty
        self._mesh_3d_bottom = Guid.Empty
        self._mesh_3d_lateral = Guid.Empty
        self._mesh_3d_medial = Guid.Empty
        self._scan_mesh_original = Guid.Empty
        self._scan_mesh_oriented = Guid.Empty
        self._scan_mesh_positioned = Guid.Empty
        self._outline_3d = Guid.Empty
        self._center_line_3d = Guid.Empty
        self._ball_line_3d = Guid.Empty
        self._cross_sections_3d = []  # List of GUIDs for cross section curves
        self._landmark_points_3d = Guid.Empty

        # --- Measurement Curves ---
        self._ball_girth_curve = Guid.Empty
        self._instep_girth_curve = Guid.Empty
        self._waist_girth_curve = Guid.Empty
        self._heel_girth_curve = Guid.Empty
        self._ankle_girth_curve = Guid.Empty
        self._short_heel_girth_curve = Guid.Empty
        self._long_heel_girth_curve = Guid.Empty

        # --- Import/Export ---
        self._source_file_path = ""
        self._source_file_format = ""  # STL, OBJ, PLY, 3DS, etc.
        self._scan_resolution = 0.0  # mm per vertex approximately

    # =========================================================================
    # Factory / Lifecycle Methods
    # =========================================================================

    @staticmethod
    def Create():
        """Create a new Foot with default parameters."""
        foot = Foot()
        return foot

    # =========================================================================
    # Parameter Collection Methods
    # =========================================================================

    def CollectFootParameters(self):
        """Collect all foot parameters into a dictionary for serialization.

        Returns:
            Dictionary with all foot parameter key-value pairs.
        """
        params = {}
        params["Name"] = self._name
        params["Side"] = self._side
        params["FootType"] = self._foot_type
        params["Posture"] = self._posture
        params["Notes"] = self._notes
        params["PatientId"] = self._patient_id
        params["PatientName"] = self._patient_name
        params["DateScanned"] = self._date_scanned

        # Lengths
        params["FootLength"] = self._foot_length
        params["BallLineLength"] = self._ball_line_length
        params["ArchLength"] = self._arch_length
        params["HeelToToe1Length"] = self._heel_to_toe1_length
        params["HeelToToe2Length"] = self._heel_to_toe2_length
        params["HeelToToe3Length"] = self._heel_to_toe3_length
        params["HeelToToe4Length"] = self._heel_to_toe4_length
        params["HeelToToe5Length"] = self._heel_to_toe5_length
        params["HeelToBallLateralLength"] = self._heel_to_ball_lateral_length
        params["HeelToBallMedialLength"] = self._heel_to_ball_medial_length
        params["HeelToNavicularLength"] = self._heel_to_navicular_length
        params["HeelToInstepLength"] = self._heel_to_instep_length

        # Widths
        params["BallWidth"] = self._ball_width
        params["BallWidthLateral"] = self._ball_width_lateral
        params["BallWidthMedial"] = self._ball_width_medial
        params["HeelWidth"] = self._heel_width
        params["MidfootWidth"] = self._midfoot_width
        params["ForefootWidth"] = self._forefoot_width
        params["ToeWidth"] = self._toe_width

        # Girths
        params["BallGirth"] = self._ball_girth
        params["InstepGirth"] = self._instep_girth
        params["WaistGirth"] = self._waist_girth
        params["HeelGirth"] = self._heel_girth
        params["AnkleGirth"] = self._ankle_girth
        params["ShortHeelGirth"] = self._short_heel_girth
        params["LongHeelGirth"] = self._long_heel_girth

        # Heights
        params["BallHeightLateral"] = self._ball_height_lateral
        params["BallHeightMedial"] = self._ball_height_medial
        params["InstepHeight"] = self._instep_height
        params["NavicularHeight"] = self._navicular_height
        params["ArchHeight"] = self._arch_height
        params["AverageMalleolusHeight"] = self._average_malleolus_height
        params["LateralMalleolusHeight"] = self._lateral_malleolus_height
        params["MedialMalleolusHeight"] = self._medial_malleolus_height
        params["AnkleHeight"] = self._ankle_height
        params["DorsumHeight"] = self._dorsum_height

        # Angles
        params["BallLineAngle"] = self._ball_line_angle
        params["HalluxValgusAngle"] = self._hallux_valgus_angle
        params["RearfootAngle"] = self._rearfoot_angle
        params["ForefootAngle"] = self._forefoot_angle
        params["ArchAngle"] = self._arch_angle

        # Posture
        params["PronationAngle"] = self._pronation_angle
        params["SupinationAngle"] = self._supination_angle
        params["ForefootVarus"] = self._forefoot_varus
        params["ForefootValgus"] = self._forefoot_valgus
        params["RearfootVarus"] = self._rearfoot_varus
        params["RearfootValgus"] = self._rearfoot_valgus

        # Landmarks as serializable dict
        landmark_data = {}
        for name, pt in self._landmarks.items():
            landmark_data[name] = {"X": pt.X, "Y": pt.Y, "Z": pt.Z}
        params["Landmarks"] = landmark_data

        # Source info
        params["SourceFilePath"] = self._source_file_path
        params["SourceFileFormat"] = self._source_file_format

        return params

    # =========================================================================
    # Curve Management
    # =========================================================================

    def DeleteCurves(self, doc):
        """Delete all foot curves and geometry from the Rhino document.

        Args:
            doc: The Rhino document.
        """
        ids_to_delete = [
            self._outline_2d, self._outline_2d_lateral, self._outline_2d_medial,
            self._center_line_2d, self._ball_line_2d, self._heel_line_2d,
            self._arch_line_2d, self._landmark_points_2d,
            self._outline_3d, self._center_line_3d, self._ball_line_3d,
            self._landmark_points_3d,
            self._ball_girth_curve, self._instep_girth_curve,
            self._waist_girth_curve, self._heel_girth_curve,
            self._ankle_girth_curve, self._short_heel_girth_curve,
            self._long_heel_girth_curve,
        ]

        # Add toe lines
        ids_to_delete.extend(self._toe_lines_2d)
        # Add cross sections
        ids_to_delete.extend(self._cross_sections_3d)

        for guid in ids_to_delete:
            if guid != Guid.Empty:
                doc.Objects.Delete(guid, True)

        # Reset IDs
        self._outline_2d = Guid.Empty
        self._outline_2d_lateral = Guid.Empty
        self._outline_2d_medial = Guid.Empty
        self._center_line_2d = Guid.Empty
        self._ball_line_2d = Guid.Empty
        self._heel_line_2d = Guid.Empty
        self._arch_line_2d = Guid.Empty
        self._toe_lines_2d = []
        self._landmark_points_2d = Guid.Empty
        self._outline_3d = Guid.Empty
        self._center_line_3d = Guid.Empty
        self._ball_line_3d = Guid.Empty
        self._cross_sections_3d = []
        self._landmark_points_3d = Guid.Empty
        self._ball_girth_curve = Guid.Empty
        self._instep_girth_curve = Guid.Empty
        self._waist_girth_curve = Guid.Empty
        self._heel_girth_curve = Guid.Empty
        self._ankle_girth_curve = Guid.Empty
        self._short_heel_girth_curve = Guid.Empty
        self._long_heel_girth_curve = Guid.Empty

    # =========================================================================
    # 2D Foot Methods
    # =========================================================================

    def CreateFootOutlineXY(self, doc):
        """Create a parametric 2D foot outline in the XY plane.

        Generates a smooth outline curve based on the foot measurements
        (length, ball width, heel width, etc.) without requiring a scan.

        Args:
            doc: The Rhino document.

        Returns:
            GUID of the created outline curve.
        """
        # Control points for outline (heel at origin, toe at +X)
        hw_l = self._heel_width / 2.0
        hw_m = self._heel_width / 2.0
        bw_l = self._ball_width_lateral
        bw_m = self._ball_width_medial
        bl = self._ball_line_length
        fl = self._foot_length

        # Build control points for lateral side (negative Y)
        lateral_pts = [
            Point3d(0, 0, 0),                        # Heel center back
            Point3d(5, -hw_l * 0.8, 0),              # Heel lateral start
            Point3d(20, -hw_l, 0),                    # Heel widest lateral
            Point3d(bl * 0.3, -hw_l * 0.9, 0),       # Waist lateral
            Point3d(bl * 0.6, -bw_l * 0.85, 0),      # Pre-ball lateral
            Point3d(fl - bl, -bw_l, 0),               # Ball lateral
            Point3d(fl - bl * 0.5, -bw_l * 0.8, 0),  # Post-ball lateral
            Point3d(fl - 15, -self._toe_width * 0.3, 0),  # Pre-toe lateral
            Point3d(fl, 0, 0),                        # Toe tip
        ]

        # Build control points for medial side (positive Y)
        medial_pts = [
            Point3d(fl, 0, 0),                        # Toe tip
            Point3d(fl - 10, bw_m * 0.4, 0),          # Pre-toe medial
            Point3d(fl - bl * 0.4, bw_m * 0.85, 0),   # Post-ball medial
            Point3d(fl - bl, bw_m, 0),                 # Ball medial
            Point3d(bl * 0.6, bw_m * 0.8, 0),         # Pre-ball medial
            Point3d(bl * 0.3, hw_m * 0.85, 0),        # Waist medial
            Point3d(20, hw_m, 0),                      # Heel widest medial
            Point3d(5, hw_m * 0.8, 0),                 # Heel medial start
            Point3d(0, 0, 0),                          # Back to heel center
        ]

        # Combine all points for a closed curve
        all_pts = lateral_pts + medial_pts[1:]  # Skip duplicate toe tip

        curve = NurbsCurve.Create(False, 3, all_pts)
        if curve and curve.IsValid:
            # Make it closed
            curve.MakeClosed(0.01)
            self._outline_2d = doc.Objects.AddCurve(curve)

        return self._outline_2d

    def Import2DFootModel(self, file_path, doc):
        """Import a 2D foot outline from a file (DXF, SVG, AI, etc.).

        Args:
            file_path: Path to the 2D foot file.
            doc: The Rhino document.

        Returns:
            True if import was successful.
        """
        self._source_file_path = file_path
        self._foot_type = Foot.FOOT_TYPE_2D

        # Use Rhino file import
        import_options = Rhino.FileIO.FileReadOptions()
        import_options.ImportMode = True

        success = doc.Import(file_path, import_options)
        if success:
            # Find the most recently added curve
            objects = doc.Objects.GetObjectList(
                Rhino.DocObjects.ObjectEnumeratorSettings()
            )
            for obj in objects:
                if isinstance(obj.Geometry, Curve) and obj.Geometry.IsClosed:
                    self._outline_2d = obj.Id
                    break
            self._source_file_format = file_path.split(".")[-1].upper()

        return success

    def Measure2DFoot(self, doc):
        """Measure the 2D foot outline to extract key dimensions.

        Analyzes the 2D outline curve to compute foot length, ball width,
        heel width, and ball line position.

        Args:
            doc: The Rhino document.

        Returns:
            True if measurements were successfully taken.
        """
        if self._outline_2d == Guid.Empty:
            return False

        obj = doc.Objects.Find(self._outline_2d)
        if obj is None:
            return False

        curve = obj.Geometry
        if not isinstance(curve, Curve):
            return False

        bbox = curve.GetBoundingBox(True)

        # Foot length = bounding box extent in X
        self._foot_length = bbox.Max.X - bbox.Min.X

        # Total width = bounding box extent in Y
        total_width = bbox.Max.Y - bbox.Min.Y

        # Approximate ball width as maximum width in the forepart region
        # (around 70% from heel)
        ball_x = bbox.Min.X + self._foot_length * 0.70
        ball_plane = Plane(Point3d(ball_x, 0, 0), Vector3d.XAxis)
        intersections = Rhino.Geometry.Intersect.Intersection.CurvePlane(
            curve, ball_plane, 0.01
        )

        if intersections and len(intersections) >= 2:
            y_vals = sorted([ix.PointA.Y for ix in intersections])
            self._ball_width = y_vals[-1] - y_vals[0]
            center_y = (y_vals[-1] + y_vals[0]) / 2.0
            self._ball_width_lateral = abs(y_vals[0] - center_y)
            self._ball_width_medial = abs(y_vals[-1] - center_y)
            self._ball_line_length = ball_x - bbox.Min.X

        # Heel width at 15% from rear
        heel_x = bbox.Min.X + self._foot_length * 0.15
        heel_plane = Plane(Point3d(heel_x, 0, 0), Vector3d.XAxis)
        intersections = Rhino.Geometry.Intersect.Intersection.CurvePlane(
            curve, heel_plane, 0.01
        )

        if intersections and len(intersections) >= 2:
            y_vals = sorted([ix.PointA.Y for ix in intersections])
            self._heel_width = y_vals[-1] - y_vals[0]
            self._heel_width_lateral = self._heel_width / 2.0
            self._heel_width_medial = self._heel_width / 2.0

        return True

    def Adjust2DFootPosture(self, doc, adjustment_type="neutral"):
        """Adjust the 2D foot outline for posture (pronation/supination).

        Args:
            doc: The Rhino document.
            adjustment_type: Type of adjustment ("neutral", "pronated", "supinated").

        Returns:
            True if adjustment was applied.
        """
        if self._outline_2d == Guid.Empty:
            return False

        if adjustment_type == "pronated":
            # Shift medial border outward
            self._forefoot_valgus = max(self._forefoot_valgus, 2.0)
        elif adjustment_type == "supinated":
            # Shift lateral border outward
            self._forefoot_varus = max(self._forefoot_varus, 2.0)

        return True

    def Position2DFoot(self, doc, origin=None, rotation=0.0):
        """Position the 2D foot at a specified location and rotation.

        Args:
            doc: The Rhino document.
            origin: Target origin point. Defaults to world origin.
            rotation: Rotation angle in degrees around the Z axis.

        Returns:
            True if positioning was successful.
        """
        if self._outline_2d == Guid.Empty:
            return False

        if origin is None:
            origin = Point3d.Origin

        obj = doc.Objects.Find(self._outline_2d)
        if obj is None:
            return False

        curve = obj.Geometry
        if not isinstance(curve, Curve):
            return False

        # Get current position (bounding box center-bottom)
        bbox = curve.GetBoundingBox(True)
        current_origin = Point3d(bbox.Min.X, (bbox.Min.Y + bbox.Max.Y) / 2.0, 0)

        # Translation
        translation = Transform.Translation(
            origin.X - current_origin.X,
            origin.Y - current_origin.Y,
            origin.Z - current_origin.Z
        )
        doc.Objects.Transform(self._outline_2d, translation, True)

        # Rotation
        if abs(rotation) > 0.001:
            rot = Transform.Rotation(
                math.radians(rotation), Vector3d.ZAxis, origin
            )
            doc.Objects.Transform(self._outline_2d, rot, True)

        return True

    def Expand2D(self, doc, expansion_mm=0.0):
        """Expand/contract the 2D foot outline uniformly.

        Args:
            doc: The Rhino document.
            expansion_mm: Amount to expand (positive) or contract (negative) in mm.

        Returns:
            True if expansion was successful.
        """
        if self._outline_2d == Guid.Empty or abs(expansion_mm) < 0.001:
            return False

        obj = doc.Objects.Find(self._outline_2d)
        if obj is None:
            return False

        curve = obj.Geometry
        if not isinstance(curve, Curve):
            return False

        # Offset the curve
        offset_curves = curve.Offset(
            Plane.WorldXY, expansion_mm,
            0.01, Rhino.Geometry.CurveOffsetCornerStyle.Sharp
        )

        if offset_curves and len(offset_curves) > 0:
            doc.Objects.Replace(self._outline_2d, offset_curves[0])
            return True

        return False

    # =========================================================================
    # 3D Foot Methods
    # =========================================================================

    def Import3DFootModel(self, file_path, doc):
        """Import a 3D foot scan (mesh) from a file.

        Args:
            file_path: Path to the 3D scan file (STL, OBJ, PLY, etc.).
            doc: The Rhino document.

        Returns:
            True if import was successful.
        """
        self._source_file_path = file_path
        self._foot_type = Foot.FOOT_TYPE_3D
        self._source_file_format = file_path.split(".")[-1].upper()

        import_options = Rhino.FileIO.FileReadOptions()
        import_options.ImportMode = True

        success = doc.Import(file_path, import_options)
        if success:
            # Find the most recently added mesh
            settings = Rhino.DocObjects.ObjectEnumeratorSettings()
            settings.ObjectTypeFilter = Rhino.DocObjects.ObjectType.Mesh
            objects = list(doc.Objects.GetObjectList(settings))

            if objects:
                # Take the last (most recently added) mesh
                self._scan_mesh_original = objects[-1].Id
                self._mesh_3d = self._scan_mesh_original

        return success

    def SplitFoot(self, doc, split_plane=None):
        """Split the 3D foot mesh into top and bottom halves.

        Args:
            doc: The Rhino document.
            split_plane: Cutting plane. Defaults to a plane at average
                         height through the foot midpoint.

        Returns:
            True if split was successful.
        """
        if self._mesh_3d == Guid.Empty:
            return False

        obj = doc.Objects.Find(self._mesh_3d)
        if obj is None or not isinstance(obj.Geometry, Mesh):
            return False

        mesh = obj.Geometry
        bbox = mesh.GetBoundingBox(True)

        if split_plane is None:
            # Default split plane at the midpoint of the foot height
            mid_z = (bbox.Min.Z + bbox.Max.Z) * 0.4  # Slightly below center
            split_plane = Plane(
                Point3d(bbox.Center.X, bbox.Center.Y, mid_z),
                Vector3d.ZAxis
            )

        # Split mesh by plane
        split_meshes = mesh.Split(split_plane)

        if split_meshes and len(split_meshes) >= 2:
            # Identify top and bottom by average Z of vertices
            for sm in split_meshes:
                avg_z = sum(v.Z for v in sm.Vertices) / sm.Vertices.Count
                if avg_z > split_plane.Origin.Z:
                    self._mesh_3d_top = doc.Objects.AddMesh(sm)
                else:
                    self._mesh_3d_bottom = doc.Objects.AddMesh(sm)
            return True

        return False

    def Orient3DFoot(self, doc, target_plane=None):
        """Orient the 3D foot scan to the standard coordinate system.

        Aligns the foot so that:
        - X axis points from heel to toe
        - Y axis points lateral to medial
        - Z axis points up (dorsal)

        Args:
            doc: The Rhino document.
            target_plane: Target plane. Defaults to WorldXY with heel at origin.

        Returns:
            True if orientation was successful.
        """
        if self._mesh_3d == Guid.Empty:
            return False

        obj = doc.Objects.Find(self._mesh_3d)
        if obj is None or not isinstance(obj.Geometry, Mesh):
            return False

        mesh = obj.Geometry
        bbox = mesh.GetBoundingBox(True)

        if target_plane is None:
            target_plane = Plane.WorldXY

        # Current source plane: longest dimension = X (heel-toe),
        # widest = Y, shortest = Z
        dims = [
            bbox.Max.X - bbox.Min.X,
            bbox.Max.Y - bbox.Min.Y,
            bbox.Max.Z - bbox.Min.Z,
        ]

        # Create orientation transform from current to target
        source_origin = Point3d(bbox.Min.X, bbox.Center.Y, bbox.Min.Z)
        source_plane = Plane(source_origin, Vector3d.XAxis, Vector3d.YAxis)

        xform = Transform.PlaneToPlane(source_plane, target_plane)
        doc.Objects.Transform(self._mesh_3d, xform, True)
        self._scan_mesh_oriented = self._mesh_3d

        return True

    def Measure3DFoot(self, doc):
        """Measure the 3D foot scan to extract key dimensions.

        Analyzes the 3D mesh to compute foot length, widths, girths,
        and heights at various anatomical positions.

        Args:
            doc: The Rhino document.

        Returns:
            True if measurements were successfully taken.
        """
        if self._mesh_3d == Guid.Empty:
            return False

        obj = doc.Objects.Find(self._mesh_3d)
        if obj is None or not isinstance(obj.Geometry, Mesh):
            return False

        mesh = obj.Geometry
        bbox = mesh.GetBoundingBox(True)

        # Basic measurements from bounding box
        self._foot_length = bbox.Max.X - bbox.Min.X

        # Ball width at 70% of foot length from heel
        ball_x = bbox.Min.X + self._foot_length * 0.70
        ball_plane = Plane(Point3d(ball_x, 0, 0), Vector3d.XAxis)
        polylines = Rhino.Geometry.Intersect.Intersection.MeshPlane(mesh, ball_plane)

        if polylines and len(polylines) > 0:
            pline = polylines[0]
            pline_bbox = pline.BoundingBox
            self._ball_width = pline_bbox.Max.Y - pline_bbox.Min.Y
            center_y = (pline_bbox.Max.Y + pline_bbox.Min.Y) / 2.0
            self._ball_width_lateral = abs(pline_bbox.Min.Y - center_y)
            self._ball_width_medial = abs(pline_bbox.Max.Y - center_y)
            self._ball_height_lateral = pline_bbox.Max.Z - pline_bbox.Min.Z
            self._ball_line_length = ball_x - bbox.Min.X

            # Approximate ball girth from polyline length
            total_length = 0
            pts = list(pline)
            for i in range(len(pts) - 1):
                total_length += pts[i].DistanceTo(pts[i + 1])
            self._ball_girth = total_length

        # Heel width at 15% from rear
        heel_x = bbox.Min.X + self._foot_length * 0.15
        heel_plane = Plane(Point3d(heel_x, 0, 0), Vector3d.XAxis)
        polylines = Rhino.Geometry.Intersect.Intersection.MeshPlane(mesh, heel_plane)

        if polylines and len(polylines) > 0:
            pline = polylines[0]
            pline_bbox = pline.BoundingBox
            self._heel_width = pline_bbox.Max.Y - pline_bbox.Min.Y

        # Instep height at 35% from heel
        instep_x = bbox.Min.X + self._foot_length * 0.35
        instep_plane = Plane(Point3d(instep_x, 0, 0), Vector3d.XAxis)
        polylines = Rhino.Geometry.Intersect.Intersection.MeshPlane(mesh, instep_plane)

        if polylines and len(polylines) > 0:
            pline = polylines[0]
            pline_bbox = pline.BoundingBox
            self._instep_height = pline_bbox.Max.Z - pline_bbox.Min.Z

            # Approximate instep girth
            total_length = 0
            pts = list(pline)
            for i in range(len(pts) - 1):
                total_length += pts[i].DistanceTo(pts[i + 1])
            self._instep_girth = total_length

        # Arch height at 55% from heel
        arch_x = bbox.Min.X + self._foot_length * 0.55
        arch_plane = Plane(Point3d(arch_x, 0, 0), Vector3d.XAxis)
        polylines = Rhino.Geometry.Intersect.Intersection.MeshPlane(mesh, arch_plane)

        if polylines and len(polylines) > 0:
            pline = polylines[0]
            pline_bbox = pline.BoundingBox
            # Arch height is the minimum clearance on the medial side
            self._arch_height = pline_bbox.Min.Z - bbox.Min.Z

        # Navicular height
        nav_x = bbox.Min.X + self._foot_length * 0.45
        self._navicular_height = self._arch_height * 1.5  # Approximate

        # Average malleolus height from ankle region
        self._average_malleolus_height = (
            self._lateral_malleolus_height + self._medial_malleolus_height
        ) / 2.0

        return True

    def Adjust3DFootPosture(self, doc, adjustment_angles=None):
        """Adjust the 3D foot scan posture.

        Args:
            doc: The Rhino document.
            adjustment_angles: Dictionary of angle adjustments.

        Returns:
            True if adjustment was applied.
        """
        if self._mesh_3d == Guid.Empty:
            return False

        if adjustment_angles is None:
            return True

        obj = doc.Objects.Find(self._mesh_3d)
        if obj is None:
            return False

        mesh = obj.Geometry
        bbox = mesh.GetBoundingBox(True)

        # Apply rearfoot rotation (around X axis at heel)
        if "rearfoot" in adjustment_angles:
            angle = math.radians(adjustment_angles["rearfoot"])
            heel_center = Point3d(bbox.Min.X + self._foot_length * 0.2,
                                  bbox.Center.Y, bbox.Min.Z)
            xform = Transform.Rotation(angle, Vector3d.XAxis, heel_center)
            doc.Objects.Transform(self._mesh_3d, xform, True)

        # Apply forefoot rotation (around X axis at ball)
        if "forefoot" in adjustment_angles:
            angle = math.radians(adjustment_angles["forefoot"])
            ball_center = Point3d(bbox.Min.X + self._foot_length * 0.7,
                                  bbox.Center.Y, bbox.Min.Z)
            xform = Transform.Rotation(angle, Vector3d.XAxis, ball_center)
            doc.Objects.Transform(self._mesh_3d, xform, True)

        return True

    def Position3DFoot(self, doc, origin=None, rotation=0.0):
        """Position the 3D foot at a specified location and rotation.

        Args:
            doc: The Rhino document.
            origin: Target origin point. Defaults to world origin.
            rotation: Rotation angle in degrees around the Z axis.

        Returns:
            True if positioning was successful.
        """
        if self._mesh_3d == Guid.Empty:
            return False

        if origin is None:
            origin = Point3d.Origin

        obj = doc.Objects.Find(self._mesh_3d)
        if obj is None:
            return False

        mesh = obj.Geometry
        bbox = mesh.GetBoundingBox(True)

        # Position heel at origin, centered on Y
        current_origin = Point3d(bbox.Min.X, bbox.Center.Y, bbox.Min.Z)
        translation = Transform.Translation(
            origin.X - current_origin.X,
            origin.Y - current_origin.Y,
            origin.Z - current_origin.Z
        )
        doc.Objects.Transform(self._mesh_3d, translation, True)

        # Rotation around Z
        if abs(rotation) > 0.001:
            rot = Transform.Rotation(math.radians(rotation), Vector3d.ZAxis, origin)
            doc.Objects.Transform(self._mesh_3d, rot, True)

        self._scan_mesh_positioned = self._mesh_3d
        return True

    # =========================================================================
    # Serialization
    # =========================================================================

    def Write(self, file_path):
        """Serialize foot data to a JSON file.

        Args:
            file_path: Path for the output JSON file.
        """
        data = self.CollectFootParameters()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def Read(file_path):
        """Deserialize a Foot from a JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            A new Foot instance populated from the file.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        foot = Foot()
        key_map = {
            "Name": "_name", "Side": "_side", "FootType": "_foot_type",
            "Posture": "_posture", "Notes": "_notes",
            "PatientId": "_patient_id", "PatientName": "_patient_name",
            "DateScanned": "_date_scanned",
            "FootLength": "_foot_length", "BallLineLength": "_ball_line_length",
            "ArchLength": "_arch_length",
            "HeelToToe1Length": "_heel_to_toe1_length",
            "HeelToToe2Length": "_heel_to_toe2_length",
            "HeelToBallLateralLength": "_heel_to_ball_lateral_length",
            "HeelToBallMedialLength": "_heel_to_ball_medial_length",
            "HeelToNavicularLength": "_heel_to_navicular_length",
            "HeelToInstepLength": "_heel_to_instep_length",
            "BallWidth": "_ball_width", "BallWidthLateral": "_ball_width_lateral",
            "BallWidthMedial": "_ball_width_medial",
            "HeelWidth": "_heel_width",
            "BallGirth": "_ball_girth", "InstepGirth": "_instep_girth",
            "WaistGirth": "_waist_girth", "HeelGirth": "_heel_girth",
            "AnkleGirth": "_ankle_girth",
            "BallHeightLateral": "_ball_height_lateral",
            "BallHeightMedial": "_ball_height_medial",
            "InstepHeight": "_instep_height",
            "NavicularHeight": "_navicular_height",
            "ArchHeight": "_arch_height",
            "AverageMalleolusHeight": "_average_malleolus_height",
            "LateralMalleolusHeight": "_lateral_malleolus_height",
            "MedialMalleolusHeight": "_medial_malleolus_height",
            "BallLineAngle": "_ball_line_angle",
            "HalluxValgusAngle": "_hallux_valgus_angle",
            "RearfootAngle": "_rearfoot_angle",
            "ForefootAngle": "_forefoot_angle",
            "PronationAngle": "_pronation_angle",
            "SupinationAngle": "_supination_angle",
            "ForefootVarus": "_forefoot_varus",
            "ForefootValgus": "_forefoot_valgus",
            "RearfootVarus": "_rearfoot_varus",
            "RearfootValgus": "_rearfoot_valgus",
            "SourceFilePath": "_source_file_path",
            "SourceFileFormat": "_source_file_format",
        }
        for json_key, attr_name in key_map.items():
            if json_key in data:
                setattr(foot, attr_name, data[json_key])

        # Restore landmarks
        if "Landmarks" in data:
            for name, coords in data["Landmarks"].items():
                foot._landmarks[name] = Point3d(
                    coords.get("X", 0), coords.get("Y", 0), coords.get("Z", 0)
                )

        return foot

    # =========================================================================
    # Properties - Identification
    # =========================================================================

    @property
    def Name(self):
        return self._name

    @Name.setter
    def Name(self, value):
        self._name = str(value)

    @property
    def Side(self):
        return self._side

    @Side.setter
    def Side(self, value):
        self._side = str(value)

    @property
    def FootType(self):
        return self._foot_type

    @FootType.setter
    def FootType(self, value):
        self._foot_type = str(value)

    @property
    def Posture(self):
        return self._posture

    @Posture.setter
    def Posture(self, value):
        self._posture = str(value)

    @property
    def Notes(self):
        return self._notes

    @Notes.setter
    def Notes(self, value):
        self._notes = str(value)

    @property
    def PatientId(self):
        return self._patient_id

    @PatientId.setter
    def PatientId(self, value):
        self._patient_id = str(value)

    @property
    def PatientName(self):
        return self._patient_name

    @PatientName.setter
    def PatientName(self, value):
        self._patient_name = str(value)

    @property
    def DateScanned(self):
        return self._date_scanned

    @DateScanned.setter
    def DateScanned(self, value):
        self._date_scanned = str(value)

    # =========================================================================
    # Properties - Length Measurements
    # =========================================================================

    @property
    def FootLength(self):
        return self._foot_length

    @FootLength.setter
    def FootLength(self, value):
        self._foot_length = float(value)

    @property
    def BallLineLength(self):
        return self._ball_line_length

    @BallLineLength.setter
    def BallLineLength(self, value):
        self._ball_line_length = float(value)

    @property
    def ArchLength(self):
        return self._arch_length

    @ArchLength.setter
    def ArchLength(self, value):
        self._arch_length = float(value)

    @property
    def HeelToToe1Length(self):
        return self._heel_to_toe1_length

    @HeelToToe1Length.setter
    def HeelToToe1Length(self, value):
        self._heel_to_toe1_length = float(value)

    @property
    def HeelToToe2Length(self):
        return self._heel_to_toe2_length

    @HeelToToe2Length.setter
    def HeelToToe2Length(self, value):
        self._heel_to_toe2_length = float(value)

    @property
    def HeelToToe3Length(self):
        return self._heel_to_toe3_length

    @HeelToToe3Length.setter
    def HeelToToe3Length(self, value):
        self._heel_to_toe3_length = float(value)

    @property
    def HeelToToe4Length(self):
        return self._heel_to_toe4_length

    @HeelToToe4Length.setter
    def HeelToToe4Length(self, value):
        self._heel_to_toe4_length = float(value)

    @property
    def HeelToToe5Length(self):
        return self._heel_to_toe5_length

    @HeelToToe5Length.setter
    def HeelToToe5Length(self, value):
        self._heel_to_toe5_length = float(value)

    @property
    def HeelToBallLateralLength(self):
        return self._heel_to_ball_lateral_length

    @HeelToBallLateralLength.setter
    def HeelToBallLateralLength(self, value):
        self._heel_to_ball_lateral_length = float(value)

    @property
    def HeelToBallMedialLength(self):
        return self._heel_to_ball_medial_length

    @HeelToBallMedialLength.setter
    def HeelToBallMedialLength(self, value):
        self._heel_to_ball_medial_length = float(value)

    @property
    def HeelToNavicularLength(self):
        return self._heel_to_navicular_length

    @HeelToNavicularLength.setter
    def HeelToNavicularLength(self, value):
        self._heel_to_navicular_length = float(value)

    @property
    def HeelToInstepLength(self):
        return self._heel_to_instep_length

    @HeelToInstepLength.setter
    def HeelToInstepLength(self, value):
        self._heel_to_instep_length = float(value)

    @property
    def ForefootLength(self):
        return self._forefoot_length

    @ForefootLength.setter
    def ForefootLength(self, value):
        self._forefoot_length = float(value)

    @property
    def MidfootLength(self):
        return self._midfoot_length

    @MidfootLength.setter
    def MidfootLength(self, value):
        self._midfoot_length = float(value)

    @property
    def RearfootLength(self):
        return self._rearfoot_length

    @RearfootLength.setter
    def RearfootLength(self, value):
        self._rearfoot_length = float(value)

    # =========================================================================
    # Properties - Width Measurements
    # =========================================================================

    @property
    def BallWidth(self):
        return self._ball_width

    @BallWidth.setter
    def BallWidth(self, value):
        self._ball_width = float(value)

    @property
    def BallWidthLateral(self):
        return self._ball_width_lateral

    @BallWidthLateral.setter
    def BallWidthLateral(self, value):
        self._ball_width_lateral = float(value)

    @property
    def BallWidthMedial(self):
        return self._ball_width_medial

    @BallWidthMedial.setter
    def BallWidthMedial(self, value):
        self._ball_width_medial = float(value)

    @property
    def HeelWidth(self):
        return self._heel_width

    @HeelWidth.setter
    def HeelWidth(self, value):
        self._heel_width = float(value)

    @property
    def HeelWidthLateral(self):
        return self._heel_width_lateral

    @HeelWidthLateral.setter
    def HeelWidthLateral(self, value):
        self._heel_width_lateral = float(value)

    @property
    def HeelWidthMedial(self):
        return self._heel_width_medial

    @HeelWidthMedial.setter
    def HeelWidthMedial(self, value):
        self._heel_width_medial = float(value)

    @property
    def MidfootWidth(self):
        return self._midfoot_width

    @MidfootWidth.setter
    def MidfootWidth(self, value):
        self._midfoot_width = float(value)

    @property
    def ForefootWidth(self):
        return self._forefoot_width

    @ForefootWidth.setter
    def ForefootWidth(self, value):
        self._forefoot_width = float(value)

    @property
    def ToeWidth(self):
        return self._toe_width

    @ToeWidth.setter
    def ToeWidth(self, value):
        self._toe_width = float(value)

    # =========================================================================
    # Properties - Girth Measurements
    # =========================================================================

    @property
    def BallGirth(self):
        return self._ball_girth

    @BallGirth.setter
    def BallGirth(self, value):
        self._ball_girth = float(value)

    @property
    def InstepGirth(self):
        return self._instep_girth

    @InstepGirth.setter
    def InstepGirth(self, value):
        self._instep_girth = float(value)

    @property
    def WaistGirth(self):
        return self._waist_girth

    @WaistGirth.setter
    def WaistGirth(self, value):
        self._waist_girth = float(value)

    @property
    def HeelGirth(self):
        return self._heel_girth

    @HeelGirth.setter
    def HeelGirth(self, value):
        self._heel_girth = float(value)

    @property
    def AnkleGirth(self):
        return self._ankle_girth

    @AnkleGirth.setter
    def AnkleGirth(self, value):
        self._ankle_girth = float(value)

    @property
    def ShortHeelGirth(self):
        return self._short_heel_girth

    @ShortHeelGirth.setter
    def ShortHeelGirth(self, value):
        self._short_heel_girth = float(value)

    @property
    def LongHeelGirth(self):
        return self._long_heel_girth

    @LongHeelGirth.setter
    def LongHeelGirth(self, value):
        self._long_heel_girth = float(value)

    # =========================================================================
    # Properties - Height Measurements
    # =========================================================================

    @property
    def BallHeightLateral(self):
        return self._ball_height_lateral

    @BallHeightLateral.setter
    def BallHeightLateral(self, value):
        self._ball_height_lateral = float(value)

    @property
    def BallHeightMedial(self):
        return self._ball_height_medial

    @BallHeightMedial.setter
    def BallHeightMedial(self, value):
        self._ball_height_medial = float(value)

    @property
    def InstepHeight(self):
        return self._instep_height

    @InstepHeight.setter
    def InstepHeight(self, value):
        self._instep_height = float(value)

    @property
    def NavicularHeight(self):
        return self._navicular_height

    @NavicularHeight.setter
    def NavicularHeight(self, value):
        self._navicular_height = float(value)

    @property
    def ArchHeight(self):
        return self._arch_height

    @ArchHeight.setter
    def ArchHeight(self, value):
        self._arch_height = float(value)

    @property
    def AverageMalleolusHeight(self):
        return self._average_malleolus_height

    @AverageMalleolusHeight.setter
    def AverageMalleolusHeight(self, value):
        self._average_malleolus_height = float(value)

    @property
    def LateralMalleolusHeight(self):
        return self._lateral_malleolus_height

    @LateralMalleolusHeight.setter
    def LateralMalleolusHeight(self, value):
        self._lateral_malleolus_height = float(value)

    @property
    def MedialMalleolusHeight(self):
        return self._medial_malleolus_height

    @MedialMalleolusHeight.setter
    def MedialMalleolusHeight(self, value):
        self._medial_malleolus_height = float(value)

    @property
    def AnkleHeight(self):
        return self._ankle_height

    @AnkleHeight.setter
    def AnkleHeight(self, value):
        self._ankle_height = float(value)

    @property
    def DorsumHeight(self):
        return self._dorsum_height

    @DorsumHeight.setter
    def DorsumHeight(self, value):
        self._dorsum_height = float(value)

    @property
    def HeelHeight(self):
        return self._heel_height

    @HeelHeight.setter
    def HeelHeight(self, value):
        self._heel_height = float(value)

    @property
    def Toe1Height(self):
        return self._toe1_height

    @Toe1Height.setter
    def Toe1Height(self, value):
        self._toe1_height = float(value)

    @property
    def Toe5Height(self):
        return self._toe5_height

    @Toe5Height.setter
    def Toe5Height(self, value):
        self._toe5_height = float(value)

    # =========================================================================
    # Properties - Angle Measurements
    # =========================================================================

    @property
    def BallLineAngle(self):
        return self._ball_line_angle

    @BallLineAngle.setter
    def BallLineAngle(self, value):
        self._ball_line_angle = float(value)

    @property
    def HalluxValgusAngle(self):
        return self._hallux_valgus_angle

    @HalluxValgusAngle.setter
    def HalluxValgusAngle(self, value):
        self._hallux_valgus_angle = float(value)

    @property
    def RearfootAngle(self):
        return self._rearfoot_angle

    @RearfootAngle.setter
    def RearfootAngle(self, value):
        self._rearfoot_angle = float(value)

    @property
    def ForefootAngle(self):
        return self._forefoot_angle

    @ForefootAngle.setter
    def ForefootAngle(self, value):
        self._forefoot_angle = float(value)

    @property
    def TibialTorsionAngle(self):
        return self._tibial_torsion_angle

    @TibialTorsionAngle.setter
    def TibialTorsionAngle(self, value):
        self._tibial_torsion_angle = float(value)

    @property
    def ArchAngle(self):
        return self._arch_angle

    @ArchAngle.setter
    def ArchAngle(self, value):
        self._arch_angle = float(value)

    @property
    def ToeOutAngle(self):
        return self._toe_out_angle

    @ToeOutAngle.setter
    def ToeOutAngle(self, value):
        self._toe_out_angle = float(value)

    # =========================================================================
    # Properties - Posture Adjustments
    # =========================================================================

    @property
    def PronationAngle(self):
        return self._pronation_angle

    @PronationAngle.setter
    def PronationAngle(self, value):
        self._pronation_angle = float(value)

    @property
    def SupinationAngle(self):
        return self._supination_angle

    @SupinationAngle.setter
    def SupinationAngle(self, value):
        self._supination_angle = float(value)

    @property
    def ForefootVarus(self):
        return self._forefoot_varus

    @ForefootVarus.setter
    def ForefootVarus(self, value):
        self._forefoot_varus = float(value)

    @property
    def ForefootValgus(self):
        return self._forefoot_valgus

    @ForefootValgus.setter
    def ForefootValgus(self, value):
        self._forefoot_valgus = float(value)

    @property
    def RearfootVarus(self):
        return self._rearfoot_varus

    @RearfootVarus.setter
    def RearfootVarus(self, value):
        self._rearfoot_varus = float(value)

    @property
    def RearfootValgus(self):
        return self._rearfoot_valgus

    @RearfootValgus.setter
    def RearfootValgus(self, value):
        self._rearfoot_valgus = float(value)

    @property
    def Plantarflexion1stRay(self):
        return self._plantarflexion_1st_ray

    @Plantarflexion1stRay.setter
    def Plantarflexion1stRay(self, value):
        self._plantarflexion_1st_ray = float(value)

    @property
    def Dorsiflexion1stRay(self):
        return self._dorsiflexion_1st_ray

    @Dorsiflexion1stRay.setter
    def Dorsiflexion1stRay(self, value):
        self._dorsiflexion_1st_ray = float(value)

    @property
    def AnkleDorsiflexion(self):
        return self._ankle_dorsiflexion

    @AnkleDorsiflexion.setter
    def AnkleDorsiflexion(self, value):
        self._ankle_dorsiflexion = float(value)

    @property
    def AnklePlantarflexion(self):
        return self._ankle_plantarflexion

    @AnklePlantarflexion.setter
    def AnklePlantarflexion(self, value):
        self._ankle_plantarflexion = float(value)

    # =========================================================================
    # Properties - Landmarks
    # =========================================================================

    @property
    def GenericFootLandmarks(self):
        """List of generic foot landmark names."""
        return list(Foot.GENERIC_FOOT_LANDMARKS)

    @property
    def Landmarks(self):
        """Dictionary of landmark name to Point3d."""
        return self._landmarks

    @Landmarks.setter
    def Landmarks(self, value):
        self._landmarks = dict(value) if value else {}

    def GetLandmark(self, name):
        """Get a landmark point by name.

        Args:
            name: Landmark name (use Foot.LANDMARK_* constants).

        Returns:
            Point3d of the landmark, or Point3d.Origin if not found.
        """
        return self._landmarks.get(name, Point3d.Origin)

    def SetLandmark(self, name, point):
        """Set a landmark point by name.

        Args:
            name: Landmark name.
            point: Point3d position.
        """
        self._landmarks[name] = point

    # =========================================================================
    # Properties - 2D Geometry IDs
    # =========================================================================

    @property
    def Outline2D(self):
        return self._outline_2d

    @Outline2D.setter
    def Outline2D(self, value):
        self._outline_2d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def Outline2DLateral(self):
        return self._outline_2d_lateral

    @Outline2DLateral.setter
    def Outline2DLateral(self, value):
        self._outline_2d_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def Outline2DMedial(self):
        return self._outline_2d_medial

    @Outline2DMedial.setter
    def Outline2DMedial(self, value):
        self._outline_2d_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CenterLine2D(self):
        return self._center_line_2d

    @CenterLine2D.setter
    def CenterLine2D(self, value):
        self._center_line_2d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BallLine2D(self):
        return self._ball_line_2d

    @BallLine2D.setter
    def BallLine2D(self, value):
        self._ball_line_2d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelLine2D(self):
        return self._heel_line_2d

    @HeelLine2D.setter
    def HeelLine2D(self, value):
        self._heel_line_2d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def ArchLine2D(self):
        return self._arch_line_2d

    @ArchLine2D.setter
    def ArchLine2D(self, value):
        self._arch_line_2d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def ToeLines2D(self):
        return self._toe_lines_2d

    @ToeLines2D.setter
    def ToeLines2D(self, value):
        self._toe_lines_2d = list(value) if value else []

    @property
    def LandmarkPoints2D(self):
        return self._landmark_points_2d

    @LandmarkPoints2D.setter
    def LandmarkPoints2D(self, value):
        self._landmark_points_2d = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - 3D Geometry IDs
    # =========================================================================

    @property
    def Mesh3D(self):
        return self._mesh_3d

    @Mesh3D.setter
    def Mesh3D(self, value):
        self._mesh_3d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def Mesh3DTop(self):
        return self._mesh_3d_top

    @Mesh3DTop.setter
    def Mesh3DTop(self, value):
        self._mesh_3d_top = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def Mesh3DBottom(self):
        return self._mesh_3d_bottom

    @Mesh3DBottom.setter
    def Mesh3DBottom(self, value):
        self._mesh_3d_bottom = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def Mesh3DLateral(self):
        return self._mesh_3d_lateral

    @Mesh3DLateral.setter
    def Mesh3DLateral(self, value):
        self._mesh_3d_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def Mesh3DMedial(self):
        return self._mesh_3d_medial

    @Mesh3DMedial.setter
    def Mesh3DMedial(self, value):
        self._mesh_3d_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def ScanMeshOriginal(self):
        return self._scan_mesh_original

    @ScanMeshOriginal.setter
    def ScanMeshOriginal(self, value):
        self._scan_mesh_original = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def ScanMeshOriented(self):
        return self._scan_mesh_oriented

    @ScanMeshOriented.setter
    def ScanMeshOriented(self, value):
        self._scan_mesh_oriented = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def ScanMeshPositioned(self):
        return self._scan_mesh_positioned

    @ScanMeshPositioned.setter
    def ScanMeshPositioned(self, value):
        self._scan_mesh_positioned = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def Outline3D(self):
        return self._outline_3d

    @Outline3D.setter
    def Outline3D(self, value):
        self._outline_3d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CenterLine3D(self):
        return self._center_line_3d

    @CenterLine3D.setter
    def CenterLine3D(self, value):
        self._center_line_3d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BallLine3D(self):
        return self._ball_line_3d

    @BallLine3D.setter
    def BallLine3D(self, value):
        self._ball_line_3d = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CrossSections3D(self):
        return self._cross_sections_3d

    @CrossSections3D.setter
    def CrossSections3D(self, value):
        self._cross_sections_3d = list(value) if value else []

    @property
    def LandmarkPoints3D(self):
        return self._landmark_points_3d

    @LandmarkPoints3D.setter
    def LandmarkPoints3D(self, value):
        self._landmark_points_3d = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Measurement Curve IDs
    # =========================================================================

    @property
    def BallGirthCurve(self):
        return self._ball_girth_curve

    @BallGirthCurve.setter
    def BallGirthCurve(self, value):
        self._ball_girth_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def InstepGirthCurve(self):
        return self._instep_girth_curve

    @InstepGirthCurve.setter
    def InstepGirthCurve(self, value):
        self._instep_girth_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def WaistGirthCurve(self):
        return self._waist_girth_curve

    @WaistGirthCurve.setter
    def WaistGirthCurve(self, value):
        self._waist_girth_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelGirthCurve(self):
        return self._heel_girth_curve

    @HeelGirthCurve.setter
    def HeelGirthCurve(self, value):
        self._heel_girth_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def AnkleGirthCurve(self):
        return self._ankle_girth_curve

    @AnkleGirthCurve.setter
    def AnkleGirthCurve(self, value):
        self._ankle_girth_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def ShortHeelGirthCurve(self):
        return self._short_heel_girth_curve

    @ShortHeelGirthCurve.setter
    def ShortHeelGirthCurve(self, value):
        self._short_heel_girth_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def LongHeelGirthCurve(self):
        return self._long_heel_girth_curve

    @LongHeelGirthCurve.setter
    def LongHeelGirthCurve(self, value):
        self._long_heel_girth_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Import/Export
    # =========================================================================

    @property
    def SourceFilePath(self):
        return self._source_file_path

    @SourceFilePath.setter
    def SourceFilePath(self, value):
        self._source_file_path = str(value)

    @property
    def SourceFileFormat(self):
        return self._source_file_format

    @SourceFileFormat.setter
    def SourceFileFormat(self, value):
        self._source_file_format = str(value)

    @property
    def ScanResolution(self):
        return self._scan_resolution

    @ScanResolution.setter
    def ScanResolution(self, value):
        self._scan_resolution = float(value)

    # =========================================================================
    # JSON Serialization Convenience
    # =========================================================================

    def to_json(self):
        """Serialize this Foot to a JSON string."""
        return json.dumps(self.CollectFootParameters(), indent=2, default=str)

    @staticmethod
    def from_json(json_string):
        """Deserialize a Foot from a JSON string."""
        if isinstance(json_string, str):
            data = json.loads(json_string)
        else:
            data = json_string
        foot = Foot()
        key_map = {
            "Name": "_name", "Side": "_side", "FootType": "_foot_type",
            "FootLength": "_foot_length", "BallWidth": "_ball_width",
            "HeelWidth": "_heel_width", "BallGirth": "_ball_girth",
        }
        for json_key, attr_name in key_map.items():
            if json_key in data:
                setattr(foot, attr_name, data[json_key])
        return foot

    def __repr__(self):
        return (
            f'Foot(name="{self._name}", side="{self._side}", '
            f'type="{self._foot_type}", '
            f'length={self._foot_length:.1f}, '
            f'ball_width={self._ball_width:.1f})'
        )
