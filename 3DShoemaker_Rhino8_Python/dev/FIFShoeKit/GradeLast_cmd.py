# -*- coding: utf-8 -*-
"""Grade the current last to a different size

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "GradeLast"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] GradeLast invoked.")
    Rhino.RhinoApp.WriteLine("  Grade the current last to a different size")
    return 0
