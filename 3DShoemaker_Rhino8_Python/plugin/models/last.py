"""
Last (shoe last) data model for 3DShoemaker Rhino 8 Python plugin.

The Last class represents a complete shoe last with all geometric parameters,
cross-section curves, body surfaces, and style settings. This is the central
data model from which inserts, bottoms, and other components derive their geometry.

Port of PodoCAD .NET Last class to Python 3.
"""

import json
import copy
import System
from System import Guid
import Rhino
from Rhino.Geometry import (
    Point3d, Vector3d, Plane, Curve, NurbsCurve, Brep, Mesh, SubD, Surface,
    BoundingBox, Transform, Line, Arc, Circle, Interval
)


class Last:
    """Represents a shoe last with all parameters, curves, surfaces, and bodies."""

    # -------------------------------------------------------------------------
    # Class-level defaults
    # -------------------------------------------------------------------------
    DEFAULT_LENGTH = 270.0
    DEFAULT_BALL_WIDTH = 95.0
    DEFAULT_HEEL_WIDTH = 65.0
    DEFAULT_BALL_GIRTH = 240.0
    DEFAULT_INSTEP_GIRTH = 230.0
    DEFAULT_WAIST_GIRTH = 220.0
    DEFAULT_WAIST2_GIRTH = 225.0
    DEFAULT_ARCH_GIRTH = 230.0
    DEFAULT_HEEL_GIRTH = 310.0
    DEFAULT_ANKLE_GIRTH = 240.0
    DEFAULT_HEEL_HEIGHT = 25.0
    DEFAULT_TOE_SPRING = 15.0
    DEFAULT_BALL_LINE_LENGTH_MULT = 0.70
    DEFAULT_ARCH_LENGTH_MULT = 0.55
    DEFAULT_WAIST_LENGTH_MULT = 0.47
    DEFAULT_WAIST2_LENGTH_MULT = 0.42
    DEFAULT_INSTEP_LENGTH_MULT = 0.35

    # Toe style enumerations
    TOE_STYLE_ROUND = "Round"
    TOE_STYLE_POINTED = "Pointed"
    TOE_STYLE_SQUARE = "Square"
    TOE_STYLE_OBLIQUE = "Oblique"
    TOE_STYLE_ALMOND = "Almond"

    # Bottom type enumerations
    BOTTOM_TYPE_FLAT = "Flat"
    BOTTOM_TYPE_WEDGE = "Wedge"
    BOTTOM_TYPE_HEEL = "Heel"

    # Arch type enumerations
    ARCH_TYPE_LOW = "Low"
    ARCH_TYPE_MEDIUM = "Medium"
    ARCH_TYPE_HIGH = "High"

    # Back edge shape enumerations
    BACK_EDGE_ROUND = "Round"
    BACK_EDGE_STRAIGHT = "Straight"
    BACK_EDGE_VSHAPED = "VShaped"

    def __init__(self):
        """Initialize a Last with default parameter values."""
        # --- Identification ---
        self._name = ""
        self._side = "Right"  # Right or Left
        self._size = ""
        self._size_system = "EU"
        self._notes = ""

        # --- Length Parameters ---
        self._length = Last.DEFAULT_LENGTH
        self._ball_line_length = 0.0
        self._arch_length = 0.0
        self._waist_length = 0.0
        self._waist2_length = 0.0
        self._instep_length = 0.0
        self._heel_girth_length = 0.0
        self._ankle_length = 0.0
        self._toe_length = 0.0
        self._alpha_joint_length = 0.0
        self._cone_length = 0.0
        self._tread_length = 0.0
        self._forepart_length = 0.0
        self._backpart_length = 0.0

        # --- Length Multipliers ---
        self._ball_line_length_mult = Last.DEFAULT_BALL_LINE_LENGTH_MULT
        self._arch_length_mult = Last.DEFAULT_ARCH_LENGTH_MULT
        self._waist_length_mult = Last.DEFAULT_WAIST_LENGTH_MULT
        self._waist2_length_mult = Last.DEFAULT_WAIST2_LENGTH_MULT
        self._instep_length_mult = Last.DEFAULT_INSTEP_LENGTH_MULT
        self._heel_girth_length_mult = 0.18
        self._ankle_length_mult = 0.10
        self._toe_length_mult = 0.85
        self._alpha_joint_length_mult = 0.75
        self._cone_length_mult = 0.90
        self._tread_length_mult = 0.68
        self._forepart_length_mult = 0.30
        self._backpart_length_mult = 0.82

        # --- Width Parameters ---
        self._ball_width = Last.DEFAULT_BALL_WIDTH
        self._ball_width_perp = 0.0
        self._ball_width_lateral = 0.0
        self._ball_width_medial = 0.0
        self._heel_width = Last.DEFAULT_HEEL_WIDTH
        self._heel_width_lateral = 0.0
        self._heel_width_medial = 0.0
        self._waist_width = 0.0
        self._waist2_width = 0.0
        self._instep_width = 0.0
        self._toe_width = 0.0
        self._alpha_joint_width = 0.0
        self._arch_width = 0.0
        self._ankle_width = 0.0
        self._cone_width = 0.0
        self._tread_width = 0.0

        # --- Width Multipliers ---
        self._ball_width_mult = 0.352
        self._ball_width_perp_mult = 0.345
        self._heel_width_mult = 0.241
        self._waist_width_mult = 0.260
        self._waist2_width_mult = 0.270
        self._instep_width_mult = 0.310
        self._toe_width_mult = 0.250
        self._alpha_joint_width_mult = 0.340
        self._arch_width_mult = 0.280
        self._ankle_width_mult = 0.260
        self._cone_width_mult = 0.200
        self._tread_width_mult = 0.340

        # --- Girth Parameters ---
        self._ball_girth = Last.DEFAULT_BALL_GIRTH
        self._instep_girth = Last.DEFAULT_INSTEP_GIRTH
        self._waist_girth = Last.DEFAULT_WAIST_GIRTH
        self._waist2_girth = Last.DEFAULT_WAIST2_GIRTH
        self._arch_girth = Last.DEFAULT_ARCH_GIRTH
        self._heel_girth = Last.DEFAULT_HEEL_GIRTH
        self._ankle_girth = Last.DEFAULT_ANKLE_GIRTH

        # --- Girth Multipliers ---
        self._ball_girth_mult = 0.889
        self._instep_girth_mult = 0.852
        self._waist_girth_mult = 0.815
        self._waist2_girth_mult = 0.833
        self._arch_girth_mult = 0.852
        self._heel_girth_mult = 1.148
        self._ankle_girth_mult = 0.889

        # --- Height Parameters ---
        self._heel_height = Last.DEFAULT_HEEL_HEIGHT
        self._toe_spring = Last.DEFAULT_TOE_SPRING
        self._ball_height = 0.0
        self._instep_height = 0.0
        self._waist_height = 0.0
        self._waist2_height = 0.0
        self._arch_height = 0.0
        self._ankle_height = 0.0
        self._cone_height = 0.0
        self._crown_height = 0.0
        self._back_height = 0.0
        self._feather_line_height_ball = 0.0
        self._feather_line_height_toe = 0.0
        self._feather_line_height_waist = 0.0
        self._feather_line_height_heel = 0.0
        self._top_line_height_ball = 0.0
        self._top_line_height_instep = 0.0
        self._top_line_height_waist = 0.0
        self._top_line_height_heel = 0.0

        # --- Height Multipliers ---
        self._heel_height_mult = 0.093
        self._toe_spring_mult = 0.056
        self._ball_height_mult = 0.130
        self._instep_height_mult = 0.220
        self._waist_height_mult = 0.170
        self._waist2_height_mult = 0.185
        self._arch_height_mult = 0.200
        self._ankle_height_mult = 0.260
        self._cone_height_mult = 0.050
        self._crown_height_mult = 0.240
        self._back_height_mult = 0.260

        # --- Allowance Parameters ---
        self._allowance_length = 12.0
        self._allowance_ball_girth = 0.0
        self._allowance_ball_width = 0.0
        self._allowance_heel_width = 0.0
        self._allowance_instep_girth = 0.0
        self._allowance_waist_girth = 0.0
        self._allowance_waist2_girth = 0.0
        self._allowance_arch_girth = 0.0
        self._allowance_heel_girth = 0.0
        self._allowance_ankle_girth = 0.0
        self._allowance_toe_spring = 0.0
        self._allowance_heel_height = 0.0
        self._allowance_cone_height = 0.0
        self._allowance_crown_height = 0.0
        self._allowance_back_height = 0.0

        # --- Angle Parameters ---
        self._ball_break_point_angle = 0.0
        self._ball_line_angle = 7.0
        self._alpha_cut_tilt_from_main_plane = 0.0
        self._heel_pitch_angle = 0.0
        self._toe_recede_angle = 15.0
        self._cone_angle = 0.0
        self._back_curve_angle = 0.0
        self._feather_line_angle_ball = 0.0
        self._feather_line_angle_toe = 0.0
        self._feather_line_angle_waist = 0.0
        self._feather_line_angle_heel = 0.0

        # --- Style Parameters ---
        self._toe_style = Last.TOE_STYLE_ROUND
        self._back_edge_shape = Last.BACK_EDGE_ROUND
        self._bottom_type = Last.BOTTOM_TYPE_FLAT
        self._arch_type = Last.ARCH_TYPE_MEDIUM
        self._toe_profile_shape = "Standard"
        self._toe_box_shape = "Standard"
        self._toe_box_height_factor = 1.0
        self._toe_box_width_factor = 1.0
        self._toe_taper_factor = 0.5
        self._toe_radius = 15.0
        self._toe_asymmetry = 0.5
        self._back_curve_depth = 3.0
        self._shank_curve = 0.5
        self._feather_edge_type = "Standard"
        self._crown_shape = "Standard"

        # --- Toe Style-Specific Parameters ---
        self._toe_style_pointed_angle = 25.0
        self._toe_style_pointed_tip_radius = 5.0
        self._toe_style_square_corner_radius = 8.0
        self._toe_style_square_width_factor = 0.85
        self._toe_style_oblique_shift = 0.3
        self._toe_style_oblique_angle = 12.0
        self._toe_style_almond_length_factor = 1.1
        self._toe_style_almond_width_factor = 0.75
        self._toe_style_round_radius_factor = 1.0
        self._toe_tip_thickness = 12.0
        self._toe_tip_drop = 0.0

        # --- Cross Section Parameters (C1C through C5C) ---
        # Each cross section has lateral(l) and medial(m) sides
        # with depth, offset, angle, height, A1/A2/A3 parameters
        self._init_cross_section_params()

        # --- BottomLine (BL) Curve IDs ---
        self._bl_mesh = Guid.Empty  # BLMesh
        self._bl_b = Guid.Empty     # BL at Ball
        self._bl_h = Guid.Empty     # BL at Heel
        self._bl_i = Guid.Empty     # BL at Instep
        self._bl_s = Guid.Empty     # BL at Shank
        self._bl_t = Guid.Empty     # BL at Toe
        self._bl_v = Guid.Empty     # BL at V (apex)
        self._bl_ia = Guid.Empty    # BL InnerArch
        self._bl_tc = Guid.Empty    # BL ToeCap
        self._bl_tw = Guid.Empty    # BL ToeWing
        self._bl_cw = Guid.Empty    # BL ConeWing
        self._bl_full = Guid.Empty  # BL Full (complete bottom line)
        self._bl_lateral = Guid.Empty
        self._bl_medial = Guid.Empty
        self._bl_forepart = Guid.Empty
        self._bl_backpart = Guid.Empty

        # --- CenterLine (CL) Curve IDs ---
        self._cl_b = Guid.Empty     # CLb - CenterLine bottom
        self._cl_t = Guid.Empty     # CLt - CenterLine top
        self._cl_bw = Guid.Empty    # CLBW - CenterLine BottomWidth
        self._cl_tw = Guid.Empty    # CLTW - CenterLine TopWidth
        self._cl_tp_xz = Guid.Empty  # CLTPxz
        self._cl_hg_l = Guid.Empty  # CLHGl - CenterLine HeelGirth lateral
        self._cl_hg_m = Guid.Empty  # CLHGm - CenterLine HeelGirth medial
        self._cl_full = Guid.Empty
        self._cl_lateral = Guid.Empty
        self._cl_medial = Guid.Empty

        # --- Cross Section Curves (C1C - C5C) ---
        # Each has lateral(l), medial(m), anterior(a), posterior(p)
        self._c1c = Guid.Empty
        self._c1c_l = Guid.Empty
        self._c1c_m = Guid.Empty
        self._c1c_a = Guid.Empty
        self._c1c_p = Guid.Empty
        self._c2c = Guid.Empty
        self._c2c_l = Guid.Empty
        self._c2c_m = Guid.Empty
        self._c2c_a = Guid.Empty
        self._c2c_p = Guid.Empty
        self._c3c = Guid.Empty
        self._c3c_l = Guid.Empty
        self._c3c_m = Guid.Empty
        self._c3c_a = Guid.Empty
        self._c3c_p = Guid.Empty
        self._c4c = Guid.Empty
        self._c4c_l = Guid.Empty
        self._c4c_m = Guid.Empty
        self._c4c_a = Guid.Empty
        self._c4c_p = Guid.Empty
        self._c5c = Guid.Empty
        self._c5c_l = Guid.Empty
        self._c5c_m = Guid.Empty
        self._c5c_a = Guid.Empty
        self._c5c_p = Guid.Empty

        # --- AlphaJoint (CA) Curve IDs ---
        self._ca = Guid.Empty
        self._ca_l = Guid.Empty
        self._ca_m = Guid.Empty

        # --- Heel (CH) Curve IDs ---
        self._ch = Guid.Empty
        self._ch_l = Guid.Empty
        self._ch_m = Guid.Empty

        # --- Girth Section Curve IDs ---
        self._cbg = Guid.Empty   # BallGirth
        self._cbg_l = Guid.Empty
        self._cbg_m = Guid.Empty
        self._cig = Guid.Empty   # InstepGirth
        self._cig_l = Guid.Empty
        self._cig_m = Guid.Empty
        self._cwg = Guid.Empty   # WaistGirth
        self._cwg_l = Guid.Empty
        self._cwg_m = Guid.Empty
        self._cw2g = Guid.Empty  # Waist2Girth
        self._cw2g_l = Guid.Empty
        self._cw2g_m = Guid.Empty

        # --- ShankBoard (CSB) Curve IDs ---
        self._csb_arch = Guid.Empty
        self._csb_ball = Guid.Empty
        self._csb_heel = Guid.Empty
        self._csb_heel_back = Guid.Empty
        self._csb_instep = Guid.Empty
        self._csb_toe = Guid.Empty
        self._csb_toe_front = Guid.Empty
        self._csb_waist = Guid.Empty
        self._csb_full = Guid.Empty

        # --- Other specialized curves ---
        self._cst = Guid.Empty        # CST
        self._cshg = Guid.Empty       # CSHG
        self._clhg = Guid.Empty       # CLHG

        # --- Local Planes for each cross section ---
        self._c1c_local_plane = Plane.WorldXY
        self._c2c_local_plane = Plane.WorldXY
        self._c3c_local_plane = Plane.WorldXY
        self._c4c_local_plane = Plane.WorldXY
        self._c5c_local_plane = Plane.WorldXY
        self._ca_local_plane = Plane.WorldXY
        self._ch_local_plane = Plane.WorldXY
        self._cbg_local_plane = Plane.WorldXY
        self._cig_local_plane = Plane.WorldXY
        self._cwg_local_plane = Plane.WorldXY
        self._cw2g_local_plane = Plane.WorldXY

        # --- Viewing Planes for each cross section ---
        self._c1c_viewing_plane = Plane.WorldXY
        self._c2c_viewing_plane = Plane.WorldXY
        self._c3c_viewing_plane = Plane.WorldXY
        self._c4c_viewing_plane = Plane.WorldXY
        self._c5c_viewing_plane = Plane.WorldXY
        self._ca_viewing_plane = Plane.WorldXY
        self._ch_viewing_plane = Plane.WorldXY
        self._cbg_viewing_plane = Plane.WorldXY
        self._cig_viewing_plane = Plane.WorldXY
        self._cwg_viewing_plane = Plane.WorldXY
        self._cw2g_viewing_plane = Plane.WorldXY

        # --- Body geometry IDs ---
        self._body_main = Guid.Empty
        self._body_main_subd = Guid.Empty
        self._body_scrap_cutter = Guid.Empty
        self._body_sole_cutter = Guid.Empty
        self._body_sole_cutter_flat = Guid.Empty
        self._body_sole_cutter_wedge = Guid.Empty
        self._body_sole_cutter_heel = Guid.Empty
        self._body_mesh = Guid.Empty
        self._body_surface = Guid.Empty

        # --- Key Points ---
        self._ball_point = Point3d.Origin
        self._heel_point = Point3d.Origin
        self._toe_point = Point3d.Origin
        self._instep_point = Point3d.Origin
        self._waist_point = Point3d.Origin
        self._waist2_point = Point3d.Origin
        self._arch_point = Point3d.Origin
        self._ankle_point = Point3d.Origin
        self._cone_point = Point3d.Origin
        self._crown_point = Point3d.Origin
        self._alpha_joint_point = Point3d.Origin
        self._back_point = Point3d.Origin
        self._ball_break_point = Point3d.Origin
        self._tread_point = Point3d.Origin

        # --- Style Parameter Dictionary (for serialization) ---
        self._last_style_parameter_dictionary = {}

    def _init_cross_section_params(self):
        """Initialize cross-section parameters for sections C1C-C5C."""
        sections = ["c1c", "c2c", "c3c", "c4c", "c5c"]
        for sec in sections:
            # CS (cross-section shape factor)
            setattr(self, f"_{sec}_cs_l", 0.5)
            setattr(self, f"_{sec}_cs_m", 0.5)
            # Depth
            setattr(self, f"_{sec}_depth_l", 0.0)
            setattr(self, f"_{sec}_depth_m", 0.0)
            # Offset
            setattr(self, f"_{sec}_offset_l", 0.0)
            setattr(self, f"_{sec}_offset_m", 0.0)
            # Angle
            setattr(self, f"_{sec}_angle_l", 0.0)
            setattr(self, f"_{sec}_angle_m", 0.0)
            # Height
            setattr(self, f"_{sec}_height_l", 0.0)
            setattr(self, f"_{sec}_height_m", 0.0)
            # A1, A2, A3 shape parameters
            for a in ["a1", "a2", "a3"]:                setattr(self, f"_{sec}_{a}_l", 0.5)
                setattr(self, f"_{sec}_{a}_m", 0.5)

    # =========================================================================
    # Factory / Lifecycle Methods
    # =========================================================================

    def Clone(self):
        """Create a deep copy of this Last instance."""
        return copy.deepcopy(self)

    @staticmethod
    def Create():
        """Create a new Last with default parameters and calculated tertiary values."""
        last = Last()
        last.SetDefaultLastGeneralStyleParameters()
        last.SetDefaultLastToeStyleParameters()
        last.CalculateLinearMeasurementsFromMults()
        last.CalculateTertiaryParameters()
        return last

    @staticmethod
    def CreateViaJSon(json_data):
        """Create a Last from a JSON string or dictionary.

        Args:
            json_data: A JSON string or dictionary with last parameters.

        Returns:
            A new Last instance populated from the JSON data.
        """
        last = Last()
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        # Map JSON keys to properties
        key_map = {
            "Name": "_name",
            "Side": "_side",
            "Size": "_size",
            "SizeSystem": "_size_system",
            "Notes": "_notes",
            "Length": "_length",
            "BallLineLength": "_ball_line_length",
            "ArchLength": "_arch_length",
            "WaistLength": "_waist_length",
            "Waist2Length": "_waist2_length",
            "InstepLength": "_instep_length",
            "HeelGirthLength": "_heel_girth_length",
            "AnkleLength": "_ankle_length",
            "BallWidth": "_ball_width",
            "BallWidthPerp": "_ball_width_perp",
            "HeelWidth": "_heel_width",
            "BallGirth": "_ball_girth",
            "InstepGirth": "_instep_girth",
            "WaistGirth": "_waist_girth",
            "Waist2Girth": "_waist2_girth",
            "ArchGirth": "_arch_girth",
            "HeelGirth": "_heel_girth",
            "AnkleGirth": "_ankle_girth",
            "HeelHeight": "_heel_height",
            "ToeSpring": "_toe_spring",
            "AllowanceLength": "_allowance_length",
            "AllowanceBallGirth": "_allowance_ball_girth",
            "AllowanceBallWidth": "_allowance_ball_width",
            "AllowanceHeelWidth": "_allowance_heel_width",
            "BallBreakPointAngle": "_ball_break_point_angle",
            "BallLineAngle": "_ball_line_angle",
            "AlphaCutTiltFromMainPlane": "_alpha_cut_tilt_from_main_plane",
            "ToeStyle": "_toe_style",
            "BackEdgeShape": "_back_edge_shape",
            "BottomType": "_bottom_type",
            "ArchType": "_arch_type",
        }

        for json_key, attr_name in key_map.items():
            if json_key in data:
                setattr(last, attr_name, data[json_key])

        # Load multipliers if present
        mult_keys = {
            "BallLineLengthMult": "_ball_line_length_mult",
            "ArchLengthMult": "_arch_length_mult",
            "WaistLengthMult": "_waist_length_mult",
            "Waist2LengthMult": "_waist2_length_mult",
            "InstepLengthMult": "_instep_length_mult",
            "BallWidthMult": "_ball_width_mult",
            "HeelWidthMult": "_heel_width_mult",
            "BallGirthMult": "_ball_girth_mult",
            "InstepGirthMult": "_instep_girth_mult",
            "WaistGirthMult": "_waist_girth_mult",
            "Waist2GirthMult": "_waist2_girth_mult",
            "ArchGirthMult": "_arch_girth_mult",
            "HeelGirthMult": "_heel_girth_mult",
            "AnkleGirthMult": "_ankle_girth_mult",
            "HeelHeightMult": "_heel_height_mult",
            "ToeSpringMult": "_toe_spring_mult",
        }

        for json_key, attr_name in mult_keys.items():
            if json_key in data:
                setattr(last, attr_name, data[json_key])

        # Load style-specific parameters
        if "LastStyleParameterDictionary" in data:
            last._last_style_parameter_dictionary = data["LastStyleParameterDictionary"]

        # Recalculate derived values
        last.CalculateLinearMeasurementsFromMults()
        last.CalculateTertiaryParameters()

        return last

    # =========================================================================
    # Parameter Collection Methods
    # =========================================================================

    def CollectLastParameters(self):
        """Collect all last parameters into a dictionary for serialization.

        Returns:
            Dictionary with all last parameter key-value pairs.
        """
        params = {}
        # Identification
        params["Name"] = self._name
        params["Side"] = self._side
        params["Size"] = self._size
        params["SizeSystem"] = self._size_system
        params["Notes"] = self._notes

        # Lengths
        params["Length"] = self._length
        params["BallLineLength"] = self._ball_line_length
        params["ArchLength"] = self._arch_length
        params["WaistLength"] = self._waist_length
        params["Waist2Length"] = self._waist2_length
        params["InstepLength"] = self._instep_length
        params["HeelGirthLength"] = self._heel_girth_length
        params["AnkleLength"] = self._ankle_length

        # Length Multipliers
        params["BallLineLengthMult"] = self._ball_line_length_mult
        params["ArchLengthMult"] = self._arch_length_mult
        params["WaistLengthMult"] = self._waist_length_mult
        params["Waist2LengthMult"] = self._waist2_length_mult
        params["InstepLengthMult"] = self._instep_length_mult

        # Widths
        params["BallWidth"] = self._ball_width
        params["BallWidthPerp"] = self._ball_width_perp
        params["HeelWidth"] = self._heel_width
        params["WaistWidth"] = self._waist_width
        params["Waist2Width"] = self._waist2_width
        params["InstepWidth"] = self._instep_width

        # Girths
        params["BallGirth"] = self._ball_girth
        params["InstepGirth"] = self._instep_girth
        params["WaistGirth"] = self._waist_girth
        params["Waist2Girth"] = self._waist2_girth
        params["ArchGirth"] = self._arch_girth
        params["HeelGirth"] = self._heel_girth
        params["AnkleGirth"] = self._ankle_girth

        # Heights
        params["HeelHeight"] = self._heel_height
        params["ToeSpring"] = self._toe_spring

        # Allowances
        params["AllowanceLength"] = self._allowance_length
        params["AllowanceBallGirth"] = self._allowance_ball_girth
        params["AllowanceBallWidth"] = self._allowance_ball_width
        params["AllowanceHeelWidth"] = self._allowance_heel_width

        # Angles
        params["BallBreakPointAngle"] = self._ball_break_point_angle
        params["BallLineAngle"] = self._ball_line_angle
        params["AlphaCutTiltFromMainPlane"] = self._alpha_cut_tilt_from_main_plane

        # Styles
        params["ToeStyle"] = self._toe_style
        params["BackEdgeShape"] = self._back_edge_shape
        params["BottomType"] = self._bottom_type
        params["ArchType"] = self._arch_type

        # Style dictionary
        params["LastStyleParameterDictionary"] = self._last_style_parameter_dictionary

        return params

    def CollectLastGeneralStyleParameters(self):
        """Collect general style parameters into the style dictionary.

        Returns:
            Dictionary of general style parameters.
        """
        style_params = {}
        style_params["ToeStyle"] = self._toe_style
        style_params["BackEdgeShape"] = self._back_edge_shape
        style_params["BottomType"] = self._bottom_type
        style_params["ArchType"] = self._arch_type
        style_params["ToeProfileShape"] = self._toe_profile_shape
        style_params["ToeBoxShape"] = self._toe_box_shape
        style_params["ToeBoxHeightFactor"] = self._toe_box_height_factor
        style_params["ToeBoxWidthFactor"] = self._toe_box_width_factor
        style_params["ToeTaperFactor"] = self._toe_taper_factor
        style_params["ToeRadius"] = self._toe_radius
        style_params["ToeAsymmetry"] = self._toe_asymmetry
        style_params["BackCurveDepth"] = self._back_curve_depth
        style_params["ShankCurve"] = self._shank_curve
        style_params["FeatherEdgeType"] = self._feather_edge_type
        style_params["CrownShape"] = self._crown_shape
        style_params["HeelPitchAngle"] = self._heel_pitch_angle
        style_params["ToeRecedeAngle"] = self._toe_recede_angle
        style_params["BackCurveAngle"] = self._back_curve_angle
        return style_params

    def CollectLastToeStyleParameters(self):
        """Collect toe style-specific parameters.

        Returns:
            Dictionary of toe style parameters.
        """
        toe_params = {}
        toe_params["ToeStyle"] = self._toe_style
        toe_params["ToeStylePointedAngle"] = self._toe_style_pointed_angle
        toe_params["ToeStylePointedTipRadius"] = self._toe_style_pointed_tip_radius
        toe_params["ToeStyleSquareCornerRadius"] = self._toe_style_square_corner_radius
        toe_params["ToeStyleSquareWidthFactor"] = self._toe_style_square_width_factor
        toe_params["ToeStyleObliqueShift"] = self._toe_style_oblique_shift
        toe_params["ToeStyleObliqueAngle"] = self._toe_style_oblique_angle
        toe_params["ToeStyleAlmondLengthFactor"] = self._toe_style_almond_length_factor
        toe_params["ToeStyleAlmondWidthFactor"] = self._toe_style_almond_width_factor
        toe_params["ToeStyleRoundRadiusFactor"] = self._toe_style_round_radius_factor
        toe_params["ToeTipThickness"] = self._toe_tip_thickness
        toe_params["ToeTipDrop"] = self._toe_tip_drop
        return toe_params

    # =========================================================================
    # Default Parameter Methods
    # =========================================================================

    def SetDefaultLastGeneralStyleParameters(self):
        """Set all general style parameters to their default values."""
        self._toe_style = Last.TOE_STYLE_ROUND
        self._back_edge_shape = Last.BACK_EDGE_ROUND
        self._bottom_type = Last.BOTTOM_TYPE_FLAT
        self._arch_type = Last.ARCH_TYPE_MEDIUM
        self._toe_profile_shape = "Standard"
        self._toe_box_shape = "Standard"
        self._toe_box_height_factor = 1.0
        self._toe_box_width_factor = 1.0
        self._toe_taper_factor = 0.5
        self._toe_radius = 15.0
        self._toe_asymmetry = 0.5
        self._back_curve_depth = 3.0
        self._shank_curve = 0.5
        self._feather_edge_type = "Standard"
        self._crown_shape = "Standard"
        self._heel_pitch_angle = 0.0
        self._toe_recede_angle = 15.0
        self._back_curve_angle = 0.0

    def SetDefaultLastToeStyleParameters(self):
        """Set toe style-specific parameters to defaults based on current ToeStyle."""
        if self._toe_style == Last.TOE_STYLE_ROUND:
            self._toe_style_round_radius_factor = 1.0
            self._toe_tip_thickness = 12.0
            self._toe_tip_drop = 0.0
        elif self._toe_style == Last.TOE_STYLE_POINTED:
            self._toe_style_pointed_angle = 25.0
            self._toe_style_pointed_tip_radius = 5.0
            self._toe_tip_thickness = 10.0
            self._toe_tip_drop = 0.0
        elif self._toe_style == Last.TOE_STYLE_SQUARE:
            self._toe_style_square_corner_radius = 8.0
            self._toe_style_square_width_factor = 0.85
            self._toe_tip_thickness = 14.0
            self._toe_tip_drop = 0.0
        elif self._toe_style == Last.TOE_STYLE_OBLIQUE:
            self._toe_style_oblique_shift = 0.3
            self._toe_style_oblique_angle = 12.0
            self._toe_tip_thickness = 12.0
            self._toe_tip_drop = 0.0
        elif self._toe_style == Last.TOE_STYLE_ALMOND:
            self._toe_style_almond_length_factor = 1.1
            self._toe_style_almond_width_factor = 0.75
            self._toe_tip_thickness = 11.0
            self._toe_tip_drop = 0.0

    # =========================================================================
    # Calculation Methods
    # =========================================================================

    def CalculateLinearMeasurementsFromMults(self):
        """Calculate all linear measurements from their multiplier values.

        Uses the base Length to derive all proportional measurements:
        section_length = Length * section_mult, etc.
        """
        length = self._length

        # Lengths from multipliers
        self._ball_line_length = length * self._ball_line_length_mult
        self._arch_length = length * self._arch_length_mult
        self._waist_length = length * self._waist_length_mult
        self._waist2_length = length * self._waist2_length_mult
        self._instep_length = length * self._instep_length_mult
        self._heel_girth_length = length * self._heel_girth_length_mult
        self._ankle_length = length * self._ankle_length_mult
        self._toe_length = length * self._toe_length_mult
        self._alpha_joint_length = length * self._alpha_joint_length_mult
        self._cone_length = length * self._cone_length_mult
        self._tread_length = length * self._tread_length_mult
        self._forepart_length = length * self._forepart_length_mult
        self._backpart_length = length * self._backpart_length_mult

        # Widths from multipliers
        self._ball_width = length * self._ball_width_mult
        self._ball_width_perp = length * self._ball_width_perp_mult
        self._heel_width = length * self._heel_width_mult
        self._waist_width = length * self._waist_width_mult
        self._waist2_width = length * self._waist2_width_mult
        self._instep_width = length * self._instep_width_mult
        self._toe_width = length * self._toe_width_mult
        self._alpha_joint_width = length * self._alpha_joint_width_mult
        self._arch_width = length * self._arch_width_mult
        self._ankle_width = length * self._ankle_width_mult
        self._cone_width = length * self._cone_width_mult
        self._tread_width = length * self._tread_width_mult

        # Lateral/medial width splits (default 50/50)
        self._ball_width_lateral = self._ball_width * 0.48
        self._ball_width_medial = self._ball_width * 0.52
        self._heel_width_lateral = self._heel_width * 0.50
        self._heel_width_medial = self._heel_width * 0.50

        # Girths from multipliers
        self._ball_girth = length * self._ball_girth_mult
        self._instep_girth = length * self._instep_girth_mult
        self._waist_girth = length * self._waist_girth_mult
        self._waist2_girth = length * self._waist2_girth_mult
        self._arch_girth = length * self._arch_girth_mult
        self._heel_girth = length * self._heel_girth_mult
        self._ankle_girth = length * self._ankle_girth_mult

        # Heights from multipliers
        self._heel_height = length * self._heel_height_mult
        self._toe_spring = length * self._toe_spring_mult
        self._ball_height = length * self._ball_height_mult
        self._instep_height = length * self._instep_height_mult
        self._waist_height = length * self._waist_height_mult
        self._waist2_height = length * self._waist2_height_mult
        self._arch_height = length * self._arch_height_mult
        self._ankle_height = length * self._ankle_height_mult
        self._cone_height = length * self._cone_height_mult
        self._crown_height = length * self._crown_height_mult
        self._back_height = length * self._back_height_mult

    def CalculateTertiaryParameters(self):
        """Calculate tertiary (derived) parameters from primary and secondary values.

        Computes feather-line heights, top-line heights, cross-section
        angles, and key anatomical point positions from existing parameters.
        """
        # Feather line heights (bottom edge of the last)
        self._feather_line_height_ball = self._toe_spring * 0.3
        self._feather_line_height_toe = self._toe_spring
        self._feather_line_height_waist = self._heel_height * 0.4
        self._feather_line_height_heel = self._heel_height

        # Top line heights
        self._top_line_height_ball = self._ball_height + self._feather_line_height_ball
        self._top_line_height_instep = self._instep_height + self._feather_line_height_waist
        self._top_line_height_waist = self._waist_height + self._feather_line_height_waist
        self._top_line_height_heel = self._back_height + self._feather_line_height_heel

        # Ball break point angle from ball line length and width
        if self._ball_width > 0:
            import math
            self._ball_break_point_angle = math.degrees(
                math.atan2(self._ball_width_medial - self._ball_width_lateral,
                           self._ball_line_length * 0.1)
            )

        # Feather line angles
        if self._ball_line_length > 0:
            import math
            rise = self._feather_line_height_toe - self._feather_line_height_ball
            run = self._ball_line_length
            self._feather_line_angle_toe = math.degrees(math.atan2(rise, run))
            self._feather_line_angle_ball = self._feather_line_angle_toe * 0.5
            self._feather_line_angle_waist = 0.0
            self._feather_line_angle_heel = 0.0

        # Key anatomical points (positioned along the X axis from heel=0 to toe=Length)
        self._heel_point = Point3d(0.0, 0.0, self._heel_height)
        self._toe_point = Point3d(self._length, 0.0, self._toe_spring)
        self._ball_point = Point3d(
            self._length - self._ball_line_length,
            0.0,
            self._feather_line_height_ball
        )
        self._instep_point = Point3d(
            self._length - self._instep_length * (self._length / self._ball_line_length) if self._ball_line_length > 0 else 0,
            0.0,
            self._top_line_height_instep
        )
        self._waist_point = Point3d(
            self._length * (1.0 - self._waist_length_mult),
            0.0,
            self._waist_height + self._feather_line_height_waist
        )
        self._waist2_point = Point3d(
            self._length * (1.0 - self._waist2_length_mult),
            0.0,
            self._waist2_height + self._feather_line_height_waist
        )
        self._arch_point = Point3d(
            self._length * (1.0 - self._arch_length_mult),
            0.0,
            self._arch_height
        )
        self._ankle_point = Point3d(
            self._length * (1.0 - self._ankle_length_mult),
            0.0,
            self._ankle_height
        )
        self._cone_point = Point3d(
            self._length * self._cone_length_mult,
            0.0,
            self._cone_height
        )
        self._crown_point = Point3d(
            self._length * 0.5,
            0.0,
            self._crown_height
        )
        self._alpha_joint_point = Point3d(
            self._length - self._alpha_joint_length,
            0.0,
            self._ball_height
        )
        self._back_point = Point3d(
            0.0,
            0.0,
            self._back_height + self._heel_height
        )
        self._ball_break_point = Point3d(
            self._length - self._ball_line_length,
            0.0,
            0.0
        )
        self._tread_point = Point3d(
            self._length - self._tread_length,
            0.0,
            0.0
        )

    # =========================================================================
    # Properties - Identification
    # =========================================================================

    @property
    def Name(self):
        """Name/identifier for this last."""
        return self._name

    @Name.setter
    def Name(self, value):
        self._name = str(value)

    @property
    def Side(self):
        """Side: 'Right' or 'Left'."""
        return self._side

    @Side.setter
    def Side(self, value):
        self._side = str(value)

    @property
    def Size(self):
        """Shoe size designation."""
        return self._size

    @Size.setter
    def Size(self, value):
        self._size = str(value)

    @property
    def SizeSystem(self):
        """Size system (EU, US, UK, etc.)."""
        return self._size_system

    @SizeSystem.setter
    def SizeSystem(self, value):
        self._size_system = str(value)

    @property
    def Notes(self):
        """Free-form notes."""
        return self._notes

    @Notes.setter
    def Notes(self, value):
        self._notes = str(value)

    # =========================================================================
    # Properties - Length Parameters
    # =========================================================================

    @property
    def Length(self):
        """Overall last length in mm."""
        return self._length

    @Length.setter
    def Length(self, value):
        self._length = float(value)

    @property
    def BallLineLength(self):
        """Distance from heel to ball line."""
        return self._ball_line_length

    @BallLineLength.setter
    def BallLineLength(self, value):
        self._ball_line_length = float(value)

    @property
    def ArchLength(self):
        """Distance from heel to arch."""
        return self._arch_length

    @ArchLength.setter
    def ArchLength(self, value):
        self._arch_length = float(value)

    @property
    def WaistLength(self):
        """Distance from heel to waist."""
        return self._waist_length

    @WaistLength.setter
    def WaistLength(self, value):
        self._waist_length = float(value)

    @property
    def Waist2Length(self):
        """Distance from heel to second waist measurement."""
        return self._waist2_length

    @Waist2Length.setter
    def Waist2Length(self, value):
        self._waist2_length = float(value)

    @property
    def InstepLength(self):
        """Distance from heel to instep."""
        return self._instep_length

    @InstepLength.setter
    def InstepLength(self, value):
        self._instep_length = float(value)

    @property
    def HeelGirthLength(self):
        """Distance from heel to heel girth measurement point."""
        return self._heel_girth_length

    @HeelGirthLength.setter
    def HeelGirthLength(self, value):
        self._heel_girth_length = float(value)

    @property
    def AnkleLength(self):
        """Distance from heel to ankle."""
        return self._ankle_length

    @AnkleLength.setter
    def AnkleLength(self, value):
        self._ankle_length = float(value)

    @property
    def ToeLength(self):
        """Distance from heel to toe section."""
        return self._toe_length

    @ToeLength.setter
    def ToeLength(self, value):
        self._toe_length = float(value)

    @property
    def AlphaJointLength(self):
        """Distance from heel to alpha joint."""
        return self._alpha_joint_length

    @AlphaJointLength.setter
    def AlphaJointLength(self, value):
        self._alpha_joint_length = float(value)

    @property
    def ConeLength(self):
        """Distance from heel to cone."""
        return self._cone_length

    @ConeLength.setter
    def ConeLength(self, value):
        self._cone_length = float(value)

    @property
    def TreadLength(self):
        """Tread length."""
        return self._tread_length

    @TreadLength.setter
    def TreadLength(self, value):
        self._tread_length = float(value)

    @property
    def ForepartLength(self):
        """Forepart length."""
        return self._forepart_length

    @ForepartLength.setter
    def ForepartLength(self, value):
        self._forepart_length = float(value)

    @property
    def BackpartLength(self):
        """Backpart length."""
        return self._backpart_length

    @BackpartLength.setter
    def BackpartLength(self, value):
        self._backpart_length = float(value)

    # =========================================================================
    # Properties - Length Multipliers
    # =========================================================================

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
    def Waist2LengthMult(self):
        return self._waist2_length_mult

    @Waist2LengthMult.setter
    def Waist2LengthMult(self, value):
        self._waist2_length_mult = float(value)

    @property
    def InstepLengthMult(self):
        return self._instep_length_mult

    @InstepLengthMult.setter
    def InstepLengthMult(self, value):
        self._instep_length_mult = float(value)

    @property
    def HeelGirthLengthMult(self):
        return self._heel_girth_length_mult

    @HeelGirthLengthMult.setter
    def HeelGirthLengthMult(self, value):
        self._heel_girth_length_mult = float(value)

    @property
    def AnkleLengthMult(self):
        return self._ankle_length_mult

    @AnkleLengthMult.setter
    def AnkleLengthMult(self, value):
        self._ankle_length_mult = float(value)

    @property
    def ToeLengthMult(self):
        return self._toe_length_mult

    @ToeLengthMult.setter
    def ToeLengthMult(self, value):
        self._toe_length_mult = float(value)

    @property
    def AlphaJointLengthMult(self):
        return self._alpha_joint_length_mult

    @AlphaJointLengthMult.setter
    def AlphaJointLengthMult(self, value):
        self._alpha_joint_length_mult = float(value)

    @property
    def ConeLengthMult(self):
        return self._cone_length_mult

    @ConeLengthMult.setter
    def ConeLengthMult(self, value):
        self._cone_length_mult = float(value)

    @property
    def TreadLengthMult(self):
        return self._tread_length_mult

    @TreadLengthMult.setter
    def TreadLengthMult(self, value):
        self._tread_length_mult = float(value)

    @property
    def ForepartLengthMult(self):
        return self._forepart_length_mult

    @ForepartLengthMult.setter
    def ForepartLengthMult(self, value):
        self._forepart_length_mult = float(value)

    @property
    def BackpartLengthMult(self):
        return self._backpart_length_mult

    @BackpartLengthMult.setter
    def BackpartLengthMult(self, value):
        self._backpart_length_mult = float(value)

    # =========================================================================
    # Properties - Width Parameters
    # =========================================================================

    @property
    def BallWidth(self):
        """Ball width in mm."""
        return self._ball_width

    @BallWidth.setter
    def BallWidth(self, value):
        self._ball_width = float(value)

    @property
    def BallWidthPerp(self):
        """Ball width measured perpendicular to the center line."""
        return self._ball_width_perp

    @BallWidthPerp.setter
    def BallWidthPerp(self, value):
        self._ball_width_perp = float(value)

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
        """Heel width in mm."""
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
    def WaistWidth(self):
        return self._waist_width

    @WaistWidth.setter
    def WaistWidth(self, value):
        self._waist_width = float(value)

    @property
    def Waist2Width(self):
        return self._waist2_width

    @Waist2Width.setter
    def Waist2Width(self, value):
        self._waist2_width = float(value)

    @property
    def InstepWidth(self):
        return self._instep_width

    @InstepWidth.setter
    def InstepWidth(self, value):
        self._instep_width = float(value)

    @property
    def ToeWidth(self):
        return self._toe_width

    @ToeWidth.setter
    def ToeWidth(self, value):
        self._toe_width = float(value)

    @property
    def AlphaJointWidth(self):
        return self._alpha_joint_width

    @AlphaJointWidth.setter
    def AlphaJointWidth(self, value):
        self._alpha_joint_width = float(value)

    @property
    def ArchWidth(self):
        return self._arch_width

    @ArchWidth.setter
    def ArchWidth(self, value):
        self._arch_width = float(value)

    @property
    def AnkleWidth(self):
        return self._ankle_width

    @AnkleWidth.setter
    def AnkleWidth(self, value):
        self._ankle_width = float(value)

    @property
    def ConeWidth(self):
        return self._cone_width

    @ConeWidth.setter
    def ConeWidth(self, value):
        self._cone_width = float(value)

    @property
    def TreadWidth(self):
        return self._tread_width

    @TreadWidth.setter
    def TreadWidth(self, value):
        self._tread_width = float(value)

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
    def BallWidthPerpMult(self):
        return self._ball_width_perp_mult

    @BallWidthPerpMult.setter
    def BallWidthPerpMult(self, value):
        self._ball_width_perp_mult = float(value)

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
    def Waist2WidthMult(self):
        return self._waist2_width_mult

    @Waist2WidthMult.setter
    def Waist2WidthMult(self, value):
        self._waist2_width_mult = float(value)

    @property
    def InstepWidthMult(self):
        return self._instep_width_mult

    @InstepWidthMult.setter
    def InstepWidthMult(self, value):
        self._instep_width_mult = float(value)

    @property
    def ToeWidthMult(self):
        return self._toe_width_mult

    @ToeWidthMult.setter
    def ToeWidthMult(self, value):
        self._toe_width_mult = float(value)

    @property
    def AlphaJointWidthMult(self):
        return self._alpha_joint_width_mult

    @AlphaJointWidthMult.setter
    def AlphaJointWidthMult(self, value):
        self._alpha_joint_width_mult = float(value)

    @property
    def ArchWidthMult(self):
        return self._arch_width_mult

    @ArchWidthMult.setter
    def ArchWidthMult(self, value):
        self._arch_width_mult = float(value)

    @property
    def AnkleWidthMult(self):
        return self._ankle_width_mult

    @AnkleWidthMult.setter
    def AnkleWidthMult(self, value):
        self._ankle_width_mult = float(value)

    @property
    def ConeWidthMult(self):
        return self._cone_width_mult

    @ConeWidthMult.setter
    def ConeWidthMult(self, value):
        self._cone_width_mult = float(value)

    @property
    def TreadWidthMult(self):
        return self._tread_width_mult

    @TreadWidthMult.setter
    def TreadWidthMult(self, value):
        self._tread_width_mult = float(value)

    # =========================================================================
    # Properties - Girth Parameters
    # =========================================================================

    @property
    def BallGirth(self):
        """Ball girth in mm."""
        return self._ball_girth

    @BallGirth.setter
    def BallGirth(self, value):
        self._ball_girth = float(value)

    @property
    def InstepGirth(self):
        """Instep girth in mm."""
        return self._instep_girth

    @InstepGirth.setter
    def InstepGirth(self, value):
        self._instep_girth = float(value)

    @property
    def WaistGirth(self):
        """Waist girth in mm."""
        return self._waist_girth

    @WaistGirth.setter
    def WaistGirth(self, value):
        self._waist_girth = float(value)

    @property
    def Waist2Girth(self):
        """Second waist girth in mm."""
        return self._waist2_girth

    @Waist2Girth.setter
    def Waist2Girth(self, value):
        self._waist2_girth = float(value)

    @property
    def ArchGirth(self):
        """Arch girth in mm."""
        return self._arch_girth

    @ArchGirth.setter
    def ArchGirth(self, value):
        self._arch_girth = float(value)

    @property
    def HeelGirth(self):
        """Heel girth in mm."""
        return self._heel_girth

    @HeelGirth.setter
    def HeelGirth(self, value):
        self._heel_girth = float(value)

    @property
    def AnkleGirth(self):
        """Ankle girth in mm."""
        return self._ankle_girth

    @AnkleGirth.setter
    def AnkleGirth(self, value):
        self._ankle_girth = float(value)

    # =========================================================================
    # Properties - Girth Multipliers
    # =========================================================================

    @property
    def BallGirthMult(self):
        return self._ball_girth_mult

    @BallGirthMult.setter
    def BallGirthMult(self, value):
        self._ball_girth_mult = float(value)

    @property
    def InstepGirthMult(self):
        return self._instep_girth_mult

    @InstepGirthMult.setter
    def InstepGirthMult(self, value):
        self._instep_girth_mult = float(value)

    @property
    def WaistGirthMult(self):
        return self._waist_girth_mult

    @WaistGirthMult.setter
    def WaistGirthMult(self, value):
        self._waist_girth_mult = float(value)

    @property
    def Waist2GirthMult(self):
        return self._waist2_girth_mult

    @Waist2GirthMult.setter
    def Waist2GirthMult(self, value):
        self._waist2_girth_mult = float(value)

    @property
    def ArchGirthMult(self):
        return self._arch_girth_mult

    @ArchGirthMult.setter
    def ArchGirthMult(self, value):
        self._arch_girth_mult = float(value)

    @property
    def HeelGirthMult(self):
        return self._heel_girth_mult

    @HeelGirthMult.setter
    def HeelGirthMult(self, value):
        self._heel_girth_mult = float(value)

    @property
    def AnkleGirthMult(self):
        return self._ankle_girth_mult

    @AnkleGirthMult.setter
    def AnkleGirthMult(self, value):
        self._ankle_girth_mult = float(value)

    # =========================================================================
    # Properties - Height Parameters
    # =========================================================================

    @property
    def HeelHeight(self):
        """Heel height in mm."""
        return self._heel_height

    @HeelHeight.setter
    def HeelHeight(self, value):
        self._heel_height = float(value)

    @property
    def ToeSpring(self):
        """Toe spring height in mm."""
        return self._toe_spring

    @ToeSpring.setter
    def ToeSpring(self, value):
        self._toe_spring = float(value)

    @property
    def BallHeight(self):
        return self._ball_height

    @BallHeight.setter
    def BallHeight(self, value):
        self._ball_height = float(value)

    @property
    def InstepHeight(self):
        return self._instep_height

    @InstepHeight.setter
    def InstepHeight(self, value):
        self._instep_height = float(value)

    @property
    def WaistHeight(self):
        return self._waist_height

    @WaistHeight.setter
    def WaistHeight(self, value):
        self._waist_height = float(value)

    @property
    def Waist2Height(self):
        return self._waist2_height

    @Waist2Height.setter
    def Waist2Height(self, value):
        self._waist2_height = float(value)

    @property
    def ArchHeight(self):
        return self._arch_height

    @ArchHeight.setter
    def ArchHeight(self, value):
        self._arch_height = float(value)

    @property
    def AnkleHeight(self):
        return self._ankle_height

    @AnkleHeight.setter
    def AnkleHeight(self, value):
        self._ankle_height = float(value)

    @property
    def ConeHeight(self):
        return self._cone_height

    @ConeHeight.setter
    def ConeHeight(self, value):
        self._cone_height = float(value)

    @property
    def CrownHeight(self):
        return self._crown_height

    @CrownHeight.setter
    def CrownHeight(self, value):
        self._crown_height = float(value)

    @property
    def BackHeight(self):
        return self._back_height

    @BackHeight.setter
    def BackHeight(self, value):
        self._back_height = float(value)

    @property
    def FeatherLineHeightBall(self):
        return self._feather_line_height_ball

    @FeatherLineHeightBall.setter
    def FeatherLineHeightBall(self, value):
        self._feather_line_height_ball = float(value)

    @property
    def FeatherLineHeightToe(self):
        return self._feather_line_height_toe

    @FeatherLineHeightToe.setter
    def FeatherLineHeightToe(self, value):
        self._feather_line_height_toe = float(value)

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

    @property
    def TopLineHeightBall(self):
        return self._top_line_height_ball

    @TopLineHeightBall.setter
    def TopLineHeightBall(self, value):
        self._top_line_height_ball = float(value)

    @property
    def TopLineHeightInstep(self):
        return self._top_line_height_instep

    @TopLineHeightInstep.setter
    def TopLineHeightInstep(self, value):
        self._top_line_height_instep = float(value)

    @property
    def TopLineHeightWaist(self):
        return self._top_line_height_waist

    @TopLineHeightWaist.setter
    def TopLineHeightWaist(self, value):
        self._top_line_height_waist = float(value)

    @property
    def TopLineHeightHeel(self):
        return self._top_line_height_heel

    @TopLineHeightHeel.setter
    def TopLineHeightHeel(self, value):
        self._top_line_height_heel = float(value)

    # =========================================================================
    # Properties - Height Multipliers
    # =========================================================================

    @property
    def HeelHeightMult(self):
        return self._heel_height_mult

    @HeelHeightMult.setter
    def HeelHeightMult(self, value):
        self._heel_height_mult = float(value)

    @property
    def ToeSpringMult(self):
        return self._toe_spring_mult

    @ToeSpringMult.setter
    def ToeSpringMult(self, value):
        self._toe_spring_mult = float(value)

    @property
    def BallHeightMult(self):
        return self._ball_height_mult

    @BallHeightMult.setter
    def BallHeightMult(self, value):
        self._ball_height_mult = float(value)

    @property
    def InstepHeightMult(self):
        return self._instep_height_mult

    @InstepHeightMult.setter
    def InstepHeightMult(self, value):
        self._instep_height_mult = float(value)

    @property
    def WaistHeightMult(self):
        return self._waist_height_mult

    @WaistHeightMult.setter
    def WaistHeightMult(self, value):
        self._waist_height_mult = float(value)

    @property
    def Waist2HeightMult(self):
        return self._waist2_height_mult

    @Waist2HeightMult.setter
    def Waist2HeightMult(self, value):
        self._waist2_height_mult = float(value)

    @property
    def ArchHeightMult(self):
        return self._arch_height_mult

    @ArchHeightMult.setter
    def ArchHeightMult(self, value):
        self._arch_height_mult = float(value)

    @property
    def AnkleHeightMult(self):
        return self._ankle_height_mult

    @AnkleHeightMult.setter
    def AnkleHeightMult(self, value):
        self._ankle_height_mult = float(value)

    @property
    def ConeHeightMult(self):
        return self._cone_height_mult

    @ConeHeightMult.setter
    def ConeHeightMult(self, value):
        self._cone_height_mult = float(value)

    @property
    def CrownHeightMult(self):
        return self._crown_height_mult

    @CrownHeightMult.setter
    def CrownHeightMult(self, value):
        self._crown_height_mult = float(value)

    @property
    def BackHeightMult(self):
        return self._back_height_mult

    @BackHeightMult.setter
    def BackHeightMult(self, value):
        self._back_height_mult = float(value)

    # =========================================================================
    # Properties - Allowance Parameters
    # =========================================================================

    @property
    def AllowanceLength(self):
        """Length allowance in mm (toe room)."""
        return self._allowance_length

    @AllowanceLength.setter
    def AllowanceLength(self, value):
        self._allowance_length = float(value)

    @property
    def AllowanceBallGirth(self):
        return self._allowance_ball_girth

    @AllowanceBallGirth.setter
    def AllowanceBallGirth(self, value):
        self._allowance_ball_girth = float(value)

    @property
    def AllowanceBallWidth(self):
        return self._allowance_ball_width

    @AllowanceBallWidth.setter
    def AllowanceBallWidth(self, value):
        self._allowance_ball_width = float(value)

    @property
    def AllowanceHeelWidth(self):
        return self._allowance_heel_width

    @AllowanceHeelWidth.setter
    def AllowanceHeelWidth(self, value):
        self._allowance_heel_width = float(value)

    @property
    def AllowanceInstepGirth(self):
        return self._allowance_instep_girth

    @AllowanceInstepGirth.setter
    def AllowanceInstepGirth(self, value):
        self._allowance_instep_girth = float(value)

    @property
    def AllowanceWaistGirth(self):
        return self._allowance_waist_girth

    @AllowanceWaistGirth.setter
    def AllowanceWaistGirth(self, value):
        self._allowance_waist_girth = float(value)

    @property
    def AllowanceWaist2Girth(self):
        return self._allowance_waist2_girth

    @AllowanceWaist2Girth.setter
    def AllowanceWaist2Girth(self, value):
        self._allowance_waist2_girth = float(value)

    @property
    def AllowanceArchGirth(self):
        return self._allowance_arch_girth

    @AllowanceArchGirth.setter
    def AllowanceArchGirth(self, value):
        self._allowance_arch_girth = float(value)

    @property
    def AllowanceHeelGirth(self):
        return self._allowance_heel_girth

    @AllowanceHeelGirth.setter
    def AllowanceHeelGirth(self, value):
        self._allowance_heel_girth = float(value)

    @property
    def AllowanceAnkleGirth(self):
        return self._allowance_ankle_girth

    @AllowanceAnkleGirth.setter
    def AllowanceAnkleGirth(self, value):
        self._allowance_ankle_girth = float(value)

    @property
    def AllowanceToeSpring(self):
        return self._allowance_toe_spring

    @AllowanceToeSpring.setter
    def AllowanceToeSpring(self, value):
        self._allowance_toe_spring = float(value)

    @property
    def AllowanceHeelHeight(self):
        return self._allowance_heel_height

    @AllowanceHeelHeight.setter
    def AllowanceHeelHeight(self, value):
        self._allowance_heel_height = float(value)

    @property
    def AllowanceConeHeight(self):
        return self._allowance_cone_height

    @AllowanceConeHeight.setter
    def AllowanceConeHeight(self, value):
        self._allowance_cone_height = float(value)

    @property
    def AllowanceCrownHeight(self):
        return self._allowance_crown_height

    @AllowanceCrownHeight.setter
    def AllowanceCrownHeight(self, value):
        self._allowance_crown_height = float(value)

    @property
    def AllowanceBackHeight(self):
        return self._allowance_back_height

    @AllowanceBackHeight.setter
    def AllowanceBackHeight(self, value):
        self._allowance_back_height = float(value)

    # =========================================================================
    # Properties - Angle Parameters
    # =========================================================================

    @property
    def BallBreakPointAngle(self):
        return self._ball_break_point_angle

    @BallBreakPointAngle.setter
    def BallBreakPointAngle(self, value):
        self._ball_break_point_angle = float(value)

    @property
    def BallLineAngle(self):
        return self._ball_line_angle

    @BallLineAngle.setter
    def BallLineAngle(self, value):
        self._ball_line_angle = float(value)

    @property
    def AlphaCutTiltFromMainPlane(self):
        return self._alpha_cut_tilt_from_main_plane

    @AlphaCutTiltFromMainPlane.setter
    def AlphaCutTiltFromMainPlane(self, value):
        self._alpha_cut_tilt_from_main_plane = float(value)

    @property
    def HeelPitchAngle(self):
        return self._heel_pitch_angle

    @HeelPitchAngle.setter
    def HeelPitchAngle(self, value):
        self._heel_pitch_angle = float(value)

    @property
    def ToeRecedeAngle(self):
        return self._toe_recede_angle

    @ToeRecedeAngle.setter
    def ToeRecedeAngle(self, value):
        self._toe_recede_angle = float(value)

    @property
    def ConeAngle(self):
        return self._cone_angle

    @ConeAngle.setter
    def ConeAngle(self, value):
        self._cone_angle = float(value)

    @property
    def BackCurveAngle(self):
        return self._back_curve_angle

    @BackCurveAngle.setter
    def BackCurveAngle(self, value):
        self._back_curve_angle = float(value)

    @property
    def FeatherLineAngleBall(self):
        return self._feather_line_angle_ball

    @FeatherLineAngleBall.setter
    def FeatherLineAngleBall(self, value):
        self._feather_line_angle_ball = float(value)

    @property
    def FeatherLineAngleToe(self):
        return self._feather_line_angle_toe

    @FeatherLineAngleToe.setter
    def FeatherLineAngleToe(self, value):
        self._feather_line_angle_toe = float(value)

    @property
    def FeatherLineAngleWaist(self):
        return self._feather_line_angle_waist

    @FeatherLineAngleWaist.setter
    def FeatherLineAngleWaist(self, value):
        self._feather_line_angle_waist = float(value)

    @property
    def FeatherLineAngleHeel(self):
        return self._feather_line_angle_heel

    @FeatherLineAngleHeel.setter
    def FeatherLineAngleHeel(self, value):
        self._feather_line_angle_heel = float(value)

    # =========================================================================
    # Properties - Style Parameters
    # =========================================================================

    @property
    def ToeStyle(self):
        return self._toe_style

    @ToeStyle.setter
    def ToeStyle(self, value):
        self._toe_style = str(value)

    @property
    def BackEdgeShape(self):
        return self._back_edge_shape

    @BackEdgeShape.setter
    def BackEdgeShape(self, value):
        self._back_edge_shape = str(value)

    @property
    def BottomType(self):
        return self._bottom_type

    @BottomType.setter
    def BottomType(self, value):
        self._bottom_type = str(value)

    @property
    def ArchType(self):
        return self._arch_type

    @ArchType.setter
    def ArchType(self, value):
        self._arch_type = str(value)

    @property
    def ToeProfileShape(self):
        return self._toe_profile_shape

    @ToeProfileShape.setter
    def ToeProfileShape(self, value):
        self._toe_profile_shape = str(value)

    @property
    def ToeBoxShape(self):
        return self._toe_box_shape

    @ToeBoxShape.setter
    def ToeBoxShape(self, value):
        self._toe_box_shape = str(value)

    @property
    def ToeBoxHeightFactor(self):
        return self._toe_box_height_factor

    @ToeBoxHeightFactor.setter
    def ToeBoxHeightFactor(self, value):
        self._toe_box_height_factor = float(value)

    @property
    def ToeBoxWidthFactor(self):
        return self._toe_box_width_factor

    @ToeBoxWidthFactor.setter
    def ToeBoxWidthFactor(self, value):
        self._toe_box_width_factor = float(value)

    @property
    def ToeTaperFactor(self):
        return self._toe_taper_factor

    @ToeTaperFactor.setter
    def ToeTaperFactor(self, value):
        self._toe_taper_factor = float(value)

    @property
    def ToeRadius(self):
        return self._toe_radius

    @ToeRadius.setter
    def ToeRadius(self, value):
        self._toe_radius = float(value)

    @property
    def ToeAsymmetry(self):
        return self._toe_asymmetry

    @ToeAsymmetry.setter
    def ToeAsymmetry(self, value):
        self._toe_asymmetry = float(value)

    @property
    def BackCurveDepth(self):
        return self._back_curve_depth

    @BackCurveDepth.setter
    def BackCurveDepth(self, value):
        self._back_curve_depth = float(value)

    @property
    def ShankCurve(self):
        return self._shank_curve

    @ShankCurve.setter
    def ShankCurve(self, value):
        self._shank_curve = float(value)

    @property
    def FeatherEdgeType(self):
        return self._feather_edge_type

    @FeatherEdgeType.setter
    def FeatherEdgeType(self, value):
        self._feather_edge_type = str(value)

    @property
    def CrownShape(self):
        return self._crown_shape

    @CrownShape.setter
    def CrownShape(self, value):
        self._crown_shape = str(value)

    # =========================================================================
    # Properties - Toe Style-Specific Parameters
    # =========================================================================

    @property
    def ToeStylePointedAngle(self):
        return self._toe_style_pointed_angle

    @ToeStylePointedAngle.setter
    def ToeStylePointedAngle(self, value):
        self._toe_style_pointed_angle = float(value)

    @property
    def ToeStylePointedTipRadius(self):
        return self._toe_style_pointed_tip_radius

    @ToeStylePointedTipRadius.setter
    def ToeStylePointedTipRadius(self, value):
        self._toe_style_pointed_tip_radius = float(value)

    @property
    def ToeStyleSquareCornerRadius(self):
        return self._toe_style_square_corner_radius

    @ToeStyleSquareCornerRadius.setter
    def ToeStyleSquareCornerRadius(self, value):
        self._toe_style_square_corner_radius = float(value)

    @property
    def ToeStyleSquareWidthFactor(self):
        return self._toe_style_square_width_factor

    @ToeStyleSquareWidthFactor.setter
    def ToeStyleSquareWidthFactor(self, value):
        self._toe_style_square_width_factor = float(value)

    @property
    def ToeStyleObliqueShift(self):
        return self._toe_style_oblique_shift

    @ToeStyleObliqueShift.setter
    def ToeStyleObliqueShift(self, value):
        self._toe_style_oblique_shift = float(value)

    @property
    def ToeStyleObliqueAngle(self):
        return self._toe_style_oblique_angle

    @ToeStyleObliqueAngle.setter
    def ToeStyleObliqueAngle(self, value):
        self._toe_style_oblique_angle = float(value)

    @property
    def ToeStyleAlmondLengthFactor(self):
        return self._toe_style_almond_length_factor

    @ToeStyleAlmondLengthFactor.setter
    def ToeStyleAlmondLengthFactor(self, value):
        self._toe_style_almond_length_factor = float(value)

    @property
    def ToeStyleAlmondWidthFactor(self):
        return self._toe_style_almond_width_factor

    @ToeStyleAlmondWidthFactor.setter
    def ToeStyleAlmondWidthFactor(self, value):
        self._toe_style_almond_width_factor = float(value)

    @property
    def ToeStyleRoundRadiusFactor(self):
        return self._toe_style_round_radius_factor

    @ToeStyleRoundRadiusFactor.setter
    def ToeStyleRoundRadiusFactor(self, value):
        self._toe_style_round_radius_factor = float(value)

    @property
    def ToeTipThickness(self):
        return self._toe_tip_thickness

    @ToeTipThickness.setter
    def ToeTipThickness(self, value):
        self._toe_tip_thickness = float(value)

    @property
    def ToeTipDrop(self):
        return self._toe_tip_drop

    @ToeTipDrop.setter
    def ToeTipDrop(self, value):
        self._toe_tip_drop = float(value)

    # =========================================================================
    # Properties - BottomLine (BL) Curve IDs
    # =========================================================================

    @property
    def BLMesh(self):
        """GUID of the bottom line mesh."""
        return self._bl_mesh

    @BLMesh.setter
    def BLMesh(self, value):
        self._bl_mesh = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLB(self):
        """GUID of the bottom line at ball."""
        return self._bl_b

    @BLB.setter
    def BLB(self, value):
        self._bl_b = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLH(self):
        """GUID of the bottom line at heel."""
        return self._bl_h

    @BLH.setter
    def BLH(self, value):
        self._bl_h = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLI(self):
        """GUID of the bottom line at instep."""
        return self._bl_i

    @BLI.setter
    def BLI(self, value):
        self._bl_i = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLS(self):
        """GUID of the bottom line at shank."""
        return self._bl_s

    @BLS.setter
    def BLS(self, value):
        self._bl_s = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLT(self):
        """GUID of the bottom line at toe."""
        return self._bl_t

    @BLT.setter
    def BLT(self, value):
        self._bl_t = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLV(self):
        """GUID of the bottom line at V (apex)."""
        return self._bl_v

    @BLV.setter
    def BLV(self, value):
        self._bl_v = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLIA(self):
        """GUID of the bottom line inner arch curve."""
        return self._bl_ia

    @BLIA.setter
    def BLIA(self, value):
        self._bl_ia = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLTC(self):
        """GUID of the bottom line toe cap curve."""
        return self._bl_tc

    @BLTC.setter
    def BLTC(self, value):
        self._bl_tc = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLTW(self):
        """GUID of the bottom line toe wing curve."""
        return self._bl_tw

    @BLTW.setter
    def BLTW(self, value):
        self._bl_tw = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLCW(self):
        """GUID of the bottom line cone wing curve."""
        return self._bl_cw

    @BLCW.setter
    def BLCW(self, value):
        self._bl_cw = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLFull(self):
        """GUID of the full bottom line curve."""
        return self._bl_full

    @BLFull.setter
    def BLFull(self, value):
        self._bl_full = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLLateral(self):
        return self._bl_lateral

    @BLLateral.setter
    def BLLateral(self, value):
        self._bl_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLMedial(self):
        return self._bl_medial

    @BLMedial.setter
    def BLMedial(self, value):
        self._bl_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLForepart(self):
        return self._bl_forepart

    @BLForepart.setter
    def BLForepart(self, value):
        self._bl_forepart = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BLBackpart(self):
        return self._bl_backpart

    @BLBackpart.setter
    def BLBackpart(self, value):
        self._bl_backpart = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - CenterLine (CL) Curve IDs
    # =========================================================================

    @property
    def CLb(self):
        """GUID of the center line bottom curve."""
        return self._cl_b

    @CLb.setter
    def CLb(self, value):
        self._cl_b = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLt(self):
        """GUID of the center line top curve."""
        return self._cl_t

    @CLt.setter
    def CLt(self, value):
        self._cl_t = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLBW(self):
        """GUID of the center line bottom width curve."""
        return self._cl_bw

    @CLBW.setter
    def CLBW(self, value):
        self._cl_bw = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLTW(self):
        """GUID of the center line top width curve."""
        return self._cl_tw

    @CLTW.setter
    def CLTW(self, value):
        self._cl_tw = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLTPxz(self):
        """GUID of the center line top profile in XZ plane."""
        return self._cl_tp_xz

    @CLTPxz.setter
    def CLTPxz(self, value):
        self._cl_tp_xz = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLHGl(self):
        """GUID of the center line heel girth lateral."""
        return self._cl_hg_l

    @CLHGl.setter
    def CLHGl(self, value):
        self._cl_hg_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLHGm(self):
        """GUID of the center line heel girth medial."""
        return self._cl_hg_m

    @CLHGm.setter
    def CLHGm(self, value):
        self._cl_hg_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLFull(self):
        return self._cl_full

    @CLFull.setter
    def CLFull(self, value):
        self._cl_full = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLLateral(self):
        return self._cl_lateral

    @CLLateral.setter
    def CLLateral(self, value):
        self._cl_lateral = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLMedial(self):
        return self._cl_medial

    @CLMedial.setter
    def CLMedial(self, value):
        self._cl_medial = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Cross Section Curves (C1C - C5C)
    # =========================================================================

    @property
    def C1C(self):
        return self._c1c

    @C1C.setter
    def C1C(self, value):
        self._c1c = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C1Cl(self):
        return self._c1c_l

    @C1Cl.setter
    def C1Cl(self, value):
        self._c1c_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C1Cm(self):
        return self._c1c_m

    @C1Cm.setter
    def C1Cm(self, value):
        self._c1c_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C1Ca(self):
        return self._c1c_a

    @C1Ca.setter
    def C1Ca(self, value):
        self._c1c_a = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C1Cp(self):
        return self._c1c_p

    @C1Cp.setter
    def C1Cp(self, value):
        self._c1c_p = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C2C(self):
        return self._c2c

    @C2C.setter
    def C2C(self, value):
        self._c2c = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C2Cl(self):
        return self._c2c_l

    @C2Cl.setter
    def C2Cl(self, value):
        self._c2c_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C2Cm(self):
        return self._c2c_m

    @C2Cm.setter
    def C2Cm(self, value):
        self._c2c_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C2Ca(self):
        return self._c2c_a

    @C2Ca.setter
    def C2Ca(self, value):
        self._c2c_a = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C2Cp(self):
        return self._c2c_p

    @C2Cp.setter
    def C2Cp(self, value):
        self._c2c_p = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C3C(self):
        return self._c3c

    @C3C.setter
    def C3C(self, value):
        self._c3c = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C3Cl(self):
        return self._c3c_l

    @C3Cl.setter
    def C3Cl(self, value):
        self._c3c_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C3Cm(self):
        return self._c3c_m

    @C3Cm.setter
    def C3Cm(self, value):
        self._c3c_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C3Ca(self):
        return self._c3c_a

    @C3Ca.setter
    def C3Ca(self, value):
        self._c3c_a = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C3Cp(self):
        return self._c3c_p

    @C3Cp.setter
    def C3Cp(self, value):
        self._c3c_p = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C4C(self):
        return self._c4c

    @C4C.setter
    def C4C(self, value):
        self._c4c = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C4Cl(self):
        return self._c4c_l

    @C4Cl.setter
    def C4Cl(self, value):
        self._c4c_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C4Cm(self):
        return self._c4c_m

    @C4Cm.setter
    def C4Cm(self, value):
        self._c4c_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C4Ca(self):
        return self._c4c_a

    @C4Ca.setter
    def C4Ca(self, value):
        self._c4c_a = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C4Cp(self):
        return self._c4c_p

    @C4Cp.setter
    def C4Cp(self, value):
        self._c4c_p = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C5C(self):
        return self._c5c

    @C5C.setter
    def C5C(self, value):
        self._c5c = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C5Cl(self):
        return self._c5c_l

    @C5Cl.setter
    def C5Cl(self, value):
        self._c5c_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C5Cm(self):
        return self._c5c_m

    @C5Cm.setter
    def C5Cm(self, value):
        self._c5c_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C5Ca(self):
        return self._c5c_a

    @C5Ca.setter
    def C5Ca(self, value):
        self._c5c_a = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def C5Cp(self):
        return self._c5c_p

    @C5Cp.setter
    def C5Cp(self, value):
        self._c5c_p = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - AlphaJoint (CA) and Heel (CH) Curve IDs
    # =========================================================================

    @property
    def CA(self):
        """GUID of the alpha joint curve."""
        return self._ca

    @CA.setter
    def CA(self, value):
        self._ca = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CAl(self):
        return self._ca_l

    @CAl.setter
    def CAl(self, value):
        self._ca_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CAm(self):
        return self._ca_m

    @CAm.setter
    def CAm(self, value):
        self._ca_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CH(self):
        """GUID of the heel curve."""
        return self._ch

    @CH.setter
    def CH(self, value):
        self._ch = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CHl(self):
        return self._ch_l

    @CHl.setter
    def CHl(self, value):
        self._ch_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CHm(self):
        return self._ch_m

    @CHm.setter
    def CHm(self, value):
        self._ch_m = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Girth Section Curve IDs
    # =========================================================================

    @property
    def CBG(self):
        """GUID of the ball girth curve."""
        return self._cbg

    @CBG.setter
    def CBG(self, value):
        self._cbg = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CBGl(self):
        return self._cbg_l

    @CBGl.setter
    def CBGl(self, value):
        self._cbg_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CBGm(self):
        return self._cbg_m

    @CBGm.setter
    def CBGm(self, value):
        self._cbg_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CIG(self):
        """GUID of the instep girth curve."""
        return self._cig

    @CIG.setter
    def CIG(self, value):
        self._cig = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CIGl(self):
        return self._cig_l

    @CIGl.setter
    def CIGl(self, value):
        self._cig_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CIGm(self):
        return self._cig_m

    @CIGm.setter
    def CIGm(self, value):
        self._cig_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CWG(self):
        """GUID of the waist girth curve."""
        return self._cwg

    @CWG.setter
    def CWG(self, value):
        self._cwg = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CWGl(self):
        return self._cwg_l

    @CWGl.setter
    def CWGl(self, value):
        self._cwg_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CWGm(self):
        return self._cwg_m

    @CWGm.setter
    def CWGm(self, value):
        self._cwg_m = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CW2G(self):
        """GUID of the waist 2 girth curve."""
        return self._cw2g

    @CW2G.setter
    def CW2G(self, value):
        self._cw2g = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CW2Gl(self):
        return self._cw2g_l

    @CW2Gl.setter
    def CW2Gl(self, value):
        self._cw2g_l = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CW2Gm(self):
        return self._cw2g_m

    @CW2Gm.setter
    def CW2Gm(self, value):
        self._cw2g_m = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - ShankBoard (CSB) Curve IDs
    # =========================================================================

    @property
    def CSBArch(self):
        """GUID of the shank board arch curve."""
        return self._csb_arch

    @CSBArch.setter
    def CSBArch(self, value):
        self._csb_arch = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSBBall(self):
        return self._csb_ball

    @CSBBall.setter
    def CSBBall(self, value):
        self._csb_ball = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSBHeel(self):
        return self._csb_heel

    @CSBHeel.setter
    def CSBHeel(self, value):
        self._csb_heel = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSBHeelBack(self):
        return self._csb_heel_back

    @CSBHeelBack.setter
    def CSBHeelBack(self, value):
        self._csb_heel_back = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSBInstep(self):
        return self._csb_instep

    @CSBInstep.setter
    def CSBInstep(self, value):
        self._csb_instep = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSBToe(self):
        return self._csb_toe

    @CSBToe.setter
    def CSBToe(self, value):
        self._csb_toe = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSBToeFront(self):
        return self._csb_toe_front

    @CSBToeFront.setter
    def CSBToeFront(self, value):
        self._csb_toe_front = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSBWaist(self):
        return self._csb_waist

    @CSBWaist.setter
    def CSBWaist(self, value):
        self._csb_waist = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSBFull(self):
        return self._csb_full

    @CSBFull.setter
    def CSBFull(self, value):
        self._csb_full = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CST(self):
        return self._cst

    @CST.setter
    def CST(self, value):
        self._cst = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CSHG(self):
        return self._cshg

    @CSHG.setter
    def CSHG(self, value):
        self._cshg = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def CLHG(self):
        return self._clhg

    @CLHG.setter
    def CLHG(self, value):
        self._clhg = Guid(str(value)) if not isinstance(value, Guid) else value

    # =========================================================================
    # Properties - Local and Viewing Planes
    # =========================================================================

    @property
    def C1CLocalPlane(self):
        return self._c1c_local_plane

    @C1CLocalPlane.setter
    def C1CLocalPlane(self, value):
        self._c1c_local_plane = value

    @property
    def C2CLocalPlane(self):
        return self._c2c_local_plane

    @C2CLocalPlane.setter
    def C2CLocalPlane(self, value):
        self._c2c_local_plane = value

    @property
    def C3CLocalPlane(self):
        return self._c3c_local_plane

    @C3CLocalPlane.setter
    def C3CLocalPlane(self, value):
        self._c3c_local_plane = value

    @property
    def C4CLocalPlane(self):
        return self._c4c_local_plane

    @C4CLocalPlane.setter
    def C4CLocalPlane(self, value):
        self._c4c_local_plane = value

    @property
    def C5CLocalPlane(self):
        return self._c5c_local_plane

    @C5CLocalPlane.setter
    def C5CLocalPlane(self, value):
        self._c5c_local_plane = value

    @property
    def CALocalPlane(self):
        return self._ca_local_plane

    @CALocalPlane.setter
    def CALocalPlane(self, value):
        self._ca_local_plane = value

    @property
    def CHLocalPlane(self):
        return self._ch_local_plane

    @CHLocalPlane.setter
    def CHLocalPlane(self, value):
        self._ch_local_plane = value

    @property
    def CBGLocalPlane(self):
        return self._cbg_local_plane

    @CBGLocalPlane.setter
    def CBGLocalPlane(self, value):
        self._cbg_local_plane = value

    @property
    def CIGLocalPlane(self):
        return self._cig_local_plane

    @CIGLocalPlane.setter
    def CIGLocalPlane(self, value):
        self._cig_local_plane = value

    @property
    def CWGLocalPlane(self):
        return self._cwg_local_plane

    @CWGLocalPlane.setter
    def CWGLocalPlane(self, value):
        self._cwg_local_plane = value

    @property
    def CW2GLocalPlane(self):
        return self._cw2g_local_plane

    @CW2GLocalPlane.setter
    def CW2GLocalPlane(self, value):
        self._cw2g_local_plane = value

    @property
    def C1CViewingPlane(self):
        return self._c1c_viewing_plane

    @C1CViewingPlane.setter
    def C1CViewingPlane(self, value):
        self._c1c_viewing_plane = value

    @property
    def C2CViewingPlane(self):
        return self._c2c_viewing_plane

    @C2CViewingPlane.setter
    def C2CViewingPlane(self, value):
        self._c2c_viewing_plane = value

    @property
    def C3CViewingPlane(self):
        return self._c3c_viewing_plane

    @C3CViewingPlane.setter
    def C3CViewingPlane(self, value):
        self._c3c_viewing_plane = value

    @property
    def C4CViewingPlane(self):
        return self._c4c_viewing_plane

    @C4CViewingPlane.setter
    def C4CViewingPlane(self, value):
        self._c4c_viewing_plane = value

    @property
    def C5CViewingPlane(self):
        return self._c5c_viewing_plane

    @C5CViewingPlane.setter
    def C5CViewingPlane(self, value):
        self._c5c_viewing_plane = value

    @property
    def CAViewingPlane(self):
        return self._ca_viewing_plane

    @CAViewingPlane.setter
    def CAViewingPlane(self, value):
        self._ca_viewing_plane = value

    @property
    def CHViewingPlane(self):
        return self._ch_viewing_plane

    @CHViewingPlane.setter
    def CHViewingPlane(self, value):
        self._ch_viewing_plane = value

    @property
    def CBGViewingPlane(self):
        return self._cbg_viewing_plane

    @CBGViewingPlane.setter
    def CBGViewingPlane(self, value):
        self._cbg_viewing_plane = value

    @property
    def CIGViewingPlane(self):
        return self._cig_viewing_plane

    @CIGViewingPlane.setter
    def CIGViewingPlane(self, value):
        self._cig_viewing_plane = value

    @property
    def CWGViewingPlane(self):
        return self._cwg_viewing_plane

    @CWGViewingPlane.setter
    def CWGViewingPlane(self, value):
        self._cwg_viewing_plane = value

    @property
    def CW2GViewingPlane(self):
        return self._cw2g_viewing_plane

    @CW2GViewingPlane.setter
    def CW2GViewingPlane(self, value):
        self._cw2g_viewing_plane = value

    # =========================================================================
    # Properties - Cross Section Specific Params (dynamic via getattr/setattr)
    # =========================================================================

    def GetCrossSectionParam(self, section, param_type, side):
        """Get a cross-section parameter value.

        Args:
            section: Section name (e.g., "c1c", "c2c", ..., "c5c").
            param_type: Parameter type ("cs", "depth", "offset", "angle",
                        "height", "a1", "a2", "a3").
            side: Side ("l" for lateral, "m" for medial).

        Returns:
            The parameter value as a float.
        """
        attr_name = f"_{section}_{param_type}_{side}"
        return getattr(self, attr_name, 0.0)

    def SetCrossSectionParam(self, section, param_type, side, value):
        """Set a cross-section parameter value.

        Args:
            section: Section name (e.g., "c1c", "c2c", ..., "c5c").
            param_type: Parameter type ("cs", "depth", "offset", "angle",
                        "height", "a1", "a2", "a3").
            side: Side ("l" for lateral, "m" for medial).
            value: The value to set.
        """
        attr_name = f"_{section}_{param_type}_{side}"
        setattr(self, attr_name, float(value))

    # =========================================================================
    # Properties - Body Geometry IDs
    # =========================================================================

    @property
    def BodyMain(self):
        """GUID of the main body Brep."""
        return self._body_main

    @BodyMain.setter
    def BodyMain(self, value):
        self._body_main = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyMainSubD(self):
        """GUID of the main body SubD."""
        return self._body_main_subd

    @BodyMainSubD.setter
    def BodyMainSubD(self, value):
        self._body_main_subd = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyScrapCutter(self):
        """GUID of the scrap cutter body."""
        return self._body_scrap_cutter

    @BodyScrapCutter.setter
    def BodyScrapCutter(self, value):
        self._body_scrap_cutter = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodySoleCutter(self):
        """GUID of the sole cutter body."""
        return self._body_sole_cutter

    @BodySoleCutter.setter
    def BodySoleCutter(self, value):
        self._body_sole_cutter = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodySoleCutterFlat(self):
        return self._body_sole_cutter_flat

    @BodySoleCutterFlat.setter
    def BodySoleCutterFlat(self, value):
        self._body_sole_cutter_flat = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodySoleCutterWedge(self):
        return self._body_sole_cutter_wedge

    @BodySoleCutterWedge.setter
    def BodySoleCutterWedge(self, value):
        self._body_sole_cutter_wedge = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodySoleCutterHeel(self):
        return self._body_sole_cutter_heel

    @BodySoleCutterHeel.setter
    def BodySoleCutterHeel(self, value):
        self._body_sole_cutter_heel = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodyMesh(self):
        return self._body_mesh

    @BodyMesh.setter
    def BodyMesh(self, value):
        self._body_mesh = Guid(str(value)) if not isinstance(value, Guid) else value

    @property
    def BodySurface(self):
        return self._body_surface

    @BodySurface.setter
    def BodySurface(self, value):
        self._body_surface = Guid(str(value)) if not isinstance(value, Guid) else value

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
    def InstepPoint(self):
        return self._instep_point

    @InstepPoint.setter
    def InstepPoint(self, value):
        self._instep_point = value

    @property
    def WaistPoint(self):
        return self._waist_point

    @WaistPoint.setter
    def WaistPoint(self, value):
        self._waist_point = value

    @property
    def Waist2Point(self):
        return self._waist2_point

    @Waist2Point.setter
    def Waist2Point(self, value):
        self._waist2_point = value

    @property
    def ArchPoint(self):
        return self._arch_point

    @ArchPoint.setter
    def ArchPoint(self, value):
        self._arch_point = value

    @property
    def AnklePoint(self):
        return self._ankle_point

    @AnklePoint.setter
    def AnklePoint(self, value):
        self._ankle_point = value

    @property
    def ConePoint(self):
        return self._cone_point

    @ConePoint.setter
    def ConePoint(self, value):
        self._cone_point = value

    @property
    def CrownPoint(self):
        return self._crown_point

    @CrownPoint.setter
    def CrownPoint(self, value):
        self._crown_point = value

    @property
    def AlphaJointPoint(self):
        return self._alpha_joint_point

    @AlphaJointPoint.setter
    def AlphaJointPoint(self, value):
        self._alpha_joint_point = value

    @property
    def BackPoint(self):
        return self._back_point

    @BackPoint.setter
    def BackPoint(self, value):
        self._back_point = value

    @property
    def BallBreakPoint(self):
        return self._ball_break_point

    @BallBreakPoint.setter
    def BallBreakPoint(self, value):
        self._ball_break_point = value

    @property
    def TreadPoint(self):
        return self._tread_point

    @TreadPoint.setter
    def TreadPoint(self, value):
        self._tread_point = value

    # =========================================================================
    # Properties - Style Parameter Dictionary
    # =========================================================================

    @property
    def LastStyleParameterDictionary(self):
        """Dictionary of all style parameters for serialization."""
        return self._last_style_parameter_dictionary

    @LastStyleParameterDictionary.setter
    def LastStyleParameterDictionary(self, value):
        self._last_style_parameter_dictionary = dict(value) if value else {}

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_json(self):
        """Serialize this Last to a JSON string.

        Returns:
            JSON string representation of the last parameters.
        """
        return json.dumps(self.CollectLastParameters(), indent=2, default=str)

    @staticmethod
    def from_json(json_string):
        """Deserialize a Last from a JSON string.

        Args:
            json_string: JSON string with last parameters.

        Returns:
            A new Last instance.
        """
        return Last.CreateViaJSon(json_string)

    def __repr__(self):
        return (
            f"Last(name=\"{self._name}\", side=\"{self._side}\", "
            f"length={self._length:.1f}, "
            f"ball_width={self._ball_width:.1f}, "
            f"heel_height={self._heel_height:.1f}, "
            f"toe_style=\"{self._toe_style}\")"
        )
