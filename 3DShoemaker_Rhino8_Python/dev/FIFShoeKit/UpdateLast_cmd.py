# -*- coding: utf-8 -*-
"""Update the current last geometry

Feet in Focus Shoe Kit command wrapper.
This file is required by Rhino's plugin installer to register the command.
"""

import Rhino
import Rhino.Commands

__commandname__ = "UpdateLast"


def RunCommand(is_interactive):
    """Run the UpdateLast command."""
    try:
        from plugin.commands.last_commands import UpdateLast
        cmd = UpdateLast()
        mode = Rhino.Commands.RunMode.Interactive if is_interactive else Rhino.Commands.RunMode.Scripted
        result = cmd.RunCommand(Rhino.RhinoDoc.ActiveDoc, mode)
        if hasattr(result, "value__"):
            return 0 if result == Rhino.Commands.Result.Success else 1
        return 0
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] UpdateLast: {0}".format(ex)
        )
        return 1
