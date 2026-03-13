# -*- coding: utf-8 -*-
"""Create a generic component

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "MakeComponent"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] MakeComponent invoked.")
    Rhino.RhinoApp.WriteLine("  Create a generic component")
    return 0
