"""
Foot data model for 3DShoemaker Rhino 8 plugin.
Represents foot scan data, measurements, and landmarks.
"""

import json
import os
import System
import Rhino
import Rhino.Geometry as rg
import Rhino.DocObjects as rdo
import rhinoscriptsyntax as rs
import math


class Foot:
    """
    Represents a foot model including scan data, measurements,
    and anatomical landmarks for use in last and insert design.
    """

    def __init__(self):
        self.parameters = {}
        self.geometry_ids = {}
        self.landmarks = {}
        self._init_parameters()

    def _init_parameters(self):
        """Initialize all foot parameters with defaults."""

        # Basic measurements
        measurement_params = {
            "FootLength": 0.0,
            "FootWidth": 0.0,
            "FootWidthPerp": 0.0,
            "HeelWidth": 0.0,
            "BallGirth": 0.0,
            "InstepGirth": 0.0,
            "WaistGirth": 0.0,
            "AnkleGirth": 0.0,
            "AnkleGirthAlt": 0.0,
            "ArchLength": 0.0,
            "ArchHeight": 0.0,
            "ArchWidth": 0.0,
            "ArchHeightAsRatioOfArchLength": 0.0,
            "HeelToBallLength": 0.0,
            "ToeLength": 0.0,
            "AverageMalleolusHeight": 0.0,
            "LateralHeight": 0.0,
            "MedialHeight": 0.0,
        }

        # Foot outline parameters
        outline_params = {
            "FootOutlineXY": System.Guid.Empty,
            "FootOutlineXYID": System.Guid.Empty,
            "FootOutlineLateral": None,
            "FootOutlineMedial": None,
            "FootOutlineToe": None,
            "FootOutlineHeel": None,
        }

        # 2D foot model parameters
        foot_2d_params = {
            "Foot2DModelID": System.Guid.Empty,
            "Foot2DOutlineID": System.Guid.Empty,
            "Foot2DPositioned": False,
            "Foot2DExpanded": False,
            "Foot2DPostureAdjusted": False,
        }

        # 3D foot model parameters
        foot_3d_params = {
            "Foot3DModelID": System.Guid.Empty,
            "Foot3DMeshID": System.Guid.Empty,
            "Foot3DSplitDorsalID": System.Guid.Empty,
            "Foot3DSplitPlantarID": System.Guid.Empty,
            "Foot3DOriented": False,
            "Foot3DPositioned": False,
            "Foot3DPostureAdjusted": False,
            "Foot3DMeasured": False,
        }

        # Landmark points
        landmark_params = {
            "LandmarkHeel": None,
            "LandmarkToe": None,
            "LandmarkBallLateral": None,
            "LandmarkBallMedial": None,
            "LandmarkArchHighPoint": None,
            "LandmarkAnkleLateral": None,
            "LandmarkAnkleMedial": None,
            "LandmarkInstep": None,
            "LandmarkMTP1": None,
            "LandmarkMTP5": None,
            "LandmarkNavicular": None,
            "LandmarkCalcaneus": None,
        }

        # Generic foot landmarks dictionary
        generic_landmarks = {
            "GenericFootLandmarks": {},
        }

        # Scan/import parameters
        scan_params = {
            "ScanFilePath": "",
            "ScanFileType": "",
            "ScanScale": 1.0,
            "ScanUnits": "mm",
            "AdjustForWeightBearingExpansion": False,
        }

        # Posture adjustment parameters
        posture_params = {
            "AnteriorArchLateral": None,
            "AnteriorArchLateralXY": None,
            "AnteriorArchLateralXYString": "",
            "AnteriorArchMedial": None,
            "AnteriorArchMedialXY": None,
            "AnteriorArchMedialXYString": "",
            "ArchLateral": None,
            "ArchLateralXY": None,
            "ArchLateralXYString": "",
            "ArchMedial": None,
            "ArchMedialXY": None,
            "ArchMedialXYString": "",
        }

        # Combine all parameters
        all_params = {}
        for d in [measurement_params, outline_params, foot_2d_params,
                   foot_3d_params, landmark_params, generic_landmarks,
                   scan_params, posture_params]:
            all_params.update(d)

        self.parameters = all_params

    def Clone(self):
        """Creates a deep copy of this Foot."""
        new_foot = Foot()
        new_foot.parameters = dict(self.parameters)
        new_foot.geometry_ids = dict(self.geometry_ids)
        new_foot.landmarks = dict(self.landmarks)
        return new_foot

    @staticmethod
    def Create():
        """Creates a new Foot with default parameters."""
        return Foot()

    def CollectFootParameters(self):
        """Collects all foot measurement parameters."""
        foot_params = {}
        measurement_keys = [
            "FootLength", "FootWidth", "FootWidthPerp", "HeelWidth",
            "BallGirth", "InstepGirth", "WaistGirth", "AnkleGirth",
            "ArchLength", "ArchHeight", "ArchWidth", "HeelToBallLength",
            "ToeLength", "AverageMalleolusHeight", "LateralHeight", "MedialHeight",
        ]
        for key in measurement_keys:
            if key in self.parameters:
                foot_params[key] = self.parameters[key]
        return foot_params

    def DeleteCurves(self):
        """Deletes all foot-related curves from the document."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        curve_ids = [v for k, v in self.geometry_ids.items()
                     if isinstance(v, System.Guid) and v != System.Guid.Empty]
        for guid in curve_ids:
            doc.Objects.Delete(guid, True)

    def CreateFootOutlineXY(self):
        """Creates a 2D foot outline in the XY plane from foot data."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return None

        foot_length = self.parameters.get("FootLength", 260.0)
        foot_width = self.parameters.get("FootWidth", 95.0)
        heel_width = self.parameters.get("HeelWidth", 60.0)

        if foot_length <= 0:
            Rhino.RhinoApp.WriteLine("Invalid foot length.")
            return None

        # Build approximate foot outline from key measurements
        heel_center = rg.Point3d(0, 0, 0)
        toe_point = rg.Point3d(0, foot_length, 0)
        ball_lateral = rg.Point3d(-foot_width / 2, foot_length * 0.62, 0)
        ball_medial = rg.Point3d(foot_width / 2, foot_length * 0.62, 0)
        heel_lateral = rg.Point3d(-heel_width / 2, 0, 0)
        heel_medial = rg.Point3d(heel_width / 2, 0, 0)
        waist_lateral = rg.Point3d(-foot_width * 0.38, foot_length * 0.35, 0)
        waist_medial = rg.Point3d(foot_width * 0.42, foot_length * 0.35, 0)
        midfoot_lateral = rg.Point3d(-foot_width * 0.42, foot_length * 0.48, 0)
        midfoot_medial = rg.Point3d(foot_width * 0.48, foot_length * 0.48, 0)
        toe_lateral = rg.Point3d(-foot_width * 0.35, foot_length * 0.88, 0)
        toe_medial = rg.Point3d(foot_width * 0.15, foot_length * 0.95, 0)

        points = [
            heel_center, heel_lateral, waist_lateral, midfoot_lateral,
            ball_lateral, toe_lateral, toe_point, toe_medial,
            ball_medial, midfoot_medial, waist_medial, heel_medial,
            heel_center,
        ]

        outline = rg.Curve.CreateInterpolatedCurve(
            points, 3, rg.CurveKnotStyle.ChordSquareRoot
        )

        if outline is not None:
            attrs = rdo.ObjectAttributes()
            attrs.Name = "FootOutlineXY"
            layer_idx = doc.Layers.FindByFullPath("3DShoemaker::Foot", -1)
            if layer_idx >= 0:
                attrs.LayerIndex = layer_idx

            guid = doc.Objects.AddCurve(outline, attrs)
            if guid != System.Guid.Empty:
                self.parameters["FootOutlineXYID"] = guid
                self.geometry_ids["FootOutlineXY"] = guid

            doc.Views.Redraw()
            return outline

        return None

    def Import2DFootModel(self, filepath):
        """Imports a 2D foot model from a file (typically a scanned outline)."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return False

        if not os.path.exists(filepath):
            Rhino.RhinoApp.WriteLine(f"File not found: {filepath}")
            return False

        ext = os.path.splitext(filepath)[1].lower()
        self.parameters["ScanFilePath"] = filepath
        self.parameters["ScanFileType"] = ext

        script = f'_-Import "{filepath}" _Enter'
        result = Rhino.RhinoApp.RunScript(script, False)

        if result:
            selected = doc.Objects.GetSelectedObjects(False, False)
            for obj in selected:
                if isinstance(obj.Geometry, rg.Curve):
                    self.parameters["Foot2DModelID"] = obj.Id
                    self.parameters["Foot2DOutlineID"] = obj.Id
                    self.geometry_ids["Foot2DModel"] = obj.Id
                    obj.Attributes.Name = "Foot2DModel"
                    obj.CommitChanges()
                    break

            self.Measure2DFoot()
            return True

        return False

    def Measure2DFoot(self):
        """Measures the 2D foot model to extract key dimensions."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        outline_id = self.parameters.get("Foot2DOutlineID", System.Guid.Empty)
        if outline_id == System.Guid.Empty:
            return

        obj = doc.Objects.FindId(outline_id)
        if obj is None or not isinstance(obj.Geometry, rg.Curve):
            return

        curve = obj.Geometry
        bbox = curve.GetBoundingBox(True)

        self.parameters["FootLength"] = bbox.Max.Y - bbox.Min.Y
        self.parameters["FootWidth"] = bbox.Max.X - bbox.Min.X

        length = curve.GetLength()
        Rhino.RhinoApp.WriteLine(f"2D Foot: Length={self.parameters['FootLength']:.1f}, Width={self.parameters['FootWidth']:.1f}")

    def Adjust2DFootPosture(self):
        """Adjusts the 2D foot model posture (rotation/alignment)."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        outline_id = self.parameters.get("Foot2DOutlineID", System.Guid.Empty)
        if outline_id == System.Guid.Empty:
            return

        obj = doc.Objects.FindId(outline_id)
        if obj is None:
            return

        curve = obj.Geometry
        if not isinstance(curve, rg.Curve):
            return

        bbox = curve.GetBoundingBox(True)
        center = bbox.Center

        # Align foot centerline with Y axis
        heel_pt = rg.Point3d(center.X, bbox.Min.Y, 0)
        toe_pt = rg.Point3d(center.X, bbox.Max.Y, 0)

        angle = math.atan2(toe_pt.X - heel_pt.X, toe_pt.Y - heel_pt.Y)
        if abs(angle) > 0.01:
            rotation = rg.Transform.Rotation(-angle, rg.Vector3d.ZAxis, center)
            doc.Objects.Transform(outline_id, rotation, True)

        self.parameters["Foot2DPostureAdjusted"] = True
        doc.Views.Redraw()

    def Position2DFoot(self):
        """Positions the 2D foot model at the origin."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        outline_id = self.parameters.get("Foot2DOutlineID", System.Guid.Empty)
        if outline_id == System.Guid.Empty:
            return

        obj = doc.Objects.FindId(outline_id)
        if obj is None:
            return

        bbox = obj.Geometry.GetBoundingBox(True)
        heel_center = rg.Point3d((bbox.Min.X + bbox.Max.X) / 2, bbox.Min.Y, 0)

        move = rg.Vector3d(-heel_center.X, -heel_center.Y, -heel_center.Z)
        doc.Objects.Transform(outline_id, rg.Transform.Translation(move), True)

        self.parameters["Foot2DPositioned"] = True
        doc.Views.Redraw()

    def Expand2D(self):
        """Expands the 2D foot outline for weight-bearing adjustment."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        outline_id = self.parameters.get("Foot2DOutlineID", System.Guid.Empty)
        if outline_id == System.Guid.Empty:
            return

        obj = doc.Objects.FindId(outline_id)
        if obj is None or not isinstance(obj.Geometry, rg.Curve):
            return

        curve = obj.Geometry
        expansion = 2.0  # mm

        offset_curves = curve.Offset(
            rg.Plane.WorldXY, expansion, doc.ModelAbsoluteTolerance,
            rg.CurveOffsetCornerStyle.Sharp
        )

        if offset_curves and len(offset_curves) > 0:
            doc.Objects.Replace(outline_id, offset_curves[0])
            self.parameters["Foot2DExpanded"] = True
            doc.Views.Redraw()

    def Import3DFootModel(self, filepath):
        """Imports a 3D foot scan from file (STL, OBJ, PLY)."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return False

        if not os.path.exists(filepath):
            Rhino.RhinoApp.WriteLine(f"File not found: {filepath}")
            return False

        ext = os.path.splitext(filepath)[1].lower()
        self.parameters["ScanFilePath"] = filepath
        self.parameters["ScanFileType"] = ext

        script = f'_-Import "{filepath}" _Enter'
        result = Rhino.RhinoApp.RunScript(script, False)

        if result:
            selected = list(doc.Objects.GetSelectedObjects(False, False))
            for obj in selected:
                if isinstance(obj.Geometry, rg.Mesh):
                    self.parameters["Foot3DModelID"] = obj.Id
                    self.parameters["Foot3DMeshID"] = obj.Id
                    self.geometry_ids["Foot3DModel"] = obj.Id
                    obj.Attributes.Name = "Foot3DModel"
                    obj.CommitChanges()

                    # Apply scale if needed
                    scale = self.parameters.get("ScanScale", 1.0)
                    if scale != 1.0:
                        xform = rg.Transform.Scale(rg.Point3d.Origin, scale)
                        doc.Objects.Transform(obj.Id, xform, True)

                    break

            doc.Views.Redraw()
            return True

        return False

    def SplitFoot(self):
        """Splits 3D foot model into dorsal and plantar halves."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        mesh_id = self.parameters.get("Foot3DMeshID", System.Guid.Empty)
        if mesh_id == System.Guid.Empty:
            return

        obj = doc.Objects.FindId(mesh_id)
        if obj is None or not isinstance(obj.Geometry, rg.Mesh):
            return

        mesh = obj.Geometry
        bbox = mesh.GetBoundingBox(True)
        center = bbox.Center

        # Split plane at roughly the midline height
        split_plane = rg.Plane(
            rg.Point3d(center.X, center.Y, center.Z),
            rg.Vector3d.ZAxis
        )

        # Use mesh split
        split_meshes = mesh.Split(split_plane)
        if split_meshes and len(split_meshes) >= 2:
            attrs_dorsal = rdo.ObjectAttributes()
            attrs_dorsal.Name = "Foot3DDorsal"
            dorsal_id = doc.Objects.AddMesh(split_meshes[0], attrs_dorsal)
            self.parameters["Foot3DSplitDorsalID"] = dorsal_id

            attrs_plantar = rdo.ObjectAttributes()
            attrs_plantar.Name = "Foot3DPlantar"
            plantar_id = doc.Objects.AddMesh(split_meshes[1], attrs_plantar)
            self.parameters["Foot3DSplitPlantarID"] = plantar_id

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Foot split into dorsal and plantar.")

    def Orient3DFoot(self):
        """Orients the 3D foot model to standard position."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        mesh_id = self.parameters.get("Foot3DMeshID", System.Guid.Empty)
        if mesh_id == System.Guid.Empty:
            return

        obj = doc.Objects.FindId(mesh_id)
        if obj is None:
            return

        bbox = obj.Geometry.GetBoundingBox(True)
        center = bbox.Center

        # Move to origin with heel at Y=0 and bottom at Z=0
        move = rg.Vector3d(-center.X, -bbox.Min.Y, -bbox.Min.Z)
        doc.Objects.Transform(mesh_id, rg.Transform.Translation(move), True)

        self.parameters["Foot3DOriented"] = True
        doc.Views.Redraw()

    def Measure3DFoot(self):
        """Measures the 3D foot model to extract key dimensions."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        mesh_id = self.parameters.get("Foot3DMeshID", System.Guid.Empty)
        if mesh_id == System.Guid.Empty:
            return

        obj = doc.Objects.FindId(mesh_id)
        if obj is None or not isinstance(obj.Geometry, rg.Mesh):
            return

        mesh = obj.Geometry
        bbox = mesh.GetBoundingBox(True)

        self.parameters["FootLength"] = bbox.Max.Y - bbox.Min.Y
        self.parameters["FootWidth"] = bbox.Max.X - bbox.Min.X

        # Estimate arch height
        center_x = (bbox.Min.X + bbox.Max.X) / 2
        arch_y = bbox.Min.Y + (bbox.Max.Y - bbox.Min.Y) * 0.4
        arch_ray = rg.Ray3d(
            rg.Point3d(center_x, arch_y, bbox.Min.Z - 10),
            rg.Vector3d.ZAxis
        )
        t = rg.Intersect.Intersection.MeshRay(mesh, arch_ray)
        if t >= 0:
            self.parameters["ArchHeight"] = t - 10

        self.parameters["Foot3DMeasured"] = True
        Rhino.RhinoApp.WriteLine(
            f"3D Foot: Length={self.parameters['FootLength']:.1f}, "
            f"Width={self.parameters['FootWidth']:.1f}"
        )

    def Adjust3DFootPosture(self):
        """Adjusts 3D foot posture for neutral alignment."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        mesh_id = self.parameters.get("Foot3DMeshID", System.Guid.Empty)
        if mesh_id == System.Guid.Empty:
            return

        self.parameters["Foot3DPostureAdjusted"] = True
        Rhino.RhinoApp.WriteLine("3D foot posture adjusted.")

    def Position3DFoot(self):
        """Positions the 3D foot model at standard location."""
        doc = Rhino.RhinoDoc.ActiveDoc
        if doc is None:
            return

        mesh_id = self.parameters.get("Foot3DMeshID", System.Guid.Empty)
        if mesh_id == System.Guid.Empty:
            return

        obj = doc.Objects.FindId(mesh_id)
        if obj is None:
            return

        bbox = obj.Geometry.GetBoundingBox(True)
        heel_center = rg.Point3d(
            (bbox.Min.X + bbox.Max.X) / 2,
            bbox.Min.Y,
            bbox.Min.Z
        )

        move = rg.Vector3d(-heel_center.X, -heel_center.Y, -heel_center.Z)
        doc.Objects.Transform(mesh_id, rg.Transform.Translation(move), True)

        self.parameters["Foot3DPositioned"] = True
        doc.Views.Redraw()

    def Write(self, filepath):
        """Writes foot data to a JSON file."""
        data = self.to_json()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        Rhino.RhinoApp.WriteLine(f"Foot data written to: {filepath}")

    def Read(self, filepath):
        """Reads foot data from a JSON file."""
        if not os.path.exists(filepath):
            Rhino.RhinoApp.WriteLine(f"File not found: {filepath}")
            return False

        with open(filepath, 'r') as f:
            data = json.load(f)

        if isinstance(data, dict):
            for key, value in data.items():
                if key in self.parameters:
                    self.parameters[key] = value

        Rhino.RhinoApp.WriteLine(f"Foot data read from: {filepath}")
        return True

    def to_json(self):
        """Serializes foot parameters to JSON-compatible dict."""
        result = {}
        for key, value in self.parameters.items():
            if isinstance(value, (int, float, str, bool, type(None))):
                result[key] = value
            elif isinstance(value, System.Guid):
                result[key] = str(value)
            elif isinstance(value, rg.Point3d):
                result[key] = {"X": value.X, "Y": value.Y, "Z": value.Z}
        return result

    @staticmethod
    def from_json(data):
        """Creates Foot from JSON data."""
        foot = Foot()
        if isinstance(data, dict):
            for key, value in data.items():
                if key in foot.parameters:
                    foot.parameters[key] = value
        return foot
