# -*- coding: utf-8 -*-
"""Feet in Focus Shoe Kit - Bootstrap Command

This file enables the Rhino Installer Engine to recognize the plugin
as a valid Python plugin package. The actual commands (NewBuild,
ImportLast, CreateInsole, etc.) are registered as Rhino.Commands.Command
subclasses by __init__.py at load time.

Type any command name (e.g. NewBuild, ImportLast) in the Rhino command
line to use the plugin.
"""

import Rhino


__commandname__ = "FIFShoeKit"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Plugin is loaded. "
        "Type a command name (e.g. NewBuild, ImportLast, CreateInsole) to begin."
    )
    return 0
