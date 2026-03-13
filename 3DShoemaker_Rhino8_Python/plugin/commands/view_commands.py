"""
View and display commands for Feet in Focus Shoe Kit Rhino 8 plugin.
Handles clipping planes, rendering, flattening, and print preparation.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input as ri
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import Rhino.Display as rd
import rhinoscriptsyntax as rs
import System
import math


class DrawClippingPlanes(Rhino.Commands.Command):
    """Creates clipping planes at cross-section locations on the last."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "DrawClippingPlanes"

    def RunCommand(self, doc, mode):
        try:
            from ..plugin_main import PodoCADPlugIn
            plugin = PodoCADPlugIn.Instance
            if plugin is None or plugin.last is None:
                Rhino.RhinoApp.WriteLine("No active last found. Create or import a last first.")
                return rc.Result.Failure

            last = plugin.last
            plane_locations = {
                "Ball": last.parameters.get("BallGirthLocalPlane"),
                "Instep": last.parameters.get("InstepGirthLocalPlane"),
                "Waist": last.parameters.get("WaistGirthLocalPlane"),
                "Waist2": last.parameters.get("Waist2GirthLocalPlane"),
                "Arch": last.parameters.get("ArchLocalPlane"),
                "Arch2": last.parameters.get("Arch2GirthLocalPlane"),
                "Heel": last.parameters.get("HeelGirthLocalPlane"),
            }

            layer_name = "Feet in Focus Shoe Kit::ClippingPlanes"
            layer_index = doc.Layers.FindByFullPath(layer_name, -1)
            if layer_index < 0:
                layer = rdo.Layer()
                layer.Name = "ClippingPlanes"
                parent_idx = doc.Layers.FindByFullPath("Feet in Focus Shoe Kit", -1)
                if parent_idx >= 0:
                    layer.ParentLayerId = doc.Layers[parent_idx].Id
                layer.Color = System.Drawing.Color.FromArgb(128, 128, 128)
                layer_index = doc.Layers.Add(layer)

            attrs = rdo.ObjectAttributes()
            attrs.LayerIndex = layer_index

            active_view = doc.Views.ActiveView
            if active_view is None:
                Rhino.RhinoApp.WriteLine("No active view found.")
                return rc.Result.Failure

            viewport = active_view.ActiveViewport
            bbox = rg.BoundingBox.Empty
            for obj in doc.Objects:
                if obj.Geometry is not None:
                    bbox.Union(obj.Geometry.GetBoundingBox(True))

            if not bbox.IsValid:
                bbox = rg.BoundingBox(rg.Point3d(-100, -100, -100), rg.Point3d(100, 100, 100))

            clip_size = bbox.Diagonal.Length * 0.5
            count = 0

            for name, plane_data in plane_locations.items():
                if plane_data is not None:
                    if isinstance(plane_data, rg.Plane):
                        plane = plane_data
                    else:
                        plane = rg.Plane.WorldXY
                        plane.Origin = rg.Point3d(0, 0, float(plane_data) if plane_data else 0)

                    clip_id = doc.Objects.AddClippingPlane(
                        plane, clip_size, clip_size, viewport.Id, attrs
                    )
                    if clip_id != System.Guid.Empty:
                        obj = doc.Objects.FindId(clip_id)
                        if obj is not None:
                            obj.Attributes.Name = f"CP_{name}"
                            obj.CommitChanges()
                        count += 1

            if count == 0:
                ball_plane = rg.Plane.WorldYZ
                ball_plane.Origin = rg.Point3d(0, 0, 0)
                doc.Objects.AddClippingPlane(
                    ball_plane, clip_size, clip_size, viewport.Id, attrs
                )
                count = 1

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(f"Created {count} clipping plane(s).")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error creating clipping planes: {e}")
            return rc.Result.Failure


class RenderComponents(Rhino.Commands.Command):
    """Renders footwear components with materials and lighting."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "RenderComponents"

    def RunCommand(self, doc, mode):
        try:
            component_materials = {
                "Last": System.Drawing.Color.FromArgb(200, 180, 160),
                "Insert": System.Drawing.Color.FromArgb(60, 60, 180),
                "Sole": System.Drawing.Color.FromArgb(40, 40, 40),
                "Heel": System.Drawing.Color.FromArgb(50, 50, 50),
                "ShankBoard": System.Drawing.Color.FromArgb(139, 90, 43),
                "TopPiece": System.Drawing.Color.FromArgb(80, 80, 80),
                "MetPad": System.Drawing.Color.FromArgb(100, 150, 200),
            }

            for layer_idx in range(doc.Layers.Count):
                layer = doc.Layers[layer_idx]
                layer_name = layer.Name
                for comp_name, color in component_materials.items():
                    if comp_name.lower() in layer_name.lower():
                        mat_index = doc.Materials.Add()
                        mat = doc.Materials[mat_index]
                        mat.DiffuseColor = color
                        mat.Shine = 0.3 * Rhino.DocObjects.Material.MaxShine
                        mat.Transparency = 0.0
                        mat.CommitChanges()

                        objs = doc.Objects.FindByLayer(layer)
                        if objs:
                            for obj in objs:
                                obj.Attributes.MaterialSource = rdo.ObjectMaterialSource.MaterialFromObject
                                obj.Attributes.MaterialIndex = mat_index
                                obj.CommitChanges()
                        break

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Render materials applied to components.")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error rendering components: {e}")
            return rc.Result.Failure


class FlattenInsert(Rhino.Commands.Command):
    """Flattens insert geometry to a 2D pattern."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "FlattenInsert"

    def _flatten_geometry(self, doc, geom, name):
        brep = None
        if isinstance(geom, rg.Brep):
            brep = geom
        elif isinstance(geom, rg.SubD):
            brep = geom.ToBrep(rg.SubDToBrepOptions())
        elif isinstance(geom, rg.Surface):
            brep = geom.ToBrep()

        if brep is None:
            return False

        mesh_list = rg.Mesh.CreateFromBrep(brep, rg.MeshingParameters.Default)
        if not mesh_list or len(mesh_list) == 0:
            return False

        combined = rg.Mesh()
        for m in mesh_list:
            combined.Append(m)

        bbox = combined.GetBoundingBox(True)

        flat_mesh = rg.Mesh()
        for i in range(combined.Vertices.Count):
            pt = combined.Vertices[i]
            flat_mesh.Vertices.Add(rg.Point3d(pt.X, pt.Y, 0))

        for i in range(combined.Faces.Count):
            face = combined.Faces[i]
            if face.IsQuad:
                flat_mesh.Faces.AddFace(face.A, face.B, face.C, face.D)
            else:
                flat_mesh.Faces.AddFace(face.A, face.B, face.C)

        flat_mesh.Normals.ComputeNormals()
        flat_mesh.Compact()

        offset = rg.Vector3d(bbox.Diagonal.X * 1.5, 0, 0)
        flat_mesh.Translate(offset)

        layer_index = doc.Layers.FindByFullPath("Feet in Focus Shoe Kit::Flattened", -1)
        if layer_index < 0:
            layer = rdo.Layer()
            layer.Name = "Flattened"
            parent_idx = doc.Layers.FindByFullPath("Feet in Focus Shoe Kit", -1)
            if parent_idx >= 0:
                layer.ParentLayerId = doc.Layers[parent_idx].Id
            layer_index = doc.Layers.Add(layer)

        attrs = rdo.ObjectAttributes()
        attrs.LayerIndex = layer_index
        attrs.Name = name

        outline_curves = flat_mesh.GetNakedEdges()
        if outline_curves:
            for curve in outline_curves:
                doc.Objects.AddCurve(curve, attrs)

        doc.Objects.AddMesh(flat_mesh, attrs)
        return True

    def RunCommand(self, doc, mode):
        try:
            go = ric.GetObject()
            go.SetCommandPrompt("Select insert surface to flatten")
            go.GeometryFilter = rdo.ObjectType.Surface | rdo.ObjectType.Brep | rdo.ObjectType.SubD
            go.Get()
            if go.CommandResult() != rc.Result.Success:
                return go.CommandResult()

            geom = go.Object(0).Geometry()
            if geom is None:
                return rc.Result.Failure

            if self._flatten_geometry(doc, geom, "FlattenedInsert"):
                doc.Views.Redraw()
                Rhino.RhinoApp.WriteLine("Insert flattened successfully.")
                return rc.Result.Success
            else:
                Rhino.RhinoApp.WriteLine("Could not flatten insert.")
                return rc.Result.Failure

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error flattening insert: {e}")
            return rc.Result.Failure


class FlattenSole(Rhino.Commands.Command):
    """Flattens sole geometry to a 2D pattern."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "FlattenSole"

    def RunCommand(self, doc, mode):
        try:
            go = ric.GetObject()
            go.SetCommandPrompt("Select sole surface to flatten")
            go.GeometryFilter = rdo.ObjectType.Surface | rdo.ObjectType.Brep | rdo.ObjectType.SubD
            go.Get()
            if go.CommandResult() != rc.Result.Success:
                return go.CommandResult()

            geom = go.Object(0).Geometry()
            if geom is None:
                return rc.Result.Failure

            flatten_cmd = FlattenInsert.Instance
            if flatten_cmd._flatten_geometry(doc, geom, "FlattenedSole"):
                doc.Views.Redraw()
                Rhino.RhinoApp.WriteLine("Sole flattened successfully.")
                return rc.Result.Success
            else:
                Rhino.RhinoApp.WriteLine("Could not flatten sole.")
                return rc.Result.Failure

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error flattening sole: {e}")
            return rc.Result.Failure


class FlattenBottomSides(Rhino.Commands.Command):
    """Flattens bottom side geometry to 2D patterns."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "FlattenBottomSides"

    def RunCommand(self, doc, mode):
        try:
            go = ric.GetObject()
            go.SetCommandPrompt("Select bottom side surfaces to flatten")
            go.GeometryFilter = rdo.ObjectType.Surface | rdo.ObjectType.Brep
            go.EnablePreSelect(True, True)
            go.GetMultiple(1, 0)
            if go.CommandResult() != rc.Result.Success:
                return go.CommandResult()

            count = 0
            flatten_cmd = FlattenInsert.Instance
            for i in range(go.ObjectCount):
                geom = go.Object(i).Geometry()
                if geom and flatten_cmd._flatten_geometry(doc, geom, f"FlattenedBottomSide_{i}"):
                    count += 1

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(f"Flattened {count} bottom side(s).")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error flattening bottom sides: {e}")
            return rc.Result.Failure


class PrintPrep(Rhino.Commands.Command):
    """Prepares model for 3D printing with shell creation and support generation."""

    _instance = None

    @classmethod
    @property
    def Instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def EnglishName(self):
        return "PrintPrep"

    def RunCommand(self, doc, mode):
        try:
            from ..forms.print_prep_form import PrintPrepForm

            form = PrintPrepForm()
            result = form.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

            if result is None or not form.accepted:
                return rc.Result.Cancel

            go = ric.GetObject()
            go.SetCommandPrompt("Select objects to prepare for printing")
            go.GeometryFilter = rdo.ObjectType.Brep | rdo.ObjectType.Mesh | rdo.ObjectType.SubD
            go.EnablePreSelect(True, True)
            go.GetMultiple(1, 0)
            if go.CommandResult() != rc.Result.Success:
                return go.CommandResult()

            shell_thickness = form.shell_thickness
            maximize_printable = form.maximize_printable_area
            post_process = form.for_post_processing

            layer_name = "Feet in Focus Shoe Kit::PrintPrep"
            layer_index = doc.Layers.FindByFullPath(layer_name, -1)
            if layer_index < 0:
                layer = rdo.Layer()
                layer.Name = "PrintPrep"
                parent_idx = doc.Layers.FindByFullPath("Feet in Focus Shoe Kit", -1)
                if parent_idx >= 0:
                    layer.ParentLayerId = doc.Layers[parent_idx].Id
                layer_index = doc.Layers.Add(layer)

            attrs = rdo.ObjectAttributes()
            attrs.LayerIndex = layer_index

            processed = 0
            for i in range(go.ObjectCount):
                geom = go.Object(i).Geometry()
                mesh = None
                if isinstance(geom, rg.Mesh):
                    mesh = geom.DuplicateMesh()
                elif isinstance(geom, rg.Brep):
                    mesh_list = rg.Mesh.CreateFromBrep(geom, rg.MeshingParameters.Default)
                    if mesh_list:
                        mesh = rg.Mesh()
                        for m in mesh_list:
                            mesh.Append(m)
                elif isinstance(geom, rg.SubD):
                    brep = geom.ToBrep(rg.SubDToBrepOptions())
                    if brep:
                        mesh_list = rg.Mesh.CreateFromBrep(brep, rg.MeshingParameters.Default)
                        if mesh_list:
                            mesh = rg.Mesh()
                            for m in mesh_list:
                                mesh.Append(m)

                if mesh is None:
                    continue

                mesh.Normals.ComputeNormals()
                mesh.Compact()
                mesh.FillHoles()

                if shell_thickness > 0:
                    offset_mesh = mesh.Offset(shell_thickness)
                    if offset_mesh:
                        mesh.Normals.Flip(True)
                        combined = rg.Mesh()
                        combined.Append(mesh)
                        combined.Append(offset_mesh)
                        mesh = combined

                if maximize_printable:
                    bbox = mesh.GetBoundingBox(True)
                    center = bbox.Center
                    move = rg.Vector3d(-center.X, -center.Y, -bbox.Min.Z)
                    mesh.Translate(move)
                    diagonal = bbox.Diagonal
                    if diagonal.X > diagonal.Y:
                        rotation = rg.Transform.Rotation(
                            math.pi / 2, rg.Vector3d.ZAxis, rg.Point3d.Origin
                        )
                        mesh.Transform(rotation)

                if post_process:
                    mesh.Compact()
                    mesh.Normals.ComputeNormals()
                    mesh.UnifyNormals()

                attrs.Name = f"PrintReady_{processed}"
                doc.Objects.AddMesh(mesh, attrs)
                processed += 1

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine(f"Prepared {processed} object(s) for printing.")
            return rc.Result.Success

        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error in print preparation: {e}")
            return rc.Result.Failure
