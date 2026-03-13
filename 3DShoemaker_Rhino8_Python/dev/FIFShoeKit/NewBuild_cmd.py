# -*- coding: utf-8 -*-
"""Create a new shoe last build

Feet in Focus Shoe Kit command wrapper.
This file is required by Rhino's plugin installer to register the command.
"""

import Rhino
import Rhino.Commands

__commandname__ = "NewBuild"


def RunCommand(is_interactive):
    """Run the NewBuild command."""
    try:
        from plugin.commands.last_commands import NewBuild
        cmd = NewBuild()
        mode = Rhino.Commands.RunMode.Interactive if is_interactive else Rhino.Commands.RunMode.Scripted
        result = cmd.RunCommand(Rhino.RhinoDoc.ActiveDoc, mode)
        if hasattr(result, "value__"):
            return 0 if result == Rhino.Commands.Result.Success else 1
        return 0
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] NewBuild: {0}".format(ex)
        )
        return 1
