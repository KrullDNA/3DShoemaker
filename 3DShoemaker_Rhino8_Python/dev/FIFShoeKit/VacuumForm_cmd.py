# -*- coding: utf-8 -*-
"""Opens the vacuum forming preparation dialog.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import scriptcontext as sc
import System

__commandname__ = "VacuumForm"


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        # Prompt for vacuum form parameters
        go_opts = ric.GetOption()
        go_opts.SetCommandPrompt("Vacuum form options (Enter when done)")
        go_opts.AcceptNothing(True)

        opt_thickness = ric.OptionDouble(3.0, 0.5, 20.0)
        opt_draft = ric.OptionDouble(5.0, 0.0, 45.0)

        go_opts.AddOptionDouble("MaterialThickness", opt_thickness)
        go_opts.AddOptionDouble("DraftAngle", opt_draft)

        while True:
            res = go_opts.Get()
            if res == Rhino.Input.GetResult.Option:
                continue
            break

        # Select object
        go = ric.GetObject()
        go.SetCommandPrompt("Select object for vacuum forming")
        go.GeometryFilter = rdo.ObjectType.Brep | rdo.ObjectType.Mesh | rdo.ObjectType.SubD
        go.Get()
        if go.CommandResult() != rc.Result.Success:
            return go.CommandResult()

        geom = go.Object(0).Geometry()
        if geom is None:
            return rc.Result.Failure

        brep = None
        if isinstance(geom, rg.Brep):
            brep = geom
        elif isinstance(geom, rg.SubD):
            brep = geom.ToBrep(rg.SubDToBrepOptions())
        elif isinstance(geom, rg.Mesh):
            brep = rg.Brep.CreateFromMesh(geom, True)

        if brep is None:
            Rhino.RhinoApp.WriteLine("Could not process geometry.")
            return rc.Result.Failure

        thickness = opt_thickness.CurrentValue

        offset_brep = rg.Brep.CreateOffsetBrep(
            brep, thickness, True, True, 0.01
        )

        if offset_brep and len(offset_brep) > 0:
            attrs = rdo.ObjectAttributes()
            attrs.Name = "VacuumFormed"
            layer_idx = doc.Layers.FindByFullPath(
                "Feet in Focus Shoe Kit::VacuumForm", -1
            )
            if layer_idx >= 0:
                attrs.LayerIndex = layer_idx

            for b in offset_brep:
                if isinstance(b, rg.Brep):
                    doc.Objects.AddBrep(b, attrs)

            doc.Views.Redraw()
            Rhino.RhinoApp.WriteLine("Vacuum form shell created.")
            return rc.Result.Success
        else:
            Rhino.RhinoApp.WriteLine("Could not create offset shell.")
            return rc.Result.Failure

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error in vacuum form: {0}".format(e))
        return rc.Result.Failure
