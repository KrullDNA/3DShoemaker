"""
Bottom (sole/heel/support) data model for 3DShoemaker Rhino 8 Python plugin.

The Bottom class represents the sole, heel, and support components of footwear.
It includes parameters for outsole, midsole, heel block, platform, and wedge
configurations with full design curve and body generation capabilities.

Port of PodoCAD .NET Bottom class to Python 3.
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


class Bottom:
    """Represents the sole/heel/support structure with all parameters, curves, and bodies."""

    # -------------------------------------------------------------------------
    # Bottom type enumerations
    # -------------------------------------------------------------------------
    BOTTOM_TYPE_FLAT = "Flat"
    BOTTOM_TYPE_WEDGE = "Wedge"
    BOTTOM_TYPE_HEEL = "Heel"
    BOTTOM_TYPE_PLATFORM = "Platform"
    BOTTOM_TYPE_NEGATIVE_HEEL = "NegativeHeel"

    # Sole type enumerations
    SOLE_TYPE_FLAT = "Flat"
    SOLE_TYPE_ROCKER = "Rocker"
    SOLE_TYPE_THOMAS = "Thomas"
    SOLE_TYPE_REVERSE_THOMAS = "ReverseThomas"
    SOLE_TYPE_METATARSAL_BAR = "MetatarsalBar"
    SOLE_TYPE_ROCKER_BAR = "RockerBar"

    # Heel type enumerations
    HEEL_TYPE_STANDARD = "Standard"
    HEEL_TYPE_CUBAN = "Cuban"
    HEEL_TYPE_STILETTO = "Stiletto"
    HEEL_TYPE_BLOCK = "Block"
    HEEL_TYPE_WEDGE = "Wedge"
    HEEL_TYPE_STACKED = "Stacked"
    HEEL_TYPE_LOUIS = "Louis"
    HEEL_TYPE_KITTEN = "Kitten"

    # Support type enumerations
    SUPPORT_TYPE_NONE = "None"
    SUPPORT_TYPE_SHANK = "Shank"
    SUPPORT_TYPE_PLATE = "Plate"
    SUPPORT_TYPE_SPRING = "Spring"

    # Tread pattern enumerations
    TREAD_PATTERN_SMOOTH = "Smooth"
    TREAD_PATTERN_LUG = "Lug"
    TREAD_PATTERN_HERRINGBONE = "Herringbone"
    TREAD_PATTERN_WAFFLE = "Waffle"
    TREAD_PATTERN_CUSTOM = "Custom"

    def __init__(self):
        """Initialize a Bottom with default parameter values."""
        # --- Identification ---
        self._name = ""
        self._side = "Right"
        self._notes = ""

        # --- Type and Style ---
        self._bottom_type = Bottom.BOTTOM_TYPE_FLAT
        self._sole_type = Bottom.SOLE_TYPE_FLAT
        self._heel_type = Bottom.HEEL_TYPE_STANDARD
        self._support_type = Bottom.SUPPORT_TYPE_SHANK
        self._tread_pattern = Bottom.TREAD_PATTERN_SMOOTH

        # --- Reference to parent Last ---
        self._last_name = ""

        # --- Overall Dimensions ---
        self._length = 270.0
        self._ball_line_length = 189.0
        self._ball_width = 95.0
        self._heel_width = 65.0
        self._waist_width = 55.0

        # --- Sole Parameters ---
        self._sole_thickness_toe = 8.0
        self._sole_thickness_ball = 10.0
        self._sole_thickness_waist = 10.0
        self._sole_thickness_heel = 12.0
        self._sole_thickness_arch = 10.0
        self._sole_thickness_center = 10.0
        self._sole_edge_width = 2.0
        self._sole_edge_angle = 0.0
        self._sole_extension_lateral = 0.0
        self._sole_extension_medial = 0.0
        self._sole_rocker_angle = 0.0
        self._sole_rocker_apex_position = 0.65
        self._sole_thomas_heel_extension = 0.0
        self._sole_metatarsal_bar_position = 0.0
        self._sole_metatarsal_bar_height = 0.0
        self._sole_metatarsal_bar_width = 0.0
        self._sole_flare_lateral = 0.0
        self._sole_flare_medial = 0.0
        self._sole_flare_heel = 0.0
        self._sole_bevel_toe = 0.0
        self._sole_bevel_heel = 0.0

        # --- Sole Multipliers ---
        self._sole_thickness_toe_mult = 0.030
        self._sole_thickness_ball_mult = 0.037
        self._sole_thickness_waist_mult = 0.037
        self._sole_thickness_heel_mult = 0.044
        self._sole_thickness_arch_mult = 0.037

        # --- Heel Parameters ---
        self._heel_height = 25.0
        self._heel_height_effective = 25.0
        self._heel_top_width = 55.0
        self._heel_top_length = 50.0
        self._heel_bottom_width = 50.0
        self._heel_bottom_length = 45.0
        self._heel_breast_angle = 5.0
        self._heel_seat_angle = 0.0
        self._heel_pitch_angle = 0.0
        self._heel_taper_lateral = 2.0
        self._heel_taper_medial = 2.0
        self._heel_taper_back = 3.0
        self._heel_corner_radius = 5.0
        self._heel_breast_curve_depth = 3.0
        self._heel_stack_count = 1
        self._heel_stack_layer_height = 0.0
        self._heel_lift_height = 0.0
        self._heel_counter_height = 0.0
        self._heel_counter_thickness = 2.0
        self._heel_rand_width = 0.0
        self._heel_rand_height = 0.0

        # --- Heel Multipliers ---
        self._heel_height_mult = 0.093
        self._heel_top_width_mult = 0.204
        self._heel_top_length_mult = 0.185
        self._heel_bottom_width_mult = 0.185
        self._heel_bottom_length_mult = 0.167

        # --- Wedge Parameters ---
        self._wedge_angle = 0.0
        self._wedge_height_front = 0.0
        self._wedge_height_back = 0.0
        self._wedge_medial_posting_angle = 0.0
        self._wedge_lateral_posting_angle = 0.0

        # --- Platform Parameters ---
        self._platform_height = 0.0
        self._platform_sole_thickness = 10.0
        self._platform_taper_toe = 0.0
        self._platform_taper_heel = 0.0
        self._platform_edge_radius = 3.0

        # --- Support (Shank/Plate) Parameters ---
        self._support_length = 0.0
        self._support_width = 0.0
        self._support_thickness = 2.0
        self._support_position_x = 0.0
        self._support_curvature = 0.5
        self._support_spring_rate = 0.0

        # --- Support Multipliers ---
        self._support_length_mult = 0.35
        self._support_width_mult = 0.15

        # --- Tread Parameters ---
        self._tread_depth = 2.0
        self._tread_spacing = 8.0
        self._tread_lug_width = 5.0
        self._tread_lug_height = 3.0
        self._tread_pattern_scale = 1.0
        self._tread_pattern_rotation = 0.0

        # --- Feather Line Parameters ---
        self._feather_line_offset = 0.0
        self._feather_line_height_toe = 0.0
        self._feather_line_height_ball = 0.0
        self._feather_line_height_waist = 0.0
        self._feather_line_height_heel = 0.0

        # --- Toe Spring and Related ---
        self._toe_spring = 15.0
        self._toe_spring_mult = 0.056
        self._toe_cap_length = 0.0
        self._toe_cap_height = 0.0
        self._toe_bumper_height = 0.0
        self._toe_bumper_length = 0.0

        # --- Bottom Line (Outline) Curve IDs ---
        self._outline_curve = Guid.Empty
        self._outline_curve_lateral = Guid.Empty
        self._outline_curve_medial = Guid.Empty
        self._outline_curve_sole = Guid.Empty
        self._outline_curve_heel = Guid.Empty

        # --- Sole Design Curve IDs ---
        self._sole_bottom_curve = Guid.Empty
        self._sole_top_curve = Guid.Empty
        self._sole_edge_curve_lateral = Guid.Empty
        self._sole_edge_curve_medial = Guid.Empty
        self._sole_center_line = Guid.Empty
        self._sole_tread_curve = Guid.Empty
        self._sole_rocker_curve = Guid.Empty
        self._sole_thomas_curve = Guid.Empty
        self._sole_met_bar_curve = Guid.Empty

        # --- Sole Cross Section Curve IDs ---
        self._sole_cs_toe = Guid.Empty
        self._sole_cs_ball = Guid.Empty
        self._sole_cs_waist = Guid.Empty
        self._sole_cs_arch = Guid.Empty
        self._sole_cs_heel = Guid.Empty

        # --- Heel Design Curve IDs ---
        self._heel_top_curve = Guid.Empty
        self._heel_bottom_curve = Guid.Empty
        self._heel_breast_curve = Guid.Empty
        self._heel_back_curve = Guid.Empty
        self._heel_lateral_curve = Guid.Empty
        self._heel_medial_curve = Guid.Empty
        self._heel_seat_curve = Guid.Empty
        self._heel_profile_curve = Guid.Empty
        self._heel_counter_curve = Guid.Empty
        self._heel_rand_curve = Guid.Empty

        # --- Support Design Curve IDs ---
        self._support_outline_curve = Guid.Empty
        self._support_profile_curve = Guid.Empty
        self._support_center_line = Guid.Empty

        # --- Surface IDs ---
        self._surface_sole_top = Guid.Empty
        self._surface_sole_bottom = Guid.Empty
        self._surface_heel_top = Guid.Empty
        self._surface_heel_bottom = Guid.Empty
        self._surface_heel_sides = Guid.Empty
        self._surface_support = Guid.Empty
        self._surface_platform = Guid.Empty
        self._surface_tread = Guid.Empty

        # --- Body Geometry IDs ---
        self._body_sole = Guid.Empty
        self._body_heel = Guid.Empty
        self._body_bottom_combined = Guid.Empty
        self._body_support = Guid.Empty
        self._body_platform = Guid.Empty
        self._body_wedge = Guid.Empty
        self._body_tread = Guid.Empty
        self._body_toe_cap = Guid.Empty
        self._body_toe_bumper = Guid.Empty
        self._body_heel_counter = Guid.Empty
        self._body_heel_rand = Guid.Empty
        self._body_mesh = Guid.Empty
        self._body_shoe = Guid.Empty

        # --- Key Points ---
        self._toe_point = Point3d.Origin
        self._ball_point = Point3d.Origin
        self._waist_point = Point3d.Origin
        self._arch_point = Point3d.Origin
        self._heel_point = Point3d.Origin
        self._heel_breast_point = Point3d.Origin
        self._heel_back_point = Point3d.Origin
        self._rocker_apex_point = Point3d.Origin

        # --- Style Parameter Dictionary ---
        self._support_style_parameter_dictionary = {}

    # =========================================================================
    # Factory / Lifecycle Methods
    # =========================================================================

    def Clone(self):
        """Create a deep copy of this Bottom instance."""
        return copy.deepcopy(self)

    @staticmethod
    def Create():
        """Create a new Bottom with default parameters."""
        bottom = Bottom()
        bottom.SetDefaultSupportStyleParameters()
        bottom.CalculateLinearMeasurementsFromMults()
        return bottom

    # =========================================================================
    # Parameter Collection Methods
    # =========================================================================

    def CollectHeelParameters(self):
        """Collect all heel parameters into a dictionary.

        Returns:
            Dictionary with heel parameter key-value pairs.
        """
        params = {}
        params["HeelType"] = self._heel_type
        params["HeelHeight"] = self._heel_height
        params["HeelHeightEffective"] = self._heel_height_effective
        params["HeelTopWidth"] = self._heel_top_width
        params["HeelTopLength"] = self._heel_top_length
        params["HeelBottomWidth"] = self._heel_bottom_width
        params["HeelBottomLength"] = self._heel_bottom_length
        params["HeelBreastAngle"] = self._heel_breast_angle
        params["HeelSeatAngle"] = self._heel_seat_angle
        params["HeelPitchAngle"] = self._heel_pitch_angle
        params["HeelTaperLateral"] = self._heel_taper_lateral
        params["HeelTaperMedial"] = self._heel_taper_medial
        params["HeelTaperBack"] = self._heel_taper_back
        params["HeelCornerRadius"] = self._heel_corner_radius
        params["HeelBreastCurveDepth"] = self._heel_breast_curve_depth
        params["HeelStackCount"] = self._heel_stack_count
        params["HeelStackLayerHeight"] = self._heel_stack_layer_height
        params["HeelLiftHeight"] = self._heel_lift_height
        params["HeelCounterHeight"] = self._heel_counter_height
        params["HeelCounterThickness"] = self._heel_counter_thickness
        params["HeelRandWidth"] = self._heel_rand_width
        params["HeelRandHeight"] = self._heel_rand_height
        return params

    def CollectSupportStyleParameters(self):
        """Collect support style parameters into a dictionary.

        Returns:
            Dictionary of support style parameters.
        """
        style_params = {}
        style_params["BottomType"] = self._bottom_type
        style_params["SoleType"] = self._sole_type
        style_params["HeelType"] = self._heel_type
        style_params["SupportType"] = self._support_type
        style_params["TreadPattern"] = self._tread_pattern
        style_params["SoleThicknessToe"] = self._sole_thickness_toe
        style_params["SoleThicknessBall"] = self._sole_thickness_ball
        style_params["SoleThicknessWaist"] = self._sole_thickness_waist
        style_params["SoleThicknessHeel"] = self._sole_thickness_heel
        style_params["SoleEdgeWidth"] = self._sole_edge_width
        style_params["SoleEdgeAngle"] = self._sole_edge_angle
        style_params["HeelHeight"] = self._heel_height
        style_params["HeelBreastAngle"] = self._heel_breast_angle
        style_params["HeelCornerRadius"] = self._heel_corner_radius
        style_params["SupportThickness"] = self._support_thickness
        style_params["SupportCurvature"] = self._support_curvature
        style_params["TreadDepth"] = self._tread_depth
        style_params["WedgeAngle"] = self._wedge_angle
        style_params["PlatformHeight"] = self._platform_height
        return style_params

    # =========================================================================
    # Default Parameter Methods
    # =========================================================================

    def SetDefaultSupportStyleParameters(self):
        """Set all support style parameters to their default values."""
        self._bottom_type = Bottom.BOTTOM_TYPE_FLAT
        self._sole_type = Bottom.SOLE_TYPE_FLAT
        self._heel_type = Bottom.HEEL_TYPE_STANDARD
        self._support_type = Bottom.SUPPORT_TYPE_SHANK
        self._tread_pattern = Bottom.TREAD_PATTERN_SMOOTH
        self._sole_edge_width = 2.0
        self._sole_edge_angle = 0.0
        self._heel_breast_angle = 5.0
        self._heel_corner_radius = 5.0
        self._support_thickness = 2.0
        self._support_curvature = 0.5
        self._tread_depth = 2.0
        self._wedge_angle = 0.0
        self._platform_height = 0.0

    # =========================================================================
    # Calculation Methods
    # =========================================================================

    def CalculateLinearMeasurementsFromMults(self):
        """Calculate all linear measurements from their multiplier values."""
        length = self._length

        # Sole thicknesses
        self._sole_thickness_toe = length * self._sole_thickness_toe_mult
        self._sole_thickness_ball = length * self._sole_thickness_ball_mult
        self._sole_thickness_waist = length * self._sole_thickness_waist_mult
        self._sole_thickness_heel = length * self._sole_thickness_heel_mult
        self._sole_thickness_arch = length * self._sole_thickness_arch_mult
        self._sole_thickness_center = (self._sole_thickness_ball + self._sole_thickness_waist) / 2.0

        # Heel dimensions
        self._heel_height = length * self._heel_height_mult
        self._heel_height_effective = self._heel_height
        self._heel_top_width = length * self._heel_top_width_mult
        self._heel_top_length = length * self._heel_top_length_mult
        self._heel_bottom_width = length * self._heel_bottom_width_mult
        self._heel_bottom_length = length * self._heel_bottom_length_mult

        # Support dimensions
        self._support_length = length * self._support_length_mult
        self._support_width = length * self._support_width_mult

        # Toe spring
        self._toe_spring = length * self._toe_spring_mult

        # Calculate heel stack layer height if stacked
        if self._heel_stack_count > 1:
            self._heel_stack_layer_height = self._heel_height / self._heel_stack_count

        # Key anatomical points
        self._toe_point = Point3d(self._length, 0.0, self._toe_spring)
        self._ball_point = Point3d(
            self._length - self._ball_line_length,
            0.0,
            0.0
        )
        self._heel_point = Point3d(0.0, 0.0, self._heel_height)
        self._heel_back_point = Point3d(0.0, 0.0, 0.0)
        self._waist_point = Point3d(
            self._length * 0.47,
            0.0,
            self._heel_height * 0.5
        )
        self._arch_point = Point3d(
            self._length * 0.55,
            0.0,
            self._heel_height * 0.3
        )
        self._heel_breast_point = Point3d(
            self._heel_top_length,
            0.0,
            self._heel_height
        )

        # Rocker apex
        if abs(self._sole_rocker_angle) > 0.01:
            apex_x = self._length * self._sole_rocker_apex_position
            self._rocker_apex_point = Point3d(apex_x, 0.0, 0.0)

    # =========================================================================
    # Design Curve Methods
    # =========================================================================

    def DesignCurves(self, last, doc):
        """Design all bottom curves based on the parent Last geometry.

        Args:
            last: The parent Last instance providing base geometry.
            doc: The Rhino document for adding geometry.
        """
        # Transfer key measurements from last
        self._length = last.Length
        self._ball_line_length = last.BallLineLength
        self._ball_width = last.BallWidth
        self._heel_width = last.HeelWidth

        # Design curves based on bottom type
        self.DesignCurvesForBottoms(last, doc)
        self.DesignCurvesForSoles(last, doc)

    def DesignCurvesForBottoms(self, last, doc):
        """Design outline and structural curves for the bottom unit.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        # Create the bottom outline from last bottom line with sole extension
        self._design_bottom_outline(last, doc)

        # Design heel curves
        if self._bottom_type in [Bottom.BOTTOM_TYPE_HEEL, Bottom.BOTTOM_TYPE_WEDGE]:
            self._design_heel_curves(last, doc)

        # Design wedge curves
        if self._bottom_type == Bottom.BOTTOM_TYPE_WEDGE:
            self._design_wedge_curves(last, doc)

        # Design platform curves
        if self._bottom_type == Bottom.BOTTOM_TYPE_PLATFORM:
            self._design_platform_curves(last, doc)

        # Design support (shank/plate) curves
        if self._support_type != Bottom.SUPPORT_TYPE_NONE:
            self._design_support_curves(last, doc)

    def _design_bottom_outline(self, last, doc):
        """Create bottom outline from last bottom line."""
        pass

    def _design_heel_curves(self, last, doc):
        """Create heel geometry curves."""
        pass

    def _design_wedge_curves(self, last, doc):
        """Create wedge geometry curves."""
        pass

    def _design_platform_curves(self, last, doc):
        """Create platform geometry curves."""
        pass

    def _design_support_curves(self, last, doc):
        """Create shank/plate/spring support curves."""
        pass

    def DesignCurvesForSoles(self, last, doc):
        """Design sole-specific curves.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        # Sole outline offset from bottom outline
        self._design_sole_outline(last, doc)

        # Cross section curves at key positions
        self._design_sole_cross_sections(last, doc)

        # Sole-type specific curves
        if self._sole_type == Bottom.SOLE_TYPE_ROCKER:
            self._design_rocker_curve(last, doc)
        elif self._sole_type == Bottom.SOLE_TYPE_THOMAS:
            self._design_thomas_curve(last, doc)
        elif self._sole_type == Bottom.SOLE_TYPE_METATARSAL_BAR:
            self._design_met_bar_curve(last, doc)

        # Tread pattern curves
        if self._tread_pattern != Bottom.TREAD_PATTERN_SMOOTH:
            self._design_tread_curves(last, doc)

    def _design_sole_outline(self, last, doc):
        """Create sole outline curves."""
        pass

    def _design_sole_cross_sections(self, last, doc):
        """Create sole cross section curves at key positions."""
        pass

    def _design_rocker_curve(self, last, doc):
        """Create rocker sole profile curve."""
        pass

    def _design_thomas_curve(self, last, doc):
        """Create Thomas heel extension curve."""
        pass

    def _design_met_bar_curve(self, last, doc):
        """Create metatarsal bar curves."""
        pass

    def _design_tread_curves(self, last, doc):
        """Create tread pattern curves."""
        pass

    # =========================================================================
    # Body Design Methods
    # =========================================================================

    def DesignBody(self, last, doc):
        """Design the complete bottom body geometry.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        self.DesignBodyForBottoms(last, doc)
        self.DesignBodyForSoles(last, doc)

    def DesignBodyForBottoms(self, last, doc):
        """Design bottom unit bodies (heel, wedge, platform, support).

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        # Design heel body
        if self._bottom_type == Bottom.BOTTOM_TYPE_HEEL:
            self._design_heel_body(last, doc)
        elif self._bottom_type == Bottom.BOTTOM_TYPE_WEDGE:
            self._design_wedge_body(last, doc)
        elif self._bottom_type == Bottom.BOTTOM_TYPE_PLATFORM:
            self._design_platform_body(last, doc)

        # Design support body
        if self._support_type != Bottom.SUPPORT_TYPE_NONE:
            self._design_support_body(last, doc)

        # Design heel accessories
        if self._heel_counter_height > 0:
            self._design_heel_counter_body(last, doc)
        if self._heel_rand_width > 0:
            self._design_heel_rand_body(last, doc)

        # Design toe accessories
        if self._toe_cap_length > 0:
            self._design_toe_cap_body(last, doc)
        if self._toe_bumper_length > 0:
            self._design_toe_bumper_body(last, doc)

    def _design_heel_body(self, last, doc):
        """Create the heel block body from heel curves."""
        # Get heel curves
        if self._heel_top_curve == Guid.Empty or self._heel_bottom_curve == Guid.Empty:
            return

        top_obj = doc.Objects.Find(self._heel_top_curve)
        bottom_obj = doc.Objects.Find(self._heel_bottom_curve)

        if top_obj is None or bottom_obj is None:
            return

        top_curve = top_obj.Geometry
        bottom_curve = bottom_obj.Geometry

        if not isinstance(top_curve, Curve) or not isinstance(bottom_curve, Curve):
            return

        tolerance = doc.ModelAbsoluteTolerance
        loft_type = Rhino.Geometry.LoftType.Straight

        # Loft between top and bottom heel curves
        breps = Brep.CreateFromLoft(
            [top_curve, bottom_curve],
            Point3d.Unset, Point3d.Unset,
            loft_type, False
        )

        if breps and len(breps) > 0:
            heel_brep = breps[0]
            capped = heel_brep.CapPlanarHoles(tolerance)
            if capped:
                heel_brep = capped
            self._body_heel = doc.Objects.AddBrep(heel_brep)

    def _design_wedge_body(self, last, doc):
        """Create the wedge body."""
        pass

    def _design_platform_body(self, last, doc):
        """Create the platform body."""
        pass

    def _design_support_body(self, last, doc):
        """Create the shank/plate/spring support body."""
        if self._support_outline_curve == Guid.Empty:
            return

        outline_obj = doc.Objects.Find(self._support_outline_curve)
        if outline_obj is None:
            return

        outline = outline_obj.Geometry
        if not isinstance(outline, Curve) or not outline.IsClosed:
            return

        # Extrude the support outline by support thickness
        extrusion = Rhino.Geometry.Extrusion.Create(
            outline, self._support_thickness, True
        )
        if extrusion:
            support_brep = extrusion.ToBrep()
            if support_brep:
                self._body_support = doc.Objects.AddBrep(support_brep)

    def _design_heel_counter_body(self, last, doc):
        """Create the heel counter body."""
        pass

    def _design_heel_rand_body(self, last, doc):
        """Create the heel rand body."""
        pass

    def _design_toe_cap_body(self, last, doc):
        """Create the toe cap body."""
        pass

    def _design_toe_bumper_body(self, last, doc):
        """Create the toe bumper body."""
        pass

    def DesignBodyForSoles(self, last, doc):
        """Design sole body from sole curves.

        Args:
            last: The parent Last instance.
            doc: The Rhino document.
        """
        # Collect sole cross section curves
        cs_ids = [
            self._sole_cs_toe,
            self._sole_cs_ball,
            self._sole_cs_arch,
            self._sole_cs_waist,
            self._sole_cs_heel,
        ]

        curves = []
        for cs_id in cs_ids:
            if cs_id != Guid.Empty:
                obj = doc.Objects.Find(cs_id)
                if obj and isinstance(obj.Geometry, Curve):
                    curves.append(obj.Geometry)

        if len(curves) < 3:
            return

        tolerance = doc.ModelAbsoluteTolerance
        loft_type = Rhino.Geometry.LoftType.Normal

        breps = Brep.CreateFromLoft(
            curves, Point3d.Unset, Point3d.Unset,
            loft_type, False
        )

        if breps and len(breps) > 0:
            sole_brep = breps[0]
            capped = sole_brep.CapPlanarHoles(tolerance)
            if capped:
                sole_brep = capped
            self._body_sole = doc.Objects.AddBrep(sole_brep)

        # Design tread body
        if self._tread_pattern != Bottom.TREAD_PATTERN_SMOOTH:
            self._design_tread_body(last, doc)

    def _design_tread_body(self, last, doc):
        """Create the tread pattern body."""
        pass

    def DesignBodyForShoes(self, last, insert, doc):
        """Design the combined shoe body (last + insert + bottom).

        Creates the final combined shoe geometry by joining the
        last body, insert body, and bottom unit into a single entity.

        Args:
            last: The parent Last instance.
            insert: The Insert instance.
            doc: The Rhino document.
        """
        bodies_to_join = []
        tolerance = doc.ModelAbsoluteTolerance

        # Collect valid bodies
        for body_id in [self._body_sole, self._body_heel,
                        self._body_platform, self._body_wedge]:
            if body_id != Guid.Empty:
                obj = doc.Objects.Find(body_id)
                if obj and isinstance(obj.Geometry, Brep):
                    bodies_to_join.append(obj.Geometry)

        if len(bodies_to_join) == 0:
            return

        if len(bodies_to_join) == 1:
            self._body_bottom_combined = doc.Objects.AddBrep(bodies_to_join[0])
            self._body_shoe = self._body_bottom_combined
            return

        # Boolean union all bottom components
        joined = Brep.CreateBooleanUnion(bodies_to_join, tolerance)
        if joined and len(joined) > 0:
            self._body_bottom_combined = doc.Objects.AddBrep(joined[0])
        else:
            # Fallback: join without boolean
            joined_breps = Brep.JoinBreps(bodies_to_join, tolerance)
            if joined_breps and len(joined_breps) > 0:
                self._body_bottom_combined = doc.Objects.AddBrep(joined_breps[0])

        # Now combine with last body if available
        if last.BodyMain != Guid.Empty and self._body_bottom_combined != Guid.Empty:
            last_obj = doc.Objects.Find(last.BodyMain)
            bottom_obj = doc.Objects.Find(self._body_bottom_combined)
            if last_obj and bottom_obj:
                last_brep = last_obj.Geometry
                bottom_brep = bottom_obj.Geometry
                if isinstance(last_brep, Brep) and isinstance(bottom_brep, Brep):
                    shoe = Brep.CreateBooleanUnion(
                        [last_brep, bottom_brep], tolerance
                    )
                    if shoe and len(shoe) > 0:
                        self._body_shoe = doc.Objects.AddBrep(shoe[0])

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
    def BottomType(self):
        return self._bottom_type

    @BottomType.setter
    def BottomType(self, value):
        self._bottom_type = str(value)

    @property
    def SoleType(self):
        return self._sole_type

    @SoleType.setter
    def SoleType(self, value):
        self._sole_type = str(value)

    @property
    def HeelType(self):
        return self._heel_type

    @HeelType.setter
    def HeelType(self, value):
        self._heel_type = str(value)

    @property
    def SupportType(self):
        return self._support_type

    @SupportType.setter
    def SupportType(self, value):
        self._support_type = str(value)

    @property
    def TreadPattern(self):
        return self._tread_pattern

    @TreadPattern.setter
    def TreadPattern(self, value):
        self._tread_pattern = str(value)

    # =========================================================================
    # Properties - Overall Dimensions
    # =========================================================================

    @property
    def Length(self):
        return self._length

    @Length.setter
    def Length(self, value):
        self._length = float(value)

    @property
    def BallLineLength(self):
        return self._ball_line_length

    @BallLineLength.setter
    def BallLineLength(self, value):
        self._ball_line_length = float(value)

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

    # =========================================================================
    # Properties - Sole Parameters
    # =========================================================================

    @property
    def SoleThicknessToe(self):
        return self._sole_thickness_toe

    @SoleThicknessToe.setter
    def SoleThicknessToe(self, value):
        self._sole_thickness_toe = float(value)

    @property
    def SoleThicknessBall(self):
        return self._sole_thickness_ball

    @SoleThicknessBall.setter
    def SoleThicknessBall(self, value):
        self._sole_thickness_ball = float(value)

    @property
    def SoleThicknessWaist(self):
        return self._sole_thickness_waist

    @SoleThicknessWaist.setter
    def SoleThicknessWaist(self, value):
        self._sole_thickness_waist = float(value)

    @property
    def SoleThicknessHeel(self):
        return self._sole_thickness_heel

    @SoleThicknessHeel.setter
    def SoleThicknessHeel(self, value):
        self._sole_thickness_heel = float(value)

    @property
    def SoleThicknessArch(self):
        return self._sole_thickness_arch

    @SoleThicknessArch.setter
    def SoleThicknessArch(self, value):
        self._sole_thickness_arch = float(value)

    @property
    def SoleThicknessCenter(self):
        return self._sole_thickness_center

    @SoleThicknessCenter.setter
    def SoleThicknessCenter(self, value):
        self._sole_thickness_center = float(value)

    @property
    def SoleEdgeWidth(self):
        return self._sole_edge_width

    @SoleEdgeWidth.setter
    def SoleEdgeWidth(self, value):
        self._sole_edge_width = float(value)

    @property
    def SoleEdgeAngle(self):
        return self._sole_edge_angle

    @SoleEdgeAngle.setter
    def SoleEdgeAngle(self, value):
        self._sole_edge_angle = float(value)

    @property
    def SoleExtensionLateral(self):
        return self._sole_extension_lateral

    @SoleExtensionLateral.setter
    def SoleExtensionLateral(self, value):
        self._sole_extension_lateral = float(value)

    @property
    def SoleExtensionMedial(self):
        return self._sole_extension_medial

    @SoleExtensionMedial.setter
    def SoleExtensionMedial(self, value):
        self._sole_extension_medial = float(value)

    @property
    def SoleRockerAngle(self):
        return self._sole_rocker_angle

    @SoleRockerAngle.setter
    def SoleRockerAngle(self, value):
        self._sole_rocker_angle = float(value)

    @property
    def SoleRockerApexPosition(self):
        return self._sole_rocker_apex_position

    @SoleRockerApexPosition.setter
    def SoleRockerApexPosition(self, value):
        self._sole_rocker_apex_position = float(value)

    @property
    def SoleThomasHeelExtension(self):
        return self._sole_thomas_heel_extension

    @SoleThomasHeelExtension.setter
    def SoleThomasHeelExtension(self, value):
        self._sole_thomas_heel_extension = float(value)

    @property
    def SoleMetatarsalBarPosition(self):
        return self._sole_metatarsal_bar_position

    @SoleMetatarsalBarPosition.setter
    def SoleMetatarsalBarPosition(self, value):
        self._sole_metatarsal_bar_position = float(value)

    @property
    def SoleMetatarsalBarHeight(self):
        return self._sole_metatarsal_bar_height

    @SoleMetatarsalBarHeight.setter
    def SoleMetatarsalBarHeight(self, value):
        self._sole_metatarsal_bar_height = float(value)

    @property
    def SoleMetatarsalBarWidth(self):
        return self._sole_metatarsal_bar_width

    @SoleMetatarsalBarWidth.setter
    def SoleMetatarsalBarWidth(self, value):
        self._sole_metatarsal_bar_width = float(value)

    @property
    def SoleFlareLateral(self):
        return self._sole_flare_lateral

    @SoleFlareLateral.setter
    def SoleFlareLateral(self, value):
        self._sole_flare_lateral = float(value)

    @property
    def SoleFlareMedial(self):
        return self._sole_flare_medial

    @SoleFlareMedial.setter
    def SoleFlareMedial(self, value):
        self._sole_flare_medial = float(value)

    @property
    def SoleFlareHeel(self):
        return self._sole_flare_heel

    @SoleFlareHeel.setter
    def SoleFlareHeel(self, value):
        self._sole_flare_heel = float(value)

    @property
    def SoleBevelToe(self):
        return self._sole_bevel_toe

    @SoleBevelToe.setter
    def SoleBevelToe(self, value):
        self._sole_bevel_toe = float(value)

    @property
    def SoleBevelHeel(self):
        return self._sole_bevel_heel

    @SoleBevelHeel.setter
    def SoleBevelHeel(self, value):
        self._sole_bevel_heel = float(value)

    # =========================================================================
    # Properties - Sole Multipliers
    # =========================================================================

    @property
    def SoleThicknessToeMult(self):
        return self._sole_thickness_toe_mult

    @SoleThicknessToeMult.setter
    def SoleThicknessToeMult(self, value):
        self._sole_thickness_toe_mult = float(value)

    @property
    def SoleThicknessBallMult(self):
        return self._sole_thickness_ball_mult

    @SoleThicknessBallMult.setter
    def SoleThicknessBallMult(self, value):
        self._sole_thickness_ball_mult = float(value)

    @property
    def SoleThicknessWaistMult(self):
        return self._sole_thickness_waist_mult

    @SoleThicknessWaistMult.setter
    def SoleThicknessWaistMult(self, value):
        self._sole_thickness_waist_mult = float(value)

    @property
    def SoleThicknessHeelMult(self):
        return self._sole_thickness_heel_mult

    @SoleThicknessHeelMult.setter
    def SoleThicknessHeelMult(self, value):
        self._sole_thickness_heel_mult = float(value)

    @property
    def SoleThicknessArchMult(self):
        return self._sole_thickness_arch_mult

    @SoleThicknessArchMult.setter
    def SoleThicknessArchMult(self, value):
        self._sole_thickness_arch_mult = float(value)

    # =========================================================================
    # Properties - Heel Parameters
    # =========================================================================

    @property
    def HeelHeight(self):
        return self._heel_height

    @HeelHeight.setter
    def HeelHeight(self, value):
        self._heel_height = float(value)

    @property
    def HeelHeightEffective(self):
        return self._heel_height_effective

    @HeelHeightEffective.setter
    def HeelHeightEffective(self, value):
        self._heel_height_effective = float(value)

    @property
    def HeelTopWidth(self):
        return self._heel_top_width

    @HeelTopWidth.setter
    def HeelTopWidth(self, value):
        self._heel_top_width = float(value)

    @property
    def HeelTopLength(self):
        return self._heel_top_length

    @HeelTopLength.setter
    def HeelTopLength(self, value):
        self._heel_top_length = float(value)

    @property
    def HeelBottomWidth(self):
        return self._heel_bottom_width

    @HeelBottomWidth.setter
    def HeelBottomWidth(self, value):
        self._heel_bottom_width = float(value)

    @property
    def HeelBottomLength(self):
        return self._heel_bottom_length

    @HeelBottomLength.setter
    def HeelBottomLength(self, value):
        self._heel_bottom_length = float(value)

    @property
    def HeelBreastAngle(self):
        return self._heel_breast_angle

    @HeelBreastAngle.setter
    def HeelBreastAngle(self, value):
        self._heel_breast_angle = float(value)

    @property
    def HeelSeatAngle(self):
        return self._heel_seat_angle

    @HeelSeatAngle.setter
    def HeelSeatAngle(self, value):
        self._heel_seat_angle = float(value)

    @property
    def HeelPitchAngle(self):
        return self._heel_pitch_angle

    @HeelPitchAngle.setter
    def HeelPitchAngle(self, value):
        self._heel_pitch_angle = float(value)

    @property
    def HeelTaperLateral(self):
        return self._heel_taper_lateral

    @HeelTaperLateral.setter
    def HeelTaperLateral(self, value):
        self._heel_taper_lateral = float(value)

    @property
    def HeelTaperMedial(self):
        return self._heel_taper_medial

    @HeelTaperMedial.setter
    def HeelTaperMedial(self, value):
        self._heel_taper_medial = float(value)

    @property
    def HeelTaperBack(self):
        return self._heel_taper_back

    @HeelTaperBack.setter
    def HeelTaperBack(self, value):
        self._heel_taper_back = float(value)

    @property
    def HeelCornerRadius(self):
        return self._heel_corner_radius

    @HeelCornerRadius.setter
    def HeelCornerRadius(self, value):
        self._heel_corner_radius = float(value)

    @property
    def HeelBreastCurveDepth(self):
        return self._heel_breast_curve_depth

    @HeelBreastCurveDepth.setter
    def HeelBreastCurveDepth(self, value):
        self._heel_breast_curve_depth = float(value)

    @property
    def HeelStackCount(self):
        return self._heel_stack_count

    @HeelStackCount.setter
    def HeelStackCount(self, value):
        self._heel_stack_count = int(value)

    @property
    def HeelStackLayerHeight(self):
        return self._heel_stack_layer_height

    @HeelStackLayerHeight.setter
    def HeelStackLayerHeight(self, value):
        self._heel_stack_layer_height = float(value)

    @property
    def HeelLiftHeight(self):
        return self._heel_lift_height

    @HeelLiftHeight.setter
    def HeelLiftHeight(self, value):
        self._heel_lift_height = float(value)

    @property
    def HeelCounterHeight(self):
        return self._heel_counter_height

    @HeelCounterHeight.setter
    def HeelCounterHeight(self, value):
        self._heel_counter_height = float(value)

    @property
    def HeelCounterThickness(self):
        return self._heel_counter_thickness

    @HeelCounterThickness.setter
    def HeelCounterThickness(self, value):
        self._heel_counter_thickness = float(value)

    @property
    def HeelRandWidth(self):
        return self._heel_rand_width

    @HeelRandWidth.setter
    def HeelRandWidth(self, value):
        self._heel_rand_width = float(value)

    @property
    def HeelRandHeight(self):
        return self._heel_rand_height

    @HeelRandHeight.setter
    def HeelRandHeight(self, value):
        self._heel_rand_height = float(value)

    # =========================================================================
    # Properties - Heel Multipliers
    # =========================================================================

    @property
    def HeelHeightMult(self):
        return self._heel_height_mult

    @HeelHeightMult.setter
    def HeelHeightMult(self, value):
        self._heel_height_mult = float(value)

    @property
    def HeelTopWidthMult(self):
        return self._heel_top_width_mult

    @HeelTopWidthMult.setter
    def HeelTopWidthMult(self, value):
        self._heel_top_width_mult = float(value)

    @property
    def HeelTopLengthMult(self):
        return self._heel_top_length_mult

    @HeelTopLengthMult.setter
    def HeelTopLengthMult(self, value):
        self._heel_top_length_mult = float(value)

    @property
    def HeelBottomWidthMult(self):
        return self._heel_bottom_width_mult

    @HeelBottomWidthMult.setter
    def HeelBottomWidthMult(self, value):
        self._heel_bottom_width_mult = float(value)

    @property
    def HeelBottomLengthMult(self):
        return self._heel_bottom_length_mult

    @HeelBottomLengthMult.setter
    def HeelBottomLengthMult(self, value):
        self._heel_bottom_length_mult = float(value)

    # =========================================================================
    # Properties - Wedge Parameters
    # =========================================================================

    @property
    def WedgeAngle(self):
        return self._wedge_angle

    @WedgeAngle.setter
    def WedgeAngle(self, value):
        self._wedge_angle = float(value)

    @property
    def WedgeHeightFront(self):
        return self._wedge_height_front

    @WedgeHeightFront.setter
    def WedgeHeightFront(self, value):
        self._wedge_height_front = float(value)

    @property
    def WedgeHeightBack(self):
        return self._wedge_height_back

    @WedgeHeightBack.setter
    def WedgeHeightBack(self, value):
        self._wedge_height_back = float(value)

    @property
    def WedgeMedialPostingAngle(self):
        return self._wedge_medial_posting_angle

    @WedgeMedialPostingAngle.setter
    def WedgeMedialPostingAngle(self, value):
        self._wedge_medial_posting_angle = float(value)

    @property
    def WedgeLateralPostingAngle(self):
        return self._wedge_lateral_posting_angle

    @WedgeLateralPostingAngle.setter
    def WedgeLateralPostingAngle(self, value):
        self._wedge_lateral_posting_angle = float(value)

    # =========================================================================
    # Properties - Platform Parameters
    # =========================================================================

    @property
    def PlatformHeight(self):
        return self._platform_height

    @PlatformHeight.setter
    def PlatformHeight(self, value):
        self._platform_height = float(value)

    @property
    def PlatformSoleThickness(self):
        return self._platform_sole_thickness

    @PlatformSoleThickness.setter
    def PlatformSoleThickness(self, value):
        self._platform_sole_thickness = float(value)

    @property
    def PlatformTaperToe(self):
        return self._platform_taper_toe

    @PlatformTaperToe.setter
    def PlatformTaperToe(self, value):
        self._platform_taper_toe = float(value)

    @property
    def PlatformTaperHeel(self):
        return self._platform_taper_heel

    @PlatformTaperHeel.setter
    def PlatformTaperHeel(self, value):
        self._platform_taper_heel = float(value)

    @property
    def PlatformEdgeRadius(self):
        return self._platform_edge_radius

    @PlatformEdgeRadius.setter
    def PlatformEdgeRadius(self, value):
        self._platform_edge_radius = float(value)

    # =========================================================================
    # Properties - Support Parameters
    # =========================================================================

    @property
    def SupportLength(self):
        return self._support_length

    @SupportLength.setter
    def SupportLength(self, value):
        self._support_length = float(value)

    @property
    def SupportWidth(self):
        return self._support_width

    @SupportWidth.setter
    def SupportWidth(self, value):
        self._support_width = float(value)

    @property
    def SupportThickness(self):
        return self._support_thickness

    @SupportThickness.setter
    def SupportThickness(self, value):
        self._support_thickness = float(value)

    @property
    def SupportPositionX(self):
        return self._support_position_x

    @SupportPositionX.setter
    def SupportPositionX(self, value):
        self._support_position_x = float(value)

    @property
    def SupportCurvature(self):
        return self._support_curvature

    @SupportCurvature.setter
    def SupportCurvature(self, value):
        self._support_curvature = float(value)

    @property
    def SupportSpringRate(self):
        return self._support_spring_rate

    @SupportSpringRate.setter
    def SupportSpringRate(self, value):
        self._support_spring_rate = float(value)

    @property
    def SupportLengthMult(self):
        return self._support_length_mult

    @SupportLengthMult.setter
    def SupportLengthMult(self, value):
        self._support_length_mult = float(value)

    @property
    def SupportWidthMult(self):
        return self._support_width_mult

    @SupportWidthMult.setter
    def SupportWidthMult(self, value):
        self._support_width_mult = float(value)

    # =========================================================================
    # Properties - Tread Parameters
    # =========================================================================

    @property
    def TreadDepth(self):
        return self._tread_depth

    @TreadDepth.setter
    def TreadDepth(self, value):
        self._tread_depth = float(value)

    @property
    def TreadSpacing(self):
        return self._tread_spacing

    @TreadSpacing.setter
    def TreadSpacing(self, value):
        self._tread_spacing = float(value)

    @property
    def TreadLugWidth(self):
        return self._tread_lug_width

    @TreadLugWidth.setter
    def TreadLugWidth(self, value):
        self._tread_lug_width = float(value)

    @property
    def TreadLugHeight(self):
        return self._tread_lug_height

    @TreadLugHeight.setter
    def TreadLugHeight(self, value):
        self._tread_lug_height = float(value)

    @property
    def TreadPatternScale(self):
        return self._tread_pattern_scale

    @TreadPatternScale.setter
    def TreadPatternScale(self, value):
        self._tread_pattern_scale = float(value)

    @property
    def TreadPatternRotation(self):
        return self._tread_pattern_rotation

    @TreadPatternRotation.setter
    def TreadPatternRotation(self, value):
        self._tread_pattern_rotation = float(value)

    # =========================================================================
    # Properties - Toe Spring and Related
    # =========================================================================

    @property
    def ToeSpring(self):
        return self._toe_spring

    @ToeSpring.setter
    def ToeSpring(self, value):
        self._toe_spring = float(value)

    @property
    def ToeSpringMult(self):
        return self._toe_spring_mult

    @ToeSpringMult.setter
    def ToeSpringMult(self, value):
        self._toe_spring_mult = float(value)

    @property
    def ToeCapLength(self):
        return self._toe_cap_length

    @ToeCapLength.setter
    def ToeCapLength(self, value):
        self._toe_cap_length = float(value)

    @property
    def ToeCapHeight(self):
        return self._toe_cap_height

    @ToeCapHeight.setter
    def ToeCapHeight(self, value):
        self._toe_cap_height = float(value)

    @property
    def ToeBumperHeight(self):
        return self._toe_bumper_height

    @ToeBumperHeight.setter
    def ToeBumperHeight(self, value):
        self._toe_bumper_height = float(value)

    @property
    def ToeBumperLength(self):
        return self._toe_bumper_length

    @ToeBumperLength.setter
    def ToeBumperLength(self, value):
        self._toe_bumper_length = float(value)

    # =========================================================================
    # Properties - Feather Line Parameters
    # =========================================================================

    @property
    def FeatherLineOffset(self):
        return self._feather_line_offset

    @FeatherLineOffset.setter
    def FeatherLineOffset(self, value):
        self._feather_line_offset = float(value)

    @property
    def FeatherLineHeightToe(self):
        return self._feather_line_height_toe

    @FeatherLineHeightToe.setter
    def FeatherLineHeightToe(self, value):
        self._feather_line_height_toe = float(value)

    @property
    def FeatherLineHeightBall(self):
        return self._feather_line_height_ball

    @FeatherLineHeightBall.setter
    def FeatherLineHeightBall(self, value):
        self._feather_line_height_ball = float(value)

    @property
    def FeatherLineHeightWaist(self):
        return self._feather_line_height_waist

    @FeatherLineHeightWaist.setter
    def FeatherLineHeightWaist(self, value):
        self._feather_line_height_waist = float(value)

    @property
    def FeatherLineHeightHeel(self):
        return self._feather_line_height_heel

    @FeatherLineHeightHeel.setter
    def FeatherLineHeightHeel(self, value):
        self._feather_line_height_heel = float(value)

    # =========================================================================
    # Properties - Curve IDs
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
    def OutlineCurveSole(self):
        return self._outline_curve_sole

    @OutlineCurveSole.setter
    def OutlineCurveSole(self, value):
        self._outline_curve_sole = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def OutlineCurveHeel(self):
        return self._outline_curve_heel

    @OutlineCurveHeel.setter
    def OutlineCurveHeel(self, value):
        self._outline_curve_heel = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleBottomCurve(self):
        return self._sole_bottom_curve

    @SoleBottomCurve.setter
    def SoleBottomCurve(self, value):
        self._sole_bottom_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleTopCurve(self):
        return self._sole_top_curve

    @SoleTopCurve.setter
    def SoleTopCurve(self, value):
        self._sole_top_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleEdgeCurveLateral(self):
        return self._sole_edge_curve_lateral

    @SoleEdgeCurveLateral.setter
    def SoleEdgeCurveLateral(self, value):
        self._sole_edge_curve_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleEdgeCurveMedial(self):
        return self._sole_edge_curve_medial

    @SoleEdgeCurveMedial.setter
    def SoleEdgeCurveMedial(self, value):
        self._sole_edge_curve_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleCenterLine(self):
        return self._sole_center_line

    @SoleCenterLine.setter
    def SoleCenterLine(self, value):
        self._sole_center_line = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleTreadCurve(self):
        return self._sole_tread_curve

    @SoleTreadCurve.setter
    def SoleTreadCurve(self, value):
        self._sole_tread_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleRockerCurve(self):
        return self._sole_rocker_curve

    @SoleRockerCurve.setter
    def SoleRockerCurve(self, value):
        self._sole_rocker_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleThomasCurve(self):
        return self._sole_thomas_curve

    @SoleThomasCurve.setter
    def SoleThomasCurve(self, value):
        self._sole_thomas_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleMetBarCurve(self):
        return self._sole_met_bar_curve

    @SoleMetBarCurve.setter
    def SoleMetBarCurve(self, value):
        self._sole_met_bar_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    # Sole cross section IDs
    @property
    def SoleCSToe(self):
        return self._sole_cs_toe

    @SoleCSToe.setter
    def SoleCSToe(self, value):
        self._sole_cs_toe = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleCSBall(self):
        return self._sole_cs_ball

    @SoleCSBall.setter
    def SoleCSBall(self, value):
        self._sole_cs_ball = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleCSWaist(self):
        return self._sole_cs_waist

    @SoleCSWaist.setter
    def SoleCSWaist(self, value):
        self._sole_cs_waist = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleCSArch(self):
        return self._sole_cs_arch

    @SoleCSArch.setter
    def SoleCSArch(self, value):
        self._sole_cs_arch = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SoleCSHeel(self):
        return self._sole_cs_heel

    @SoleCSHeel.setter
    def SoleCSHeel(self, value):
        self._sole_cs_heel = Guid(str(value)) if not isinstance(value, Guid) else value

    # Heel curve IDs
    @property
    def HeelTopCurve(self):
        return self._heel_top_curve

    @HeelTopCurve.setter
    def HeelTopCurve(self, value):
        self._heel_top_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelBottomCurve(self):
        return self._heel_bottom_curve

    @HeelBottomCurve.setter
    def HeelBottomCurve(self, value):
        self._heel_bottom_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelBreastCurve(self):
        return self._heel_breast_curve

    @HeelBreastCurve.setter
    def HeelBreastCurve(self, value):
        self._heel_breast_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelBackCurve(self):
        return self._heel_back_curve

    @HeelBackCurve.setter
    def HeelBackCurve(self, value):
        self._heel_back_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelLateralCurve(self):
        return self._heel_lateral_curve

    @HeelLateralCurve.setter
    def HeelLateralCurve(self, value):
        self._heel_lateral_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelMedialCurve(self):
        return self._heel_medial_curve

    @HeelMedialCurve.setter
    def HeelMedialCurve(self, value):
        self._heel_medial_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelSeatCurve(self):
        return self._heel_seat_curve

    @HeelSeatCurve.setter
    def HeelSeatCurve(self, value):
        self._heel_seat_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelProfileCurve(self):
        return self._heel_profile_curve

    @HeelProfileCurve.setter
    def HeelProfileCurve(self, value):
        self._heel_profile_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelCounterCurve(self):
        return self._heel_counter_curve

    @HeelCounterCurve.setter
    def HeelCounterCurve(self, value):
        self._heel_counter_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def HeelRandCurve(self):
        return self._heel_rand_curve

    @HeelRandCurve.setter
    def HeelRandCurve(self, value):
        self._heel_rand_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    # Support curve IDs
    @property
    def SupportOutlineCurve(self):
        return self._support_outline_curve

    @SupportOutlineCurve.setter
    def SupportOutlineCurve(self, value):
        self._support_outline_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SupportProfileCurve(self):
        return self._support_profile_curve

    @SupportProfileCurve.setter
    def SupportProfileCurve(self, value):
        self._support_profile_curve = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SupportCenterLine(self):
        return self._support_center_line

    @SupportCenterLine.setter
    def SupportCenterLine(self, value):
        self._support_center_line = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Surface IDs
    # =========================================================================

    @property
    def SurfaceSoleTop(self):
        return self._surface_sole_top

    @SurfaceSoleTop.setter
    def SurfaceSoleTop(self, value):
        self._surface_sole_top = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceSoleBottom(self):
        return self._surface_sole_bottom

    @SurfaceSoleBottom.setter
    def SurfaceSoleBottom(self, value):
        self._surface_sole_bottom = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceHeelTop(self):
        return self._surface_heel_top

    @SurfaceHeelTop.setter
    def SurfaceHeelTop(self, value):
        self._surface_heel_top = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceHeelBottom(self):
        return self._surface_heel_bottom

    @SurfaceHeelBottom.setter
    def SurfaceHeelBottom(self, value):
        self._surface_heel_bottom = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceHeelSides(self):
        return self._surface_heel_sides

    @SurfaceHeelSides.setter
    def SurfaceHeelSides(self, value):
        self._surface_heel_sides = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceSupport(self):
        return self._surface_support

    @SurfaceSupport.setter
    def SurfaceSupport(self, value):
        self._surface_support = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfacePlatform(self):
        return self._surface_platform

    @SurfacePlatform.setter
    def SurfacePlatform(self, value):
        self._surface_platform = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def SurfaceTread(self):
        return self._surface_tread

    @SurfaceTread.setter
    def SurfaceTread(self, value):
        self._surface_tread = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Body Geometry IDs
    # =========================================================================

    @property
    def BodySole(self):
        return self._body_sole

    @BodySole.setter
    def BodySole(self, value):
        self._body_sole = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyHeel(self):
        return self._body_heel

    @BodyHeel.setter
    def BodyHeel(self, value):
        self._body_heel = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyBottomCombined(self):
        return self._body_bottom_combined

    @BodyBottomCombined.setter
    def BodyBottomCombined(self, value):
        self._body_bottom_combined = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodySupport(self):
        return self._body_support

    @BodySupport.setter
    def BodySupport(self, value):
        self._body_support = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyPlatform(self):
        return self._body_platform

    @BodyPlatform.setter
    def BodyPlatform(self, value):
        self._body_platform = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyWedge(self):
        return self._body_wedge

    @BodyWedge.setter
    def BodyWedge(self, value):
        self._body_wedge = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyTread(self):
        return self._body_tread

    @BodyTread.setter
    def BodyTread(self, value):
        self._body_tread = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyToeCap(self):
        return self._body_toe_cap

    @BodyToeCap.setter
    def BodyToeCap(self, value):
        self._body_toe_cap = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyToeBumper(self):
        return self._body_toe_bumper

    @BodyToeBumper.setter
    def BodyToeBumper(self, value):
        self._body_toe_bumper = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyHeelCounter(self):
        return self._body_heel_counter

    @BodyHeelCounter.setter
    def BodyHeelCounter(self, value):
        self._body_heel_counter = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyHeelRand(self):
        return self._body_heel_rand

    @BodyHeelRand.setter
    def BodyHeelRand(self, value):
        self._body_heel_rand = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyMesh(self):
        return self._body_mesh

    @BodyMesh.setter
    def BodyMesh(self, value):
        self._body_mesh = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyShoe(self):
        return self._body_shoe

    @BodyShoe.setter
    def BodyShoe(self, value):
        self._body_shoe = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Key Points
    # =========================================================================

    @property
    def ToePoint(self):
        return self._toe_point

    @ToePoint.setter
    def ToePoint(self, value):
        self._toe_point = value

    @property
    def BallPoint(self):
        return self._ball_point

    @BallPoint.setter
    def BallPoint(self, value):
        self._ball_point = value

    @property
    def WaistPoint(self):
        return self._waist_point

    @WaistPoint.setter
    def WaistPoint(self, value):
        self._waist_point = value

    @property
    def ArchPoint(self):
        return self._arch_point

    @ArchPoint.setter
    def ArchPoint(self, value):
        self._arch_point = value

    @property
    def HeelPoint(self):
        return self._heel_point

    @HeelPoint.setter
    def HeelPoint(self, value):
        self._heel_point = value

    @property
    def HeelBreastPoint(self):
        return self._heel_breast_point

    @HeelBreastPoint.setter
    def HeelBreastPoint(self, value):
        self._heel_breast_point = value

    @property
    def HeelBackPoint(self):
        return self._heel_back_point

    @HeelBackPoint.setter
    def HeelBackPoint(self, value):
        self._heel_back_point = value

    @property
    def RockerApexPoint(self):
        return self._rocker_apex_point

    @RockerApexPoint.setter
    def RockerApexPoint(self, value):
        self._rocker_apex_point = value

    # =========================================================================
    # Properties - Style Parameter Dictionary
    # =========================================================================

    @property
    def SupportStyleParameterDictionary(self):
        return self._support_style_parameter_dictionary

    @SupportStyleParameterDictionary.setter
    def SupportStyleParameterDictionary(self, value):
        self._support_style_parameter_dictionary = dict(value) if value else {}

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_json(self):
        """Serialize this Bottom to a JSON string."""
        params = {}
        params["Name"] = self._name
        params["Side"] = self._side
        params["Notes"] = self._notes
        params["BottomType"] = self._bottom_type
        params["SoleType"] = self._sole_type
        params["HeelType"] = self._heel_type
        params["SupportType"] = self._support_type
        params["TreadPattern"] = self._tread_pattern
        params["Length"] = self._length
        params["BallWidth"] = self._ball_width
        params["HeelWidth"] = self._heel_width
        params.update(self.CollectHeelParameters())
        params.update(self.CollectSupportStyleParameters())
        params["SupportStyleParameterDictionary"] = self._support_style_parameter_dictionary
        return json.dumps(params, indent=2, default=str)

    @staticmethod
    def from_json(json_string):
        """Deserialize a Bottom from a JSON string."""
        bottom = Bottom()
        if isinstance(json_string, str):
            data = json.loads(json_string)
        else:
            data = json_string

        key_map = {
            "Name": "_name", "Side": "_side", "Notes": "_notes",
            "BottomType": "_bottom_type", "SoleType": "_sole_type",
            "HeelType": "_heel_type", "SupportType": "_support_type",
            "TreadPattern": "_tread_pattern",
            "Length": "_length", "BallWidth": "_ball_width",
            "HeelWidth": "_heel_width", "HeelHeight": "_heel_height",
            "SoleThicknessToe": "_sole_thickness_toe",
            "SoleThicknessBall": "_sole_thickness_ball",
            "SoleThicknessHeel": "_sole_thickness_heel",
        }
        for json_key, attr_name in key_map.items():
            if json_key in data:
                setattr(bottom, attr_name, data[json_key])

        if "SupportStyleParameterDictionary" in data:
            bottom._support_style_parameter_dictionary = data["SupportStyleParameterDictionary"]

        return bottom

    def __repr__(self):
        return (
            f'Bottom(name="{self._name}", side="{self._side}", '
            f'type="{self._bottom_type}", '
            f'heel_type="{self._heel_type}", '
            f'heel_height={self._heel_height:.1f})'
        )
