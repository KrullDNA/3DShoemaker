# -*- coding: utf-8 -*-
"""Sculpt surfaces interactively

Feet in Focus Shoe Kit command wrapper.
This file is required by Rhino's plugin installer to register the command.
"""

import Rhino
import Rhino.Commands

__commandname__ = "Sculpt"


def RunCommand(is_interactive):
    """Run the Sculpt command."""
    try:
        from plugin.commands.editing_commands import Sculpt
        cmd = Sculpt()
        mode = Rhino.Commands.RunMode.Interactive if is_interactive else Rhino.Commands.RunMode.Scripted
        result = cmd.RunCommand(Rhino.RhinoDoc.ActiveDoc, mode)
        if hasattr(result, "value__"):
            return 0 if result == Rhino.Commands.Result.Success else 1
        return 0
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Sculpt: {0}".format(ex)
        )
        return 1
