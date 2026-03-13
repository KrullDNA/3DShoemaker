# -*- coding: utf-8 -*-
"""Export insert parameters to file

Feet in Focus Shoe Kit command wrapper.
This file is required by Rhino's plugin installer to register the command.
"""

import Rhino
import Rhino.Commands

__commandname__ = "ExportInsertParameters"


def RunCommand(is_interactive):
    """Run the ExportInsertParameters command."""
    try:
        from plugin.commands.export_commands import ExportInsertParameters
        cmd = ExportInsertParameters()
        mode = Rhino.Commands.RunMode.Interactive if is_interactive else Rhino.Commands.RunMode.Scripted
        result = cmd.RunCommand(Rhino.RhinoDoc.ActiveDoc, mode)
        if hasattr(result, "value__"):
            return 0 if result == Rhino.Commands.Result.Success else 1
        return 0
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] ExportInsertParameters: {0}".format(ex)
        )
        return 1
