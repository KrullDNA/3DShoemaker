"""
Insert (insole/insert) data model for 3DShoemaker Rhino 8 Python plugin.

The Insert class represents a shoe insert/insole with all geometric parameters,
design curves, surfaces, and body geometry. Inserts derive their base geometry
from the Last and can be customized with their own style parameters.

Port of PodoCAD .NET Insert class to Python 3.
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


class Insert:
    """Represents a shoe insert/insole with all parameters, curves, surfaces, and bodies."""

    # -------------------------------------------------------------------------
    # Insert type enumerations
    # -------------------------------------------------------------------------
    INSERT_TYPE_FULL_LENGTH = "FullLength"
    INSERT_TYPE_THREE_QUARTER = "ThreeQuarter"
    INSERT_TYPE_HALF = "Half"
    INSERT_TYPE_HEEL_CUP = "HeelCup"
    INSERT_TYPE_FOREFOOT = "Forefoot"
    INSERT_TYPE_SANDAL = "Sandal"

    # Shell type enumerations
    SHELL_TYPE_NONE = "None"
    SHELL_TYPE_FULL = "Full"
    SHELL_TYPE_PARTIAL = "Partial"

    # Top cover type enumerations
    TOP_COVER_NONE = "None"
    TOP_COVER_FLAT = "Flat"
    TOP_COVER_CONTOURED = "Contoured"

    # Posting type enumerations
    POSTING_TYPE_NONE = "None"
    POSTING_TYPE_INTRINSIC = "Intrinsic"
    POSTING_TYPE_EXTRINSIC = "Extrinsic"

    # Arch support type enumerations
    ARCH_SUPPORT_NONE = "None"
    ARCH_SUPPORT_LOW = "Low"
    ARCH_SUPPORT_MEDIUM = "Medium"
    ARCH_SUPPORT_HIGH = "High"
    ARCH_SUPPORT_CUSTOM = "Custom"

    def __init__(self):
        """Initialize an Insert with default parameter values."""
        # --- Identification ---
        self._name = ""
        self._side = "Right"
        self._notes = ""

        # --- Type and Style ---
        self._insert_type = Insert.INSERT_TYPE_FULL_LENGTH
        self._shell_type = Insert.SHELL_TYPE_NONE
        self._top_cover_type = Insert.TOP_COVER_FLAT
        self._posting_type = Insert.POSTING_TYPE_NONE
        self._arch_support_type = Insert.ARCH_SUPPORT_MEDIUM

        # --- Reference to parent Last ---
        self._last_name = ""

        # --- Length Parameters ---
        self._length = 270.0
        self._forefoot_length = 0.0
        self._midfoot_length = 0.0
        self._rearfoot_length = 0.0
        self._trim_line_length = 270.0
        self._ball_line_length = 189.0
        self._arch_length = 148.5
        self._waist_length = 126.9
        self._instep_length = 94.5
        self._heel_length = 0.0
        self._three_quarter_length = 0.0

        # --- Length Multipliers ---
        self._forefoot_length_mult = 0.30
        self._midfoot_length_mult = 0.40
        self._rearfoot_length_mult = 0.30
        self._ball_line_length_mult = 0.70
        self._arch_length_mult = 0.55
        self._waist_length_mult = 0.47
        self._instep_length_mult = 0.35
        self._three_quarter_length_mult = 0.75

        # --- Width Parameters ---
        self._ball_width = 95.0
        self._heel_width = 65.0
        self._waist_width = 70.0
        self._arch_width = 75.0
        self._toe_width = 67.5
        self._trim_width_lateral = 0.0
        self._trim_width_medial = 0.0
        self._flange_width_lateral = 3.0
        self._flange_width_medial = 3.0
        self._flange_width_heel = 3.0

        # --- Width Multipliers ---
        self._ball_width_mult = 0.352
        self._heel_width_mult = 0.241
        self._waist_width_mult = 0.260
        self._arch_width_mult = 0.280
        self._toe_width_mult = 0.250

        # --- Thickness Parameters ---
        self._thickness_toe = 3.0
        self._thickness_ball = 3.0
        self._thickness_arch = 4.0
        self._thickness_waist = 4.0
        self._thickness_heel = 4.0
        self._thickness_heel_center = 5.0
        self._thickness_top_cover = 1.5
        self._thickness_shell = 2.0
        self._thickness_posting = 3.0
        self._thickness_metatarsal_pad = 0.0
        self._thickness_heel_pad = 0.0
        self._thickness_forefoot_extension = 0.0

        # --- Height/Depth Parameters ---
        self._arch_height = 15.0
        self._heel_cup_depth = 12.0
        self._heel_cup_depth_lateral = 12.0
        self._heel_cup_depth_medial = 12.0
        self._metatarsal_dome_height = 0.0
        self._heel_lift = 0.0
        self._forefoot_wedge_height = 0.0
        self._rearfoot_wedge_height = 0.0
        self._medial_skive_depth = 0.0
        self._lateral_skive_depth = 0.0

        # --- Angle Parameters ---
        self._forefoot_posting_angle = 0.0
        self._rearfoot_posting_angle = 0.0
        self._medial_skive_angle = 0.0
        self._lateral_skive_angle = 0.0
        self._heel_cup_flare_angle = 0.0
        self._arch_fill_angle = 0.0
        self._inversion_angle = 0.0
        self._eversion_angle = 0.0
        self._blake_inverted_angle = 0.0

        # --- Offset Parameters ---
        self._offset_from_last_surface = 0.0
        self._offset_ball_lateral = 0.0
        self._offset_ball_medial = 0.0
        self._offset_heel_lateral = 0.0
        self._offset_heel_medial = 0.0
        self._offset_arch_lateral = 0.0
        self._offset_arch_medial = 0.0
        self._offset_waist_lateral = 0.0
        self._offset_waist_medial = 0.0

        # --- Cross Section Shape Parameters ---
        self._cs_ball_lateral = 0.5
        self._cs_ball_medial = 0.5
        self._cs_arch_lateral = 0.5
        self._cs_arch_medial = 0.5
        self._cs_waist_lateral = 0.5
        self._cs_waist_medial = 0.5
        self._cs_heel_lateral = 0.5
        self._cs_heel_medial = 0.5
        self._cs_toe_lateral = 0.5
        self._cs_toe_medial = 0.5

        # --- Feature flags ---
        self._has_metatarsal_pad = False
        self._has_heel_pad = False
        self._has_forefoot_extension = False
        self._has_heel_lift = False
        self._has_medial_flange = True
        self._has_lateral_flange = True
        self._has_heel_flange = True
        self._has_arch_fill = False
        self._has_top_cover = True
        self._has_posting = False
        self._is_sandal = False

        # --- Metatarsal Pad Parameters ---
        self._met_pad_position_x = 0.0
        self._met_pad_position_y = 0.0
        self._met_pad_width = 25.0
        self._met_pad_length = 25.0
        self._met_pad_height = 5.0
        self._met_pad_shape = "Dome"

        # --- Heel Pad Parameters ---
        self._heel_pad_width = 30.0
        self._heel_pad_length = 30.0
        self._heel_pad_depth = 3.0
        self._heel_pad_shape = "Round"

        # --- Sandal-Specific Parameters ---
        self._sandal_thickness = 10.0
        self._sandal_edge_radius = 2.0
        self._sandal_toe_bar_height = 5.0
        self._sandal_arch_cookie_height = 8.0
        self._sandal_heel_cup_depth = 6.0
        self._sandal_contour_depth = 3.0
        self._sandal_rocker_angle = 0.0

        # --- Design Curve IDs ---
        self._outline_curve = Guid.Empty
        self._outline_curve_lateral = Guid.Empty
        self._outline_curve_medial = Guid.Empty
        self._trim_curve = Guid.Empty
        self._trim_curve_lateral = Guid.Empty
        self._trim_curve_medial = Guid.Empty
        self._heel_cup_curve = Guid.Empty
        self._heel_cup_curve_lateral = Guid.Empty
        self._heel_cup_curve_medial = Guid.Empty
        self._arch_curve = Guid.Empty
        self._flange_curve_lateral = Guid.Empty
        self._flange_curve_medial = Guid.Empty
        self._flange_curve_heel = Guid.Empty
        self._center_line = Guid.Empty
        self._bottom_line = Guid.Empty
        self._top_line = Guid.Empty
        self._met_pad_curve = Guid.Empty
        self._heel_pad_curve = Guid.Empty
        self._forefoot_extension_curve = Guid.Empty
        self._posting_boundary_curve = Guid.Empty

        # --- Cross Section Curve IDs ---
        self._cs_curve_ball = Guid.Empty
        self._cs_curve_arch = Guid.Empty
        self._cs_curve_waist = Guid.Empty
        self._cs_curve_heel = Guid.Empty
        self._cs_curve_toe = Guid.Empty
        self._cs_curve_instep = Guid.Empty
        self._cs_curve_three_quarter = Guid.Empty

        # --- Surface IDs ---
        self._surface_top = Guid.Empty
        self._surface_bottom = Guid.Empty
        self._surface_shell = Guid.Empty
        self._surface_top_cover = Guid.Empty
        self._surface_posting = Guid.Empty
        self._surface_trim = Guid.Empty

        # --- Body Geometry IDs ---
        self._body_main = Guid.Empty
        self._body_main_subd = Guid.Empty
        self._body_shell = Guid.Empty
        self._body_top_cover = Guid.Empty
        self._body_posting = Guid.Empty
        self._body_met_pad = Guid.Empty
        self._body_heel_pad = Guid.Empty
        self._body_forefoot_extension = Guid.Empty
        self._body_sandal = Guid.Empty
        self._body_sandal_contour = Guid.Empty
        self._body_mesh = Guid.Empty

        # --- Sandal Curve IDs ---
        self._sandal_outline_curve = Guid.Empty
        self._sandal_contour_curve = Guid.Empty
        self._sandal_toe_bar_curve = Guid.Empty
        self._sandal_arch_cookie_curve = Guid.Empty
        self._sandal_heel_cup_curve = Guid.Empty
        self._sandal_rocker_curve = Guid.Empty

        # --- Sandal Body IDs ---
        self._sandal_body_base = Guid.Empty
        self._sandal_body_contour = Guid.Empty
        self._sandal_body_toe_bar = Guid.Empty
        self._sandal_body_arch_cookie = Guid.Empty

        # --- Key Points ---
        self._ball_point = Point3d.Origin
        self._heel_point = Point3d.Origin
        self._toe_point = Point3d.Origin
        self._arch_point = Point3d.Origin
        self._waist_point = Point3d.Origin
        self._instep_point = Point3d.Origin
        self._met_pad_center = Point3d.Origin
        self._heel_pad_center = Point3d.Origin

        # --- Last Surface Reference (trimmed by insert) ---
        self._last_surface_trimmed = Guid.Empty
        self._last_surface_original = Guid.Empty

        # --- Style Parameter Dictionary ---
        self._insert_style_parameter_dictionary = {}

    # =========================================================================
    # Factory / Lifecycle Methods
    # =========================================================================

    def Clone(self):
        """Create a deep copy of this Insert instance."""
        return copy.deepcopy(self)

    @staticmethod
    def Create():
        """Create a new Insert with default parameters."""
        insert = Insert()
        insert.SetDefaultInsertStyleParameters()
        insert.CalculateLinearMeasurementsFromMults()
        return insert

    # =========================================================================
    # Parameter Collection Methods
    # =========================================================================

    def CollectInsertParameters(self):
        """Collect all insert parameters into a dictionary for serialization.

        Returns:
            Dictionary with all insert parameter key-value pairs.
        """
        params = {}
        params["Name"] = self._name
        params["Side"] = self._side
        params["Notes"] = self._notes
        params["InsertType"] = self._insert_type
        params["ShellType"] = self._shell_type
        params["TopCoverType"] = self._top_cover_type
        params["PostingType"] = self._posting_type
        params["ArchSupportType"] = self._arch_support_type
        params["LastName"] = self._last_name

        # Lengths
        params["Length"] = self._length
        params["ForefootLength"] = self._forefoot_length
        params["MidfootLength"] = self._midfoot_length
        params["RearfootLength"] = self._rearfoot_length
        params["TrimLineLength"] = self._trim_line_length
        params["BallLineLength"] = self._ball_line_length
        params["ArchLength"] = self._arch_length
        params["WaistLength"] = self._waist_length
        params["InstepLength"] = self._instep_length
        params["ThreeQuarterLength"] = self._three_quarter_length

        # Widths
        params["BallWidth"] = self._ball_width
        params["HeelWidth"] = self._heel_width
        params["WaistWidth"] = self._waist_width
        params["ArchWidth"] = self._arch_width
        params["ToeWidth"] = self._toe_width
        params["FlangeWidthLateral"] = self._flange_width_lateral
        params["FlangeWidthMedial"] = self._flange_width_medial
        params["FlangeWidthHeel"] = self._flange_width_heel

        # Thicknesses
        params["ThicknessToe"] = self._thickness_toe
        params["ThicknessBall"] = self._thickness_ball
        params["ThicknessArch"] = self._thickness_arch
        params["ThicknessWaist"] = self._thickness_waist
        params["ThicknessHeel"] = self._thickness_heel
        params["ThicknessHeelCenter"] = self._thickness_heel_center
        params["ThicknessTopCover"] = self._thickness_top_cover
        params["ThicknessShell"] = self._thickness_shell
        params["ThicknessPosting"] = self._thickness_posting

        # Heights/Depths
        params["ArchHeight"] = self._arch_height
        params["HeelCupDepth"] = self._heel_cup_depth
        params["HeelCupDepthLateral"] = self._heel_cup_depth_lateral
        params["HeelCupDepthMedial"] = self._heel_cup_depth_medial
        params["MetatarsalDomeHeight"] = self._metatarsal_dome_height
        params["HeelLift"] = self._heel_lift

        # Angles
        params["ForefootPostingAngle"] = self._forefoot_posting_angle
        params["RearfootPostingAngle"] = self._rearfoot_posting_angle
        params["MedialSkiveAngle"] = self._medial_skive_angle
        params["LateralSkiveAngle"] = self._lateral_skive_angle
        params["HeelCupFlareAngle"] = self._heel_cup_flare_angle
        params["InversionAngle"] = self._inversion_angle
        params["EversionAngle"] = self._eversion_angle
        params["BlakeInvertedAngle"] = self._blake_inverted_angle

        # Offsets
        params["OffsetFromLastSurface"] = self._offset_from_last_surface

        # Features
        params["HasMetatarsalPad"] = self._has_metatarsal_pad
        params["HasHeelPad"] = self._has_heel_pad
        params["HasForefootExtension"] = self._has_forefoot_extension
        params["HasHeelLift"] = self._has_heel_lift
        params["HasMedialFlange"] = self._has_medial_flange
        params["HasLateralFlange"] = self._has_lateral_flange
        params["HasHeelFlange"] = self._has_heel_flange
        params["HasArchFill"] = self._has_arch_fill
        params["HasTopCover"] = self._has_top_cover
        params["HasPosting"] = self._has_posting
        params["IsSandal"] = self._is_sandal

        # Style dictionary
        params["InsertStyleParameterDictionary"] = self._insert_style_parameter_dictionary

        return params

    def CollectInsertStyleParameters(self):
        """Collect insert style parameters into a dictionary.

        Returns:
            Dictionary of style parameters.
        """
        style_params = {}
        style_params["InsertType"] = self._insert_type
        style_params["ShellType"] = self._shell_type
        style_params["TopCoverType"] = self._top_cover_type
        style_params["PostingType"] = self._posting_type
        style_params["ArchSupportType"] = self._arch_support_type
        style_params["HasMetatarsalPad"] = self._has_metatarsal_pad
        style_params["HasHeelPad"] = self._has_heel_pad
        style_params["HasForefootExtension"] = self._has_forefoot_extension
        style_params["HasHeelLift"] = self._has_heel_lift
        style_params["HasMedialFlange"] = self._has_medial_flange
        style_params["HasLateralFlange"] = self._has_lateral_flange
        style_params["HasHeelFlange"] = self._has_heel_flange
        style_params["HasArchFill"] = self._has_arch_fill
        style_params["HasTopCover"] = self._has_top_cover
        style_params["HasPosting"] = self._has_posting
        style_params["IsSandal"] = self._is_sandal
        style_params["ThicknessTopCover"] = self._thickness_top_cover
        style_params["ThicknessShell"] = self._thickness_shell
        style_params["ThicknessPosting"] = self._thickness_posting
        style_params["HeelCupFlareAngle"] = self._heel_cup_flare_angle
        style_params["SandalThickness"] = self._sandal_thickness
        style_params["SandalEdgeRadius"] = self._sandal_edge_radius
        return style_params

    # =========================================================================
    # Default Parameter Methods
    # =========================================================================

    def SetDefaultInsertStyleParameters(self):
        """Set all insert style parameters to their default values."""
        self._insert_type = Insert.INSERT_TYPE_FULL_LENGTH
        self._shell_type = Insert.SHELL_TYPE_NONE
        self._top_cover_type = Insert.TOP_COVER_FLAT
        self._posting_type = Insert.POSTING_TYPE_NONE
        self._arch_support_type = Insert.ARCH_SUPPORT_MEDIUM
        self._has_metatarsal_pad = False
        self._has_heel_pad = False
        self._has_forefoot_extension = False
        self._has_heel_lift = False
        self._has_medial_flange = True
        self._has_lateral_flange = True
        self._has_heel_flange = True
        self._has_arch_fill = False
        self._has_top_cover = True
        self._has_posting = False
        self._is_sandal = False
        self._thickness_top_cover = 1.5
        self._thickness_shell = 2.0
        self._thickness_posting = 3.0
        self._heel_cup_flare_angle = 0.0
        self._sandal_thickness = 10.0
        self._sandal_edge_radius = 2.0

    # =========================================================================
    # Calculation Methods
    # =========================================================================

    def CalculateLinearMeasurementsFromMults(self):
        """Calculate all linear measurements from their multiplier values."""
        length = self._length
        self._ball_line_length = length * self._ball_line_length_mult
        self._arch_length = length * self._arch_length_mult
        self._waist_length = length * self._waist_length_mult
        self._instep_length = length * self._instep_length_mult
        self._forefoot_length = length * self._forefoot_length_mult
        self._midfoot_length = length * self._midfoot_length_mult
        self._rearfoot_length = length * self._rearfoot_length_mult
        self._three_quarter_length = length * self._three_quarter_length_mult
        self._ball_width = length * self._ball_width_mult
        self._heel_width = length * self._heel_width_mult
        self._waist_width = length * self._waist_width_mult
        self._arch_width = length * self._arch_width_mult
        self._toe_width = length * self._toe_width_mult

    # =========================================================================
    # Design Methods
    # =========================================================================

    def DesignCurves(self, last, doc):
        """Design all insert curves based on the parent Last geometry.

        Creates outline, trim, heel cup, arch, flange, center line,
        and cross section curves for this insert.

        Args:
            last: The parent Last instance providing base geometry.
            doc: The Rhino document for adding geometry.
        """
        # Transfer key measurements from last
        self._length = last.Length
        self._ball_line_length = last.BallLineLength
        self._ball_width = last.BallWidth
        self._heel_width = last.HeelWidth

        # Key points derived from the last
        self._ball_point = last.BallPoint
        self._heel_point = last.HeelPoint
        self._toe_point = last.ToePoint
        self._arch_point = last.ArchPoint
        self._waist_point = last.WaistPoint
        self._instep_point = last.InstepPoint

        # Design outline by offsetting the last bottom line
        self._design_outline_from_last(last, doc)
        # Design trim curve (how far the insert extends)
        self._design_trim_curve(last, doc)
        # Design heel cup curve
        self._design_heel_cup_curve(last, doc)
        # Design arch support curve
        self._design_arch_curve(last, doc)
        # Design flange curves
        self._design_flange_curves(last, doc)
        # Design cross section curves at key positions
        self._design_cross_section_curves(last, doc)

    def _design_outline_from_last(self, last, doc):
        """Create insert outline from last bottom line with offsets."""
        # Implementation uses last BLFull curve offset by insert-specific values
        pass

    def _design_trim_curve(self, last, doc):
        """Create the trim boundary curve for the insert length."""
        pass

    def _design_heel_cup_curve(self, last, doc):
        """Create heel cup curves from heel section of last."""
        pass

    def _design_arch_curve(self, last, doc):
        """Create arch support profile curve."""
        pass

    def _design_flange_curves(self, last, doc):
        """Create lateral, medial, and heel flange curves."""
        pass

    def _design_cross_section_curves(self, last, doc):
        """Create cross section curves at ball, arch, waist, heel, toe."""
        pass

    def MorphExtendTrimCurve(self, curve_id, last, doc, extension_type="linear"):
        """Morph, extend, or trim a curve relative to the insert boundary.

        Args:
            curve_id: GUID of the curve to modify.
            last: The parent Last instance.
            doc: The Rhino document.
            extension_type: Type of extension ("linear", "arc", "smooth").

        Returns:
            GUID of the modified curve, or Guid.Empty on failure.
        """
        if curve_id == Guid.Empty:
            return Guid.Empty

        rhino_obj = doc.Objects.Find(curve_id)
        if rhino_obj is None:
            return Guid.Empty

        curve = rhino_obj.Geometry
        if not isinstance(curve, Curve):
            return Guid.Empty

        # Get the trim boundary
        trim_obj = doc.Objects.Find(self._trim_curve)
        if trim_obj is None:
            return curve_id

        trim_curve = trim_obj.Geometry

        # Determine if we need to extend or trim
        bbox_insert = trim_curve.GetBoundingBox(True)
        bbox_curve = curve.GetBoundingBox(True)

        if bbox_curve.Max.X > bbox_insert.Max.X:
            # Curve extends beyond insert - trim it
            intersections = Rhino.Geometry.Intersect.Intersection.CurveCurve(
                curve, trim_curve, 0.001, 0.001
            )
            if intersections and intersections.Count > 0:
                t = intersections[0].ParameterA
                trimmed = curve.Trim(curve.Domain.Min, t)
                if trimmed:
                    doc.Objects.Replace(curve_id, trimmed)
        elif bbox_curve.Max.X < bbox_insert.Max.X * 0.95:
            # Curve is short - extend it
            if extension_type == "linear":
                end_pt = curve.PointAtEnd
                tangent = curve.TangentAtEnd
                extension_length = bbox_insert.Max.X - end_pt.X
                new_end = Point3d(
                    end_pt.X + tangent.X * extension_length,
                    end_pt.Y + tangent.Y * extension_length,
                    end_pt.Z + tangent.Z * extension_length
                )
                extended = curve.Extend(
                    Rhino.Geometry.CurveEnd.End,
                    Rhino.Geometry.CurveExtensionStyle.Line,
                    [new_end]
                )
                if extended:
                    doc.Objects.Replace(curve_id, extended)

        return curve_id

    def DesignCrossSectionCurve(self, section_name, last, doc, plane=None):
        """Design a single cross section curve at the specified anatomical section.

        Args:
            section_name: Name of the section ("Ball", "Arch", "Waist", "Heel", "Toe").
            last: The parent Last instance.
            doc: The Rhino document.
            plane: Optional custom cutting plane. If None, uses the section default.

        Returns:
            GUID of the created cross section curve.
        """
        section_params = {
            "Ball": {
                "cs_l": self._cs_ball_lateral,
                "cs_m": self._cs_ball_medial,
                "thickness": self._thickness_ball,
                "position_mult": self._ball_line_length_mult,
            },
            "Arch": {
                "cs_l": self._cs_arch_lateral,
                "cs_m": self._cs_arch_medial,
                "thickness": self._thickness_arch,
                "position_mult": self._arch_length_mult,
            },
            "Waist": {
                "cs_l": self._cs_waist_lateral,
                "cs_m": self._cs_waist_medial,
                "thickness": self._thickness_waist,
                "position_mult": self._waist_length_mult,
            },
            "Heel": {
                "cs_l": self._cs_heel_lateral,
                "cs_m": self._cs_heel_medial,
                "thickness": self._thickness_heel,
                "position_mult": 0.10,
            },
            "Toe": {
                "cs_l": self._cs_toe_lateral,
                "cs_m": self._cs_toe_medial,
                "thickness": self._thickness_toe,
                "position_mult": self._ball_line_length_mult + 0.10,
            },
        }

        if section_name not in section_params:
            return Guid.Empty

        params = section_params[section_name]
        x_position = self._length * (1.0 - params["position_mult"])

        if plane is None:
            plane = Plane(Point3d(x_position, 0, 0), Vector3d.YAxis, Vector3d.ZAxis)

        # The cross section curve would be created by intersecting the
        # last body with the cutting plane and then offsetting inward
        # by the insert thickness. The shape is controlled by the cs_l/cs_m
        # parameters which blend between circular and flat profiles.
        # Actual implementation requires Rhino geometry operations.
        return Guid.Empty

    def DesignCrossSectionCurveBeforeRemovingSeparateLRTreatment(
        self, section_name, last, doc
    ):
        """Design cross section before removing separate left/right treatment.

        This is a pre-processing step that creates the cross section curve
        using unified left/right parameters, before the separate L/R
        treatment is applied during final design.

        Args:
            section_name: Name of the section.
            last: The parent Last instance.
            doc: The Rhino document.

        Returns:
            GUID of the pre-processed cross section curve.
        """
        return self.DesignCrossSectionCurve(section_name, last, doc)

    def DesignCrossSectionCurveBeforeSwitchingToLastEdgeRelativeMeasurements(
        self, section_name, last, doc
    ):
        """Design cross section before switching to last-edge-relative measurements.

        Creates cross section curves using absolute measurements before
        converting to relative-to-last-edge measurements.

        Args:
            section_name: Name of the section.
            last: The parent Last instance.
            doc: The Rhino document.

        Returns:
            GUID of the cross section curve in absolute coordinates.
        """
        return self.DesignCrossSectionCurve(section_name, last, doc)

    def DesignSurfaces(self, last, doc):
        """Design all insert surfaces from curves.

        Creates top surface, bottom surface, shell, top cover, and
        posting surfaces by lofting through cross section curves.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        # Loft through cross section curves to create the top surface
        self._design_top_surface(last, doc)
        # Offset top surface downward by thickness to create bottom
        self._design_bottom_surface(last, doc)
        # Create shell surface if applicable
        if self._shell_type != Insert.SHELL_TYPE_NONE:
            self._design_shell_surface(last, doc)
        # Create top cover surface if applicable
        if self._has_top_cover:
            self._design_top_cover_surface(last, doc)
        # Create posting surface if applicable
        if self._has_posting:
            self._design_posting_surface(last, doc)

    def _design_top_surface(self, last, doc):
        """Create the top (foot-facing) surface of the insert."""
        pass

    def _design_bottom_surface(self, last, doc):
        """Create the bottom surface of the insert."""
        pass

    def _design_shell_surface(self, last, doc):
        """Create the shell surface."""
        pass

    def _design_top_cover_surface(self, last, doc):
        """Create the top cover surface."""
        pass

    def _design_posting_surface(self, last, doc):
        """Create the posting surface."""
        pass

    def TrimLastByInsertSurface(self, last, doc):
        """Trim the last body surface where the insert meets it.

        Creates a trimmed version of the last surface that represents
        the contact area between the insert and the last.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.

        Returns:
            GUID of the trimmed last surface.
        """
        if self._surface_top == Guid.Empty:
            return Guid.Empty

        last_body_id = last.BodyMain
        if last_body_id == Guid.Empty:
            return Guid.Empty

        # Get the last body and insert top surface
        last_obj = doc.Objects.Find(last_body_id)
        insert_surf_obj = doc.Objects.Find(self._surface_top)

        if last_obj is None or insert_surf_obj is None:
            return Guid.Empty

        last_brep = last_obj.Geometry
        insert_surf = insert_surf_obj.Geometry

        if not isinstance(last_brep, Brep) or not isinstance(insert_surf, (Brep, Surface)):
            return Guid.Empty

        # Split the last body with the insert surface
        tolerance = doc.ModelAbsoluteTolerance
        split_results = last_brep.Split(
            insert_surf if isinstance(insert_surf, Brep) else insert_surf.ToBrep(),
            tolerance
        )

        if split_results and len(split_results) > 0:
            # Keep the bottom portion (the part below the insert)
            bottom_piece = min(split_results, key=lambda b: b.GetBoundingBox(True).Center.Z)
            trimmed_id = doc.Objects.AddBrep(bottom_piece)
            self._last_surface_trimmed = trimmed_id
            return trimmed_id

        return Guid.Empty

    # =========================================================================
    # Body Design Methods
    # =========================================================================

    def DesignBody(self, last, doc):
        """Design the complete insert body geometry.

        Dispatches to the appropriate body design method based on
        insert type and configuration.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        if self._is_sandal:
            self.DesignSandalBody(last, doc)
        elif (self._shell_type != Insert.SHELL_TYPE_NONE and
              self._insert_type == Insert.INSERT_TYPE_FULL_LENGTH):
            self.DesignBodySubDFullLengthNonShell(last, doc)
        else:
            self.DesignBodyAllOtherCases(last, doc)

    def DesignBodySubDFullLengthNonShell(self, last, doc):
        """Design the insert body as a SubD for full-length non-shell inserts.

        Uses subdivision surface modeling for smooth, high-quality geometry
        suitable for direct manufacturing.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        # Collect cross section curves
        cs_curves = [
            self._cs_curve_toe,
            self._cs_curve_ball,
            self._cs_curve_arch,
            self._cs_curve_waist,
            self._cs_curve_heel,
        ]
        valid_curves = [c for c in cs_curves if c != Guid.Empty]

        if len(valid_curves) < 3:
            return

        # Build SubD from cross section curves
        # The SubD approach provides smooth interpolation between sections
        # with proper control of edge flow for manufacturing
        curves = []
        for curve_id in valid_curves:
            obj = doc.Objects.Find(curve_id)
            if obj and isinstance(obj.Geometry, Curve):
                curves.append(obj.Geometry)

        if len(curves) >= 3:
            # Create lofted SubD through the cross section curves
            subd = SubD.CreateFromLoft(curves, False, False, 0, 0)
            if subd and subd.IsValid:
                self._body_main_subd = doc.Objects.AddSubD(subd)

    def DesignBodyAllOtherCases(self, last, doc):
        """Design the insert body for all non-SubD cases.

        Uses Brep lofting and boolean operations for shell inserts,
        partial-length inserts, and other configurations.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        # Collect cross section curves
        cs_curves = [
            self._cs_curve_toe,
            self._cs_curve_ball,
            self._cs_curve_arch,
            self._cs_curve_waist,
            self._cs_curve_heel,
        ]

        # Filter out empty GUIDs and collect actual curve geometry
        curves = []
        for curve_id in cs_curves:
            if curve_id != Guid.Empty:
                obj = doc.Objects.Find(curve_id)
                if obj and isinstance(obj.Geometry, Curve):
                    curves.append(obj.Geometry)

        if len(curves) < 3:
            return

        # Create the main body via lofting
        tolerance = doc.ModelAbsoluteTolerance
        loft_type = Rhino.Geometry.LoftType.Normal
        breps = Brep.CreateFromLoft(curves, Point3d.Unset, Point3d.Unset,
                                     loft_type, False)
        if breps and len(breps) > 0:
            main_brep = breps[0]

            # Cap the ends
            capped = main_brep.CapPlanarHoles(tolerance)
            if capped:
                main_brep = capped

            self._body_main = doc.Objects.AddBrep(main_brep)

        # Add shell if needed
        if self._shell_type != Insert.SHELL_TYPE_NONE and self._body_main != Guid.Empty:
            self._design_shell_body(doc)

        # Add top cover if needed
        if self._has_top_cover and self._body_main != Guid.Empty:
            self._design_top_cover_body(doc)

        # Add posting if needed
        if self._has_posting and self._body_main != Guid.Empty:
            self._design_posting_body(doc)

        # Add met pad if needed
        if self._has_metatarsal_pad and self._body_main != Guid.Empty:
            self._design_met_pad_body(doc)

        # Add heel pad if needed
        if self._has_heel_pad and self._body_main != Guid.Empty:
            self._design_heel_pad_body(doc)

    def _design_shell_body(self, doc):
        """Create the shell body by offsetting the main body inward."""
        pass

    def _design_top_cover_body(self, doc):
        """Create the top cover body."""
        pass

    def _design_posting_body(self, doc):
        """Create the posting body."""
        pass

    def _design_met_pad_body(self, doc):
        """Create the metatarsal pad body."""
        pass

    def _design_heel_pad_body(self, doc):
        """Create the heel pad body."""
        pass

    # =========================================================================
    # Sandal Design Methods
    # =========================================================================

    def DesignSandalCurves(self, last, doc):
        """Design all sandal-specific curves.

        Creates outline, contour, toe bar, arch cookie, heel cup,
        and rocker curves for sandal inserts.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        if not self._is_sandal:
            return

        # Sandal outline is wider than standard insert
        # Uses last bottom line with additional offset
        self._design_sandal_outline(last, doc)
        self._design_sandal_contour(last, doc)
        self._design_sandal_toe_bar(last, doc)
        self._design_sandal_arch_cookie(last, doc)
        self._design_sandal_heel_cup(last, doc)

        if abs(self._sandal_rocker_angle) > 0.01:
            self._design_sandal_rocker(last, doc)

    def _design_sandal_outline(self, last, doc):
        """Create the sandal outline curve."""
        pass

    def _design_sandal_contour(self, last, doc):
        """Create the sandal top contour curve."""
        pass

    def _design_sandal_toe_bar(self, last, doc):
        """Create the sandal toe bar curve."""
        pass

    def _design_sandal_arch_cookie(self, last, doc):
        """Create the sandal arch cookie curve."""
        pass

    def _design_sandal_heel_cup(self, last, doc):
        """Create the sandal heel cup curve."""
        pass

    def _design_sandal_rocker(self, last, doc):
        """Create the sandal rocker curve."""
        pass

    def DesignSandalBody(self, last, doc):
        """Design the complete sandal body.

        Creates the sandal base block and then adds contour, toe bar,
        arch cookie, and heel cup features.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        if not self._is_sandal:
            return

        # Create base sandal block from outline curve extruded to sandal_thickness
        if self._sandal_outline_curve == Guid.Empty:
            return

        outline_obj = doc.Objects.Find(self._sandal_outline_curve)
        if outline_obj is None:
            return

        outline = outline_obj.Geometry
        if not isinstance(outline, Curve) or not outline.IsClosed:
            return

        tolerance = doc.ModelAbsoluteTolerance

        # Extrude the outline downward to create the base block
        extrusion_vec = Vector3d(0, 0, -self._sandal_thickness)
        extrusion = Rhino.Geometry.Extrusion.Create(
            outline, -self._sandal_thickness, True
        )
        if extrusion:
            base_brep = extrusion.ToBrep()
            if base_brep:
                self._sandal_body_base = doc.Objects.AddBrep(base_brep)

        # Add contour to top surface
        if self._sandal_contour_curve != Guid.Empty:
            contour_obj = doc.Objects.Find(self._sandal_contour_curve)
            if contour_obj and isinstance(contour_obj.Geometry, Curve):
                # Project contour onto top surface and create raised feature
                pass

        # Add toe bar
        if self._sandal_toe_bar_curve != Guid.Empty:
            pass

        # Add arch cookie
        if self._sandal_arch_cookie_curve != Guid.Empty:
            pass

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
    def Notes(self):
        return self._notes

    @Notes.setter
    def Notes(self, value):
        self._notes = str(value)

    @property
    def LastName(self):
        return self._last_name

    @LastName.setter
    def LastName(self, value):
        self._last_name = str(value)

    # =========================================================================
    # Properties - Type and Style
    # =========================================================================

    @property
    def InsertType(self):
        return self._insert_type

    @InsertType.setter
    def InsertType(self, value):
        self._insert_type = str(value)

    @property
    def ShellType(self):
        return self._shell_type

    @ShellType.setter
    def ShellType(self, value):
        self._shell_type = str(value)

    @property
    def TopCoverType(self):
        return self._top_cover_type

    @TopCoverType.setter
    def TopCoverType(self, value):
        self._top_cover_type = str(value)

    @property
    def PostingType(self):
        return self._posting_type

    @PostingType.setter
    def PostingType(self, value):
        self._posting_type = str(value)

    @property
    def ArchSupportType(self):
        return self._arch_support_type

    @ArchSupportType.setter
    def ArchSupportType(self, value):
        self._arch_support_type = str(value)

    # =========================================================================
    # Properties - Length Parameters
    # =========================================================================

    @property
    def Length(self):
        return self._length

    @Length.setter
    def Length(self, value):
        self._length = float(value)

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

    @property
    def TrimLineLength(self):
        return self._trim_line_length

    @TrimLineLength.setter
    def TrimLineLength(self, value):
        self._trim_line_length = float(value)

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
    def WaistLength(self):
        return self._waist_length

    @WaistLength.setter
    def WaistLength(self, value):
        self._waist_length = float(value)

    @property
    def InstepLength(self):
        return self._instep_length

    @InstepLength.setter
    def InstepLength(self, value):
        self._instep_length = float(value)

    @property
    def HeelLength(self):
        return self._heel_length

    @HeelLength.setter
    def HeelLength(self, value):
        self._heel_length = float(value)

    @property
    def ThreeQuarterLength(self):
        return self._three_quarter_length

    @ThreeQuarterLength.setter
    def ThreeQuarterLength(self, value):
        self._three_quarter_length = float(value)

    # =========================================================================
    # Properties - Length Multipliers
    # =========================================================================

    @property
    def ForefootLengthMult(self):
        return self._forefoot_length_mult

    @ForefootLengthMult.setter
    def ForefootLengthMult(self, value):
        self._forefoot_length_mult = float(value)

    @property
    def MidfootLengthMult(self):
        return self._midfoot_length_mult

    @MidfootLengthMult.setter
    def MidfootLengthMult(self, value):
        self._midfoot_length_mult = float(value)

    @property
    def RearfootLengthMult(self):
        return self._rearfoot_length_mult

    @RearfootLengthMult.setter
    def RearfootLengthMult(self, value):
        self._rearfoot_length_mult = float(value)

    @property
    def BallLineLengthMult(self):
        return self._ball_line_length_mult

    @BallLineLengthMult.setter
    def BallLineLengthMult(self, value):
        self._ball_line_length_mult = float(value)

    @property
    def ArchLengthMult(self):
        return self._arch_length_mult

    @ArchLengthMult.setter
    def ArchLengthMult(self, value):
        self._arch_length_mult = float(value)

    @property
    def WaistLengthMult(self):
        return self._waist_length_mult

    @WaistLengthMult.setter
    def WaistLengthMult(self, value):
        self._waist_length_mult = float(value)

    @property
    def InstepLengthMult(self):
        return self._instep_length_mult

    @InstepLengthMult.setter
    def InstepLengthMult(self, value):
        self._instep_length_mult = float(value)

    @property
    def ThreeQuarterLengthMult(self):
        return self._three_quarter_length_mult

    @ThreeQuarterLengthMult.setter
    def ThreeQuarterLengthMult(self, value):
        self._three_quarter_length_mult = float(value)

    # =========================================================================
    # Properties - Width Parameters
    # =========================================================================

    @property
    def BallWidth(self):
        return self._ball_width

    @BallWidth.setter
    def BallWidth(self, value):
        self._ball_width = float(value)

    @property
    def HeelWidth(self):
        return self._heel_width

    @HeelWidth.setter
    def HeelWidth(self, value):
        self._heel_width = float(value)

    @property
    def WaistWidth(self):
        return self._waist_width

    @WaistWidth.setter
    def WaistWidth(self, value):
        self._waist_width = float(value)

    @property
    def ArchWidth(self):
        return self._arch_width

    @ArchWidth.setter
    def ArchWidth(self, value):
        self._arch_width = float(value)

    @property
    def ToeWidth(self):
        return self._toe_width

    @ToeWidth.setter
    def ToeWidth(self, value):
        self._toe_width = float(value)

    @property
    def TrimWidthLateral(self):
        return self._trim_width_lateral

    @TrimWidthLateral.setter
    def TrimWidthLateral(self, value):
        self._trim_width_lateral = float(value)

    @property
    def TrimWidthMedial(self):
        return self._trim_width_medial

    @TrimWidthMedial.setter
    def TrimWidthMedial(self, value):
        self._trim_width_medial = float(value)

    @property
    def FlangeWidthLateral(self):
        return self._flange_width_lateral

    @FlangeWidthLateral.setter
    def FlangeWidthLateral(self, value):
        self._flange_width_lateral = float(value)

    @property
    def FlangeWidthMedial(self):
        return self._flange_width_medial

    @FlangeWidthMedial.setter
    def FlangeWidthMedial(self, value):
        self._flange_width_medial = float(value)

    @property
    def FlangeWidthHeel(self):
        return self._flange_width_heel

    @FlangeWidthHeel.setter
    def FlangeWidthHeel(self, value):
        self._flange_width_heel = float(value)

    # =========================================================================
    # Properties - Width Multipliers
    # =========================================================================

    @property
    def BallWidthMult(self):
        return self._ball_width_mult

    @BallWidthMult.setter
    def BallWidthMult(self, value):
        self._ball_width_mult = float(value)

    @property
    def HeelWidthMult(self):
        return self._heel_width_mult

    @HeelWidthMult.setter
    def HeelWidthMult(self, value):
        self._heel_width_mult = float(value)

    @property
    def WaistWidthMult(self):
        return self._waist_width_mult

    @WaistWidthMult.setter
    def WaistWidthMult(self, value):
        self._waist_width_mult = float(value)

    @property
    def ArchWidthMult(self):
        return self._arch_width_mult

    @ArchWidthMult.setter
    def ArchWidthMult(self, value):
        self._arch_width_mult = float(value)

    @property
    def ToeWidthMult(self):
        return self._toe_width_mult

    @ToeWidthMult.setter
    def ToeWidthMult(self, value):
        self._toe_width_mult = float(value)

    # =========================================================================
    # Properties - Thickness Parameters
    # =========================================================================

    @property
    def ThicknessToe(self):
        return self._thickness_toe

    @ThicknessToe.setter
    def ThicknessToe(self, value):
        self._thickness_toe = float(value)

    @property
    def ThicknessBall(self):
        return self._thickness_ball

    @ThicknessBall.setter
    def ThicknessBall(self, value):
        self._thickness_ball = float(value)

    @property
    def ThicknessArch(self):
        return self._thickness_arch

    @ThicknessArch.setter
    def ThicknessArch(self, value):
        self._thickness_arch = float(value)

    @property
    def ThicknessWaist(self):
        return self._thickness_waist

    @ThicknessWaist.setter
    def ThicknessWaist(self, value):
        self._thickness_waist = float(value)

    @property
    def ThicknessHeel(self):
        return self._thickness_heel

    @ThicknessHeel.setter
    def ThicknessHeel(self, value):
        self._thickness_heel = float(value)

    @property
    def ThicknessHeelCenter(self):
        return self._thickness_heel_center

    @ThicknessHeelCenter.setter
    def ThicknessHeelCenter(self, value):
        self._thickness_heel_center = float(value)

    @property
    def ThicknessTopCover(self):
        return self._thickness_top_cover

    @ThicknessTopCover.setter
    def ThicknessTopCover(self, value):
        self._thickness_top_cover = float(value)

    @property
    def ThicknessShell(self):
        return self._thickness_shell

    @ThicknessShell.setter
    def ThicknessShell(self, value):
        self._thickness_shell = float(value)

    @property
    def ThicknessPosting(self):
        return self._thickness_posting

    @ThicknessPosting.setter
    def ThicknessPosting(self, value):
        self._thickness_posting = float(value)

    @property
    def ThicknessMetatarsalPad(self):
        return self._thickness_metatarsal_pad

    @ThicknessMetatarsalPad.setter
    def ThicknessMetatarsalPad(self, value):
        self._thickness_metatarsal_pad = float(value)

    @property
    def ThicknessHeelPad(self):
        return self._thickness_heel_pad

    @ThicknessHeelPad.setter
    def ThicknessHeelPad(self, value):
        self._thickness_heel_pad = float(value)

    @property
    def ThicknessForefootExtension(self):
        return self._thickness_forefoot_extension

    @ThicknessForefootExtension.setter
    def ThicknessForefootExtension(self, value):
        self._thickness_forefoot_extension = float(value)

    # =========================================================================
    # Properties - Height/Depth Parameters
    # =========================================================================

    @property
    def ArchHeight(self):
        return self._arch_height

    @ArchHeight.setter
    def ArchHeight(self, value):
        self._arch_height = float(value)

    @property
    def HeelCupDepth(self):
        return self._heel_cup_depth

    @HeelCupDepth.setter
    def HeelCupDepth(self, value):
        self._heel_cup_depth = float(value)

    @property
    def HeelCupDepthLateral(self):
        return self._heel_cup_depth_lateral

    @HeelCupDepthLateral.setter
    def HeelCupDepthLateral(self, value):
        self._heel_cup_depth_lateral = float(value)

    @property
    def HeelCupDepthMedial(self):
        return self._heel_cup_depth_medial

    @HeelCupDepthMedial.setter
    def HeelCupDepthMedial(self, value):
        self._heel_cup_depth_medial = float(value)

    @property
    def MetatarsalDomeHeight(self):
        return self._metatarsal_dome_height

    @MetatarsalDomeHeight.setter
    def MetatarsalDomeHeight(self, value):
        self._metatarsal_dome_height = float(value)

    @property
    def HeelLift(self):
        return self._heel_lift

    @HeelLift.setter
    def HeelLift(self, value):
        self._heel_lift = float(value)

    @property
    def ForefootWedgeHeight(self):
        return self._forefoot_wedge_height

    @ForefootWedgeHeight.setter
    def ForefootWedgeHeight(self, value):
        self._forefoot_wedge_height = float(value)

    @property
    def RearfootWedgeHeight(self):
        return self._rearfoot_wedge_height

    @RearfootWedgeHeight.setter
    def RearfootWedgeHeight(self, value):
        self._rearfoot_wedge_height = float(value)

    @property
    def MedialSkiveDepth(self):
        return self._medial_skive_depth

    @MedialSkiveDepth.setter
    def MedialSkiveDepth(self, value):
        self._medial_skive_depth = float(value)

    @property
    def LateralSkiveDepth(self):
        return self._lateral_skive_depth

    @LateralSkiveDepth.setter
    def LateralSkiveDepth(self, value):
        self._lateral_skive_depth = float(value)

    # =========================================================================
    # Properties - Angle Parameters
    # =========================================================================

    @property
    def ForefootPostingAngle(self):
        return self._forefoot_posting_angle

    @ForefootPostingAngle.setter
    def ForefootPostingAngle(self, value):
        self._forefoot_posting_angle = float(value)

    @property
    def RearfootPostingAngle(self):
        return self._rearfoot_posting_angle

    @RearfootPostingAngle.setter
    def RearfootPostingAngle(self, value):
        self._rearfoot_posting_angle = float(value)

    @property
    def MedialSkiveAngle(self):
        return self._medial_skive_angle

    @MedialSkiveAngle.setter
    def MedialSkiveAngle(self, value):
        self._medial_skive_angle = float(value)

    @property
    def LateralSkiveAngle(self):
        return self._lateral_skive_angle

    @LateralSkiveAngle.setter
    def LateralSkiveAngle(self, value):
        self._lateral_skive_angle = float(value)

    @property
    def HeelCupFlareAngle(self):
        return self._heel_cup_flare_angle

    @HeelCupFlareAngle.setter
    def HeelCupFlareAngle(self, value):
        self._heel_cup_flare_angle = float(value)

    @property
    def ArchFillAngle(self):
        return self._arch_fill_angle

    @ArchFillAngle.setter
    def ArchFillAngle(self, value):
        self._arch_fill_angle = float(value)

    @property
    def InversionAngle(self):
        return self._inversion_angle

    @InversionAngle.setter
    def InversionAngle(self, value):
        self._inversion_angle = float(value)

    @property
    def EversionAngle(self):
        return self._eversion_angle

    @EversionAngle.setter
    def EversionAngle(self, value):
        self._eversion_angle = float(value)

    @property
    def BlakeInvertedAngle(self):
        return self._blake_inverted_angle

    @BlakeInvertedAngle.setter
    def BlakeInvertedAngle(self, value):
        self._blake_inverted_angle = float(value)

    # =========================================================================
    # Properties - Offset Parameters
    # =========================================================================

    @property
    def OffsetFromLastSurface(self):
        return self._offset_from_last_surface

    @OffsetFromLastSurface.setter
    def OffsetFromLastSurface(self, value):
        self._offset_from_last_surface = float(value)

    @property
    def OffsetBallLateral(self):
        return self._offset_ball_lateral

    @OffsetBallLateral.setter
    def OffsetBallLateral(self, value):
        self._offset_ball_lateral = float(value)

    @property
    def OffsetBallMedial(self):
        return self._offset_ball_medial

    @OffsetBallMedial.setter
    def OffsetBallMedial(self, value):
        self._offset_ball_medial = float(value)

    @property
    def OffsetHeelLateral(self):
        return self._offset_heel_lateral

    @OffsetHeelLateral.setter
    def OffsetHeelLateral(self, value):
        self._offset_heel_lateral = float(value)

    @property
    def OffsetHeelMedial(self):
        return self._offset_heel_medial

    @OffsetHeelMedial.setter
    def OffsetHeelMedial(self, value):
        self._offset_heel_medial = float(value)

    @property
    def OffsetArchLateral(self):
        return self._offset_arch_lateral

    @OffsetArchLateral.setter
    def OffsetArchLateral(self, value):
        self._offset_arch_lateral = float(value)

    @property
    def OffsetArchMedial(self):
        return self._offset_arch_medial

    @OffsetArchMedial.setter
    def OffsetArchMedial(self, value):
        self._offset_arch_medial = float(value)

    @property
    def OffsetWaistLateral(self):
        return self._offset_waist_lateral

    @OffsetWaistLateral.setter
    def OffsetWaistLateral(self, value):
        self._offset_waist_lateral = float(value)

    @property
    def OffsetWaistMedial(self):
        return self._offset_waist_medial

    @OffsetWaistMedial.setter
    def OffsetWaistMedial(self, value):
        self._offset_waist_medial = float(value)

    # =========================================================================
    # Properties - Feature Flags
    # =========================================================================

    @property
    def HasMetatarsalPad(self):
        return self._has_metatarsal_pad

    @HasMetatarsalPad.setter
    def HasMetatarsalPad(self, value):
        self._has_metatarsal_pad = bool(value)

    @property
    def HasHeelPad(self):
        return self._has_heel_pad

    @HasHeelPad.setter
    def HasHeelPad(self, value):
        self._has_heel_pad = bool(value)

    @property
    def HasForefootExtension(self):
        return self._has_forefoot_extension

    @HasForefootExtension.setter
    def HasForefootExtension(self, value):
        self._has_forefoot_extension = bool(value)

    @property
    def HasHeelLift(self):
        return self._has_heel_lift

    @HasHeelLift.setter
    def HasHeelLift(self, value):
        self._has_heel_lift = bool(value)

    @property
    def HasMedialFlange(self):
        return self._has_medial_flange

    @HasMedialFlange.setter
    def HasMedialFlange(self, value):
        self._has_medial_flange = bool(value)

    @property
    def HasLateralFlange(self):
        return self._has_lateral_flange

    @HasLateralFlange.setter
    def HasLateralFlange(self, value):
        self._has_lateral_flange = bool(value)

    @property
    def HasHeelFlange(self):
        return self._has_heel_flange

    @HasHeelFlange.setter
    def HasHeelFlange(self, value):
        self._has_heel_flange = bool(value)

    @property
    def HasArchFill(self):
        return self._has_arch_fill

    @HasArchFill.setter
    def HasArchFill(self, value):
        self._has_arch_fill = bool(value)

    @property
    def HasTopCover(self):
        return self._has_top_cover

    @HasTopCover.setter
    def HasTopCover(self, value):
        self._has_top_cover = bool(value)

    @property
    def HasPosting(self):
        return self._has_posting

    @HasPosting.setter
    def HasPosting(self, value):
        self._has_posting = bool(value)

    @property
    def IsSandal(self):
        return self._is_sandal

    @IsSandal.setter
    def IsSandal(self, value):
        self._is_sandal = bool(value)

    # =========================================================================
    # Properties - Sandal Parameters
    # =========================================================================

    @property
    def SandalThickness(self):
        return self._sandal_thickness

    @SandalThickness.setter
    def SandalThickness(self, value):
        self._sandal_thickness = float(value)

    @property
    def SandalEdgeRadius(self):
        return self._sandal_edge_radius

    @SandalEdgeRadius.setter
    def SandalEdgeRadius(self, value):
        self._sandal_edge_radius = float(value)

    @property
    def SandalToeBarHeight(self):
        return self._sandal_toe_bar_height

    @SandalToeBarHeight.setter
    def SandalToeBarHeight(self, value):
        self._sandal_toe_bar_height = float(value)

    @property
    def SandalArchCookieHeight(self):
        return self._sandal_arch_cookie_height

    @SandalArchCookieHeight.setter
    def SandalArchCookieHeight(self, value):
        self._sandal_arch_cookie_height = float(value)

    @property
    def SandalHeelCupDepth(self):
        return self._sandal_heel_cup_depth

    @SandalHeelCupDepth.setter
    def SandalHeelCupDepth(self, value):
        self._sandal_heel_cup_depth = float(value)

    @property
    def SandalContourDepth(self):
        return self._sandal_contour_depth

    @SandalContourDepth.setter
    def SandalContourDepth(self, value):
        self._sandal_contour_depth = float(value)

    @property
    def SandalRockerAngle(self):
        return self._sandal_rocker_angle

    @SandalRockerAngle.setter
    def SandalRockerAngle(self, value):
        self._sandal_rocker_angle = float(value)

    # =========================================================================
    # Properties - Metatarsal Pad Parameters
    # =========================================================================

    @property
    def MetPadPositionX(self):
        return self._met_pad_position_x

    @MetPadPositionX.setter
    def MetPadPositionX(self, value):
        self._met_pad_position_x = float(value)

    @property
    def MetPadPositionY(self):
        return self._met_pad_position_y

    @MetPadPositionY.setter
    def MetPadPositionY(self, value):
        self._met_pad_position_y = float(value)

    @property
    def MetPadWidth(self):
        return self._met_pad_width

    @MetPadWidth.setter
    def MetPadWidth(self, value):
        self._met_pad_width = float(value)

    @property
    def MetPadLength(self):
        return self._met_pad_length

    @MetPadLength.setter
    def MetPadLength(self, value):
        self._met_pad_length = float(value)

    @property
    def MetPadHeight(self):
        return self._met_pad_height

    @MetPadHeight.setter
    def MetPadHeight(self, value):
        self._met_pad_height = float(value)

    @property
    def MetPadShape(self):
        return self._met_pad_shape

    @MetPadShape.setter
    def MetPadShape(self, value):
        self._met_pad_shape = str(value)

    # =========================================================================
    # Properties - Heel Pad Parameters
    # =========================================================================

    @property
    def HeelPadWidth(self):
        return self._heel_pad_width

    @HeelPadWidth.setter
    def HeelPadWidth(self, value):
        self._heel_pad_width = float(value)

    @property
    def HeelPadLength(self):
        return self._heel_pad_length

    @HeelPadLength.setter
    def HeelPadLength(self, value):
        self._heel_pad_length = float(value)

    @property
    def HeelPadDepth(self):
        return self._heel_pad_depth

    @HeelPadDepth.setter
    def HeelPadDepth(self, value):
        self._heel_pad_depth = float(value)

    @property
    def HeelPadShape(self):
        return self._heel_pad_shape

    @HeelPadShape.setter
    def HeelPadShape(self, value):
        self._heel_pad_shape = str(value)

    # =========================================================================
    # Properties - Geometry IDs (Design Curves)
    # =========================================================================

    @property
    def OutlineCurve(self):
        return self._outline_curve

    @OutlineCurve.setter
    def OutlineCurve(self, value):
        self._outline_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def OutlineCurveLateral(self):
        return self._outline_curve_lateral

    @OutlineCurveLateral.setter
    def OutlineCurveLateral(self, value):
        self._outline_curve_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def OutlineCurveMedial(self):
        return self._outline_curve_medial

    @OutlineCurveMedial.setter
    def OutlineCurveMedial(self, value):
        self._outline_curve_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def TrimCurve(self):
        return self._trim_curve

    @TrimCurve.setter
    def TrimCurve(self, value):
        self._trim_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def TrimCurveLateral(self):
        return self._trim_curve_lateral

    @TrimCurveLateral.setter
    def TrimCurveLateral(self, value):
        self._trim_curve_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def TrimCurveMedial(self):
        return self._trim_curve_medial

    @TrimCurveMedial.setter
    def TrimCurveMedial(self, value):
        self._trim_curve_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelCupCurve(self):
        return self._heel_cup_curve

    @HeelCupCurve.setter
    def HeelCupCurve(self, value):
        self._heel_cup_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelCupCurveLateral(self):
        return self._heel_cup_curve_lateral

    @HeelCupCurveLateral.setter
    def HeelCupCurveLateral(self, value):
        self._heel_cup_curve_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelCupCurveMedial(self):
        return self._heel_cup_curve_medial

    @HeelCupCurveMedial.setter
    def HeelCupCurveMedial(self, value):
        self._heel_cup_curve_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def ArchCurve(self):
        return self._arch_curve

    @ArchCurve.setter
    def ArchCurve(self, value):
        self._arch_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def FlangeCurveLateral(self):
        return self._flange_curve_lateral

    @FlangeCurveLateral.setter
    def FlangeCurveLateral(self, value):
        self._flange_curve_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def FlangeCurveMedial(self):
        return self._flange_curve_medial

    @FlangeCurveMedial.setter
    def FlangeCurveMedial(self, value):
        self._flange_curve_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def FlangeCurveHeel(self):
        return self._flange_curve_heel

    @FlangeCurveHeel.setter
    def FlangeCurveHeel(self, value):
        self._flange_curve_heel = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CenterLine(self):
        return self._center_line

    @CenterLine.setter
    def CenterLine(self, value):
        self._center_line = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BottomLine(self):
        return self._bottom_line

    @BottomLine.setter
    def BottomLine(self, value):
        self._bottom_line = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def TopLine(self):
        return self._top_line

    @TopLine.setter
    def TopLine(self, value):
        self._top_line = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def MetPadCurve(self):
        return self._met_pad_curve

    @MetPadCurve.setter
    def MetPadCurve(self, value):
        self._met_pad_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelPadCurve(self):
        return self._heel_pad_curve

    @HeelPadCurve.setter
    def HeelPadCurve(self, value):
        self._heel_pad_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def ForefootExtensionCurve(self):
        return self._forefoot_extension_curve

    @ForefootExtensionCurve.setter
    def ForefootExtensionCurve(self, value):
        self._forefoot_extension_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def PostingBoundaryCurve(self):
        return self._posting_boundary_curve

    @PostingBoundaryCurve.setter
    def PostingBoundaryCurve(self, value):
        self._posting_boundary_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Cross Section Curve IDs
    # =========================================================================

    @property
    def CSCurveBall(self):
        return self._cs_curve_ball

    @CSCurveBall.setter
    def CSCurveBall(self, value):
        self._cs_curve_ball = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSCurveArch(self):
        return self._cs_curve_arch

    @CSCurveArch.setter
    def CSCurveArch(self, value):
        self._cs_curve_arch = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSCurveWaist(self):
        return self._cs_curve_waist

    @CSCurveWaist.setter
    def CSCurveWaist(self, value):
        self._cs_curve_waist = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSCurveHeel(self):
        return self._cs_curve_heel

    @CSCurveHeel.setter
    def CSCurveHeel(self, value):
        self._cs_curve_heel = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSCurveToe(self):
        return self._cs_curve_toe

    @CSCurveToe.setter
    def CSCurveToe(self, value):
        self._cs_curve_toe = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSCurveInstep(self):
        return self._cs_curve_instep

    @CSCurveInstep.setter
    def CSCurveInstep(self, value):
        self._cs_curve_instep = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSCurveThreeQuarter(self):
        return self._cs_curve_three_quarter

    @CSCurveThreeQuarter.setter
    def CSCurveThreeQuarter(self, value):
        self._cs_curve_three_quarter = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Surface IDs
    # =========================================================================

    @property
    def SurfaceTop(self):
        return self._surface_top

    @SurfaceTop.setter
    def SurfaceTop(self, value):
        self._surface_top = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceBottom(self):
        return self._surface_bottom

    @SurfaceBottom.setter
    def SurfaceBottom(self, value):
        self._surface_bottom = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceShell(self):
        return self._surface_shell

    @SurfaceShell.setter
    def SurfaceShell(self, value):
        self._surface_shell = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceTopCover(self):
        return self._surface_top_cover

    @SurfaceTopCover.setter
    def SurfaceTopCover(self, value):
        self._surface_top_cover = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfacePosting(self):
        return self._surface_posting

    @SurfacePosting.setter
    def SurfacePosting(self, value):
        self._surface_posting = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceTrim(self):
        return self._surface_trim

    @SurfaceTrim.setter
    def SurfaceTrim(self, value):
        self._surface_trim = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Body Geometry IDs
    # =========================================================================

    @property
    def BodyMain(self):
        return self._body_main

    @BodyMain.setter
    def BodyMain(self, value):
        self._body_main = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyMainSubD(self):
        return self._body_main_subd

    @BodyMainSubD.setter
    def BodyMainSubD(self, value):
        self._body_main_subd = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyShell(self):
        return self._body_shell

    @BodyShell.setter
    def BodyShell(self, value):
        self._body_shell = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyTopCover(self):
        return self._body_top_cover

    @BodyTopCover.setter
    def BodyTopCover(self, value):
        self._body_top_cover = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyPosting(self):
        return self._body_posting

    @BodyPosting.setter
    def BodyPosting(self, value):
        self._body_posting = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyMetPad(self):
        return self._body_met_pad

    @BodyMetPad.setter
    def BodyMetPad(self, value):
        self._body_met_pad = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyHeelPad(self):
        return self._body_heel_pad

    @BodyHeelPad.setter
    def BodyHeelPad(self, value):
        self._body_heel_pad = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyForefootExtension(self):
        return self._body_forefoot_extension

    @BodyForefootExtension.setter
    def BodyForefootExtension(self, value):
        self._body_forefoot_extension = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodySandal(self):
        return self._body_sandal

    @BodySandal.setter
    def BodySandal(self, value):
        self._body_sandal = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyMesh(self):
        return self._body_mesh

    @BodyMesh.setter
    def BodyMesh(self, value):
        self._body_mesh = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Last Surface References
    # =========================================================================

    @property
    def LastSurfaceTrimmed(self):
        return self._last_surface_trimmed

    @LastSurfaceTrimmed.setter
    def LastSurfaceTrimmed(self, value):
        self._last_surface_trimmed = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def LastSurfaceOriginal(self):
        return self._last_surface_original

    @LastSurfaceOriginal.setter
    def LastSurfaceOriginal(self, value):
        self._last_surface_original = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Key Points
    # =========================================================================

    @property
    def BallPoint(self):
        return self._ball_point

    @BallPoint.setter
    def BallPoint(self, value):
        self._ball_point = value

    @property
    def HeelPoint(self):
        return self._heel_point

    @HeelPoint.setter
    def HeelPoint(self, value):
        self._heel_point = value

    @property
    def ToePoint(self):
        return self._toe_point

    @ToePoint.setter
    def ToePoint(self, value):
        self._toe_point = value

    @property
    def ArchPoint(self):
        return self._arch_point

    @ArchPoint.setter
    def ArchPoint(self, value):
        self._arch_point = value

    @property
    def WaistPoint(self):
        return self._waist_point

    @WaistPoint.setter
    def WaistPoint(self, value):
        self._waist_point = value

    @property
    def InstepPoint(self):
        return self._instep_point

    @InstepPoint.setter
    def InstepPoint(self, value):
        self._instep_point = value

    @property
    def MetPadCenter(self):
        return self._met_pad_center

    @MetPadCenter.setter
    def MetPadCenter(self, value):
        self._met_pad_center = value

    @property
    def HeelPadCenter(self):
        return self._heel_pad_center

    @HeelPadCenter.setter
    def HeelPadCenter(self, value):
        self._heel_pad_center = value

    # =========================================================================
    # Properties - Style Parameter Dictionary
    # =========================================================================

    @property
    def InsertStyleParameterDictionary(self):
        return self._insert_style_parameter_dictionary

    @InsertStyleParameterDictionary.setter
    def InsertStyleParameterDictionary(self, value):
        self._insert_style_parameter_dictionary = dict(value) if value else {}

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_json(self):
        """Serialize this Insert to a JSON string."""
        return json.dumps(self.CollectInsertParameters(), indent=2, default=str)

    @staticmethod
    def from_json(json_string):
        """Deserialize an Insert from a JSON string."""
        insert = Insert()
        if isinstance(json_string, str):
            data = json.loads(json_string)
        else:
            data = json_string

        key_map = {
            "Name": "_name", "Side": "_side", "Notes": "_notes",
            "InsertType": "_insert_type", "ShellType": "_shell_type",
            "TopCoverType": "_top_cover_type", "PostingType": "_posting_type",
            "ArchSupportType": "_arch_support_type", "LastName": "_last_name",
            "Length": "_length", "BallLineLength": "_ball_line_length",
            "BallWidth": "_ball_width", "HeelWidth": "_heel_width",
            "ThicknessToe": "_thickness_toe", "ThicknessBall": "_thickness_ball",
            "ThicknessArch": "_thickness_arch", "ThicknessHeel": "_thickness_heel",
            "ArchHeight": "_arch_height", "HeelCupDepth": "_heel_cup_depth",
            "ForefootPostingAngle": "_forefoot_posting_angle",
            "RearfootPostingAngle": "_rearfoot_posting_angle",
            "HasMetatarsalPad": "_has_metatarsal_pad",
            "HasHeelPad": "_has_heel_pad",
            "IsSandal": "_is_sandal",
        }
        for json_key, attr_name in key_map.items():
            if json_key in data:
                setattr(insert, attr_name, data[json_key])

        if "InsertStyleParameterDictionary" in data:
            insert._insert_style_parameter_dictionary = data["InsertStyleParameterDictionary"]

        return insert

    def __repr__(self):
        return (
            f'Insert(name="{self._name}", side="{self._side}", '
            f'type="{self._insert_type}", '
            f'length={self._length:.1f})'
        )
