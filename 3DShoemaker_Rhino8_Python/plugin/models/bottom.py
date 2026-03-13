"""
Bottom data model for 3DShoemaker Rhino 8 plugin.
Represents sole, heel, and support components of footwear.
"""

import json
import System
import Rhino
import Rhino.Geometry as rg
import Rhino.DocObjects as rdo
import rhinoscriptsyntax as rs


class Bottom:
    """
    Represents the bottom components of footwear including sole, heel,
    shank board, top piece, and support structures.
    """

    def __init__(self):
        self.parameters = {}
        self.geometry_ids = {}
        self.support_style_parameter_dictionary = {}
        self._init_parameters()

    def _init_parameters(self):
        """Initialize all bottom parameters with defaults."""

        # Sole parameters
        sole_params = {
            "SoleThickness": 5.0,
            "SoleThicknessBall": 5.0,
            "SoleThicknessHeel": 8.0,
            "SoleThicknessWaist": 6.0,
            "SoleForePartLength": 0.0,
            "SoleWidth": 0.0,
            "SoleExtension": 2.0,
            "SoleMaterial": "Rubber",
            "SoleDensity": 1.1,
            "SoleHardness": 60,
            "SoleColor": "Black",
            "SoleProfile": None,
            "SoleProfileID": System.Guid.Empty,
        }

        # Heel parameters
        heel_params = {
            "HeelHeight": 25.0,
            "HeelHeightFront": 20.0,
            "HeelWidth": 0.0,
            "HeelLength": 0.0,
            "HeelForwardOffset": 0.0,
            "HeelMedialOffset": 0.0,
            "HeelCurveRadius": 5.0,
            "HeelTopRadius": 3.0,
            "HeelBottomRadius": 5.0,
            "HeelBreastAngle": 15.0,
            "HeelSeatCurve": None,
            "HeelSeatCurveID": System.Guid.Empty,
            "HeelFrontProfile": None,
            "HeelFrontProfileID": System.Guid.Empty,
            "HeelBackEdge": None,
            "HeelBackEdgeID": System.Guid.Empty,
            "HeelMaterial": "Rubber",
            "HeelDensity": 1.2,
            "HeelHardness": 70,
        }

        # Support style parameters
        support_params = {
            "SupportType": "Standard",
            "SupportMaterial": "Steel",
            "ShankBoardLength": 0.0,
            "ShankBoardWidth": 0.0,
            "ShankBoardThickness": 1.5,
            "ShankBoardCurvature": 0.0,
            "TopPieceThickness": 3.0,
            "TopPieceMaterial": "Rubber",
            "TopPieceHardness": 70,
            "MetPadThickness": 3.0,
            "MetPadWidth": 0.0,
            "MetPadLength": 0.0,
            "MetPadPosition": 0.0,
        }

        # Body geometry IDs
        body_ids = {
            "BodyMain": System.Guid.Empty,
            "BodyMainID": System.Guid.Empty,
            "BodyMainString": "",
            "BodyMainSubD": System.Guid.Empty,
            "BodyMainSubDID": System.Guid.Empty,
            "BodyMainSubDString": "",
            "BodyMainSecondaryID": System.Guid.Empty,
            "BodyScrapCutter": System.Guid.Empty,
            "BodyScrapID": System.Guid.Empty,
            "BodyScrapSecondaryID": System.Guid.Empty,
            "BodySoleCutterMain": System.Guid.Empty,
            "BodySoleCutterMainTrimmed": System.Guid.Empty,
            "BodySoleCutterHeel": System.Guid.Empty,
            "BodySoleCutterHeelTrimmed": System.Guid.Empty,
            "BodySoleCutterJoined": System.Guid.Empty,
            "BodySoleID": System.Guid.Empty,
            "BodySoleSecondaryID": System.Guid.Empty,
        }

        # Bottom profile and template
        profile_params = {
            "BottomBodyThicknessUnderBallCurve": 0.0,
            "BottomMaterial": "EVA",
            "BottomProfileCurveExtrudedSurfaceBrep": None,
            "BottomProfileCurveExtrudedSurfaceBrepString": "",
            "BottomSideWall": None,
            "BottomTemplate": "Standard",
            "BottomTypeByNumber": 0,
            "BottomIsNonParametric": False,
            "BuildBottomBody": True,
        }

        # Cross section curve IDs
        cs_curves = {
            "CSBArch": System.Guid.Empty, "CSBArchID": System.Guid.Empty, "CSBArchString": "",
            "CSBBall": System.Guid.Empty, "CSBBallID": System.Guid.Empty, "CSBBallString": "",
            "CSBHeel": System.Guid.Empty, "CSBHeelID": System.Guid.Empty, "CSBHeelString": "",
            "CSBHeelBack": System.Guid.Empty, "CSBHeelBackID": System.Guid.Empty, "CSBHeelBackString": "",
            "CSBInstep": System.Guid.Empty, "CSBInstepID": System.Guid.Empty, "CSBInstepString": "",
            "CSBToe": System.Guid.Empty, "CSBToeID": System.Guid.Empty, "CSBToeString": "",
            "CSBToeFront": System.Guid.Empty, "CSBToeFrontID": System.Guid.Empty, "CSBToeFrontString": "",
            "CSBWaist": System.Guid.Empty, "CSBWaistID": System.Guid.Empty, "CSBWaistString": "",
            "CSBID": System.Guid.Empty, "CSBString": "",
        }

        # Design curve IDs for sole/bottom
        design_curves = {
            "BCl": System.Guid.Empty, "BClID": System.Guid.Empty,
            "BCm": System.Guid.Empty, "BCmID": System.Guid.Empty,
            "BCLTcExtruded": None, "BCLTpExtruded": None,
        }

        # Multiplier parameters
        multipliers = {
            "SoleThicknessMult": 1.0,
            "HeelHeightMult": 1.0,
            "ShankBoardLengthMult": 1.0,
            "ShankBoardWidthMult": 1.0,
        }

        # Back edge and profile parameters
        back_edge_params = {
            "BackEdgeShapeByNumber": 0,
            "BackLine": System.Guid.Empty,
            "BackLineID": System.Guid.Empty,
            "BackLineCurveDup": System.Guid.Empty,
            "BackLineCurveDupMirroredID": System.Guid.Empty,
            "BackProfile": System.Guid.Empty,
        }

        # BPHM (Bottom Profile Height Map) parameters
        bphm_params = {
            "BPHM": System.Guid.Empty,
            "BPHMID": System.Guid.Empty,
        }

        # Girth curve parameters (bottom-level)
        girth_params = {
            "BGCdlsCPi": None, "BGCdlsCPs": None,
            "BGCdmsCPi": None, "BGCdmsCPs": None,
        }

        # Combine all parameters
        all_params = {}
        for d in [sole_params, heel_params, support_params, body_ids,
                   profile_params, cs_curves, design_curves, multipliers,
                   back_edge_params, bphm_params, girth_params]:
            all_params.update(d)

        self.parameters = all_params

    def Clone(self):
        """Creates a deep copy of this Bottom."""
        new_bottom = Bottom()
        new_bottom.parameters = dict(self.parameters)
        new_bottom.geometry_ids = dict(self.geometry_ids)
        new_bottom.support_style_parameter_dictionary = dict(self.support_style_parameter_dictionary)
        return new_bottom

    @staticmethod
    def Create():
        """Creates a new Bottom with default parameters."""
        return Bottom()

    def CollectHeelParameters(self):
        """Collects heel-specific parameters from the current state."""
        heel_params = {}
        heel_keys = [k for k in self.parameters if k.startswith("Heel")]
        for key in heel_keys:
            heel_params[key] = self.parameters[key]
        return heel_params

    def CollectSupportStyleParameters(self):
        """Collects support style parameters."""
        support_params = {}
        support_keys = ["SupportType", "SupportMaterial", "ShankBoardLength",
                       "ShankBoardWidth", "ShankBoardThickness", "ShankBoardCurvature",
                       "TopPieceThickness", "TopPieceMaterial", "TopPieceHardness",
                       "MetPadThickness", "MetPadWidth", "MetPadLength", "MetPadPosition"]
        for key in support_keys:
            if key in self.parameters:
                support_params[key] = self.parameters[key]
        self.support_style_parameter_dictionary = support_params
        return support_params

    def SetDefaultSupportStyleParameters(self):
        """Resets support style parameters to defaults."""
        self.parameters["SupportType"] = "Standard"
        self.parameters["SupportMaterial"] = "Steel"
        self.parameters["ShankBoardThickness"] = 1.5
        self.parameters["TopPieceThickness"] = 3.0
        self.parameters["TopPieceMaterial"] = "Rubber"
        self.parameters["TopPieceHardness"] = 70
        self.parameters["MetPadThickness"] = 3.0

    def CalculateLinearMeasurementsFromMults(self):
        """Calculates linear measurements from multiplier values."""
        mult_pairs = {
            "SoleThickness": "SoleThicknessMult",
            "HeelHeight": "HeelHeightMult",
            "ShankBoardLength": "ShankBoardLengthMult",
            "ShankBoardWidth": "ShankBoardWidthMult",
        }
        for param, mult in mult_pairs.items():
            if param in self.parameters and mult in self.parameters:
                base_val = self.parameters[param]
                mult_val = self.parameters[mult]
                if isinstance(base_val, (int, float)) and isinstance(mult_val, (int, float)):
                    self.parameters[param] = base_val * mult_val

    def DesignCurves(self):
        """Designs all curves for the bottom components."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        self.DesignCurvesForBottoms()
        self.DesignCurvesForSoles()

    def DesignCurvesForBottoms(self):
        """Designs curves specifically for bottom components."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        sole_thickness = self.parameters.get("SoleThickness", 5.0)
        heel_height = self.parameters.get("HeelHeight", 25.0)

        Rhino.RhinoApp.WriteLine(f"Designing bottom curves: sole={sole_thickness}, heel={heel_height}")

    def DesignCurvesForSoles(self):
        """Designs curves specifically for sole components."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        Rhino.RhinoApp.WriteLine("Designing sole curves...")

    def DesignBody(self):
        """Designs the main body geometry for the bottom."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        bottom_type = self.parameters.get("BottomTypeByNumber", 0)

        if bottom_type == 0:
            self.DesignBodyForBottoms()
        elif bottom_type == 1:
            self.DesignBodyForSoles()
        else:
            self.DesignBodyForShoes()

    def DesignBodyForBottoms(self):
        """Creates body geometry for bottom/platform style."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        sole_thickness = self.parameters.get("SoleThickness", 5.0)
        Rhino.RhinoApp.WriteLine(f"Designing bottom body with thickness={sole_thickness}")

        from ..plugin_main import PodoCADPlugIn
        plugin = PodoCADPlugIn.Instance
        if plugin is None or plugin.last is None:
            Rhino.RhinoApp.WriteLine("No last available for bottom body design.")
            return

        last = plugin.last
        bl_id = last.geometry_ids.get("BLB")
        if bl_id and bl_id != System.Guid.Empty:
            bl_obj = doc.Objects.FindId(bl_id)
            if bl_obj and bl_obj.Geometry:
                bottom_surface = bl_obj.Geometry
                if isinstance(bottom_surface, rg.Brep):
                    offset_result = rg.Brep.CreateOffsetBrep(
                        bottom_surface, -sole_thickness, True, True, doc.ModelAbsoluteTolerance
                    )
                    if offset_result:
                        attrs = rdo.ObjectAttributes()
                        attrs.Name = "BottomBody"
                        layer_idx = doc.Layers.FindByFullPath("3DShoemaker::Bottom", -1)
                        if layer_idx >= 0:
                            attrs.LayerIndex = layer_idx

                        for brep in offset_result:
                            guid = doc.Objects.AddBrep(brep, attrs)
                            if guid != System.Guid.Empty:
                                self.parameters["BodyMainID"] = guid

    def DesignBodyForSoles(self):
        """Creates body geometry for separate sole components."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        Rhino.RhinoApp.WriteLine("Designing sole body...")

    def DesignBodyForShoes(self):
        """Creates body geometry for complete shoe bottoms."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        self.DesignBodyForBottoms()
        self.DesignBodyForSoles()
        Rhino.RhinoApp.WriteLine("Shoe bottom body design complete.")

    def to_json(self):
        """Serializes bottom parameters to JSON-compatible dict."""
        result = {}
        for key, value in self.parameters.items():
            if isinstance(value, (int, float, str, bool, type(None))):
                result[key] = value
            elif isinstance(value, System.Guid):
                result[key] = str(value)
        return result

    @staticmethod
    def from_json(data):
        """Creates Bottom from JSON data."""
        bottom = Bottom()
        if isinstance(data, dict):
            for key, value in data.items():
                if key in bottom.parameters:
                    bottom.parameters[key] = value
        return bottom
