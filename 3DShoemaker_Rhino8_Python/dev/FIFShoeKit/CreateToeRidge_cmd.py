# -*- coding: utf-8 -*-
"""Create a toe ridge

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateToeRidge"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateToeRidge invoked.")
    Rhino.RhinoApp.WriteLine("  Create a toe ridge")
    return 0
