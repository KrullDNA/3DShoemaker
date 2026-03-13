# -*- coding: utf-8 -*-
"""Create a shoe tree

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateShoeTree"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateShoeTree invoked.")
    Rhino.RhinoApp.WriteLine("  Create a shoe tree")
    return 0
